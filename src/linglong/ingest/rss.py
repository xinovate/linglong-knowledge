"""RSS feed ingestion source."""

import hashlib

import feedparser
import httpx

from linglong.core.config import get_config
from linglong.core.models import Entity, EntityFacet, Source, SourceType
from linglong.knowledge.review import ReviewEngine
from linglong.knowledge.store import KnowledgeStore


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
        self.review_engine = ReviewEngine()

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
            entity = self.review_engine.review(entity)
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

        return Entity(
            id=entity_id,
            content=content,
            facet=EntityFacet.SOURCE,
            summary=getattr(entry, "summary", None),
            created_by="agent:ingest",
            confidence=get_config().ingest.default_confidence.get("rss", 0.7),  # RSS content has moderate confidence
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


class RSSIngestor:
    """Manager for multiple RSS sources."""

    def __init__(self, store: KnowledgeStore):
        self.store = store
        self.sources: list[RSSSource] = []

    def add_source(self, source: RSSSource) -> None:
        """Add an RSS source."""
        self.sources.append(source)

    async def ingest_all(self) -> dict:
        """Ingest from all sources."""
        results = {"total": 0, "created": 0, "failed": 0}

        for source in self.sources:
            try:
                entities = await source.fetch()
                for entity in entities:
                    # 检查实体是否已存在
                    existing = self.store.get(entity.id)
                    if existing is None:
                        self.store.create(entity)
                        results["created"] += 1
                    results["total"] += 1
            except Exception as e:
                print(f"Failed to ingest from {source.name}: {e}")
                results["failed"] += 1

        return results
