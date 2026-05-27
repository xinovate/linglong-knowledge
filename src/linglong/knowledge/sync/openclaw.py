"""OpenClaw sync adapter.

Reads OpenClaw wiki files from the filesystem and syncs them
into Linglong's KnowledgeStore as Entity objects.

Only syncs ``wiki/`` directory content (long-term knowledge).
Short-term memory (Dreaming files, task indexes, daily task details) is
excluded per Linglong's boundary: Linglong only handles shared long-term
knowledge, not agent session state.
"""

import hashlib
import logging
import re
from datetime import UTC, datetime
from pathlib import Path

import frontmatter

from linglong.core.config import get_config
from linglong.core.models import Entity, EntityFacet, EntityStatus, Source, SourceType
from linglong.knowledge.store import KnowledgeStore

logger = logging.getLogger(__name__)

_WIKILINK_PATTERN = re.compile(r"\[\[(.*?)\]\]")

# OpenClaw wiki top-level dir → Linglong wiki subdirectory mapping
_WIKI_DIR_TO_SUBDIR: dict[str, str] = {
    "projects": "projects",
    "references": "references",
    "problems": "problems",
    "concepts": "",         # flat, subdirectory names preserved
    "experiences": "",      # flat, subdirectory names preserved
    "methodologies": "",    # flat
    "user": "",             # flat under personal
    "emotion": "",          # merged into personal, flat
    "soul": "diary",        # merged into personal/diary/
    "infra": "infra",       # merged into personal/infra/
    "dashboards": "",       # not migrated
    "templates": "",        # not migrated
    "todo": "",             # merged into personal, flat
}

# Directory-level facet override: files in these dirs always get the specified facet
_DIR_FACET_OVERRIDE: dict[str, EntityFacet] = {
    "user": EntityFacet.PERSONAL,
    "emotion": EntityFacet.PERSONAL,
    "soul": EntityFacet.PERSONAL,
    "infra": EntityFacet.PERSONAL,
    "todo": EntityFacet.PERSONAL,
    "concepts": EntityFacet.CONCEPT,
    "experiences": EntityFacet.EXPERIENCE,
    "methodologies": EntityFacet.METHODOLOGY,
    "projects": EntityFacet.PROJECT,
    "references": EntityFacet.REFERENCE,
    "problems": EntityFacet.EXPERIENCE,
}

TYPE_TO_FACET: dict[str, EntityFacet] = {
    # Standard facets
    "concept": EntityFacet.CONCEPT,
    "entity": EntityFacet.CONCEPT,
    "experience": EntityFacet.EXPERIENCE,
    "methodology": EntityFacet.METHODOLOGY,
    "personal": EntityFacet.PERSONAL,
    "source": EntityFacet.REFERENCE,
    "synthesis": EntityFacet.CONCEPT,
    # OpenClaw-specific types — content
    "article": EntityFacet.REFERENCE,
    "tutorial": EntityFacet.METHODOLOGY,
    "debug-log": EntityFacet.EXPERIENCE,
    "decision": EntityFacet.CONCEPT,
    "tip": EntityFacet.EXPERIENCE,
    "reference": EntityFacet.REFERENCE,
    "howto": EntityFacet.METHODOLOGY,
    "note": EntityFacet.EXPERIENCE,
    "project": EntityFacet.PROJECT,
    "area": EntityFacet.CONCEPT,
    "moc": EntityFacet.CONCEPT,
    "daily": EntityFacet.PERSONAL,
    "meeting": EntityFacet.PERSONAL,
    "idea": EntityFacet.CONCEPT,
    "bookmark": EntityFacet.REFERENCE,
    # OpenClaw-specific types — supplementary
    "skill": EntityFacet.EXPERIENCE,
    "template": EntityFacet.METHODOLOGY,
    "user": EntityFacet.PERSONAL,
    "soul": EntityFacet.PERSONAL,
    "todo": EntityFacet.PERSONAL,
    "feedback": EntityFacet.EXPERIENCE,
    "problem": EntityFacet.CONCEPT,
    "dashboard": EntityFacet.CONCEPT,
    # OpenClaw-specific types — source code analysis
    "source-code-note": EntityFacet.REFERENCE,
    "source-code-analysis": EntityFacet.REFERENCE,
    # OpenClaw-specific types — project sub-documents
    "test-report": EntityFacet.PROJECT,
    "dependency-map": EntityFacet.PROJECT,
    "design-spec": EntityFacet.PROJECT,
    "change-list": EntityFacet.PROJECT,
    "validation-report": EntityFacet.PROJECT,
    "task-anchor": EntityFacet.PROJECT,
    "integration-guide": EntityFacet.METHODOLOGY,
    "project-development": EntityFacet.PROJECT,
    "project-history": EntityFacet.PROJECT,
    "orchestrator-spec": EntityFacet.PROJECT,
    "agent-coordination": EntityFacet.PROJECT,
    "quality-gate": EntityFacet.METHODOLOGY,
    "task-decomposition": EntityFacet.METHODOLOGY,
    "knowledge-flow": EntityFacet.CONCEPT,
    "comprehensive-report": EntityFacet.PROJECT,
    "final-summary": EntityFacet.PROJECT,
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

    file_type = post.get("type", "reference")
    facet = TYPE_TO_FACET.get(file_type, EntityFacet.REFERENCE)

    parts = Path(relative_path).parts

    # Directory-level facet override takes precedence
    if parts:
        top_dir = parts[0]
        dir_facet = _DIR_FACET_OVERRIDE.get(top_dir)
        if dir_facet is not None:
            facet = dir_facet
    subdir = ""
    if len(parts) >= 2:
        top_dir = parts[0]
        subdir = _WIKI_DIR_TO_SUBDIR.get(top_dir, "")
        # Preserve OpenClaw second-level dir name (e.g. concepts/skills/ → concept/skills/)
        if not subdir and len(parts) >= 3:
            subdir = parts[1]
    if subdir:
        metadata["_subdir"] = subdir

    entity_id = _compute_id(relative_path)

    source = Source(
        type=SourceType.FILE,
        name="openclaw-wiki",
        url=relative_path,
    )

    # Preserve original creation time (frontmatter created → Entity created_at)
    entity_kwargs: dict = dict(
        id=entity_id,
        content=post.content,
        facet=facet,
        group=subdir if subdir else None,
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
    """Sync adapter for OpenClaw wiki files.

    Only syncs wiki/ content. Short-term memory (Dreaming, task indexes,
    daily task details) is excluded.
    """

    def __init__(self, wiki_path: str, store: KnowledgeStore) -> None:
        self.wiki_path = Path(wiki_path)
        self.store = store

    def sync_to_linglong(self) -> dict:
        """Read all ``.md`` files under the wiki path and sync them.

        Skips ``index.md``. Returns sync stats.
        """
        stats = {"total": 0, "created": 0, "updated": 0, "skipped": 0, "failed": 0}

        if not self.wiki_path.exists():
            logger.warning("Source path does not exist: %s", self.wiki_path)
            return stats

        md_files = [p for p in self.wiki_path.rglob("*.md")]

        for file_path in md_files:
            if file_path.name == "index.md":
                continue

            stats["total"] += 1
            try:
                relative_path = str(file_path.relative_to(self.wiki_path))
                entity = _file_to_entity(file_path, relative_path)

                existing = self.store.get(entity.id)
                if existing is not None:
                    if existing.content == entity.content:
                        stats["skipped"] += 1
                        continue
                    stats["updated"] += 1
                else:
                    stats["created"] += 1

                self.store.create(entity)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to sync %s: %s", file_path, exc)
                stats["failed"] += 1

        return stats
