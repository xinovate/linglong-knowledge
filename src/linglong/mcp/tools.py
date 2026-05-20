"""MCP tool implementations for Linglong knowledge base."""

import json
import logging
from typing import Any

from linglong.core.config import get_config
from linglong.core.models import Entity, EntityFacet, EntityStatus
from linglong.knowledge.store import KnowledgeStore

logger = logging.getLogger(__name__)

# Lazy-initialized store instance
_store: KnowledgeStore | None = None


def _get_store() -> KnowledgeStore:
    """Get or create the KnowledgeStore instance."""
    global _store
    if _store is None:
        get_config()  # Ensure config is loaded
        _store = KnowledgeStore()
    return _store


def _extract_title(content: str) -> str | None:
    """Extract title from first markdown heading."""
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _entity_to_preview(entity: Entity) -> dict[str, Any]:
    """Convert entity to a lightweight preview dict."""
    title = _extract_title(entity.content) or "(无标题)"
    preview = entity.content.replace("\n", " ")[:120].strip()
    return {
        "id": entity.id,
        "facet": entity.facet.value,
        "status": entity.status.value,
        "confidence": float(entity.confidence) if entity.confidence else None,
        "updated_at": entity.updated_at.isoformat() if entity.updated_at else None,
        "title": title,
        "preview": preview,
    }


def _facet_enum(facet: str | None) -> EntityFacet | None:
    """Convert string facet to EntityFacet enum."""
    if facet is None:
        return None
    try:
        return EntityFacet(facet)
    except ValueError as exc:
        valid = ", ".join(f.value for f in EntityFacet)
        raise ValueError(f"Invalid facet '{facet}'. Must be one of: {valid}") from exc


def search_wiki(query: str, facet: str | None = None, limit: int = 10) -> str:
    """Search the Linglong knowledge base using full-text search (FTS5)."""
    try:
        store = _get_store()
        facet_enum = _facet_enum(facet)
        results = store.search(query=query, facet=facet_enum, limit=limit)
        previews = [_entity_to_preview(e) for e in results]
        return json.dumps({"results": previews, "count": len(previews)}, ensure_ascii=False)
    except Exception as exc:
        logger.exception("search_wiki failed")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


def search_similar(query: str, facet: str | None = None, limit: int = 10) -> str:
    """Semantic vector search over the Linglong knowledge base. Falls back to FTS5 if embeddings unavailable."""
    try:
        store = _get_store()
        facet_enum = _facet_enum(facet)
        results = store.search_similar(query=query, facet=facet_enum, limit=limit)
        previews = [_entity_to_preview(e) for e in results]
        response: dict[str, Any] = {"results": previews, "count": len(previews)}
        if not store._vector_available:
            response["warning"] = "Vector search unavailable; using keyword fallback"
        return json.dumps(response, ensure_ascii=False)
    except Exception as exc:
        logger.exception("search_similar failed")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


def read_entity(entity_id: str) -> str:
    """Read a full knowledge entity by its ID."""
    try:
        store = _get_store()
        entity = store.get(entity_id)
        if entity is None:
            return json.dumps(
                {"error": "Entity not found", "entity_id": entity_id},
                ensure_ascii=False,
            )
        return json.dumps(entity.model_dump(mode="json"), ensure_ascii=False)
    except Exception as exc:
        logger.exception("read_entity failed")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


def write_entity(title: str, content: str, facet: str, tags: list[str] | None = None) -> str:
    """Create a new knowledge entity in the Linglong wiki."""
    try:
        store = _get_store()
        facet_enum = _facet_enum(facet)
        if facet_enum is None:
            raise ValueError("facet is required")

        full_content = f"# {title}\n\n{content}"
        metadata: dict[str, Any] = {}
        if tags:
            metadata["tags"] = tags

        entity = Entity(
            content=full_content,
            facet=facet_enum,
            created_by="agent:mcp",
            confidence=0.9,
            metadata=metadata,
        )
        created = store.create(entity)
        return json.dumps(
            {
                "id": created.id,
                "facet": created.facet.value,
                "status": created.status.value,
                "message": "Entity created successfully",
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        logger.exception("write_entity failed")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


def list_entities(facet: str | None = None, since: str | None = None, limit: int = 20) -> str:
    """Browse recent knowledge entities, optionally filtered by facet."""
    try:
        store = _get_store()
        facet_enum = _facet_enum(facet)
        results = store.search(facet=facet_enum, since=since, limit=limit)
        previews = [_entity_to_preview(e) for e in results]
        return json.dumps({"results": previews, "count": len(previews)}, ensure_ascii=False)
    except Exception as exc:
        logger.exception("list_entities failed")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
