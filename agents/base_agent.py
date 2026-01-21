"""
智能体基类接口
所有智能体的抽象基类
"""
from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """所有智能体的基类接口"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """智能体名称"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """智能体版本"""
        pass
    
    @abstractmethod
    async def process(self, query: str, **kwargs) -> Any:
        """
        处理用户查询
        
        Args:
            query: 用户查询
            **kwargs: 其他参数
            
        Returns:
            处理结果
        """
        pass
