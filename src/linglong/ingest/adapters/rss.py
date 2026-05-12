"""RSS source adapter."""

from linglong.core.models import Entity
from linglong.ingest.adapter import SourceAdapter
from linglong.ingest.rss import RSSSource


class RSSAdapter(SourceAdapter):
    """Adapter for RSS feeds."""

    adapter_type = "rss"

    def __init__(self, source_id: str, config: dict, metadata: dict):
        super().__init__(source_id, config, metadata)
        self._rss_source = RSSSource(
            name=source_id,
            url=config["url"],
            category=metadata.get("category"),
            max_items=config.get("max_items", 50),
        )

    async def fetch(self) -> list[Entity]:
        entities = await self._rss_source.fetch()
        for entity in entities:
            for source in entity.sources:
                source.metadata.update(self.metadata)
        return entities

    def health_check(self) -> bool:
        return bool(self.config.get("url"))
