"""
AI 智能体平台 - 主入口
"""
import uvicorn
from config.settings import get_settings, validate_config
from shared.api.gateway import create_app
from shared.utils.logger import setup_logger

logger = setup_logger("main")


def main():
    """主函数"""
    # 验证配置
    if not validate_config():
        logger.error("❌ 配置验证失败，程序退出")
        return
    
    # 获取配置
    settings = get_settings()
    
    # 创建应用
    app = create_app()
    
    # 启动服务
    logger.info("=" * 60)
    logger.info("🚀 AI 智能体平台启动中...")
    logger.info(f"📍 服务地址: http://{settings.host}:{settings.port}")
    logger.info(f"📚 API 文档: http://{settings.host}:{settings.port}/docs")
    logger.info("=" * 60)
    
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
