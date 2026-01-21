"""
API 端点 - 使用 Java 标准消息协议
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import asyncio

from shared.protocols.java_protocol import (
    build_plan_declared,
    build_plan_change_status,
    build_stream_thing,
    build_stream_content,
    build_invocation_declared,
    build_invocation_complete,
    build_artifact,
    build_artifact_change,
    build_end,
    StageStatus,
    InvocationType,
    generate_invocation_id,
    format_retrieval_result,
    JavaEventType,
    build_java_message,
    build_context
)
from agents.zhiku.llm.dual_agent_orchestrator import DualAgentOrchestrator
from shared.utils.logger import setup_logger

logger = setup_logger("v2_endpoints")

# 初始化三智能体协调器
orchestrator = DualAgentOrchestrator()

router = APIRouter()


class QueryRequest(BaseModel):
    """查询请求模型"""
    query: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "分析人工智能在金融行业的应用趋势"
            }
        }


@router.post("/api/v2/query")
async def query_with_tools(request: QueryRequest):
    """
    查询接口（v2 - Java 标准协议）
    
    **事件类型**：
    - PLAN_DECLARED: 声明所有阶段
    - PLAN_CHANGE: 阶段状态变更
    - STREAM_THING: 思考过程
    - INVOCATION_DECLARED: 查询开始
    - INVOCATION_CHANGE: 查询完成
    - STREAM_CONTENT: 正文流式输出
    - ARTIFACT: 参考文献
    - END: 结束
    """
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="查询内容不能为空")
    
    logger.info(f"[v2] 收到查询请求: {request.query}")

    async def generate_events(query: str):
        """生成 SSE 事件流"""
        try:
            plan_declared_sent = False  # 标记 PLAN_DECLARED 是否已发送

            # ========== 0. 模拟think ==========
            txt = "正在分析用户问题并制定检索计划..."
            for txti in txt:
                await asyncio.sleep(0.05)  # 使用异步 sleep，50ms 延迟
                msg = build_stream_thing(txti)
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"

            # ========== 1. 调用三智能体协调器 ==========
            async for event in orchestrator.process(query):
                event_type = event.get("type")
                
                # ========== 规划阶段 ==========
                if event_type == "planning_start":
                    # 规划阶段开始
                    msg = build_plan_change_status("planning", StageStatus.RUNNING)
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                    

                
                elif event_type == "planning_end":
                    # 规划完成
                    plan = event.get("plan", {})
                    analysis = plan.get("analysis", "")
                    has_web_search = "web_search_plan" in plan

                    # 如果还没有发送 PLAN_DECLARED，现在发送
                    if not plan_declared_sent:
                        # 根据是否需要网页搜索来决定包含哪些阶段
                        msg = build_plan_declared(include_web_search=has_web_search)
                        yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                        plan_declared_sent = True

                    # 可选：发送分析结果
                    msg = build_stream_thing(f"分析完成: {analysis}")
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"

                    # 规划阶段完成
                    msg = build_plan_change_status("planning", StageStatus.COMPLETED)
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                
                # ========== 检索阶段 ==========
                elif event_type == "retrieval_start":
                    # 检索阶段开始
                    msg = build_plan_change_status("retrieval", StageStatus.RUNNING)
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                
                elif event_type == "query_start":
                    # 单个查询开始
                    task_id = event.get("task_id", "")
                    kb_name = event.get("kb_name", "")
                    query_text = event.get("query", "")
                    
                    # 生成确定性的 invocation_id（使用 task_id 确保唯一性）
                    invocation_id = generate_invocation_id(kb_name, query_text, task_id)
                    
                    # 声明调用
                    msg = build_invocation_declared(
                        stage_id="retrieval",
                        invocation_id=invocation_id,
                        name=f"正在查询{kb_name}: {query_text[:30]}...",
                        invocation_type=InvocationType.SEARCH
                    )
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                
                elif event_type == "query_end":
                    # 单个查询完成
                    task_id = event.get("task_id", "")
                    kb_name = event.get("kb_name", "")
                    query_text = event.get("query", "")
                    success = event.get("success", False)
                    doc_count = event.get("doc_count", 0)
                    doc_metadata = event.get("doc_metadata", [])
                    
                    # 使用相同的参数生成 invocation_id（确保与 query_start 一致）
                    invocation_id = generate_invocation_id(kb_name, query_text, task_id)
                    
                    # 格式化结果内容为 JSON
                    if success and doc_metadata:
                        # 将文档元数据转换为 JSON 字符串
                        content = json.dumps({
                            "success": True,
                            "doc_count": doc_count,
                            "documents": doc_metadata
                        }, ensure_ascii=False)
                    elif success:
                        # 成功但没有文档
                        content = json.dumps({
                            "success": True,
                            "doc_count": 0,
                            "message": "未检索到相关文档"
                        }, ensure_ascii=False)
                    else:
                        # 失败
                        error = event.get("error", "Unknown")
                        content = json.dumps({
                            "success": False,
                            "error": error
                        }, ensure_ascii=False)
                    
                    # 调用完成
                    msg = build_invocation_complete(
                        stage_id="retrieval",
                        invocation_id=invocation_id,
                        content=content
                    )
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                
                elif event_type == "retrieval_end":
                    # 检索阶段完成
                    total = event.get("total", 0)

                    # 可选：发送总结信息
                    msg = build_stream_thing(f"知识库检索完成，共找到 {total} 个文档")
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"

                    # 检索阶段完成
                    msg = build_plan_change_status("retrieval", StageStatus.COMPLETED)
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"

                # ========== 网页搜索阶段 ==========
                elif event_type == "web_search_start":
                    # 网页搜索阶段开始
                    msg = build_plan_change_status("web_search", StageStatus.RUNNING)
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"

                elif event_type == "web_search_query_start":
                    # 单个网页搜索查询开始
                    query = event.get("query", "")

                    # 生成 invocation_id
                    invocation_id = generate_invocation_id("web_search", query, "web")

                    # 声明调用
                    msg = build_invocation_declared(
                        stage_id="web_search",
                        invocation_id=invocation_id,
                        name=f"网页搜索: {query[:30]}...",
                        invocation_type=InvocationType.SEARCH,
                        executor="web-search-agent"
                    )
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"

                elif event_type == "web_search_query_end":
                    # 单个网页搜索查询完成
                    query = event.get("query", "")
                    result = event.get("result", {})

                    # 生成 invocation_id（与 query_start 保持一致）
                    invocation_id = generate_invocation_id("web_search", query, "web")

                    # 格式化结果
                    if result.get("success"):
                        content = json.dumps({
                            "success": True,
                            "result_count": result.get("count", 0),
                            "query": query
                        }, ensure_ascii=False)
                    else:
                        content = json.dumps({
                            "success": False,
                            "error": result.get("error", "Unknown")
                        }, ensure_ascii=False)

                    # 调用完成
                    msg = build_invocation_complete(
                        stage_id="web_search",
                        invocation_id=invocation_id,
                        content=content,
                        executor="web-search-agent"
                    )
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"

                elif event_type == "web_search_end":
                    # 网页搜索阶段完成
                    added_count = event.get("added_count", 0)
                    total = event.get("total", 0)

                    # 可选：发送总结信息
                    msg = build_stream_thing(f"网页搜索完成，新增 {added_count} 个结果，总计 {total} 个文档")
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"

                    # 网页搜索阶段完成
                    msg = build_plan_change_status("web_search", StageStatus.COMPLETED)
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                
                
                # ========== 参考文献（在总结前） ==========
                elif event_type == "references":
                    # 参考文献
                    references = event.get("references", [])
                    
                    # 转换为 JSON 字符串
                    content = json.dumps(references, ensure_ascii=False)
                    
                    # 1. 先发送参考文献 ARTIFACT 声明（内容为空）
                    msg = build_artifact(
                        stage_id="summary",
                        artifact_id="references-001",
                        artifact_name="参考文献",
                        artifact_type="reference_list",
                        content="",  # 初始内容为空
                        source="知识库检索",
                        scope="STAGE",
                        data_type="STRUCTURED"
                    )
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                    
                    # 2. 再发送 ARTIFACT_CHANGE 包含实际内容
                    msg = build_artifact_change(
                        stage_id="summary",
                        artifact_id="references-001",
                        content=content,
                        change_type="CONTENT_APPEND",
                        artifact_name="参考文献",
                        artifact_type="reference_list",
                        source="知识库检索",
                        scope="STAGE",
                        data_type="STRUCTURED"
                    )
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                    
                    # 3. 发送总结阶段开始状态
                    msg = build_plan_change_status("summary", StageStatus.RUNNING)
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                
                # ========== 总结阶段 ==========
                elif event_type == "content":
                    # 第一个 content 事件时，发送 ARTIFACT 声明
                    if not hasattr(generate_events, "_summary_started"):
                        # 发送 ARTIFACT 声明
                        msg = build_artifact(
                            stage_id="summary",
                            artifact_id="summary-content-001",
                            artifact_name="总结报告",
                            artifact_type="summary_report",
                            content="",  # 初始内容为空
                            source="知识库检索",
                            scope="STAGE",
                            data_type="FILE"  # 修改为 FILE
                        )
                        yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                        generate_events._summary_started = True
                    
                    # 流式输出正文 - 使用 ARTIFACT_CHANGE
                    msg = build_artifact_change(
                        stage_id="summary",
                        artifact_id="summary-content-001",
                        content=event["content"],
                        change_type="CONTENT_APPEND",
                        scope="STAGE",
                        data_type="FILE"  # 修改为 FILE
                    )
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                
                
                # ========== 总结完成 ==========
                elif event_type == "summary_complete":
                    # 流式输出完整内容（逐字符）
                    content = event["content"]
                    for char in content:
                        await asyncio.sleep(0.03)  # 30ms 延迟
                        msg = build_stream_content(char)
                        yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"

                    # 总结阶段完成
                    msg = build_plan_change_status("summary", StageStatus.COMPLETED)
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"

                
                elif event_type == "error":
                    # 错误处理
                    error_msg = event.get("error", "Unknown error")
                    logger.error(f"处理过程出错: {error_msg}")
                    
                    # 发送错误信息
                    msg = build_stream_thing(f"❌ 错误: {error_msg}")
                    yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
            
            # ========== 3. 发送结束消息 ==========
            end_msg = build_end()
            yield f"data: {json.dumps(end_msg, ensure_ascii=False)}\n\n"
        
        except Exception as e:
            logger.error(f"事件生成出错: {e}", exc_info=True)
            
            # 发送错误消息
            error_msg = build_stream_thing(f"系统错误: {str(e)}")
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"
            
            # 发送结束消息
            end_msg = build_end()
            yield f"data: {json.dumps(end_msg, ensure_ascii=False)}\n\n"
    
    
    return StreamingResponse(
        generate_events(request.query),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲
            "Transfer-Encoding": "chunked"  # 明确使用分块传输
        }
    )


