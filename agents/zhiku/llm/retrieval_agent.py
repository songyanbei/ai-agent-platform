"""
检索智能体 - 负责分析问题并执行多轮检索
"""
from openai import AsyncOpenAI
from typing import List, Dict, Any
import json
import asyncio
import uuid
import httpx

from config.settings import get_settings
from agents.zhiku.tools.knowledge_retrieval import AVAILABLE_TOOLS as KB_AVAILABLE_TOOLS, TOOL_FUNCTIONS as KB_TOOL_FUNCTIONS
from agents.zhiku.tools.web_search import AVAILABLE_TOOLS as WEB_AVAILABLE_TOOLS, TOOL_FUNCTIONS as WEB_TOOL_FUNCTIONS
from shared.utils.logger import setup_logger
from shared.utils.document_manager import Document, DocumentManager

logger = setup_logger("retrieval_agent")


class RetrievalAgent:
    """
    检索智能体
    
    职责:
    1. 分析用户问题
    2. 判断是否需要拆解为多个检索查询
    3. 多次调用 retrieve_knowledge 工具
    4. 收集并去重文档
    5. 返回文档列表
    """
    
    def __init__(self):
        settings = get_settings()
        
        # 配置超时设置
        timeout = httpx.Timeout(
            connect=60.0,  # 连接超时: 60秒
            read=300.0,    # 读取超时: 5分钟
            write=300.0,   # 写入超时: 5分钟
            pool=60.0      # 连接池超时: 60秒
        )
        
        # 初始化 DeepSeek 客户端
        self.client = AsyncOpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            timeout=timeout,
            max_retries=3  # 添加重试机制
        )
        self.model = settings.deepseek_model
        
        # 注册工具（合并知识库检索和网页搜索）
        self.tools = KB_AVAILABLE_TOOLS + WEB_AVAILABLE_TOOLS
        self.tool_functions = {**KB_TOOL_FUNCTIONS, **WEB_TOOL_FUNCTIONS}
        
        # 文档管理器
        self.doc_manager = DocumentManager()
        
        logger.info(f"检索智能体初始化完成,模型: {self.model}")
    
    async def retrieve(self, user_query: str, max_iterations: int = 5):
        """
        执行检索任务
        
        Args:
            user_query: 用户问题
            max_iterations: 最大工具调用轮数
            
        Yields:
            Dict: 事件
                - {"type": "tool_call_start", "tool": "retrieve_knowledge", "arguments": {...}}
                - {"type": "tool_call_end", "tool": "retrieve_knowledge", "result": {...}}
                - {"type": "retrieval_complete", "doc_manager": DocumentManager}
        """
        logger.info(f"🔍 检索智能体开始工作: {user_query}")
        
        # 专门的检索提示词
        system_prompt = """你是一个专业的检索助手。你的任务是为用户问题找到最相关的文档和最新信息。

**核心任务**:
- 分析用户问题,提取核心概念
- 根据问题类型选择合适的检索方式

**检索策略**:

1. **知识库检索** (retrieve_knowledge):
   - 用于查找专业知识、研报数据、技术文档
   - 适合需要引用权威来源的场景
   - 建议调用 2-3 次,使用不同关键词

2. **网页搜索** (web_search):
   - 用于获取最新新闻、动态或实时信息
   - 当知识库信息过时或不足时补充
   - 适合查找最新资讯、公开资料

**使用建议**:
- 如果问题涉及时效性（如"最新"、"近期"、"今年"），优先使用 web_search
- 如果问题需要专业知识或历史数据，优先使用 retrieve_knowledge
- 可以组合使用两种工具，先搜索知识库，再补充最新信息
- 每次使用不同的关键词组合，避免重复

**示例**:
用户问"人工智能在金融领域的最新应用"
- 调用1: retrieve_knowledge(query="人工智能 金融应用", top_k=5)
- 调用2: web_search(query="人工智能 金融 最新应用 2025", num_results=5)
- 调用3: retrieve_knowledge(query="AI 银行 风控 智能投顾", top_k=5)

**重要**:
- 检索完成后,直接停止(不需要生成答案)
- 充分利用两种检索工具的优势，为用户提供全面信息"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请为以下问题进行多角度检索:{user_query}"}
        ]
        
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"📍 检索第 {iteration} 轮")
            
            try:
                # 调用 DeepSeek
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.tools,
                    stream=False,  # 检索阶段不需要流式
                    temperature=0.3  # 降低温度,让检索更稳定
                )
                
                choice = response.choices[0]
                message = choice.message
                
                # 检查是否有工具调用
                if not message.tool_calls:
                    logger.info("✅ 检索智能体完成所有检索")
                    break
                
                # 记录助手消息
                messages.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in message.tool_calls
                    ]
                })
                
                # 执行工具调用
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"🔧 调用工具: {function_name}({json.dumps(arguments, ensure_ascii=False)})")
                    
                    # 通知前端:工具调用开始
                    yield {
                        "type": "tool_call_start",
                        "tool": function_name,
                        "arguments": arguments
                    }
                    
                    # 执行工具
                    if function_name in self.tool_functions:
                        result = await self.tool_functions[function_name](**arguments)
                        
                        # 收集文档
                        if result.get("success") and "results" in result:
                            for item in result["results"]:
                                doc = Document(
                                    content=item.get("content", ""),
                                    source=item.get("source", "Unknown"),
                                    knowledge_id=item.get("chunk_id"),
                                    metadata={
                                        "score": item.get("score"),
                                        "doc_id": item.get("doc_id"),
                                        "doc_url": item.get("doc_url"),
                                        "knowledge_base_id": item.get("knowledge_base_id"),
                                        "knowledge_base_name": item.get("knowledge_base_name")
                                    }
                                )
                                self.doc_manager.add_document(doc)
                            
                            logger.info(f"✅ 本次检索到 {len(result['results'])} 个文档,总计: {len(self.doc_manager.documents)}")
                    else:
                        result = {"success": False, "error": f"未知工具: {function_name}"}
                    
                    # 通知前端:工具调用结束
                    yield {
                        "type": "tool_call_end",
                        "tool": function_name,
                        "result": result
                    }
                    
                    # 添加工具结果到消息
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, ensure_ascii=False)
                    })
                
            except Exception as e:
                logger.error(f"❌ 检索过程出错: {e}", exc_info=True)
                break
        
        logger.info(f"🎉 检索完成,共收集 {len(self.doc_manager.documents)} 个唯一文档")
        
        # 返回文档管理器
        yield {
            "type": "retrieval_complete",
            "doc_manager": self.doc_manager
        }
    
    async def retrieve_with_plan_parallel(
        self, 
        retrieval_plan: List[Dict[str, Any]],
        max_queries_per_kb: int = 3
    ):
        """
        根据规划执行并行多知识库检索
        
        Args:
            retrieval_plan: 检索计划
            max_queries_per_kb: 每个知识库最大查询次数
            
        Yields:
            Dict: 事件
                - {"type": "kb_start", "kb_id": "...", "kb_name": "...", "task_id": "..."}
                - {"type": "query_start", "task_id": "...", "query": "...", "kb_name": "..."}
                - {"type": "query_end", "task_id": "...", "success": true, "doc_count": N}
                - {"type": "kb_end", "task_id": "...", "kb_name": "...", "total_docs": N}
                - {"type": "retrieval_complete", "doc_manager": DocumentManager}
        """
        logger.info(f"🔍 检索智能体开始并行检索,共 {len(retrieval_plan)} 个知识库")
        
        # 为每个知识库创建任务
        async def collect_kb_events(task_id, kb_id, kb_name, queries):
            """收集单个知识库的所有事件"""
            events = []
            async for event in self._retrieve_kb_async(task_id, kb_id, kb_name, queries):
                events.append(event)
            return events
        
        # 创建所有任务
        all_tasks = []
        for plan_item in retrieval_plan:
            kb_id = plan_item["knowledge_base_id"]
            kb_name = plan_item["knowledge_base_name"]
            queries = plan_item["queries"][:max_queries_per_kb]
            
            # 生成唯一任务ID
            task_id = str(uuid.uuid4())[:8]
            
            # 创建任务(注意:这里是协程,不是生成器)
            task = collect_kb_events(task_id, kb_id, kb_name, queries)
            all_tasks.append(task)
        
        # 并行执行所有知识库的检索
        logger.info(f"🚀 启动 {len(all_tasks)} 个并行检索任务")
        
        # 使用 asyncio.as_completed 来实时获取完成的任务
        for coro in asyncio.as_completed(all_tasks):
            events = await coro
            # 按顺序yield所有事件
            for event in events:
                yield event
        
        logger.info(f"🎉 并行检索完成,共收集 {len(self.doc_manager.documents)} 个唯一文档")
        
        # 返回文档管理器
        yield {
            "type": "retrieval_complete",
            "doc_manager": self.doc_manager
        }
    
    async def _retrieve_kb_async(
        self,
        task_id: str,
        kb_id: str,
        kb_name: str,
        queries: List[str]
    ):
        """
        异步检索单个知识库
        
        Args:
            task_id: 任务ID
            kb_id: 知识库ID
            kb_name: 知识库名称
            queries: 查询列表
            
        Yields:
            Dict: 事件
        """
        logger.info(f"[{task_id}] 开始检索知识库: {kb_name}")
        
        # 通知:知识库检索开始
        yield {
            "type": "kb_start",
            "task_id": task_id,
            "kb_id": kb_id,
            "kb_name": kb_name,
            "query_count": len(queries)
        }
        
        kb_doc_count = 0
        
        for query in queries:
            logger.info(f"[{task_id}] 执行查询: {query}")
            
            # 通知:查询开始
            yield {
                "type": "query_start",
                "task_id": task_id,
                "kb_name": kb_name,
                "query": query
            }
            
            try:
                # 执行检索
                arguments = {
                    "query": query,
                    "top_k": 5,
                    "knowledge_base_id": kb_id
                }
                
                result = await self.tool_functions["retrieve_knowledge"](**arguments)
                
                # 收集文档
                doc_count = 0
                doc_metadata = []  # 收集文档元数据
                if result.get("success") and "results" in result:
                    for item in result["results"]:
                        doc = Document(
                            content=item.get("content", ""),
                            source=item.get("source", "Unknown"),
                            knowledge_id=item.get("chunk_id"),
                            metadata={
                                "score": item.get("score"),
                                "doc_id": item.get("doc_id"),
                                "doc_url": item.get("doc_url"),
                                "knowledge_base_id": item.get("knowledge_base_id"),
                                "knowledge_base_name": item.get("knowledge_base_name")
                            }
                        )
                        self.doc_manager.add_document(doc)
                        doc_count += 1
                        
                        # 收集元数据用于前端展示
                        doc_metadata.append({
                            "title": item.get("source", "Unknown"),
                            "score": item.get("score", 0),
                            "chunk_id": item.get("chunk_id"),
                            "doc_id": item.get("doc_id")
                        })
                    
                    kb_doc_count += doc_count
                    logger.info(f"[{task_id}] ✅ 本次检索到 {doc_count} 个文档")
                
                # 通知:查询结束
                yield {
                    "type": "query_end",
                    "task_id": task_id,
                    "kb_name": kb_name,
                    "query": query,
                    "success": result.get("success", False),
                    "doc_count": doc_count,
                    "doc_metadata": [
                        {**meta, "file_id": meta.get("doc_id"), "file_name": meta.get("title")} 
                        for meta in doc_metadata
                    ]  # 添加文档元数据，并映射 file_id 和 file_name
                }
                
            except Exception as e:
                logger.error(f"[{task_id}] ❌ 查询失败: {e}", exc_info=True)
                
                # 通知:查询失败
                yield {
                    "type": "query_end",
                    "task_id": task_id,
                    "kb_name": kb_name,
                    "query": query,
                    "success": False,
                    "error": str(e),
                    "doc_count": 0
                }
        
        # 通知:知识库检索完成
        logger.info(f"[{task_id}] ✅ 知识库 {kb_name} 检索完成,共 {kb_doc_count} 个文档")
        yield {
            "type": "kb_end",
            "task_id": task_id,
            "kb_id": kb_id,
            "kb_name": kb_name,
            "total_docs": kb_doc_count
        }
    
    async def retrieve_with_plan(
        self, 
        retrieval_plan: List[Dict[str, Any]],
        max_iterations_per_kb: int = 3
    ):
        """
        根据规划执行多知识库检索(串行版本,保留用于兼容)
        
        Args:
            retrieval_plan: 检索计划
            max_iterations_per_kb: 每个知识库最大查询次数
            
        Yields:
            Dict: 事件
        """
        logger.info(f"🔍 检索智能体开始执行规划,共 {len(retrieval_plan)} 个知识库")
        
        for plan_item in retrieval_plan:
            kb_id = plan_item["knowledge_base_id"]
            kb_name = plan_item["knowledge_base_name"]
            queries = plan_item["queries"][:max_iterations_per_kb]
            
            logger.info(f"📍 切换到知识库: {kb_name} ({kb_id})")
            logger.info(f"   计划查询: {queries}")
            
            # 通知前端:切换知识库
            yield {
                "type": "kb_switch",
                "kb_id": kb_id,
                "kb_name": kb_name,
                "queries": queries
            }
            
            # 执行该知识库的所有查询
            for query in queries:
                logger.info(f"🔧 执行查询: {query}")
                
                # 构造工具调用参数
                arguments = {
                    "query": query,
                    "top_k": 5,
                    "knowledge_base_id": kb_id
                }
                
                # 通知前端:工具调用开始
                yield {
                    "type": "tool_call_start",
                    "tool": "retrieve_knowledge",
                    "arguments": arguments
                }
                
                # 执行检索
                try:
                    result = await self.tool_functions["retrieve_knowledge"](**arguments)
                    
                    # 收集文档
                    if result.get("success") and "results" in result:
                        for item in result["results"]:
                            doc = Document(
                                content=item.get("content", ""),
                                source=item.get("source", "Unknown"),
                                knowledge_id=item.get("chunk_id"),
                                metadata={
                                    "score": item.get("score"),
                                    "doc_id": item.get("doc_id"),
                                    "doc_url": item.get("doc_url"),
                                    "knowledge_base_id": item.get("knowledge_base_id"),
                                    "knowledge_base_name": item.get("knowledge_base_name")
                                }
                            )
                            self.doc_manager.add_document(doc)
                        
                        logger.info(f"✅ 本次检索到 {len(result['results'])} 个文档,总计: {len(self.doc_manager.documents)}")
                    
                    # 通知前端:工具调用结束
                    yield {
                        "type": "tool_call_end",
                        "tool": "retrieve_knowledge",
                        "result": result
                    }
                    
                except Exception as e:
                    logger.error(f"❌ 检索出错: {e}", exc_info=True)
                    error_result = {"success": False, "error": str(e)}
                    yield {
                        "type": "tool_call_end",
                        "tool": "retrieve_knowledge",
                        "result": error_result
                    }
        
        logger.info(f"🎉 多库检索完成,共收集 {len(self.doc_manager.documents)} 个唯一文档")
        
        # 返回文档管理器
        yield {
            "type": "retrieval_complete",
            "doc_manager": self.doc_manager
        }
