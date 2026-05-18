"""OpenClaw sync adapter.

Reads OpenClaw files from the filesystem (wiki or memory) and syncs them
into Linglong's KnowledgeStore as Entity objects.

Two modes:
- **wiki mode** (default): Reads ``.md`` files with YAML frontmatter that
  include a ``type`` field for facet mapping.
- **memory mode**: Reads ``~/.openclaw/workspace/memory/`` diary and task
  files.  Facet is inferred from the file's position in the directory tree:
  top-level daily ``*.md`` and ``*-index.md`` → ``PERSONAL``; files inside
  date sub-directories → ``EXPERIENCE``.
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


_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_FILE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}(-index)?\.md$")
_INDEX_FILE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-index\.md$")


def _detect_mode(path: Path) -> str:
    """Detect whether *path* is a wiki directory or a memory directory.

    Returns ``"memory"`` when the directory (or its basename) looks like an
    OpenClaw memory directory — i.e. it contains top-level date-named files
    or date-named subdirectories.  Otherwise returns ``"wiki"``.
    """
    if path.name == "memory":
        return "memory"
    # Heuristic: if >50% of top-level entries match date patterns → memory
    try:
        entries = list(path.iterdir())
    except OSError:
        return "wiki"
    if not entries:
        return "wiki"
    date_like = sum(
        1 for e in entries
        if _DATE_PATTERN.match(e.name) or _DATE_FILE_PATTERN.match(e.name)
    )
    return "memory" if date_like > len(entries) * 0.5 else "wiki"


def _memory_file_to_entity(file_path: Path, relative_path: str) -> Entity:
    """Convert a memory/ file into a Linglong Entity.

    Facet and subdirectory rules (aligned with docs/knowledge/design/02-directory-structure.md):
    - Top-level ``YYYY-MM-DD.md`` → ``PERSONAL/diary/``
    - Top-level ``YYYY-MM-DD-index.md`` → ``PERSONAL/diary/``
    - Inside a date subdirectory (``YYYY-MM-DD/*.md``) → ``EXPERIENCE/task-record/``
    """
    parts = Path(relative_path).parts
    is_in_subdir = len(parts) > 1

    if is_in_subdir:
        facet = EntityFacet.EXPERIENCE
        subdir = "task-record"
        file_type = "task-record"
    else:
        facet = EntityFacet.PERSONAL
        if _INDEX_FILE_PATTERN.match(Path(relative_path).name):
            subdir = "diary"
            file_type = "daily-index"
        else:
            subdir = "diary"
            file_type = "daily"

    raw_content = file_path.read_text(encoding="utf-8")
    # Strip frontmatter if present (memory files may have it)
    if raw_content.startswith("---"):
        try:
            post = frontmatter.loads(raw_content)
            content = post.content
        except Exception:  # noqa: BLE001
            content = raw_content
    else:
        content = raw_content

    entity_id = _compute_id(relative_path)

    metadata: dict = {"type": file_type, "_subdir": subdir}

    # Use file modification time as created_at
    mtime = file_path.stat().st_mtime
    created_at = datetime.fromtimestamp(mtime, tz=UTC)

    source = Source(
        type=SourceType.FILE,
        name="openclaw-memory",
        url=relative_path,
    )

    return Entity(
        id=entity_id,
        content=content,
        facet=facet,
        created_by="agent:openclaw",
        status=EntityStatus.AUTO_CONFIRMED,
        sources=[source],
        confidence=get_config().knowledge.sync_confidence,
        metadata=metadata,
        created_at=created_at,
    )


class OpenClawSyncAdapter:
    """Sync adapter for OpenClaw files (wiki or memory)."""

    def __init__(self, wiki_path: str, store: KnowledgeStore) -> None:
        self.wiki_path = Path(wiki_path)
        self.store = store
        self._mode = _detect_mode(self.wiki_path)

    def sync_to_linglong(self) -> dict:
        """Read all ``.md`` files under the source path and sync them.

        In **wiki mode** skips ``index.md``.
        Returns sync stats ``{"total": N, "created": N, "failed": N}``.
        """
        stats = {"total": 0, "created": 0, "failed": 0}

        if not self.wiki_path.exists():
            logger.warning("Source path does not exist: %s", self.wiki_path)
            return stats

        md_files = [p for p in self.wiki_path.rglob("*.md")]

        for file_path in md_files:
            # Skip index.md in wiki mode
            if self._mode == "wiki" and file_path.name == "index.md":
                continue

            stats["total"] += 1
            try:
                relative_path = str(file_path.relative_to(self.wiki_path))
                if self._mode == "memory":
                    entity = _memory_file_to_entity(file_path, relative_path)
                else:
                    entity = _file_to_entity(file_path, relative_path)
                self.store.create(entity)
                stats["created"] += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to sync %s: %s", file_path, exc)
                stats["failed"] += 1

        return stats
