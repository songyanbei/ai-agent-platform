"""
配置管理模块
从 .env 文件加载配置项,并提供全局访问接口
"""
from pydantic import BaseModel
from pydantic_settings import BaseSettings
from typing import Optional, List
import os
import json


class KnowledgeBaseConfig(BaseModel):
    """知识库配置模型"""
    id: str                          # 知识库ID
    name: str                        # 显示名称
    description: str                 # 详细描述(供规划智能体理解)
    domain: str = "general"          # 领域标签(如:金融、科技、医疗)
    priority: int = 0                # 优先级(可选)


class Settings(BaseSettings):
    """应用配置类"""
    
    # 智谱 AI 配置
    zhipu_api_key: str
    zhipu_knowledge_id: str = "2010913086994870272"  # 兼容旧配置:默认知识库 ID
    
    # 多知识库配置(可选,JSON格式字符串或文件路径)
    knowledge_bases_json: Optional[str] = None
    knowledge_bases_file: str = "config/knowledge_bases.json"
    
    # DeepSeek 配置
    deepseek_api_key: str
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # 网页搜索配置
    search_api_url: Optional[str] = None
    search_api_key: Optional[str] = None
    
    # 日志配置
    log_level: str = "debug"
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000
    
    # 智能体注册表
    agents_config: str = "config/agents.yaml"
    
    # MinIO 配置
    minio_endpoint: str = "play.min.io:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "agent-summaries"
    minio_secure: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def get_knowledge_bases(self) -> List[KnowledgeBaseConfig]:
        """
        获取知识库列表
        
        优先级:
        1. KNOWLEDGE_BASES_JSON 环境变量
        2. knowledge_bases.json 文件
        3. 使用默认知识库(向后兼容)
        
        Returns:
            List[KnowledgeBaseConfig]: 知识库配置列表
        """
        # 方式1: 从环境变量加载
        if self.knowledge_bases_json:
            try:
                data = json.loads(self.knowledge_bases_json)
                return [KnowledgeBaseConfig(**kb) for kb in data]
            except Exception as e:
                print(f"[WARNING] 解析 KNOWLEDGE_BASES_JSON 失败: {e}")
        
        # 方式2: 从文件加载
        if os.path.exists(self.knowledge_bases_file):
            try:
                with open(self.knowledge_bases_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return [KnowledgeBaseConfig(**kb) for kb in data]
            except Exception as e:
                print(f"[WARNING] 加载 {self.knowledge_bases_file} 失败: {e}")
        
        # 方式3: 使用默认知识库(向后兼容)
        print(f"[INFO] 使用默认知识库配置: {self.zhipu_knowledge_id}")
        return [
            KnowledgeBaseConfig(
                id=self.zhipu_knowledge_id,
                name="默认知识库",
                description="默认知识库,包含各类文档和研报",
                domain="general",
                priority=1
            )
        ]



# 全局配置实例
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    获取全局配置实例（单例模式）
    
    Returns:
        Settings: 配置对象
        
    Raises:
        ValueError: 如果缺少必要的配置项
    """
    global _settings
    
    if _settings is None:
        try:
            _settings = Settings()
        except Exception as e:
            raise ValueError(
                f"配置加载失败: {e}\n"
                "请确保 .env 文件存在且包含所有必要的配置项。\n"
                "参考 .env.example 文件进行配置。"
            )
    
    return _settings


def validate_config() -> bool:
    """
    验证配置是否完整
    
    Returns:
        bool: 配置是否有效
    """
    try:
        settings = get_settings()
        
        # 检查必填项
        if not settings.zhipu_api_key or settings.zhipu_api_key == "your_zhipu_api_key_here":
            print("[ERROR] 错误: 请在 .env 文件中配置 ZHIPU_API_KEY")
            return False
            
        if not settings.deepseek_api_key or settings.deepseek_api_key == "your_deepseek_api_key_here":
            print("[ERROR] 错误: 请在 .env 文件中配置 DEEPSEEK_API_KEY")
            return False
        
        print("[OK] 配置验证通过")
        return True
        
    except Exception as e:
        print(f"[ERROR] 配置验证失败: {e}")
        return False


if __name__ == "__main__":
    # 测试配置加载
    validate_config()
