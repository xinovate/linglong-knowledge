"""Claude Code memory sync adapter.

Reads Claude Code memory files from the filesystem and syncs them into
Linglong's KnowledgeStore as Entity objects.
"""

import hashlib
import logging
from pathlib import Path

import frontmatter

from linglong.core.models import Entity, EntityStatus, Source, SourceType
from linglong.knowledge.store import KnowledgeStore

logger = logging.getLogger(__name__)

_TYPE_TO_DIR: dict[str, str] = {
    "feedback": "experiences",
    "project": "projects",
    "user": "user",
    "reference": "references",
}


def _compute_id(filename: str) -> str:
    """Compute a stable entity ID from the memory filename."""
    sha = hashlib.sha256(filename.encode("utf-8")).hexdigest()[:16]
    return f"claude:{sha}"


def _file_to_entity(file_path: Path, relative_path: str) -> Entity:
    """Convert a single Claude Code memory file into a Linglong Entity."""
    raw_content = file_path.read_text(encoding="utf-8")
    post = frontmatter.loads(raw_content)

    metadata: dict = {}
    for key in ("name", "description", "type", "originSessionId"):
        value = post.get(key)
        if value is not None:
            metadata[key] = value

    file_type = post.get("type")
    wiki_dir = _TYPE_TO_DIR.get(file_type, "concepts")
    metadata["wiki_directory"] = wiki_dir
    metadata["original_filename"] = file_path.name

    entity_id = _compute_id(file_path.name)

    source = Source(
        type=SourceType.FILE,
        name="claude-code-memory",
        url=relative_path,
    )

    return Entity(
        id=entity_id,
        content=raw_content,
        created_by="agent:claude",
        status=EntityStatus.AUTO_CONFIRMED,
        sources=[source],
        confidence=0.95,
        metadata=metadata,
    )


class ClaudeCodeSyncAdapter:
    """Sync adapter for Claude Code memory files."""

    def __init__(self, memory_path: str, store: KnowledgeStore) -> None:
        self.memory_path = Path(memory_path)
        self.store = store

    def sync_to_linglong(self) -> dict:
        """Read all ``.md`` files under ``memory_path`` and sync them into the store.

        Skips ``MEMORY.md``. Returns sync stats
        ``{"total": N, "created": N, "failed": N, "skipped": N}``.
        """
        stats = {"total": 0, "created": 0, "failed": 0, "skipped": 0}

        if not self.memory_path.exists():
            logger.warning("Memory path does not exist: %s", self.memory_path)
            return stats

        md_files = [
            p
            for p in self.memory_path.iterdir()
            if p.is_file() and p.suffix == ".md" and p.name != "MEMORY.md"
        ]

        for file_path in md_files:
            stats["total"] += 1
            try:
                relative_path = str(file_path.relative_to(self.memory_path))
                entity_id = _compute_id(file_path.name)
                if self.store.get(entity_id) is not None:
                    stats["skipped"] += 1
                    continue
                entity = _file_to_entity(file_path, relative_path)
                self.store.create(entity)
                stats["created"] += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to sync %s: %s", file_path, exc)
                stats["failed"] += 1

        return stats
