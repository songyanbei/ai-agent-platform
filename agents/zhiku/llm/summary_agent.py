"""
总结智能体 - 负责基于文档生成带引用的总结
"""
from openai import AsyncOpenAI
from typing import AsyncGenerator, Dict, Any
import json
import httpx

from config.settings import get_settings
from shared.utils.logger import setup_logger
from shared.utils.document_manager import DocumentManager

logger = setup_logger("summary_agent")


class SummaryAgent:
    """
    总结智能体
    
    职责：
    1. 接收已排序的文档
    2. 生成专业的带引用总结
    3. 流式输出内容
    4. 不调用任何工具，专注于内容生成
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
        
        logger.info(f"总结智能体初始化完成，模型: {self.model}")
    
    async def summarize(
        self,
        user_query: str,
        doc_manager: DocumentManager,
        max_docs: int = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        基于文档生成总结
        
        Args:
            user_query: 用户原始问题
            doc_manager: 文档管理器(包含所有检索到的文档)
            max_docs: 最多使用的文档数量,None表示使用全部
            
        Yields:
            Dict: 流式事件
                - {"type": "content", "content": "文本片段"}
                - {"type": "error", "error": "错误信息"}
        """
        logger.info(f"📝 总结智能体开始工作")
        logger.info(f"   文档数量: {len(doc_manager.documents)}")
        if max_docs:
            logger.info(f"   使用前 {max_docs} 个文档")
        
        # 文档已在协调器中排序,直接使用
        docs_to_use = doc_manager.documents[:max_docs] if max_docs else doc_manager.documents
        top_docs = [f"{doc.source}(score={doc.metadata.get('score', 0):.2f})" for doc in docs_to_use[:3]]
        logger.info(f"📄 前3个文档: {top_docs}")
        
        # 构建文档上下文(限制文档数量)
        context = doc_manager.get_context_for_llm(max_docs=max_docs)
        logger.info(f"📄 文档上下文长度: {len(context)} 字符")
        
        # 3. 构建总结提示词
        system_prompt = """你是一个专业的研报分析师。你的任务是基于提供的文档生成高质量的分析报告。

**核心要求**：
1. **必须使用引用**：在答案中用 [1]、[2] 等标注信息来源
2. **序号对应文档**：[1] 对应第1个文档，[2] 对应第2个文档，依此类推
3. **基于事实**：只使用文档中的信息，不编造内容
4. **专业严谨**：使用正式的学术/商业写作风格

**格式要求**：
- 使用 Markdown 格式
- 结构清晰，分点列出
- 每个要点都标注来源

**示例**：
根据文档内容，人工智能在金融领域的应用主要包括：

1. **风险控制**[1]：通过机器学习模型预测信用风险...
2. **智能投顾**[2]：利用深度学习技术提供个性化投资建议...
3. **反欺诈检测**[1][3]：结合多源数据识别异常交易行为...

## 参考来源
以上内容基于文档 [1] [2] [3] 的分析整理。"""

        user_message = f"""用户问题:{user_query}

以下是从知识库检索到的相关文档(已按相关性排序),共 {len(docs_to_use)} 个:

{context}

请基于以上文档内容,详细回答用户问题。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        logger.info("📤 发送请求到 DeepSeek 生成总结...")
        logger.debug(f"   消息数量: {len(messages)}")
        logger.debug(f"   [0] system: {len(system_prompt)} 字符")
        logger.debug(f"   [1] user: {len(user_message)} 字符")
        
        try:
            # 流式调用 DeepSeek（不使用工具）
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                temperature=0.7
            )
            
            # 收集完整内容
            full_content = ""

            # 流式输出
            async for chunk in response:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta

                if delta.content:
                    content = delta.content
                    full_content += content
                    yield {
                        "type": "content",
                        "content": content
                    }

            logger.info("✅ 总结生成完成")

            # 发送总结完成事件（包含完整内容）
            yield {
                "type": "summary_complete",
                "content": full_content
            }
        
        except Exception as e:
            logger.error(f"❌ 总结生成出错: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e)
            }
