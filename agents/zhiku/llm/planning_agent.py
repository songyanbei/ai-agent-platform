"""
规划智能体 - 负责分析问题并规划检索策略
"""
from openai import AsyncOpenAI
from typing import List, Dict, Any
import json
import httpx
import time

from config.settings import get_settings, KnowledgeBaseConfig
from shared.utils.logger import setup_logger

logger = setup_logger("planning_agent")


class PlanningAgent:
    """
    规划智能体
    
    职责:
    1. 分析用户问题的核心意图
    2. 根据知识库描述选择最相关的知识库(1-N个)
    3. 为每个知识库生成优化的检索查询
    4. 输出结构化的检索计划
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
        
        logger.info(f"规划智能体初始化完成,模型: {self.model}")
    
    async def plan(
        self,
        user_query: str,
        knowledge_bases: List[KnowledgeBaseConfig]
    ) -> Dict[str, Any]:
        """
        为用户查询生成检索计划

        Args:
            user_query: 用户问题
            knowledge_bases: 可用的知识库列表

        Returns:
            Dict: 检索计划,格式:
            {
                "analysis": "用户想了解...",
                "retrieval_plan": [
                    {
                        "knowledge_base_id": "kb_001",
                        "knowledge_base_name": "金融研报库",
                        "queries": ["AI金融应用", "智能投顾"],
                        "reason": "该库包含金融科技相关研报"
                    }
                ],
                "web_search_plan": [
                    {
                        "queries": ["AI金融应用 最新", "2025年 金融科技趋势"],
                        "reason": "需要获取最新资讯"
                    }
                ]
            }
        """
        logger.info(f"🎯 规划智能体开始分析: {user_query}")
        
        # 如果只有一个知识库,直接返回简单计划(向后兼容)
        if len(knowledge_bases) == 1:
            kb = knowledge_bases[0]
            logger.info(f"只有一个知识库,跳过规划阶段: {kb.name}")

            # 检查是否需要网页搜索（简单的关键词匹配）
            need_web_search = self._should_use_web_search(user_query)

            plan = {
                "analysis": f"用户查询: {user_query}",
                "retrieval_plan": [
                    {
                        "knowledge_base_id": kb.id,
                        "knowledge_base_name": kb.name,
                        "queries": [user_query],  # 直接使用原始查询
                        "reason": "默认知识库"
                    }
                ]
            }

            # 如果需要网页搜索，添加网页搜索计划
            if need_web_search:
                plan["web_search_plan"] = [
                    {
                        "queries": [f"{user_query} 最新", f"{user_query} 2025"],
                        "reason": "问题涉及时效性，需要获取最新信息"
                    }
                ]

            return plan
        
        # 构建知识库描述
        kb_descriptions = []
        for kb in knowledge_bases:
            kb_descriptions.append(
                f"- **{kb.name}** (ID: {kb.id})\n"
                f"  领域: {kb.domain}\n"
                f"  描述: {kb.description}"
            )
        kb_info = "\n".join(kb_descriptions)
        
        # 规划提示词
        system_prompt = f"""你是一个专业的检索规划助手。你的任务是分析用户问题,并制定最优的检索策略。

**可用知识库**:
{kb_info}

**你的任务**:
1. 分析用户问题的核心意图和关键概念
2. 选择最相关的知识库(1-3个,避免全选)
3. 为每个知识库生成2-3个优化的检索查询
4. 判断是否需要网页搜索来获取最新信息
5. 输出JSON格式的检索计划

**何时使用网页搜索**:
- 问题包含"最新"、"近期"、"今年"、"最近"、"当前"等时效性关键词
- 问题涉及新闻、动态、实时数据
- 问题关于最新技术进展、市场趋势
- 知识库信息可能过时，需要补充最新资讯

**输出格式**:
{{
    "analysis": "简要分析用户问题的核心意图",
    "retrieval_plan": [
        {{
            "knowledge_base_id": "知识库ID",
            "knowledge_base_name": "知识库名称",
            "queries": ["查询1", "查询2"],
            "reason": "选择该知识库的理由"
        }}
    ],
    "web_search_plan": [
        {{
            "queries": ["搜索查询1", "搜索查询2"],
            "reason": "需要网页搜索的理由"
        }}
    ]
}}

注意:
- `web_search_plan` 是可选的，只有在确实需要时才包含
- 如果不需要网页搜索，不要在输出中包含 `web_search_plan` 字段

**重要原则**:
- 只选择真正相关的知识库,不要全选
- 每个查询应简洁明确,便于检索
- 从不同角度设计查询,提高覆盖率
- 如果问题跨领域,可以选择多个知识库
- 网页搜索用于获取知识库中可能缺失的最新信息

**示例1** (需要网页搜索):
用户问题: "人工智能在金融领域的最新应用"
输出:
{{
    "analysis": "用户想了解AI在金融领域的最新应用情况，需要专业知识+最新资讯",
    "retrieval_plan": [
        {{
            "knowledge_base_id": "kb_finance",
            "knowledge_base_name": "金融研报库",
            "queries": ["人工智能 金融应用", "AI银行", "智能投顾"],
            "reason": "该库包含金融行业的AI应用案例和趋势分析"
        }}
    ],
    "web_search_plan": [
        {{
            "queries": ["人工智能 金融 最新应用 2025", "AI 金融科技 最新进展"],
            "reason": "问题要求最新信息，需要搜索最新资讯"
        }}
    ]
}}

**示例2** (不需要网页搜索):
用户问题: "深度学习的基本原理"
输出:
{{
    "analysis": "用户想了解深度学习的基础知识，这是经典技术，知识库应该有足够资料",
    "retrieval_plan": [
        {{
            "knowledge_base_id": "kb_tech",
            "knowledge_base_name": "AI技术文档库",
            "queries": ["深度学习 基本原理", "神经网络 基础", "深度学习 模型"],
            "reason": "该库包含AI技术文档和教程"
        }}
    ]
}}

请直接输出JSON,不要包含其他内容。
 /no_think
"""

        try:
            # 调用 DeepSeek 生成规划
            start = time.time()
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"请为以下问题制定检索计划:\n{user_query}"}
                ],
                # temperature=0.3,  # 降低温度,让规划更稳定
                # response_format={"type": "json_object"}  # 强制JSON输出
            )
            
            # 解析响应
            content = response.choices[0].message.content
            plan = json.loads(content)

            # 记录是否包含网页搜索计划
            has_web_search = "web_search_plan" in plan
            logger.info(f"✅ 规划完成,选择了 {len(plan.get('retrieval_plan', []))} 个知识库, 网页搜索: {has_web_search}")
            logger.debug(f"规划详情: {json.dumps(plan, ensure_ascii=False, indent=2)}")
            end = time.time()
            logger.info(end-start)
            return plan
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ 解析规划结果失败: {e}")
            logger.error(f"原始响应: {content}")
            # 降级方案:使用所有知识库
            return self._fallback_plan(user_query, knowledge_bases)
        
        except Exception as e:
            logger.error(f"❌ 规划过程出错: {e}", exc_info=True)
            # 降级方案:使用所有知识库
            return self._fallback_plan(user_query, knowledge_bases)
    
    def _fallback_plan(
        self, 
        user_query: str, 
        knowledge_bases: List[KnowledgeBaseConfig]
    ) -> Dict[str, Any]:
        """
        降级方案:当规划失败时,使用所有知识库
        
        Args:
            user_query: 用户问题
            knowledge_bases: 知识库列表
            
        Returns:
            Dict: 简单的检索计划
        """
        logger.warning("使用降级方案:检索所有知识库")
        
        retrieval_plan = []
        for kb in knowledge_bases:
            retrieval_plan.append({
                "knowledge_base_id": kb.id,
                "knowledge_base_name": kb.name,
                "queries": [user_query],  # 直接使用原始查询
                "reason": "降级方案"
            })
        
        return {
            "analysis": f"用户查询: {user_query}",
            "retrieval_plan": retrieval_plan
        }

    def _should_use_web_search(self, query: str) -> bool:
        """
        判断是否需要使用网页搜索（简单关键词匹配）

        Args:
            query: 用户查询

        Returns:
            bool: 是否需要网页搜索
        """
        # 时效性关键词
        time_keywords = [
            "最新", "近期", "今年", "最近", "当前",
            "2024", "2025", "2026",  # 年份
            "新闻", "动态", "趋势", "进展"
        ]

        query_lower = query.lower()
        for keyword in time_keywords:
            if keyword in query_lower:
                logger.info(f"检测到时效性关键词 '{keyword}'，将启用网页搜索")
                return True

        return False
