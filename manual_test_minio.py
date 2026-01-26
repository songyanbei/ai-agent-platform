
import asyncio
import sys
import os
from minio.error import S3Error

# Ensure we can import from project root
sys.path.append(os.getcwd())

from agents.zhiku.tools.file_ops import write_file, minio_client, settings

async def test_minio_write():
    print("🚀 Starting MinIO Write Verification...")
    
    # Check if MinIO client is initialized
    if not minio_client:
        print("❌ MinIO Client failed to initialize. Please check logs and settings.")
        return

    session_id = "test_minio_session_001"
    content = "# MinIO Test Summary\n\nThis content is stored in MinIO."
    
    print(f"📍 Target Bucket: {settings.minio_bucket}")
    print(f"📍 Session ID: {session_id}")
    
    # Execute write
    result = await write_file(session_id, content)
    print(f"Tool Result: {result}")
    
    # Verification
    object_name = f"agent-summaries/{session_id}/summary.md"
    try:
        response = minio_client.get_object(settings.minio_bucket, object_name)
        read_content = response.read().decode('utf-8')
        response.close()
        
        if read_content == content:
            print(f"✅ Verification Successful: Content matches.")
            
            # Cleanup
            try:
                minio_client.remove_object(settings.minio_bucket, object_name)
                print("🧹 Cleanup successful.")
            except Exception as e:
                print(f"⚠️ Cleanup failed: {e}")
                
        else:
            print("❌ Verification Failed: Content mismatch.")
            print(f"Expected: {content}")
            print(f"Actual: {read_content}")
            
    except S3Error as err:
        print(f"❌ Verification Failed: S3 Error - {err}")
    except Exception as e:
        print(f"❌ Verification Failed: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(test_minio_write())
    except KeyboardInterrupt:
        pass
