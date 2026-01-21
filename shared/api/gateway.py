"""
API 网关
聚合所有智能体的路由
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agents.zhiku.api.endpoints import router as zhiku_router
from shared.utils.logger import setup_logger

logger = setup_logger("api_gateway")


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用
    
    Returns:
        FastAPI: 应用实例
    """
    app = FastAPI(
        title="AI 智能体平台",
        description="多智能体协作平台，提供知识检索、代码生成等服务",
        version="2.0.0"
    )
    
    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 注册智能体路由
    app.include_router(zhiku_router, tags=["知识检索智能体"])
    
    logger.info("✅ API 网关初始化完成")
    logger.info("📍 已注册路由: /api/v2/query (知识检索智能体)")
    
    return app
