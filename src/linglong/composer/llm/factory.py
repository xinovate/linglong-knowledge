"""LLM 客户端工厂

根据配置创建对应的 LLMClient 实例。
"""

import logging
from typing import Any, Dict

from .base import LLMClient
from .openai_compatible_client import OpenAICompatibleClient

logger = logging.getLogger(__name__)

# 已知 provider 到 base_url 的映射
_DEFAULT_BASE_URLS = {
    "openai": "https://api.openai.com",
    "deepseek": "https://api.deepseek.com",
    "mimo": "https://token-plan-cn.xiaomimimo.com",
}


def create_llm_client(config: Dict[str, Any]) -> LLMClient:
    """根据配置创建 LLM 客户端

    Args:
        config: 配置字典，需包含 provider, api_key, model 等

    Returns:
        LLMClient: 对应提供商的客户端实例
    """
    provider = config.get("provider", "openai").lower()

    # 自动补全 base_url（如果配置中未指定）
    if "base_url" not in config and provider in _DEFAULT_BASE_URLS:
        config = dict(config)
        config["base_url"] = _DEFAULT_BASE_URLS[provider]

    logger.info(f"创建 LLM 客户端: provider={provider}, model={config.get('model')}")

    # 当前所有已知 provider 都走 OpenAI-compatible 协议
    # 未来如果有非兼容协议（如 Claude 原生 SDK），在此处分支
    if provider in ("openai", "deepseek", "mimo", "openai_compatible"):
        return OpenAICompatibleClient(config)

    # 默认兜底
    logger.warning(f"未知 provider '{provider}'，使用 OpenAI-compatible 客户端")
    return OpenAICompatibleClient(config)
