"""
知识库检索工具
封装智谱官方检索 API，提供给 DeepSeek Function Calling 使用
"""
import httpx
from typing import Dict, Any, List
import json

from config.settings import get_settings
from shared.utils.logger import setup_logger

logger = setup_logger("knowledge_retrieval_tool")


# ============================================================
# 工具定义（DeepSeek Function Calling Schema）
# ============================================================

KNOWLEDGE_RETRIEVAL_TOOL = {
    "type": "function",
    "function": {
        "name": "retrieve_knowledge",
        "description": """从知识库中检索相关的文档内容。

使用场景:
- 用户提出的问题需要引用专业知识、研报数据或技术文档时
- 需要查找特定主题的详细信息时
- 需要获取最新的行业分析或市场数据时

注意:
- 可以多次调用此工具来检索不同的关键词或角度
- 可以指定 knowledge_base_id 来检索特定知识库
- 查询内容应该具体明确,便于检索到相关文档
- 返回的文档会包含相似度分数,分数越高越相关""",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "要检索的查询内容,可以是关键词、问题或主题。建议使用简洁明确的表达,例如:'人工智能应用'、'金融科技趋势'等"
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回的文档数量,取值范围 1-20。默认为 5。如果需要更全面的信息可以设置为 10-20",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20
                },
                "knowledge_base_id": {
                    "type": "string",
                    "description": "可选:指定要检索的知识库ID。如果不指定,将使用默认知识库"
                }
            },
            "required": ["query"]
        }
    }
}


# ============================================================
# 工具执行函数
# ============================================================

async def retrieve_knowledge(query: str, top_k: int = 5, knowledge_base_id: str = None) -> Dict[str, Any]:
    """
    执行知识库检索
    
    Args:
        query: 检索查询内容
        top_k: 返回的文档数量（1-20）
        knowledge_base_id: 可选,指定知识库ID。如果不指定,使用默认知识库
        
    Returns:
        Dict: 检索结果，格式：
        {
            "success": True/False,
            "results": [
                {
                    "content": "文档内容",
                    "source": "文档名称",
                    "score": 0.95,
                    "knowledge_base_id": "kb_id",
                    "knowledge_base_name": "知识库名称"
                }
            ],
            "count": 5,
            "query": "原始查询"
        }
    """
    logger.info(f"[工具调用] retrieve_knowledge: query='{query}', top_k={top_k}, kb_id={knowledge_base_id}")
    
    try:
        settings = get_settings()
        
        # 确定使用哪个知识库
        if knowledge_base_id is None:
            # 使用默认知识库(向后兼容)
            kb_id = settings.zhipu_knowledge_id
            kb_name = "默认知识库"
            logger.info(f"[INFO] 使用默认知识库: {kb_id}")
        else:
            kb_id = knowledge_base_id
            # 尝试从配置中获取知识库名称
            kb_name = knowledge_base_id
            try:
                knowledge_bases = settings.get_knowledge_bases()
                for kb in knowledge_bases:
                    if kb.id == knowledge_base_id:
                        kb_name = kb.name
                        break
            except:
                pass
        
        # 智谱知识库检索 API 端点（官方）
        url = "https://open.bigmodel.cn/api/llm-application/open/knowledge/retrieve"
        
        # 请求头
        headers = {
            "Authorization": f"Bearer {settings.zhipu_api_key}",
            "Content-Type": "application/json"
        }
        
        # 请求体
        payload = {
            "query": query,
            "knowledge_ids": [kb_id],  # 使用指定的知识库ID
            "top_k": min(max(top_k, 1), 20),  # 限制在 1-20 范围内
            "recall_method": "mixed",  # 混合检索（向量+关键词）
            "recall_ratio": 80,  # 向量检索权重 80%
            "rerank_status": 1,  # 启用重排
            "rerank_model": "rerank"  # 使用重排模型
        }
        
        logger.debug(f"[DEBUG] 请求 URL: {url}")
        logger.debug(f"[DEBUG] 请求 payload: {json.dumps(payload, ensure_ascii=False)}")
        
        # 发送请求
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            
            logger.debug(f"[DEBUG] 响应状态码: {response.status_code}")
            logger.debug(f"[DEBUG] 响应内容: {response.text[:500]}...")
            
            # 解析响应
            if response.status_code == 200:
                data = response.json()
                
                # 检查业务状态码
                if data.get("code") == 200:
                    results = []
                    
                    for item in data.get("data", []):
                        results.append({
                            "content": item.get("text", ""),
                            "source": item.get("metadata", {}).get("doc_name", "Unknown"),
                            "score": item.get("score", 0),
                            "chunk_id": item.get("metadata", {}).get("_id"),  # 切片ID（唯一）
                            "doc_id": item.get("metadata", {}).get("doc_id"),  # 文档ID（同一文章相同）
                            "doc_url": item.get("metadata", {}).get("doc_url"),
                            "knowledge_base_id": kb_id,  # 添加知识库ID
                            "knowledge_base_name": kb_name  # 添加知识库名称
                        })
                    
                    logger.info(f"[成功] 从知识库 '{kb_name}' 检索到 {len(results)} 个文档")
                    
                    return {
                        "success": True,
                        "results": results,
                        "count": len(results),
                        "query": query
                    }
                else:
                    # 业务错误
                    error_msg = data.get("message", "Unknown error")
                    logger.error(f"[失败] 业务错误: {error_msg}")
                    
                    return {
                        "success": False,
                        "error": f"检索失败: {error_msg}",
                        "query": query
                    }
            else:
                # HTTP 错误
                logger.error(f"[失败] HTTP 错误: {response.status_code} - {response.text}")
                
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}",
                    "query": query
                }
    
    except httpx.TimeoutException:
        logger.error(f"[失败] 请求超时")
        return {
            "success": False,
            "error": "请求超时，请稍后重试",
            "query": query
        }
    
    except Exception as e:
        logger.error(f"[失败] 异常: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"检索异常: {str(e)}",
            "query": query
        }


# ============================================================
# 工具函数映射（供 Orchestrator 使用）
# ============================================================

TOOL_FUNCTIONS = {
    "retrieve_knowledge": retrieve_knowledge
}


# ============================================================
# 工具列表（供 Orchestrator 注册）
# ============================================================

AVAILABLE_TOOLS = [
    KNOWLEDGE_RETRIEVAL_TOOL
]
