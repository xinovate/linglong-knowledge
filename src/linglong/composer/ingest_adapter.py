"""Adapter from KnowledgeStore Entity to pipeline internal format."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

from linglong.core.models import Entity


@dataclass
class MemoryFragment:
    """Internal pipeline representation of a knowledge fragment."""

    source: str
    content: str
    timestamp: datetime
    metadata: Dict[str, Any]
    raw_path: str = ""

    @property
    def content_hash(self) -> str:
        """Compute a content hash for deduplication."""
        import hashlib

        raw = f"{self.source}:{self.content}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()


class IngestAdapter:
    """Adapt Entity objects from KnowledgeStore into MemoryFragments."""

    @staticmethod
    def adapt(entity: Entity) -> MemoryFragment:
        """Convert a single Entity to MemoryFragment."""
        source_name = entity.sources[0].name if entity.sources else "unknown"
        return MemoryFragment(
            source=source_name,
            content=entity.content,
            timestamp=entity.created_at,
            metadata={
                "entity_id": entity.id,
                "confidence": float(entity.confidence),
                "status": entity.status.value if hasattr(entity.status, "value") else str(entity.status),
                "created_by": str(entity.created_by),
            },
            raw_path="",
        )

    @staticmethod
    def adapt_many(entities: List[Entity]) -> List[MemoryFragment]:
        """Convert multiple Entities."""
        return [IngestAdapter.adapt(e) for e in entities]
