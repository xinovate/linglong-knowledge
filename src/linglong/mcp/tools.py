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
    # Prefer AI-generated summary for relevance judgment; fall back to content snippet.
    if entity.summary:
        preview = entity.summary.strip()
    else:
        preview = entity.content.replace("\n", " ")[:500].strip()
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


def search_and_read(query: str, facet: str | None = None, limit: int = 3) -> str:
    """Search the knowledge base and automatically read the top-N most relevant entities.

    This is a convenience tool that combines search_wiki + read_entity into a single
    call, returning full content for each result.
    """
    try:
        store = _get_store()
        facet_enum = _facet_enum(facet)
        results = store.search(query=query, facet=facet_enum, limit=limit)
        full_results: list[dict[str, Any]] = []
        for entity in results:
            full_results.append(
                {
                    "id": entity.id,
                    "facet": entity.facet.value,
                    "status": entity.status.value,
                    "title": _extract_title(entity.content) or "(无标题)",
                    "content": entity.content,
                    "summary": entity.summary,
                    "updated_at": entity.updated_at.isoformat() if entity.updated_at else None,
                }
            )
        return json.dumps(
            {"results": full_results, "count": len(full_results)},
            ensure_ascii=False,
        )
    except Exception as exc:
        logger.exception("search_and_read failed")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


def update_entity(entity_id: str, content: str, append: bool = False) -> str:
    """Update an existing knowledge entity.

    Args:
        entity_id: The ID of the entity to update.
        content: New content (markdown). In append mode this is appended to existing content.
        append: If True, append content instead of replacing. Default is replace.
    """
    try:
        store = _get_store()
        entity = store.get(entity_id)
        if entity is None:
            return json.dumps(
                {"error": "Entity not found", "entity_id": entity_id},
                ensure_ascii=False,
            )

        if append:
            entity.content = entity.content + "\n\n" + content
            entity.metadata["update_mode"] = "append"
        else:
            entity.content = content

        updated = store.update(entity)
        return json.dumps(
            {
                "id": updated.id,
                "facet": updated.facet.value,
                "status": updated.status.value,
                "message": "Entity updated successfully",
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        logger.exception("update_entity failed")
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


def write_entity(
    title: str,
    content: str,
    facet: str,
    tags: list[str] | None = None,
    reference_entity_ids: list[str] | None = None,
) -> str:
    """Create a new knowledge entity in the Linglong wiki.

    Best practice: before writing, call search_wiki with the same facet to find
    existing entries and reference their frontmatter style and structure.
    """
    try:
        store = _get_store()
        facet_enum = _facet_enum(facet)
        if facet_enum is None:
            raise ValueError("facet is required")

        full_content = f"# {title}\n\n{content}"
        metadata: dict[str, Any] = {}
        if tags:
            metadata["tags"] = tags
        if reference_entity_ids:
            metadata["references"] = reference_entity_ids

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
