"""RSS feed ingestion source."""

import hashlib

import feedparser
import httpx

from linglong.core.config import get_config
from linglong.core.models import Entity, EntityFacet, Source, SourceType


class RSSSource:
    """RSS feed source for ingesting articles."""

    def __init__(
        self,
        name: str,
        url: str,
        category: str | None = None,
        max_items: int = 50,
    ):
        self.name = name
        self.url = url
        self.category = category or "general"
        self.max_items = max_items

    async def fetch(self) -> list[Entity]:
        """Fetch and parse RSS feed."""
        timeout = get_config().ingest.rss_timeout
        async with httpx.AsyncClient() as client:
            response = await client.get(self.url, timeout=timeout)
            response.raise_for_status()

        feed = feedparser.parse(response.text)
        entities = []

        for entry in feed.entries[: self.max_items]:
            entity = self._entry_to_entity(entry)
            entities.append(entity)

        return entities

    def _entry_to_entity(self, entry) -> Entity:
        """Convert RSS entry to knowledge entity."""
        # 从 URL 生成确定性 ID
        entity_id = hashlib.sha256(entry.link.encode()).hexdigest()[:16]

        # 构建内容
        content = f"""# {entry.title}

**Source:** [{self.name}]({entry.link})
**Published:** {getattr(entry, 'published', 'Unknown')}

{getattr(entry, 'summary', '')}
"""

        # 提取标签（如有）
        tags = []
        if hasattr(entry, "tags"):
            tags = [tag.term for tag in entry.tags]

        # 保留原始发布时间
        published_parsed = getattr(entry, "published_parsed", None)
        entity_kwargs: dict = dict(
            id=entity_id,
            content=content,
            facet=EntityFacet.REFERENCE,
            summary=getattr(entry, "summary", None),
            created_by="agent:rss",
            confidence=get_config().ingest.default_confidence.get("rss", 0.7),
            sources=[
                Source(
                    type=SourceType.RSS,
                    name=self.name,
                    url=entry.link,
                    metadata={
                        "category": self.category,
                        "tags": tags,
                        "published": getattr(entry, "published", None),
                    },
                )
            ],
        )
        if published_parsed:
            from datetime import datetime, timezone

            try:
                entity_kwargs["created_at"] = datetime(
                    *published_parsed[:6], tzinfo=timezone.utc
                )
            except Exception:
                pass

        return Entity(**entity_kwargs)


class RSSIngestor:
    """Manager for multiple RSS sources."""

    def __init__(self) -> None:
        self.sources: list[RSSSource] = []

    def add_source(self, source: RSSSource) -> None:
        """Add an RSS source."""
        self.sources.append(source)

    async def ingest_all(self) -> list[Entity]:
        """Fetch from all sources and return collected entities."""
        all_entities: list[Entity] = []

        for source in self.sources:
            try:
                entities = await source.fetch()
                all_entities.extend(entities)
            except Exception as e:
                print(f"Failed to ingest from {source.name}: {e}")

        return all_entities
