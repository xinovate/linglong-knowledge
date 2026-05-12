"""Web search source adapter."""

from linglong.core.models import Entity
from linglong.ingest.adapter import SourceAdapter


class WebSearchAdapter(SourceAdapter):
    """Adapter for web search (DuckDuckGo / Bing CN)."""

    adapter_type = "web_search"

    async def fetch(self) -> list[Entity]:
        # Placeholder: actual search implementation requires
        # duckduckgo-search library or Bing CN scraping
        return []

    def health_check(self) -> bool:
        return bool(self.config.get("queries"))
