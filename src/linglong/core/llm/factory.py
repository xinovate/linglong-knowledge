"""LLM 客户端工厂

根据配置创建对应的 LLMClient 实例。
"""

import logging
from typing import Any

from .base import LLMClient
from .openai_compatible_client import OpenAICompatibleClient

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com",
    "deepseek": "https://api.deepseek.com",
    "mimo": "https://token-plan-cn.xiaomimimo.com",
}


def create_llm_client(config: dict[str, Any]) -> LLMClient:
    """根据配置创建 LLM 客户端

    Args:
        config: 配置字典，需包含 provider, api_key, model 等

    Returns:
        LLMClient: 对应提供商的客户端实例
    """
    provider = config.get("provider", "openai").lower()

    if "base_url" not in config and provider in _DEFAULT_BASE_URLS:
        config = dict(config)
        config["base_url"] = _DEFAULT_BASE_URLS[provider]

    logger.info("Creating LLM client: provider=%s, model=%s", provider, config.get('model'))

    # All known providers use the OpenAI-compatible protocol
    # Branch here for non-compatible protocols (e.g. Claude native SDK) in the future
    if provider in ("openai", "deepseek", "mimo", "zhipu", "openai_compatible"):
        return OpenAICompatibleClient(config)

    logger.warning("Unknown provider '%s', falling back to OpenAI-compatible client", provider)
    return OpenAICompatibleClient(config)
