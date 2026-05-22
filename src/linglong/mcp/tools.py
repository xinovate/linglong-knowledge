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
        "group": entity.group,
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
    """Search the Linglong knowledge base. Auto-selects the best search mode (keyword, vector, or hybrid)."""
    try:
        store = _get_store()
        facet_enum = _facet_enum(facet)
        results = store.search_auto(query=query, facet=facet_enum, limit=limit)
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


def search_and_read(
    query: str,
    facet: str | None = None,
    limit: int = 3,
    max_content_length: int = 2000,
) -> str:
    """Search the knowledge base and automatically read the top-N most relevant entities.

    This is a convenience tool that combines search_wiki + read_entity into a single
    call. To save tokens, content is truncated to max_content_length (default 2000).
    Set max_content_length=0 to return full content.
    """
    try:
        store = _get_store()
        facet_enum = _facet_enum(facet)
        results = store.search_auto(query=query, facet=facet_enum, limit=limit)
        full_results: list[dict[str, Any]] = []
        for entity in results:
            content = entity.content
            truncated = False
            if max_content_length > 0 and len(content) > max_content_length:
                content = content[:max_content_length] + "\n\n... [truncated]"
                truncated = True
            full_results.append(
                {
                    "id": entity.id,
                    "facet": entity.facet.value,
                    "status": entity.status.value,
                    "title": _extract_title(entity.content) or "(无标题)",
                    "content": content,
                    "summary": entity.summary,
                    "truncated": truncated,
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
    group: str | None = None,
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
            group=group,
            created_by="agent:mcp",
            confidence=0.9,
            metadata=metadata,
        )
        created = store.create(entity)

        result: dict[str, Any] = {
            "id": created.id,
            "facet": created.facet.value,
            "group": created.group,
            "status": created.status.value,
            "message": "Entity created successfully",
        }

        # Warn if facet root is getting crowded and no group was specified
        if not group:
            crowding = store.check_facet_crowding(facet_enum)
            if crowding:
                result["warning"] = (
                    f"Facet '{facet.value}' has {crowding['root_count']} ungrouped entities "
                    f"(threshold: {crowding['threshold']}). "
                    f"Consider specifying a group. Existing groups: {list(crowding['existing_groups'].keys())}"
                )

        return json.dumps(result, ensure_ascii=False)
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


def get_template(facet: str) -> str:
    """Get the writing template for a specific facet.

    Use this before writing to understand the expected structure and format.
    """
    try:
        from linglong.core.templates import get_template_manager

        manager = get_template_manager()
        content = manager.get_template(facet)
        if content is None:
            available = list(manager.list_templates().keys())
            return json.dumps(
                {
                    "error": f"Template not found for facet '{facet}'",
                    "available_templates": available,
                },
                ensure_ascii=False,
            )
        return json.dumps(
            {"facet": facet, "template": content},
            ensure_ascii=False,
        )
    except Exception as exc:
        logger.exception("get_template failed")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


def list_templates() -> str:
    """List all available writing templates."""
    try:
        from linglong.core.templates import get_template_manager

        manager = get_template_manager()
        templates = manager.list_templates()
        return json.dumps(
            {
                "templates": [
                    {"facet": k, "description": v.get("description", "")}
                    for k, v in templates.items()
                ],
                "count": len(templates),
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        logger.exception("list_templates failed")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


def fetch_rss(url: str, name: str | None = None, max_items: int = 20) -> str:
    """Fetch and parse an RSS feed. Returns entity previews for discussion.

    Use this to collect information from RSS sources. Discuss with the user
    before writing any results to the knowledge store via write_entity.
    """
    try:
        import asyncio

        from linglong.ingest.rss import RSSSource

        source = RSSSource(name=name or url, url=url, max_items=max_items)
        entities = asyncio.run(source.fetch())

        previews = [_entity_to_preview(e) for e in entities]
        return json.dumps(
            {"results": previews, "count": len(previews)},
            ensure_ascii=False,
        )
    except Exception as exc:
        logger.exception("fetch_rss failed")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


def execute_package(package_path: str) -> str:
    """Execute an ingest package (YAML-defined collection of sources).

    Returns collected entities for discussion. Use write_entity to save
    selected results to the knowledge store.
    """
    try:
        import asyncio

        from linglong.ingest.executor import PackageExecutor
        from linglong.ingest.history import IngestHistory
        from linglong.ingest.package import SourcePackage

        package = SourcePackage.from_yaml(package_path)

        config = get_config()
        history = None
        if package.output.persist:
            history = IngestHistory()

        llm_config = None
        if config.composer.llm_api_key:
            llm_config = {
                "provider": config.composer.llm_provider,
                "api_key": config.composer.llm_api_key,
                "model": config.composer.llm_model,
                "base_url": config.composer.llm_base_url,
                "temperature": config.composer.llm_temperature,
                "max_tokens": config.composer.llm_max_tokens,
            }

        executor = PackageExecutor(history=history, llm_config=llm_config)
        result = asyncio.run(executor.execute(package))

        entities = result.get("entities", [])
        previews = [_entity_to_preview(e) for e in entities]
        response: dict[str, Any] = {
            "results": previews,
            "count": len(previews),
            "total": result.get("total", 0),
            "filtered": result.get("filtered", 0),
            "package": package.name,
            "failed": result.get("failed", 0),
        }
        if result.get("output"):
            response["output"] = result["output"]
        return json.dumps(response, ensure_ascii=False)
    except Exception as exc:
        logger.exception("execute_package failed")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
