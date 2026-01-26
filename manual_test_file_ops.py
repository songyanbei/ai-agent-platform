
import asyncio
import os
import shutil
import sys

# 添加项目根目录到 sys.path，以便导入模块
sys.path.append(os.getcwd())

from agents.zhiku.tools.file_ops import write_file

async def test_write_file():
    session_id = "test_session_verification_001"
    content = """# 测试总结报告

## 概述
这是一个用于验证文件写入工具的测试文件。

## 内容
- 测试点1：目录创建
- 测试点2：文件写入
- 测试点3：编码正确性
"""
    
    print(f"🚀 开始测试 write_file 工具...")
    print(f"📍 Session ID: {session_id}")
    
    # 执行写入
    result = await write_file(session_id, content)
    print(f"工具返回: {result}")
    
    # 验证文件是否存在
    expected_path = f"storage/sessions/{session_id}/summary.md"
    if os.path.exists(expected_path):
        print(f"✅ 文件已创建: {expected_path}")
        
        # 验证内容
        with open(expected_path, 'r', encoding='utf-8') as f:
            read_content = f.read()
            if read_content == content:
                print("✅ 内容验证通过")
            else:
                print("❌ 内容不匹配")
                print("预期内容:", content[:50] + "...")
                print("实际内容:", read_content[:50] + "...")
    else:
        print(f"❌ 文件未找到: {expected_path}")

    # 清理
    try:
        if os.path.exists(f"storage/sessions/{session_id}"):
            shutil.rmtree(f"storage/sessions/{session_id}")
            print("🧹 测试数据清理完成")
    except Exception as e:
        print(f"⚠️ 清理失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_write_file())
