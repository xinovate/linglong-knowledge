"""MCP tool implementations for Linglong knowledge base."""

import asyncio
import json
import logging
from typing import Any

from linglong.core.config import get_config
from linglong.core.models import Entity, EntityFacet, EntityStatus
from linglong.knowledge.store import KnowledgeStore

logger = logging.getLogger(__name__)


def _run_async(coro: Any) -> Any:
    """Run an async coroutine, handling both fresh and existing event loops."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)

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
                content = f"{content[:max_content_length]}\n\n... [truncated]"
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
            entity.content = f"{entity.content}\n\n{content}"
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
        import re

        import feedparser
        import httpx

        config = get_config()
        if config.ingest.rsshub_access_key and (":1200/" in url or url.rstrip("/").endswith(":1200")):
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}key={config.ingest.rsshub_access_key}"

        async def _fetch():
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
                )
                resp.raise_for_status()
            return resp.text

        xml_text = _run_async(_fetch())
        feed = feedparser.parse(xml_text)
        items = []
        for entry in feed.entries[:max_items]:
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            clean = re.sub(r"<[^>]+>", "", summary)[:300]
            items.append({
                "title": getattr(entry, "title", ""),
                "url": getattr(entry, "link", ""),
                "snippet": clean,
                "source": name or url,
            })

        return json.dumps(
            {"results": items, "count": len(items)},
            ensure_ascii=False,
        )
    except Exception as exc:
        logger.exception("fetch_rss failed")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


def record_feedback(
    content_hash: str,
    feedback: str,
    tags: list[str] | None = None,
) -> str:
    """Record user feedback on an ingest result for preference learning.

    Args:
        content_hash: Hash identifying the news item.
        feedback: "useful" or "not_interested".
        tags: Tags associated with the news item (optional).
    """
    try:
        from linglong.ingest.feedback import FeedbackStore

        store = FeedbackStore()
        if feedback not in ("useful", "not_interested"):
            return json.dumps(
                {"error": "feedback must be 'useful' or 'not_interested'"},
                ensure_ascii=False,
            )
        store.record(content_hash, feedback, tags)
        return json.dumps(
            {"status": "recorded", "content_hash": content_hash, "feedback": feedback},
            ensure_ascii=False,
        )
    except Exception as exc:
        logger.exception("record_feedback failed")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


def execute_package(package_path: str) -> str:
    """Execute an ingest package via IngestAgent.

    Returns the morning brief output as markdown.
    """
    try:
        import asyncio
        from pathlib import Path

        from linglong.ingest.agent import IngestAgent
        from linglong.ingest.brief_history import BriefHistory
        from linglong.ingest.feedback import FeedbackStore
        from linglong.ingest.package import SourcePackage

        package = SourcePackage.from_yaml(package_path)

        config = get_config()
        feedback_store = FeedbackStore()
        history_dir = Path(config.ingest.brief_history_dir).expanduser()
        brief_history = BriefHistory(history_dir, config.ingest.dedup_windows)
        agent = IngestAgent(feedback_store=feedback_store, brief_history=brief_history)
        output = _run_async(agent.run(package))

        response: dict[str, Any] = {
            "package": package.name,
            "output_length": len(output) if output else 0,
        }
        if output:
            response["output"] = output
        return json.dumps(response, ensure_ascii=False)
    except Exception as exc:
        logger.exception("execute_package failed")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


def generate_brief() -> str:
    """Execute an ingest package (YAML-defined collection of sources).

    Returns collected entities for discussion. Use write_entity to save
    selected results to the knowledge store.
    """
    try:
        import asyncio
        from datetime import date, timedelta
        from pathlib import Path

        from linglong.ingest.agent import IngestAgent
        from linglong.ingest.brief_history import BriefHistory
        from linglong.ingest.feedback import FeedbackStore
        from linglong.ingest.package import SourcePackage

        config = get_config()
        if not config.ingest.packages:
            return json.dumps(
                {"error": "No packages configured in .linglong.yaml"},
                ensure_ascii=False,
            )

        # Cache check: return today's brief if already generated
        output_dir = Path(config.ingest.brief_output_dir).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        today = date.today().isoformat()
        cache_path = output_dir / f"{today}.md"

        if cache_path.exists():
            cached = cache_path.read_text(encoding="utf-8")
            return json.dumps({
                "package": config.ingest.packages[0].get("name", ""),
                "output_length": len(cached),
                "cached": True,
                "output": cached,
            }, ensure_ascii=False)

        package = SourcePackage(**config.ingest.packages[0])
        feedback_store = FeedbackStore()
        history_dir = Path(config.ingest.brief_history_dir).expanduser()
        brief_history = BriefHistory(history_dir, config.ingest.dedup_windows)
        agent = IngestAgent(feedback_store=feedback_store, brief_history=brief_history)
        output = _run_async(agent.run(package))

        # Save to cache
        if output:
            cache_path.write_text(output, encoding="utf-8")

        # Cleanup old cached briefs
        cutoff = (date.today() - timedelta(days=config.ingest.brief_cache_days)).isoformat()
        for f in output_dir.glob("*.md"):
            if f.stem < cutoff:
                f.unlink()

        response: dict[str, Any] = {
            "package": package.name,
            "output_length": len(output) if output else 0,
            "cached": False,
        }
        if output:
            response["output"] = output
        return json.dumps(response, ensure_ascii=False)
    except Exception as exc:
        logger.exception("generate_brief failed")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


def search_web(query: str, max_results: int = 10) -> str:
    """Search the web via SearXNG. Returns results including web page title, web page URL, web page summary, website name, website icon, etc."""
    try:
        import asyncio

        import httpx

        config = get_config()
        base_url = config.ingest.searxng_url.rstrip("/")
        timeout = config.ingest.search_timeout

        params = {
            "q": query,
            "format": "json",
            "categories": "general",
        }
        headers: dict[str, str] = {}
        if config.ingest.searxng_api_key:
            headers["Authorization"] = f"Bearer {config.ingest.searxng_api_key}"

        async def _search():
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(f"{base_url}/search", params=params, headers=headers)
                resp.raise_for_status()
                return resp.json()

        data = _run_async(_search())
        results = []
        for r in data.get("results", [])[:max_results]:
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", ""),
                "engine": r.get("engine", ""),
            })

        return json.dumps(
            {"results": results, "count": len(results)},
            ensure_ascii=False,
        )
    except Exception as exc:
        logger.exception("search_web failed")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


def review_article(
    content: str,
    source_entity_ids: list[str] | None = None,
) -> str:
    """Review an article for quality before publishing. Evaluates format, content richness, structure, expression, and accuracy. Passes with score >= 6.0.

    Args:
        content: Full article markdown content (including frontmatter).
        source_entity_ids: Optional knowledge entity IDs used as sources for accuracy checks.
    """
    try:
        from linglong.reviewer.reviewer import Reviewer

        reviewer = Reviewer()
        result = reviewer.review(content, source_entity_ids=source_entity_ids)

        dimensions_data = [
            {
                "name": d.name,
                "score": d.score,
                "passed": d.passed,
                "suggestions": d.suggestions,
            }
            for d in result.dimensions
        ]

        return json.dumps(
            {
                "total_score": result.total_score,
                "passed": result.passed,
                "summary": result.summary,
                "dimensions": dimensions_data,
                "rule_issues": result.rule_issues,
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        logger.exception("review_article failed")
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
