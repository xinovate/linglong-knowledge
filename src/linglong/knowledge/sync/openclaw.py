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

# OpenClaw wiki 第一级目录 → Linglong wiki 子目录映射
# 按设计文档 02-directory-structure.md 的 OpenClaw 13 目录 → 7 Facet 映射
_WIKI_DIR_TO_SUBDIR: dict[str, str] = {
    "projects": "projects",
    "references": "references",
    "problems": "problems",
    "concepts": "",         # concept 扁平，子目录保留原名
    "experiences": "",      # experience 扁平，子目录保留原名
    "methodologies": "",    # methodology 扁平
    "user": "",             # personal 扁平
    "emotion": "",          # 合入 personal 扁平
    "soul": "diary",        # 合入 personal/diary/
    "infra": "infra",       # 合入 personal/infra/
    "dashboards": "",       # 不迁移
    "templates": "",        # 不迁移
    "todo": "",             # 合入 personal 扁平
}

# 目录级 facet 覆盖：某些目录的文件无论 frontmatter type 是什么都应归入特定 facet
_DIR_FACET_OVERRIDE: dict[str, EntityFacet] = {
    "user": EntityFacet.PERSONAL,
    "emotion": EntityFacet.PERSONAL,
    "soul": EntityFacet.PERSONAL,
    "infra": EntityFacet.PERSONAL,
    "todo": EntityFacet.PERSONAL,
    "concepts": EntityFacet.CONCEPT,
    "experiences": EntityFacet.EXPERIENCE,
    "methodologies": EntityFacet.METHODOLOGY,
    "projects": EntityFacet.SOURCE,
    "references": EntityFacet.SOURCE,
    "problems": EntityFacet.SOURCE,
}

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

    # 推导子目录：取 relative_path 的前两级
    parts = Path(relative_path).parts

    # 目录级 facet 覆盖：按所在目录强制指定 facet
    if parts:
        top_dir = parts[0]
        dir_facet = _DIR_FACET_OVERRIDE.get(top_dir)
        if dir_facet is not None:
            facet = dir_facet
    subdir = ""
    if len(parts) >= 2:
        top_dir = parts[0]
        subdir = _WIKI_DIR_TO_SUBDIR.get(top_dir, "")
        # 保留 OpenClaw 二级目录名（如 concepts/skills/ → concept/skills/）
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
