"""OpenAI-compatible / Anthropic-compatible LLM 客户端

支持多种 API 格式：
- OpenAI Chat Completions（api.openai.com, deepseek 等）
- Anthropic Messages（含 /anthropic 的 base_url 自动切换）
"""

import logging
import os
import re
from typing import Any

import requests

from .base import LLMClient

logger = logging.getLogger(__name__)


class OpenAICompatibleClient(LLMClient):
    """OpenAI-compatible / Anthropic-compatible API 客户端"""

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.api_key = self._resolve_api_key(config)
        self.base_url = config.get("base_url", "https://api.openai.com").rstrip("/")
        self.timeout = config.get("timeout", 60)
        self._is_anthropic = "/anthropic" in self.base_url

    def _resolve_api_key(self, config: dict[str, Any]) -> str:
        """解析 API Key，支持环境变量引用"""
        raw = config.get("api_key", "")
        if raw.startswith("${") and raw.endswith("}"):
            env_var = raw[2:-1]
            value = os.environ.get(env_var, "")
            if not value:
                raise ValueError(f"环境变量 {env_var} 未设置")
            return value
        return raw

    def chat(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """调用 LLM API，自动选择 OpenAI 或 Anthropic 协议"""
        if self._is_anthropic:
            return self._chat_anthropic(messages, system, temperature, max_tokens)
        return self._chat_openai(messages, system, temperature, max_tokens)

    def _chat_openai(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """调用 OpenAI-compatible Chat Completions API"""
        if self.base_url.endswith("/chat/completions"):
            url = self.base_url
        elif re.search(r"/v\d+$", self.base_url):
            url = f"{self.base_url}/chat/completions"
        else:
            url = f"{self.base_url}/v1/chat/completions"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
        }

        if system:
            # 插入 system 消息到开头
            payload["messages"] = [{"role": "system", "content": system}] + messages

        logger.debug(f"LLM 请求: {url} model={self.model}")

        try:
            resp = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            if "choices" not in data or not data["choices"]:
                raise RuntimeError(f"LLM 返回异常: {data}")

            content = data["choices"][0].get("message", {}).get("content", "")
            usage = data.get("usage", {})
            logger.info(
                f"LLM 响应: prompt_tokens={usage.get('prompt_tokens')}, "
                f"completion_tokens={usage.get('completion_tokens')}, "
                f"model={self.model}"
            )
            return content.strip()

        except requests.HTTPError as e:
            logger.error(f"LLM HTTP 错误: {e.response.status_code} {e.response.text}")
            raise
        except Exception as e:
            logger.exception(f"LLM 调用失败: {e}")
            raise

    def _chat_anthropic(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """调用 Anthropic Messages API"""
        url = f"{self.base_url}/v1/messages"

        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
        }
        if system:
            payload["system"] = system
        if temperature is not None:
            payload["temperature"] = temperature
        elif self.temperature:
            payload["temperature"] = self.temperature

        logger.debug(f"LLM 请求 (anthropic): {url} model={self.model}")

        try:
            resp = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            content_blocks = data.get("content", [])
            content = "".join(
                b.get("text", "") for b in content_blocks if b.get("type") == "text"
            )
            usage = data.get("usage", {})
            logger.info(
                f"LLM 响应: input_tokens={usage.get('input_tokens')}, "
                f"output_tokens={usage.get('output_tokens')}, "
                f"model={self.model}"
            )
            return content.strip()

        except requests.HTTPError as e:
            logger.error(f"LLM HTTP 错误: {e.response.status_code} {e.response.text}")
            raise
        except Exception as e:
            logger.exception(f"LLM 调用失败: {e}")
            raise
