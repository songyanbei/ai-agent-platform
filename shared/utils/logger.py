"""
日志工具模块
提供统一的日志记录接口
"""
import logging
import sys
from typing import Optional


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    配置并返回 logger 实例
    
    Args:
        name: Logger 名称
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        
    Returns:
        logging.Logger: 配置好的 logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # 避免重复添加 handler
    if not logger.handlers:
        # 控制台输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        
        # 格式化
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
    
    return logger


# 全局 logger
app_logger = setup_logger("zhiku_agent")
