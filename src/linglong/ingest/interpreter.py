"""LLM-based interpretation for ingest results — batch per dimension."""

import json
import logging
from typing import Any

import httpx

from linglong.core.config import get_config
from linglong.core.models import Entity

logger = logging.getLogger(__name__)

_INTERPRET_BATCH_PROMPT = """你是一位 AI 领域的资深分析师。对以下新闻条目逐条生成一句话解读。

要求：
- 中文，每条 30 字以内
- 点明核心价值和行业影响
- 按编号顺序返回

按以下 JSON 格式返回：
{{"items": [{{"index": 1, "interpretation": "解读"}}, ...]}}

只返回 JSON，不要其他内容。

新闻列表：
{items_text}"""

_TOP5_PROMPT = """你是一位 AI 领域的资深战略分析师。从以下新闻中选出今日最有价值的 5 条信息。

对每条信息，从 4 个维度生成分析：
- 公司层面：对公司/组织的战略意义
- 战略层面：对行业格局的影响
- 技术视角：技术层面的关键洞察
- 启示：对个人/投资/创业的启示

按以下 JSON 格式返回：
{{"top5": [{{"index": 1, "title": "标题", "dimensions": {{"company": "公司层面", "strategy": "战略层面", "technology": "技术视角", "insight": "启示"}}}}]}}

只返回 JSON，不要其他内容。

今日 AI 新闻（含解读）：
{items_text}"""


def _call_llm(system: str, user: str, max_tokens: int = 2000) -> str:
    """Call LLM via Anthropic Messages API on ZhiPu codingplan."""
    config = get_config()
    base_url = "https://open.bigmodel.cn/api/anthropic"
    api_key = config.composer.llm_api_key

    response = httpx.post(
        f"{base_url}/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "glm-5.1",
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data["content"][0]["text"].strip()


def interpret_dimension(
    entities: list[Entity],
    llm_config: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Batch-interpret all entities in one dimension via single LLM call.

    Returns list of {"title": ..., "interpretation": ...}.
    """
    if not entities:
        return []

    items_text = "\n".join(
        f"{i+1}. {_entity_title(e)} — {_entity_snippet(e)}"
        for i, e in enumerate(entities)
    )

    try:
        system = _INTERPRET_BATCH_PROMPT.format(items_text=items_text)
        response = _call_llm(system, items_text, max_tokens=2000)
        data = json.loads(response)
        interpretations = {item["index"]: item["interpretation"] for item in data.get("items", [])}
    except Exception as e:
        logger.warning("Batch interpretation failed: %s", e)
        interpretations = {}

    results: list[dict[str, str]] = []
    for i, entity in enumerate(entities):
        title = _entity_title(entity)
        results.append({
            "title": title,
            "interpretation": interpretations.get(i + 1, ""),
        })

    return results


def generate_top5(
    all_items: list[dict[str, str]],
    llm_config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Select Top 5 most valuable items and generate deep analysis.

    Args:
        all_items: list of {"title": ..., "interpretation": ..., "dimension": ...}

    Returns:
        Top 5 items with 4-perspective analysis.
    """
    if not all_items:
        return []

    items_text = "\n".join(
        f"{i+1}. [{item.get('dimension', '')}] {item['title']} — {item.get('interpretation', '')}"
        for i, item in enumerate(all_items)
    )

    try:
        system = _TOP5_PROMPT.format(items_text=items_text)
        response = _call_llm(system, items_text, max_tokens=3000)
        data = json.loads(response)
        return data.get("top5", [])
    except Exception as e:
        logger.warning("LLM Top5 generation failed: %s", e)
        return []


def _entity_title(entity: Entity) -> str:
    for line in entity.content.split("\n"):
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return entity.content[:80].strip()


def _entity_snippet(entity: Entity) -> str:
    lines = entity.content.split("\n")
    past_title = False
    parts: list[str] = []
    for line in lines:
        s = line.strip()
        if not past_title:
            if s.startswith("# "):
                past_title = True
            continue
        if s.startswith("[Source]") or s.startswith("["):
            break
        if s:
            parts.append(s)
    return " ".join(parts)[:300]
