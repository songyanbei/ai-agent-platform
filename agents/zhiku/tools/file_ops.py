import io
import logging
from typing import Dict, Callable, Any
from minio import Minio
from minio.error import S3Error

from config.settings import get_settings

# 设置 logger
logger = logging.getLogger("file_ops")

# 初始化 MinIO 客户端
settings = get_settings()
try:
#     minio_client = Minio(
#         settings.minio_endpoint,
#         access_key=settings.minio_access_key,
#         secret_key=settings.minio_secret_key,
#         secure=settings.minio_secure
#     )
#     logger.info(f"MinIO 客户端初始化完成: {settings.minio_endpoint}")
# except Exception as e:
#     logger.error(f"MinIO 客户端初始化失败: {e}")
#     minio_client = None

async def write_file(session_id: str, content: str) -> str:
    """
    将内容写入到 MinIO 存储中。
    文件路径: {bucket}/sessions/{session_id}/summary.md
    
    Args:
        session_id: 会话ID，用于区分存储路径
        content: 要写入的内容
        
    Returns:
        str: 操作结果消息
    """
    # if not minio_client:
    #     return "错误: MinIO 客户端未初始化，无法保存文件。"

    # bucket_name = settings.minio_bucket
    # object_name = f"{session_id}/summary.md"
    # logger.info(session_id)
    # try:
    #     # 1. 确保 Bucket 存在
    #     if not minio_client.bucket_exists(bucket_name):
    #         minio_client.make_bucket(bucket_name)
    #         logger.info(f"创建 Bucket: {bucket_name}")
            
    #     # 2. 准备数据流
    #     data = content.encode('utf-8')
    #     data_stream = io.BytesIO(data)
        
    #     # 3. 上传文件
    #     minio_client.put_object(
    #         bucket_name,
    #         object_name,
    #         data_stream,
    #         length=len(data),
    #         content_type="text/markdown"
    #     )
            
        logger.info(f"成功上传文件到 MinIO: {bucket_name}/{object_name}")
        return f"成功保存文件到 MinIO: {bucket_name}/{object_name}"
        
    except S3Error as e:
        error_msg = f"MinIO 操作失败: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"保存文件失败: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return error_msg

# 工具定义
AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "将总结内容保存到对象存储(MinIO)。必须在生成总结后调用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "会话ID，用于确定存储路径"
                    },
                    "content": {
                        "type": "string",
                        "description": "要保存的完整内容"
                    }
                },
                "required": ["session_id", "content"]
            }
        }
    }
]

# 工具函数映射
TOOL_FUNCTIONS: Dict[str, Callable] = {
    "write_file": write_file
}
