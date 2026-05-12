from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class PublishResult:
    """发布结果"""

    success: bool
    url: str = ""
    message: str = ""
    error: str = ""


class Publisher(ABC):
    """发布器抽象基类"""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.name = config.get("name", "unknown")

    @abstractmethod
    def publish(self, content: str, metadata: dict[str, Any]) -> PublishResult:
        """
        发布内容

        Args:
            content: 格式化后的内容
            metadata: 元数据

        Returns:
            PublishResult: 发布结果
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """检查发布渠道是否可用"""
        pass

    def format_info(self) -> str:
        """返回发布器信息"""
        return f"{self.name}: {self.__class__.__name__}"
