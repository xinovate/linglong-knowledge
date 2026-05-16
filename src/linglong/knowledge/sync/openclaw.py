"""OpenClaw wiki sync adapter.

Reads OpenClaw wiki files from the filesystem and syncs them into
Linglong's KnowledgeStore as Entity objects.
"""

import hashlib
import logging
import re
from pathlib import Path

import frontmatter

from linglong.core.config import get_config
from linglong.core.models import Entity, EntityFacet, EntityStatus, Source, SourceType
from linglong.knowledge.store import KnowledgeStore

logger = logging.getLogger(__name__)

_WIKILINK_PATTERN = re.compile(r"\[\[(.*?)\]\]")

TYPE_TO_FACET: dict[str, EntityFacet] = {
    # 标准分面
    "concept": EntityFacet.CONCEPT,
    "entity": EntityFacet.ENTITY,
    "experience": EntityFacet.EXPERIENCE,
    "methodology": EntityFacet.METHODOLOGY,
    "personal": EntityFacet.PERSONAL,
    "source": EntityFacet.SOURCE,
    "synthesis": EntityFacet.SYNTHESIS,
    # OpenClaw 特有类型 — 内容类
    "article": EntityFacet.SOURCE,
    "tutorial": EntityFacet.METHODOLOGY,
    "debug-log": EntityFacet.EXPERIENCE,
    "decision": EntityFacet.SYNTHESIS,
    "tip": EntityFacet.EXPERIENCE,
    "reference": EntityFacet.SOURCE,
    "howto": EntityFacet.METHODOLOGY,
    "note": EntityFacet.EXPERIENCE,
    "project": EntityFacet.SYNTHESIS,
    "area": EntityFacet.CONCEPT,
    "moc": EntityFacet.SYNTHESIS,
    "daily": EntityFacet.PERSONAL,
    "meeting": EntityFacet.PERSONAL,
    "idea": EntityFacet.CONCEPT,
    "bookmark": EntityFacet.SOURCE,
    # OpenClaw 特有类型 — 补充
    "skill": EntityFacet.EXPERIENCE,
    "template": EntityFacet.METHODOLOGY,
    "user": EntityFacet.PERSONAL,
    "soul": EntityFacet.PERSONAL,
    "todo": EntityFacet.PERSONAL,
    "feedback": EntityFacet.EXPERIENCE,
    "problem": EntityFacet.CONCEPT,
    "dashboard": EntityFacet.SYNTHESIS,
    # OpenClaw 特有类型 — 源码分析
    "source-code-note": EntityFacet.SOURCE,
    "source-code-analysis": EntityFacet.SOURCE,
    # OpenClaw 特有类型 — 项目子文档
    "test-report": EntityFacet.SOURCE,
    "dependency-map": EntityFacet.SOURCE,
    "design-spec": EntityFacet.SOURCE,
    "change-list": EntityFacet.SOURCE,
    "validation-report": EntityFacet.SOURCE,
    "task-anchor": EntityFacet.SOURCE,
    "integration-guide": EntityFacet.METHODOLOGY,
    "project-development": EntityFacet.SYNTHESIS,
    "project-history": EntityFacet.SYNTHESIS,
    "orchestrator-spec": EntityFacet.SYNTHESIS,
    "agent-coordination": EntityFacet.SYNTHESIS,
    "quality-gate": EntityFacet.METHODOLOGY,
    "task-decomposition": EntityFacet.METHODOLOGY,
    "knowledge-flow": EntityFacet.CONCEPT,
    "comprehensive-report": EntityFacet.SYNTHESIS,
    "final-summary": EntityFacet.SYNTHESIS,
    "feedback-log": EntityFacet.EXPERIENCE,
}


def _compute_id(relative_path: str) -> str:
    """Compute a stable entity ID from the relative file path."""
    return hashlib.sha256(relative_path.encode("utf-8")).hexdigest()[:16]


def _extract_wikilinks(content: str) -> list[str]:
    """Extract deduplicated wikilink targets from markdown content.

    Handles ``[[target|Display]]`` and ``[[target]]`` forms.
    """
    seen: set[str] = set()
    links: list[str] = []
    for match in _WIKILINK_PATTERN.finditer(content):
        link_text = match.group(1)
        target = link_text.split("|", 1)[0].strip()
        if target and target not in seen:
            seen.add(target)
            links.append(target)
    return links


def _file_to_entity(file_path: Path, relative_path: str) -> Entity:
    """Convert a single wiki file into a Linglong Entity."""
    raw_content = file_path.read_text(encoding="utf-8")
    post = frontmatter.loads(raw_content)

    metadata: dict = {}
    if post.get("type"):
        metadata["type"] = post.get("type")
    if post.get("description"):
        metadata["description"] = post.get("description")
    created = post.get("created")
    if created is not None:
        metadata["created"] = created.isoformat() if hasattr(created, "isoformat") else str(created)

    wikilinks = _extract_wikilinks(post.content)
    if wikilinks:
        metadata["wikilinks"] = wikilinks

    file_type = post.get("type", "source")
    facet = TYPE_TO_FACET.get(file_type, EntityFacet.SOURCE)

    entity_id = _compute_id(relative_path)

    source = Source(
        type=SourceType.FILE,
        name="openclaw-wiki",
        url=relative_path,
    )

    # 保留原始创建时间（frontmatter created → Entity created_at）
    entity_kwargs: dict = dict(
        id=entity_id,
        content=post.content,
        facet=facet,
        created_by="agent:openclaw",
        status=EntityStatus.AUTO_CONFIRMED,
        sources=[source],
        confidence=get_config().knowledge.sync_confidence,
        metadata=metadata,
    )
    if created is not None:
        parsed = created if hasattr(created, "isoformat") else None
        if parsed is None:
            from datetime import datetime
            try:
                parsed = datetime.fromisoformat(str(created))
            except (ValueError, TypeError):
                pass
        if parsed is not None:
            entity_kwargs["created_at"] = parsed

    return Entity(**entity_kwargs)


class OpenClawSyncAdapter:
    """Sync adapter for OpenClaw wiki files."""

    def __init__(self, wiki_path: str, store: KnowledgeStore) -> None:
        self.wiki_path = Path(wiki_path)
        self.store = store

    def sync_to_linglong(self) -> dict:
        """Read all ``.md`` files under ``wiki_path`` and sync them into the store.

        Skips ``index.md``. Returns sync stats ``{"total": N, "created": N, "failed": N}``.
        """
        stats = {"total": 0, "created": 0, "failed": 0}

        if not self.wiki_path.exists():
            logger.warning("Wiki path does not exist: %s", self.wiki_path)
            return stats

        md_files = [p for p in self.wiki_path.rglob("*.md") if p.name != "index.md"]

        for file_path in md_files:
            stats["total"] += 1
            try:
                relative_path = str(file_path.relative_to(self.wiki_path))
                entity = _file_to_entity(file_path, relative_path)
                self.store.create(entity)
                stats["created"] += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to sync %s: %s", file_path, exc)
                stats["failed"] += 1

        return stats
