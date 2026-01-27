"""
网页搜索工具
提供互联网搜索能力，获取最新信息
"""
import httpx
from typing import Dict, Any, List
import json

from config.settings import get_settings
from shared.utils.logger import setup_logger

logger = setup_logger("web_search_tool")


# ============================================================
# 工具定义（DeepSeek Function Calling Schema）
# ============================================================

WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": """从互联网搜索最新的信息和资讯。

使用场景:
- 需要获取最新的新闻、动态或实时信息时
- 需要查找知识库中不存在的最新资料时
- 需要补充检索结果的时效性信息时
- 需要查找特定网站或公开资料时

注意:
- 搜索关键词应该准确明确,便于找到相关结果
- 可以多次调用此工具来搜索不同的关键词
- 返回的结果包含标题、摘要和链接
- 优先使用搜索引擎获取权威来源的信息""",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "要搜索的查询内容,可以是关键词、问题或主题。建议使用简洁明确的表达,例如:'人工智能最新进展'、'今日股市行情'等"
                },
                "num_results": {
                    "type": "integer",
                    "description": "返回的搜索结果数量,取值范围 1-10。默认为 5",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10
                }
            },
            "required": ["query"]
        }
    }
}


# ============================================================
# 工具执行函数
# ============================================================

async def web_search(query: str, num_results: int = 10) -> Dict[str, Any]:
    """
    执行网页搜索

    Args:
        query: 搜索查询内容
        num_results: 返回的结果数量（1-10）

    Returns:
        Dict: 搜索结果，格式：
        {
            "success": True/False,
            "results": [
                {
                    "title": "结果标题",
                    "url": "链接地址",
                    "snippet": "内容摘要",
                    "source": "来源网站"
                }
            ],
            "count": 5,
            "query": "原始查询"
        }
    """
    logger.info(f"[工具调用] web_search: query='{query}', num_results={num_results}")

    try:
        settings = get_settings()

        # 获取搜索 API 配置
        search_api_url = getattr(settings, 'search_api_url', None)
        search_api_key = getattr(settings, 'search_api_key', None)

        # 如果没有配置搜索 API，返回模拟数据
        if not search_api_url or not search_api_key:
            logger.warning("[WARNING] 搜索 API 未配置，返回模拟搜索结果")
            return _mock_search_results(query, num_results)

        # 实际的搜索 API 调用
        url = search_api_url
        headers = {
            "Authorization": f"Bearer {search_api_key}",
            "Content-Type": "application/json"
        }

        # payload = {
        #     "search_query": query,
        #     "search_engine": "search_pro_quark",
        #     "search_intent": False,
        #     "count": num_results,
        #     "search_domain_filter": "<string>",
        #     "search_recency_filter": "noLimit",
        #     "content_size": "medium",
        #     "request_id": "<string>",
        #     "user_id": "<string>"
        # }
        payload = {
                "query": query,
                "summary":  True,
                "freshness": "noLimit",
                "count": num_results
        }
        logger.info(payload)
        logger.info(headers)
        logger.info(f"[DEBUG] 搜索请求 URL: {url}")
        logger.debug(f"[DEBUG] 搜索请求 URL: {url}")
        logger.debug(f"[DEBUG] 搜索请求 payload: {json.dumps(payload, ensure_ascii=False)}")

        # 发送请求
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)

            logger.debug(f"[DEBUG] 搜索响应状态码: {response.status_code}")
            logger.debug(f"[DEBUG] 搜索响应内容: {response.text[:500]}...")

            # 解析响应
            if response.status_code == 200:
                api_response = response.json()

                results = []

                # 检查 API 响应的 code 字段
                if api_response.get("code") != 200:
                    logger.error(f"[失败] API 返回错误 code: {api_response.get('code')}, msg: {api_response.get('msg')}")
                    return {
                        "success": False,
                        "error": f"API 错误: {api_response.get('msg', 'Unknown error')}",
                        "query": query
                    }

                # 获取 data.webPages.value 中的搜索结果
                data = api_response.get("data", {})
                web_pages = data.get("webPages", {})
                search_results = web_pages.get("value", [])

                for item in search_results:
                    # 优先使用 summary，如果不存在则使用 snippet
                    content = item.get("summary") or item.get("snippet", "")
                    results.append({
                        "title": item.get("name", "Unknown Title"),
                        "url": item.get("url", ""),
                        "content": content,
                        "source": item.get("siteName", "")
                    })

                logger.info(f"[成功] 网页搜索到 {len(results)} 个结果")

                return {
                    "success": True,
                    "results": results,
                    "count": len(results),
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
        logger.error(f"[失败] 搜索请求超时")
        return {
            "success": False,
            "error": "搜索请求超时，请稍后重试",
            "query": query
        }

    except Exception as e:
        logger.error(f"[失败] 搜索异常: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"搜索异常: {str(e)}",
            "query": query
        }


def _mock_search_results(query: str, num_results: int) -> Dict[str, Any]:
    """
    生成模拟搜索结果（当 API 未配置时使用）

    Args:
        query: 搜索查询
        num_results: 结果数量

    Returns:
        Dict: 模拟搜索结果
    """
    mock_results = []

    for i in range(min(num_results, 5)):
        mock_results.append({
            "title": f"关于「{query}」的搜索结果 {i + 1}",
            "url": f"https://example.com/search/result-{i + 1}",
            "content": f"这是关于「{query}」的第 {i + 1} 条搜索结果摘要。请配置实际的搜索 API 以获取真实结果。",
            "source": "example.com"
        })

    logger.info(f"[模拟] 返回 {len(mock_results)} 条模拟搜索结果")

    return {
        "success": True,
        "results": mock_results,
        "count": len(mock_results),
        "query": query
    }


# ============================================================
# 工具函数映射（供 Orchestrator 使用）
# ============================================================

TOOL_FUNCTIONS = {
    "web_search": web_search
}


# ============================================================
# 工具列表（供 Orchestrator 注册）
# ============================================================

AVAILABLE_TOOLS = [
    WEB_SEARCH_TOOL
]
