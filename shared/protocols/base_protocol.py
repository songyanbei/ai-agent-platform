"""
基础协议接口
所有消息协议的抽象基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseProtocol(ABC):
    """消息协议基类"""
    
    @abstractmethod
    def build_message(self, event_type: str, **kwargs) -> Dict[str, Any]:
        """
        构建消息
        
        Args:
            event_type: 事件类型
            **kwargs: 其他参数
            
        Returns:
            Dict: 消息字典
        """
        pass
