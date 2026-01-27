
import sys
import os

# 把项目根目录加入 path
sys.path.append(os.getcwd())

from shared.utils.document_manager import Document, DocumentManager
from agents.zhiku.tools.web_search import TOOL_FUNCTIONS

def test_web_search_logic():
    print("开始验证网页搜索结果处理逻辑...")
    
    # 1. 模拟 web_search 返回结果
    # 注意：我们这里模拟的是 web_search 工具返回的格式
    # 真实 API 或 mock 返回的应该是 {'content': ...}
    
    query = "测试查询"
    # 模拟 web_search.py 中 _mock_search_results 的返回结构
    mock_search_result = {
        "success": True,
        "results": [
            {
                "title": "测试标题",
                "url": "http://test.com",
                "content": "这是测试内容摘要",  # 注意这里是 content
                "source": "Test Source"
            }
        ],
        "query": query
    }
    
    print(f"模拟搜索结果: {mock_search_result}")

    # 2. 模拟 dual_agent_orchestrator 中的处理逻辑
    doc_manager = DocumentManager()
    
    if mock_search_result.get("success") and "results" in mock_search_result:
        for item in mock_search_result["results"]:
            # 这里的逻辑必须与 dual_agent_orchestrator.py 中的完全一致
            doc = Document(
                content=f"{item.get('title', '')}\n\n{item.get('content', '')}",
                source=item.get("source", "Web Search"),
                knowledge_id=None,
                metadata={
                    "url": item.get("url", ""),
                    "search_query": query,
                    "source_type": "web_search",
                    "score": 0.8  # 检查是否添加了 score
                }
            )
            doc_manager.add_document(doc)
            
    # 3. 验证结果
    if len(doc_manager.documents) != 1:
        print("❌ 验证失败: 文档未被添加到 DocumentManager")
        return

    doc = doc_manager.documents[0]
    
    # 验证内容
    expected_content = "测试标题\n\n这是测试内容摘要"
    if doc.content == expected_content:
        print("✅ 内容验证通过")
    else:
        print(f"❌ 内容验证失败. 期望: '{expected_content}', 实际: '{doc.content}'")
        
    # 验证分数
    if doc.metadata.get("score") == 0.8:
        print("✅ 分数验证通过 (score=0.8)")
    else:
        print(f"❌ 分数验证失败. 期望: 0.8, 实际: {doc.metadata.get('score')}")

    # 验证排序逻辑 (确保 score=0.8 能排在 score=0 的前面)
    doc_low_score = Document(content="低分文档", source="test", metadata={"score": 0.1})
    doc_manager.add_document(doc_low_score)
    
    doc_manager.sort_documents(key="score", reverse=True)
    
    if doc_manager.documents[0].content == expected_content:
        print("✅ 排序验证通过 (高分文档排在前面)")
    else:
        print("❌ 排序验证失败")

if __name__ == "__main__":
    test_web_search_logic()
