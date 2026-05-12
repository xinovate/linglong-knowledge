"""LLM 客户端抽象基类

所有 LLM 提供商的统一接口。
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    """LLM 客户端抽象基类"""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.model = config.get("model", "")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 4096)

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """发送对话请求，返回文本内容

        Args:
            messages: 消息列表，每项为 {"role": "user"/"assistant", "content": "..."}
            system: 系统提示词
            temperature: 采样温度，None 使用默认值
            max_tokens: 最大 token 数，None 使用默认值

        Returns:
            str: LLM 返回的文本内容
        """
        pass

    def chat_with_system(
        self,
        user_content: str,
        system: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """快捷方法：单条用户消息 + 系统提示"""
        messages = [{"role": "user", "content": user_content}]
        return self.chat(
            messages,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
        )
