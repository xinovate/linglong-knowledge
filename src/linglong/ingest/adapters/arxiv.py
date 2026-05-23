"""ArXiv source adapter — AI/ML paper preprints."""

import logging
from datetime import UTC, datetime
from typing import Any
from xml.etree import ElementTree

import httpx

from linglong.core.models import Entity, EntityFacet, Source, SourceType
from linglong.ingest.adapter import SourceAdapter

logger = logging.getLogger(__name__)

_BASE_URL = "https://export.arxiv.org/api/query"
_ATOM_NS = "http://www.w3.org/2005/Atom"
_ARXIV_NS = "http://arxiv.org/schemas/atom"


class ArXivAdapter(SourceAdapter):
    """Adapter for ArXiv paper preprints."""

    adapter_type = "arxiv"

    async def fetch(self) -> list[Entity]:
        categories = self.config.get("categories", ["cs.AI"])
        max_results = self.config.get("max_results", 10)
        sort_by = self.config.get("sort_by", "submittedDate")

        query = " OR ".join(f"cat:{c}" for c in categories)
        params = {
            "search_query": query,
            "max_results": str(max_results),
            "sortBy": sort_by,
            "sortOrder": "descending",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(_BASE_URL, params=params)
            response.raise_for_status()

        return self._parse(response.text)

    def _parse(self, xml_text: str) -> list[Entity]:
        root = ElementTree.fromstring(xml_text)
        entries = root.findall(f"{{{_ATOM_NS}}}entry")

        entities: list[Entity] = []
        for entry in entries:
            entity = self._entry_to_entity(entry)
            if entity:
                entities.append(entity)

        logger.info("ArXiv: fetched %d papers", len(entities))
        return entities

    def _entry_to_entity(self, entry: ElementTree.Element) -> Entity | None:
        ns = _ATOM_NS
        title_el = entry.find(f"{{{ns}}}title")
        summary_el = entry.find(f"{{{ns}}}summary")
        id_el = entry.find(f"{{{ns}}}id")
        published_el = entry.find(f"{{{ns}}}published")

        if title_el is None or id_el is None:
            return None

        title = title_el.text.strip().replace("\n", " ") if title_el.text else ""
        summary = summary_el.text.strip().replace("\n", " ")[:500] if summary_el is not None and summary_el.text else ""
        arxiv_url = id_el.text.strip() if id_el.text else ""
        published = published_el.text.strip()[:10] if published_el is not None and published_el.text else ""

        categories = [
            el.get("term", "")
            for el in entry.findall(f"{{{ns}}}category")
        ]

        content_parts = [f"# {title}"]
        if summary:
            content_parts.extend(["", summary])
        if arxiv_url:
            content_parts.extend(["", f"[Source]({arxiv_url})"])

        arxiv_id = arxiv_url.split("/abs/")[-1] if "/abs/" in arxiv_url else ""

        return Entity(
            content="\n".join(content_parts),
            facet=EntityFacet.REFERENCE,
            created_by="agent:arxiv",
            confidence=0.8,
            sources=[
                Source(
                    type=SourceType.API,
                    name="arxiv",
                    url=arxiv_url or None,
                    metadata={
                        "arxiv_id": arxiv_id,
                        "categories": "/".join(categories),
                        "published_at": published,
                        "authority": "high",
                    },
                )
            ],
        )

    def health_check(self) -> bool:
        return True
