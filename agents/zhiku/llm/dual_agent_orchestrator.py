"""
三智能体协调器
协调规划智能体、检索智能体和总结智能体的工作流程
"""
from typing import AsyncGenerator, Dict, Any
import httpx

from agents.zhiku.llm.planning_agent import PlanningAgent
from agents.zhiku.llm.retrieval_agent import RetrievalAgent
from agents.zhiku.llm.summary_agent import SummaryAgent
from agents.zhiku.tools.web_search import TOOL_FUNCTIONS as WEB_TOOL_FUNCTIONS
from config.settings import get_settings
from shared.utils.logger import setup_logger

logger = setup_logger("triple_agent_orchestrator")

# 配置: 送入总结和返回参考文献的最大文档数
MAX_DOCS_FOR_SUMMARY = 5  # 可根据需要调整


class DualAgentOrchestrator:
    """
    三智能体协调器 (保持类名向后兼容)
    
    工作流程:
    1. 调用规划智能体 → 分析问题并制定检索计划
    2. 调用检索智能体 → 执行多库检索并收集文档
    3. 调用总结智能体 → 生成带引用的总结
    4. 返回参考文献列表
    """
    
    def __init__(self):
        self.planning_agent = PlanningAgent()
        self.retrieval_agent = RetrievalAgent()
        self.summary_agent = SummaryAgent()
        
        logger.info("🎯 三智能体协调器初始化完成")
    
    async def process(
        self,
        user_query: str
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        处理用户查询
        
        Args:
            user_query: 用户问题
            
        Yields:
            Dict: 事件流
                - {"type": "planning_start"}
                - {"type": "planning_end", "plan": {...}}
                - {"type": "retrieval_start"}
                - {"type": "kb_switch", "kb_id": "...", "kb_name": "..."}
                - {"type": "tool_call_start", ...}
                - {"type": "tool_call_end", ...}
                - {"type": "retrieval_end", "total": N}
                - {"type": "content", "content": "..."}
                - {"type": "references", "references": [...]}
                - {"type": "error", "error": "..."}
        """
        logger.info("=" * 60)
        logger.info(f"🚀 开始处理查询: {user_query}")
        logger.info("=" * 60)
        
        try:
            # ========================================
            # 阶段0: 规划智能体工作
            # ========================================
            logger.info("📍 阶段0: 制定检索计划")
            yield {"type": "planning_start"}
            
            # 获取知识库配置
            settings = get_settings()
            knowledge_bases = settings.get_knowledge_bases()
            logger.info(f"可用知识库: {[kb.name for kb in knowledge_bases]}")
            
            # 调用规划智能体
            plan = await self.planning_agent.plan(user_query, knowledge_bases)
            
            # 通知规划完成
            yield {
                "type": "planning_end",
                "plan": plan
            }

            # 记录是否包含网页搜索计划
            has_web_search = "web_search_plan" in plan
            if has_web_search:
                logger.info(f"📋 规划包含网页搜索任务")

            logger.info(f"✅ 规划完成: {plan.get('analysis', '')}")
            
            # ========================================
            # 阶段1: 检索智能体工作(并行检索)
            # ========================================
            logger.info("📍 阶段1: 并行检索")
            yield {"type": "retrieval_start"}
            
            # 调用检索智能体(并行模式)
            doc_manager = None
            retrieval_plan = plan.get("retrieval_plan", [])
            
            async for event in self.retrieval_agent.retrieve_with_plan_parallel(retrieval_plan):
                event_type = event.get("type")
                
                if event_type in ["kb_start", "query_start", "query_end", "kb_end"]:
                    # 转发并行检索事件
                    yield event
                
                elif event_type == "retrieval_complete":
                    # 检索完成,获取文档管理器
                    doc_manager = event["doc_manager"]
            
            # 检查是否成功获取文档
            if doc_manager is None:
                yield {
                    "type": "error",
                    "error": "检索过程未返回文档管理器"
                }
                return

            # 通知知识库检索完成
            doc_count = len(doc_manager.documents)
            logger.info(f"✅ 知识库检索完成,共 {doc_count} 个文档")

            # ========================================
            # 阶段1.5: 网页搜索（如果规划中包含）
            # ========================================
            if has_web_search:
                logger.info("📍 阶段1.5: 执行网页搜索")
                yield {"type": "web_search_start"}

                web_search_plan = plan.get("web_search_plan", [])

                for search_item in web_search_plan:
                    queries = search_item.get("queries", [])
                    reason = search_item.get("reason", "")

                    logger.info(f"🔍 网页搜索: {reason}")
                    logger.info(f"   查询列表: {queries}")

                    for query in queries:
                        try:
                            # 通知:网页搜索开始
                            yield {
                                "type": "web_search_query_start",
                                "query": query
                            }

                            # 执行网页搜索
                            result = await WEB_TOOL_FUNCTIONS["web_search"](query=query, num_results=5)

                            # 收集网页搜索结果（作为文档添加到管理器）
                            if result.get("success") and "results" in result:
                                from shared.utils.document_manager import Document

                                for item in result["results"]:
                                    # 将网页搜索结果转换为文档格式
                                    doc = Document(
                                        content=f"{item.get('title', '')}\n\n{item.get('snippet', '')}",
                                        source=item.get("source", "Web Search"),
                                        knowledge_id=None,  # 网页搜索没有知识库ID
                                        metadata={
                                            "url": item.get("url", ""),
                                            "search_query": query,
                                            "source_type": "web_search"
                                        }
                                    )
                                    doc_manager.add_document(doc)

                                logger.info(f"✅ 网页搜索 '{query}' 返回 {len(result['results'])} 个结果")

                            # 通知:网页搜索结束
                            yield {
                                "type": "web_search_query_end",
                                "query": query,
                                "result": result
                            }

                        except Exception as e:
                            logger.error(f"❌ 网页搜索 '{query}' 失败: {e}")
                            yield {
                                "type": "web_search_query_end",
                                "query": query,
                                "result": {"success": False, "error": str(e)}
                            }

                # 更新文档总数
                updated_doc_count = len(doc_manager.documents)
                web_search_added = updated_doc_count - doc_count

                logger.info(f"✅ 网页搜索完成,新增 {web_search_added} 个结果,总计 {updated_doc_count} 个文档")

                yield {
                    "type": "web_search_end",
                    "added_count": web_search_added,
                    "total": updated_doc_count
                }

                doc_count = updated_doc_count

            # 发送检索完成事件（包含知识库和网页搜索的总结果）
            yield {
                "type": "retrieval_end",
                "total": doc_count
            }
            
            # 如果没有文档,提前结束
            if doc_count == 0:
                yield {
                    "type": "content",
                    "content": "抱歉,没有找到相关文档。请尝试使用不同的关键词重新提问。"
                }
                return
            
            # ========================================
            # 统一文档处理:排序和分组
            # ========================================
            logger.info("📍 统一文档处理: 排序和准备参考文献")
            
            # 1. 对文档按相似度排序
            doc_manager.sort_documents(key="score", reverse=True)
            logger.info(f"✅ 文档已按分数排序")
            
            # 2. 提前生成参考文献(这会按doc_id分组)
            # 限制为前N个文档
            references = doc_manager.get_references(max_docs=MAX_DOCS_FOR_SUMMARY)
            logger.info(f"✅ 参考文献已生成: {len(references)} 篇文章 (使用前{MAX_DOCS_FOR_SUMMARY}个文档)")
            
            
            # ========================================
            # 阶段2: 返回参考文献（在总结前）
            # ========================================
            logger.info("📍 阶段2: 返回参考文献")
            
            # 使用之前生成的参考文献(已排序和分组)
            logger.info(f"📚 返回 {len(references)} 条参考文献")
            
            yield {
                "type": "references",
                "references": references
            }
            
            # ========================================
            # 阶段3: 总结智能体工作
            # ========================================
            logger.info("📍 阶段3: 生成总结")
            
            # 调用总结智能体(流式,限制文档数量)
            async for event in self.summary_agent.summarize(user_query, doc_manager, max_docs=MAX_DOCS_FOR_SUMMARY):
                yield event
            
            logger.info("=" * 60)
            logger.info("🎉 查询处理完成")
            logger.info("=" * 60)
        
        except Exception as e:
            logger.error(f"❌ 处理过程中出错: {e}", exc_info=True)
            yield {
                "type": "error",
                "error": str(e)
            }

