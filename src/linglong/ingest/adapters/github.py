"""GitHub Search source adapter — trending AI repositories."""

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx

from linglong.core.models import Entity, EntityFacet, Source, SourceType
from linglong.ingest.adapter import SourceAdapter

logger = logging.getLogger(__name__)

_API_URL = "https://api.github.com/search/repositories"


class GitHubAdapter(SourceAdapter):
    """Adapter for GitHub repository search (trending AI projects)."""

    adapter_type = "github"

    async def fetch(self) -> list[Entity]:
        topics = self.config.get("topics", ["ai"])
        min_stars = self.config.get("min_stars", 50)
        since_days = self.config.get("since_days", 7)
        max_results = self.config.get("max_results", 10)
        languages = self.config.get("languages", [])
        token = self.config.get("token", "")

        cutoff = (date.today() - timedelta(days=since_days)).isoformat()

        parts = [
            f"created:>{cutoff}",
            f"stars:>{min_stars}",
        ]
        for topic in topics:
            parts.append(f"topic:{topic}")
        for lang in languages:
            parts.append(f"language:{lang}")

        query = " ".join(parts)
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": str(max_results),
        }

        headers: dict[str, str] = {
            "Accept": "application/vnd.github.v3+json",
        }
        if token:
            headers["Authorization"] = f"token {token}"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(_API_URL, params=params, headers=headers)
            response.raise_for_status()

        data = response.json()
        items = data.get("items", [])

        entities = [self._item_to_entity(item) for item in items]
        logger.info(
            "GitHub: fetched %d repos (total_count=%d, query=%s)",
            len(entities),
            data.get("total_count", 0),
            query[:80],
        )
        return entities

    def _item_to_entity(self, item: dict[str, Any]) -> Entity:
        full_name = item.get("full_name", "unknown")
        description = item.get("description") or ""
        html_url = item.get("html_url", "")
        stars = item.get("stargazers_count", 0)
        language = item.get("language") or "?"
        topics = item.get("topics", [])
        created = item.get("created_at", "")[:10]

        content_parts = [f"# {full_name}"]
        if description:
            content_parts.extend(["", description])
        content_parts.extend(["", f"Stars: {stars} | Lang: {language} | Created: {created}"])
        if html_url:
            content_parts.extend(["", f"[Source]({html_url})"])

        return Entity(
            content="\n".join(content_parts),
            facet=EntityFacet.REFERENCE,
            created_by="agent:github",
            confidence=0.7,
            sources=[
                Source(
                    type=SourceType.API,
                    name="github",
                    url=html_url or None,
                    metadata={
                        "full_name": full_name,
                        "stars": stars,
                        "language": language,
                        "topics": topics,
                        "authority": "medium",
                    },
                )
            ],
        )

    def health_check(self) -> bool:
        return True
