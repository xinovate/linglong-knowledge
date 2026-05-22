"""AIHOT source adapter — free AI news aggregation service.

Supports two endpoints:
- /api/public/items?mode=selected — curated items with category
- /api/public/daily — daily digest organized by sections
"""

import logging
from typing import Any

import httpx

from linglong.core.models import Entity, EntityFacet, Source, SourceType
from linglong.ingest.adapter import SourceAdapter

logger = logging.getLogger(__name__)

_BASE_URL = "https://aihot.virxact.com"
_HEADERS = {
    "User-Agent": "Linglong/1.0 (AI Knowledge Hub)",
    "Accept": "application/json",
}


class AIHOTAdapter(SourceAdapter):
    """Adapter for AIHOT AI news aggregation API."""

    adapter_type = "aihot"

    async def fetch(self) -> list[Entity]:
        endpoint = self.config.get("endpoint", "items")
        if endpoint == "daily":
            return await self._fetch_daily()
        return await self._fetch_items()

    async def _fetch_items(self) -> list[Entity]:
        mode = self.config.get("mode", "selected")
        limit = self.config.get("limit", 30)
        category = self.config.get("category")
        query = self.config.get("query")

        params: dict[str, Any] = {"mode": mode, "limit": str(limit)}
        if category:
            params["category"] = category
        if query:
            params["q"] = query

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{_BASE_URL}/api/public/items",
                headers=_HEADERS,
                params=params,
            )
            response.raise_for_status()
            data = response.json()

        items = data.get("items", [])
        entities = [self._item_to_entity(item) for item in items]
        logger.info("AIHOT items: fetched %d items (mode=%s)", len(entities), mode)
        return entities

    async def _fetch_daily(self) -> list[Entity]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{_BASE_URL}/api/public/daily",
                headers=_HEADERS,
            )
            response.raise_for_status()
            data = response.json()

        entities: list[Entity] = []
        for section in data.get("sections", []):
            section_label = section.get("label", "")
            for item in section.get("items", []):
                item["_section"] = section_label
                entities.append(self._item_to_entity(item))

        logger.info(
            "AIHOT daily: fetched %d items across %d sections",
            len(entities),
            len(data.get("sections", [])),
        )
        return entities

    def _item_to_entity(self, item: dict[str, Any]) -> Entity:
        title = item.get("title", "Untitled")
        summary = item.get("summary", "")
        url = item.get("url", "")
        source_name = item.get("source", "AIHOT")
        category = item.get("category", "")
        section = item.get("_section", "")
        published_at = item.get("publishedAt", "")

        content_parts = [f"# {title}"]
        if summary:
            content_parts.append("")
            content_parts.append(summary)
        if url:
            content_parts.append("")
            content_parts.append(f"[Source]({url})")

        meta: dict[str, str] = {
            "authority": "high",
            "source_service": "aihot",
        }
        if category:
            meta["category"] = category
        if section:
            meta["section"] = section
        if published_at:
            meta["published_at"] = published_at

        return Entity(
            content="\n".join(content_parts),
            facet=EntityFacet.REFERENCE,
            created_by="agent:aihot",
            sources=[
                Source(
                    type=SourceType.WEB_SEARCH,
                    name=source_name,
                    url=url or None,
                    metadata=meta,
                )
            ],
        )

    def health_check(self) -> bool:
        return True
