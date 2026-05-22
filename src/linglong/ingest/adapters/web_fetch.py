"""Web fetch source adapter — parallel HTTP scraping."""

import asyncio

import httpx

from linglong.core.config import get_config
from linglong.core.models import Entity, EntityFacet, Source, SourceType
from linglong.ingest.adapter import SourceAdapter


class WebFetchAdapter(SourceAdapter):
    """Adapter for parallel web page fetching."""

    adapter_type = "web_fetch"

    async def fetch(self) -> list[Entity]:
        urls = self.config.get("urls", [])
        max_chars = self.config.get("max_chars", 1500)
        default_timeout = get_config().ingest.web_fetch_timeout
        timeout = self.config.get("timeout", default_timeout)

        tasks = [self._fetch_one(url, max_chars, timeout) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        entities = []
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                continue
            if result:
                entities.append(self._content_to_entity(result, url))
        return entities

    async def _fetch_one(self, url: str, max_chars: int, timeout: int) -> str | None:
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.text[:max_chars]
            except Exception:
                return None

    def _content_to_entity(self, content: str, url: str) -> Entity:
        return Entity(
            content=f"# Fetched Content\n\n{content}\n\n[Source]({url})",
            facet=EntityFacet.REFERENCE,
            created_by="agent:ingest",
            confidence=get_config().ingest.default_confidence.get("web_fetch", 0.65),
            sources=[
                Source(
                    type=SourceType.WEB_FETCH,
                    name=self.source_id,
                    url=url,
                    metadata={"authority": self.metadata.get("authority", "medium")},
                )
            ],
        )

    def health_check(self) -> bool:
        return bool(self.config.get("urls"))
