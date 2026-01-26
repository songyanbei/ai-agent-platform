
import asyncio
import json
import pytest
from unittest.mock import MagicMock, AsyncMock

# 模拟相关类和函数，避免依赖过于复杂
class MockEvent:
    def __init__(self, data):
        self.data = data
    
    def get(self, key, default=None):
        return self.data.get(key, default)
    
    def __getitem__(self, key):
        return self.data[key]

# 模拟 build_invocation_complete
def build_invocation_complete(stage_id, invocation_id, content, executor=None):
    return {
        "type": "INVOCATION_CHANGE",
        "stageId": stage_id,
        "invocationId": invocation_id,
        "status": "COMPLETED",
        "content": content,
        "executor": executor
    }

# 模拟 endpoints.py 中的逻辑片段 (提取关键逻辑进行测试)
async def process_web_search_event(event):
    query = event.get("query", "")
    result = event.get("result", {})
    invocation_id = "test-invocation-id"
    
    if result.get("success"):
        # 统一结果结构
        unified_results = []
        for item in result.get("results", []):
            unified_results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "source": item.get("source", ""),
                "doc_id": "",
                "doc_name": ""
            })

        content = json.dumps({
            "success": True,
            "res_count": result.get("count", 0),
            "results": unified_results,
            "type": "web_search"
        }, ensure_ascii=False)
    else:
        content = json.dumps({
            "success": False,
            "error": result.get("error", "Unknown")
        }, ensure_ascii=False)

    return build_invocation_complete(
        stage_id="web_search",
        invocation_id=invocation_id,
        content=content,
        executor="web-search-agent"
    )

# 模拟 retrieval_agent.py 中的逻辑片段
async def process_retrieval_event(event):
    # 这里模拟 retrieval_agent.py 中生成 query_end 事件的逻辑
    task_id = "test-task"
    kb_name = "test-kb"
    query = "test query"
    result = event.get("result", {})
    
    doc_count = 0
    doc_metadata = []
    
    if result.get("success") and "results" in result:
        for item in result["results"]:
            doc_count += 1
            doc_metadata.append({
                "title": item.get("source", "Unknown"),
                "score": item.get("score", 0),
                "chunk_id": item.get("chunk_id"),
                "doc_id": item.get("doc_id")
            })
            
    # 这是我们在 retrieval_agent.py 中添加的逻辑
    return {
        "type": "query_end",
        "task_id": task_id,
        "kb_name": kb_name,
        "query": query,
        "success": result.get("success", False),
        "doc_count": doc_count,
        "doc_metadata": [
            {**meta, "file_id": meta.get("doc_id"), "file_name": meta.get("title")} 
            for meta in doc_metadata
        ]
    }

@pytest.mark.asyncio
async def test_web_search_metadata():
    print("\nStarting Web Search Metadata Verification...")
    
    # 模拟网页搜索结果事件 (来自 dual_agent_orchestrator)
    web_event = {
        "type": "web_search_query_end",
        "query": "测试查询",
        "result": {
            "success": True,
            "count": 1,
            "results": [
                {
                    "title": "测试标题",
                    "url": "http://example.com/test",
                    "content": "这是一段测试摘要",
                    "source": "测试来源"
                }
            ]
        }
    }
    
    # 执行处理逻辑
    result = await process_web_search_event(web_event)
    
    # 验证结果
    parsed_content = json.loads(result["content"])
    print(f"Web Search Content: {json.dumps(parsed_content, ensure_ascii=False, indent=2)}")
    
    assert parsed_content["success"] is True
    assert "results" in parsed_content
    assert parsed_content["type"] == "web_search"
    assert "res_count" in parsed_content
    
    result_item = parsed_content["results"][0]
    assert "title" in result_item
    assert "url" in result_item
    assert "source" in result_item
    assert "doc_id" in result_item
    assert "doc_name" in result_item
    assert result_item["doc_id"] == ""
    assert result_item["doc_name"] == ""
    
    print("✅ Web Search Verification Passed!")

@pytest.mark.asyncio
async def test_retrieval_metadata():
    print("\nStarting Knowledge Retrieval Metadata Verification...")
    
    # 模拟工具返回结果
    tool_result = {
        "success": True,
        "results": [
            {
                "content": "文档内容",
                "source": "文件A.pdf",
                "score": 0.95,
                "chunk_id": "chunk-123",
                "doc_id": "file-abc",
                "doc_url": "http://oss/file-abc"
            }
        ]
    }
    
    # 执行处理逻辑 (retrieval_agent)
    event_payload = {"result": tool_result}
    retrieval_event = await process_retrieval_event(event_payload)
    
    # 模拟 endpoints.py 处理 query_end 的部分逻辑
    # 注意：这里我们手动模拟 endpoints.py 的转换逻辑来测试
    success = retrieval_event.get("success")
    doc_metadata = retrieval_event.get("doc_metadata")
    doc_count = retrieval_event.get("doc_count")
    
    if success:
        unified_results = []
        for doc in doc_metadata:
             unified_results.append({
                "title": doc.get("title", ""),
                "url": "",
                "source": "",
                "doc_id": doc.get("doc_id", ""),
                "doc_name": doc.get("title", "")
             })

        content = json.dumps({
            "success": True,
            "res_count": doc_count,
            "results": unified_results,
            "type": "knowledge_retrieval"
        }, ensure_ascii=False)
        
    # 验证 endpoints.py 生成的 content
    parsed_content = json.loads(content)
    print(f"Retrieval Content: {json.dumps(parsed_content, ensure_ascii=False, indent=2)}")
    
    assert parsed_content["success"] is True
    assert parsed_content["type"] == "knowledge_retrieval"
    assert "res_count" in parsed_content
    assert "results" in parsed_content
    
    result_item = parsed_content["results"][0]
    assert "title" in result_item
    assert "doc_id" in result_item
    assert "doc_name" in result_item
    assert "url" in result_item
    assert "source" in result_item
    assert result_item["url"] == ""
    assert result_item["source"] == ""
    assert result_item["doc_name"] == "文件A.pdf"
    
    print("✅ Knowledge Retrieval Verification Passed!")

if __name__ == "__main__":
    # 手动运行测试
    async def main():
        await test_web_search_metadata()
        await test_retrieval_metadata()
        
    asyncio.run(main())
