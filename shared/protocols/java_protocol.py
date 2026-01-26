"""
Java 标准消息协议适配器
将内部事件转换为 Java 后端定义的标准格式
"""
from enum import Enum
from typing import Dict, Any, List, Optional
import json
import uuid


# ============================================================
# 枚举定义
# ============================================================

class JavaEventType(str, Enum):
    """Java 事件类型"""
    STREAM_THING = "STREAM_THINK"           # 思考过程流式输出
    STREAM_CONTENT = "STREAM_CONTENT"       # 正文内容流式输出
    PLAN_DECLARED = "PLAN_DECLARED"         # 声明规划
    PLAN_CHANGE = "PLAN_CHANGE"             # 规划变更
    INVOCATION_DECLARED = "INVOCATION_DECLARED"  # 声明调用
    INVOCATION_CHANGE = "INVOCATION_CHANGE"      # 调用变更
    ARTIFACT = "ARTIFACT"                   # 产物声明
    ARTIFACT_CHANGE = "ARTIFACT_CHANGE"     # 产物变更
    END = "END"                             # 结束


class StageStatus(str, Enum):
    """阶段状态"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ChangeType(str, Enum):
    """变更类型"""
    STATUS_CHANGE = "STATUS_CHANGE"
    CONTENT_APPEND = "CONTENT_APPEND"
    PLAN_CHANGE = "PLAN_CHANGE"


class InvocationType(str, Enum):
    """调用类型"""
    SEARCH = "search"
    THINK = "think"
    ANALYZE = "analyze"


# ============================================================
# Stage 定义
# ============================================================

class StageDefinition:
    """阶段定义"""
    PLANNING = {
        "stage_id": "planning",
        "stage_name": "问题分析与规划",
        "description": "分析用户问题并制定检索计划"
    }

    RETRIEVAL = {
        "stage_id": "retrieval",
        "stage_name": "知识库检索",
        "description": "并行检索多个知识库"
    }

    WEB_SEARCH = {
        "stage_id": "web_search",
        "stage_name": "网页搜索",
        "description": "从互联网搜索最新信息"
    }

    SUMMARY = {
        "stage_id": "summary",
        "stage_name": "生成总结报告",
        "description": "基于检索结果生成带引用的总结"
    }

    @classmethod
    def get_all_stages(cls, include_web_search: bool = False) -> List[Dict[str, str]]:
        """
        获取所有阶段定义

        Args:
            include_web_search: 是否包含网页搜索阶段

        Returns:
            List[Dict]: 阶段定义列表
        """
        stages = [
            {**cls.PLANNING, "status": StageStatus.PENDING.value},
            {**cls.RETRIEVAL, "status": StageStatus.PENDING.value},
        ]

        # 如果需要网页搜索，添加网页搜索阶段
        if include_web_search:
            stages.append({**cls.WEB_SEARCH, "status": StageStatus.PENDING.value})

        stages.append({**cls.SUMMARY, "status": StageStatus.PENDING.value})

        return stages


# ============================================================
# 基础消息构建器
# ============================================================

def build_java_message(
    event_type: JavaEventType,
    context: Dict[str, Any],
    messages: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    构建 Java 标准格式消息
    
    Args:
        event_type: 事件类型
        context: 上下文信息
        messages: 消息列表
        
    Returns:
        Dict: Java 标准格式消息
    """
    return {
        "event_type": event_type.value,
        "context": context,
        "messages": messages
    }


def build_context(
    mode: str = "plan-executor",
    stage_id: Optional[str] = None,
    invocation_id: Optional[str] = None,
    executor: Optional[str] = None
) -> Dict[str, Any]:
    """
    构建上下文对象
    
    Args:
        mode: 智能体模式
        stage_id: 阶段ID（可选）
        invocation_id: 调用ID（可选）
        executor: 执行器（可选）
        
    Returns:
        Dict: 上下文对象
    """
    context = {"mode": mode}
    
    if stage_id:
        context["stage_id"] = stage_id
    if invocation_id:
        context["invocation_id"] = invocation_id
    if executor:
        context["executor"] = executor
    
    return context


# ============================================================
# PLAN 相关消息构建器
# ============================================================

def build_plan_declared(include_web_search: bool = False) -> Dict[str, Any]:
    """
    构建规划声明消息

    Args:
        include_web_search: 是否包含网页搜索阶段

    Returns:
        Dict: PLAN_DECLARED 消息
    """
    return build_java_message(
        event_type=JavaEventType.PLAN_DECLARED,
        context=build_context(),
        messages=StageDefinition.get_all_stages(include_web_search=include_web_search)
    )


def build_plan_change_status(stage_id: str, status: StageStatus) -> Dict[str, Any]:
    """
    构建阶段状态变更消息
    
    Args:
        stage_id: 阶段ID
        status: 新状态
        
    Returns:
        Dict: PLAN_CHANGE 消息
    """
    return build_java_message(
        event_type=JavaEventType.PLAN_CHANGE,
        context=build_context(),
        messages=[{
            "change_type": ChangeType.STATUS_CHANGE.value,
            "stage_id": stage_id,
            "status": status.value
        }]
    )


# ============================================================
# STREAM 相关消息构建器
# ============================================================

def build_stream_thing(content: str) -> Dict[str, Any]:
    """
    构建思考过程流式消息
    
    Args:
        content: 思考内容
        
    Returns:
        Dict: STREAM_THING 消息
    """
    return build_java_message(
        event_type=JavaEventType.STREAM_THING,
        context=build_context(),
        messages=[{"content": content}]
    )


def build_stream_content(content: str) -> Dict[str, Any]:
    """
    构建正文流式消息
    
    Args:
        content: 正文内容
        
    Returns:
        Dict: STREAM_CONTENT 消息
    """
    return build_java_message(
        event_type=JavaEventType.STREAM_CONTENT,
        context=build_context(),
        messages=[{"content": content}]
    )


# ============================================================
# INVOCATION 相关消息构建器
# ============================================================

def build_invocation_declared(
    stage_id: str,
    invocation_id: str,
    name: str,
    invocation_type: InvocationType = InvocationType.SEARCH,
    executor: str = "retrieval-agent",
    content: str = ""
) -> Dict[str, Any]:
    """
    构建调用声明消息
    
    Args:
        stage_id: 阶段ID
        invocation_id: 调用ID
        name: 调用名称（显示给用户）
        invocation_type: 调用类型
        executor: 执行器
        content: 初始内容
        
    Returns:
        Dict: INVOCATION_DECLARED 消息
    """
    return build_java_message(
        event_type=JavaEventType.INVOCATION_DECLARED,
        context=build_context(
            stage_id=stage_id,
            invocation_id=invocation_id,
            executor=executor
        ),
        messages=[{
            "name": name,
            "invocation_type": invocation_type.value,
            "click_effect": "",
            "content": content
        }]
    )


def build_invocation_change_status(
    stage_id: str,
    invocation_id: str,
    status: StageStatus,
    executor: str = "retrieval-agent"
) -> Dict[str, Any]:
    """
    构建调用状态变更消息
    
    Args:
        stage_id: 阶段ID
        invocation_id: 调用ID
        status: 新状态
        executor: 执行器
        
    Returns:
        Dict: INVOCATION_CHANGE 消息
    """
    return build_java_message(
        event_type=JavaEventType.INVOCATION_CHANGE,
        context=build_context(
            stage_id=stage_id,
            invocation_id=invocation_id,
            executor=executor
        ),
        messages=[{
            "change_type": ChangeType.STATUS_CHANGE.value,
            "status": status.value
        }]
    )


def build_invocation_change_content(
    stage_id: str,
    invocation_id: str,
    content: str,
    executor: str = "retrieval-agent"
) -> Dict[str, Any]:
    """
    构建调用内容追加消息
    
    Args:
        stage_id: 阶段ID
        invocation_id: 调用ID
        content: 追加的内容
        executor: 执行器
        
    Returns:
        Dict: INVOCATION_CHANGE 消息
    """
    return build_java_message(
        event_type=JavaEventType.INVOCATION_CHANGE,
        context=build_context(
            stage_id=stage_id,
            invocation_id=invocation_id,
            executor=executor
        ),
        messages=[{
            "change_type": ChangeType.CONTENT_APPEND.value,
            "content": content
        }]
    )


def build_invocation_complete(
    stage_id: str,
    invocation_id: str,
    content: str,
    executor: str = "retrieval-agent"
) -> Dict[str, Any]:
    """
    构建调用完成消息（状态变更 + 内容追加）
    
    Args:
        stage_id: 阶段ID
        invocation_id: 调用ID
        content: 结果内容
        executor: 执行器
        
    Returns:
        Dict: INVOCATION_CHANGE 消息
    """
    return build_java_message(
        event_type=JavaEventType.INVOCATION_CHANGE,
        context=build_context(
            stage_id=stage_id,
            invocation_id=invocation_id,
            executor=executor
        ),
        messages=[
            {
                "change_type": ChangeType.STATUS_CHANGE.value,
                "status": StageStatus.COMPLETED.value
            },
            {
                "change_type": ChangeType.CONTENT_APPEND.value,
                "content": content
            }
        ]
    )


# ============================================================
# ARTIFACT 相关消息构建器
# ============================================================

def build_artifact(
    stage_id: str,
    artifact_id: str,
    artifact_name: str,
    artifact_type: str,
    content: str,
    source: str = "知识库检索",
    scope: str = "GLOBAL",
    data_type: str = "STRUCTURED"
) -> Dict[str, Any]:
    """
    构建产物消息（ARTIFACT）
    
    Args:
        stage_id: 阶段ID
        artifact_id: 产物ID
        artifact_name: 产物名称
        artifact_type: 产物类型
        content: 产物内容（可能是路径或直接内容）
        source: 来源
        scope: 作用域（STAGE | GLOBAL）
        data_type: 数据类型（FILE | STRUCTURED）
        
    Returns:
        Dict: ARTIFACT 消息
    """
    return build_java_message(
        event_type=JavaEventType.ARTIFACT,
        context={
            "mode": "plan-executor",
            "stage_id": stage_id
        },
        messages=[{
            "scope": scope,
            "source": source,
            "artifact_id": artifact_id,
            "artifact_name": artifact_name,
            "artifact_type": artifact_type,
            "content": content
        }]
    )


def build_artifact_change(
    stage_id: str,
    artifact_id: str,
    content: str,
    change_type: str = "CONTENT_APPEND",
    artifact_name: str = "",
    artifact_type: str = "",
    source: str = "",
    scope: str = "STAGE",
    data_type: str = "STRUCTURED"
) -> Dict[str, Any]:
    """
    构建产物变更消息
    
    Args:
        stage_id: 阶段ID
        artifact_id: 产物ID
        content: 追加的内容
        change_type: 变更类型（CONTENT_APPEND）
        artifact_name: 产物名称（可选）
        artifact_type: 产物类型（可选）
        source: 来源（可选）
        scope: 作用域（STAGE | GLOBAL）
        data_type: 数据类型（FILE | STRUCTURED）
        
    Returns:
        Dict: ARTIFACT_CHANGE 消息
    """
    message = {
        "scope": scope,
        "change_type": change_type,
        "data_type": data_type,
        "content": content
    }
    
    # 可选字段
    if source:
        message["source"] = source
    if artifact_name:
        message["artifact_name"] = artifact_name
    if artifact_type:
        message["artifact_type"] = artifact_type
    
    return build_java_message(
        event_type=JavaEventType.ARTIFACT_CHANGE,
        context={
            "mode": "plan-executor",
            "artifact_id": artifact_id,
            "stage_id": stage_id
        },
        messages=[message]
    )



# ============================================================
# END 消息构建器
# ============================================================

def build_end() -> Dict[str, Any]:
    """
    构建结束消息
    
    Returns:
        Dict: END 消息
    """
    return build_java_message(
        event_type=JavaEventType.END,
        context=build_context(),
        messages=[]
    )


# ============================================================
# 工具函数
# ============================================================

def generate_invocation_id(kb_name: str, query: str, task_id: str = "") -> str:
    """
    生成调用ID（确定性，保证同一查询的 DECLARED 和 CHANGE 使用相同ID）
    
    Args:
        kb_name: 知识库名称
        query: 查询内容
        task_id: 任务ID（可选，用于区分并行任务）
        
    Returns:
        str: 调用ID
    """
    import hashlib
    
    # 使用知识库名称、查询内容和任务ID的组合生成确定性哈希
    content = f"{kb_name}::{query}::{task_id}"
    hash_value = hashlib.md5(content.encode('utf-8')).hexdigest()[:8]
    
    # 生成可读的ID
    kb_short = kb_name[:10].replace(" ", "-")
    return f"inv-{kb_short}-{hash_value}"


def format_retrieval_result(result: Dict[str, Any]) -> str:
    """
    格式化检索结果为可读文本
    
    Args:
        result: 检索结果
        
    Returns:
        str: 格式化后的文本
    """
    if not result.get("success"):
        return f"检索失败: {result.get('error', 'Unknown error')}"
    
    count = result.get("count", 0)
    if count == 0:
        return "未检索到相关文档"
    
    # 简单列出文档标题
    docs = result.get("results", [])
    doc_list = [f"- {doc.get('source', 'Unknown')}" for doc in docs[:5]]
    
    summary = f"检索到 {count} 个文档片段"
    if doc_list:
        summary += ":\n" + "\n".join(doc_list)
    
    return summary
