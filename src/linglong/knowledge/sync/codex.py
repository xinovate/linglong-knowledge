"""Codex CLI sync adapter.

Reads Codex CLI data files from the filesystem and syncs them into
Linglong's KnowledgeStore as Entity objects.

Data sources:
- AGENTS.md       : claude-mem format project memory context
- state_5.sqlite  : thread metadata (title, cwd, git info, model)
- history.jsonl   : user input history grouped by session
"""

import hashlib
import json
import logging
import sqlite3
from pathlib import Path

from linglong.core.config import get_config
from linglong.core.models import Entity, EntityStatus, Source, SourceType
from linglong.knowledge.store import KnowledgeStore

logger = logging.getLogger(__name__)


def _compute_id(prefix: str, key: str) -> str:
    """Compute a stable entity ID with codex namespace."""
    sha = hashlib.sha256(key.encode("utf-8")).hexdigest()[:12]
    return f"codex:{prefix}-{sha}"


def _parse_agents_md(content: str) -> dict:
    """Parse AGENTS.md claude-mem content into metadata dict."""
    metadata: dict = {"source_type": "agents-md"}

    # 提取 <claude-mem-context> 标签之间的内容
    start_tag = "<claude-mem-context>"
    end_tag = "</claude-mem-context>"
    start_idx = content.find(start_tag)
    end_idx = content.find(end_tag)
    if start_idx != -1 and end_idx != -1:
        inner = content[start_idx + len(start_tag) : end_idx].strip()
    else:
        inner = content

    lines = inner.splitlines()

    # 解析 $CMEM 行获取项目名和更新时间
    for line in lines:
        if line.strip().startswith("# $CMEM"):
            parts = line.strip().split()
            if len(parts) >= 3:
                metadata["project"] = parts[2]
            if len(parts) >= 4:
                metadata["last_updated"] = " ".join(parts[3:])
            break

    # 解析 Stats 行
    for line in lines:
        if line.strip().startswith("Stats:"):
            metadata["stats_line"] = line.strip()
            # 尝试提取观察记录数量
            try:
                obs_part = line.strip().split("|")[0]
                obs_count_str = obs_part.replace("Stats:", "").strip().split()[0]
                metadata["obs_count"] = int(obs_count_str)
            except (ValueError, IndexError):
                pass
            break

    # 提取观察记录标题（含 🔵 🟣 🔴 🔄 ✅ ⚖️ 的行）
    # 跳过表头行如 "Legend:", "Format:", "Stats:"
    observations: list[str] = []
    emoji_markers = ("🔵", "🟣", "🔴", "🔄", "✅", "⚖️")
    skip_prefixes = ("Legend:", "Format:", "Stats:")
    for line in lines:
        stripped = line.strip()
        if any(stripped.startswith(prefix) for prefix in skip_prefixes):
            continue
        if any(marker in stripped for marker in emoji_markers):
            observations.append(stripped)
    metadata["raw_observations"] = observations[:10]

    return metadata


def _sync_agents_md(codex_path: Path, store: KnowledgeStore, stats: dict) -> None:
    """Sync AGENTS.md into the store."""
    agents_path = codex_path / "AGENTS.md"
    if not agents_path.exists():
        return

    stats["total"] += 1
    try:
        raw_content = agents_path.read_text(encoding="utf-8")
        entity_id = _compute_id("agents-md", "AGENTS.md")

        if store.get(entity_id) is not None:
            stats["skipped"] += 1
            return

        metadata = _parse_agents_md(raw_content)
        metadata["original_filename"] = "AGENTS.md"

        source = Source(
            type=SourceType.FILE,
            name="codex-agents-md",
            url="AGENTS.md",
        )

        entity = Entity(
            id=entity_id,
            content=raw_content,
            created_by="agent:codex",
            status=EntityStatus.AUTO_CONFIRMED,
            sources=[source],
            confidence=get_config().knowledge.sync_confidence,
            metadata=metadata,
        )
        store.create(entity)
        stats["created"] += 1
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to sync AGENTS.md: %s", exc)
        stats["failed"] += 1


def _sync_state_sqlite(codex_path: Path, store: KnowledgeStore, stats: dict) -> None:
    """Sync state_5.sqlite threads into the store."""
    db_path = codex_path / "state_5.sqlite"
    if not db_path.exists():
        return

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, title, cwd, git_sha, git_branch, model, "
            "created_at, updated_at, first_user_message, archived, "
            "tokens_used, source, model_provider "
            "FROM threads WHERE archived = 0"
        )
        rows = cursor.fetchall()
        conn.close()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read state_5.sqlite: %s", exc)
        stats["failed"] += 1
        return

    for row in rows:
        stats["total"] += 1
        try:
            thread_id = row["id"]
            entity_id = _compute_id("thread", thread_id)

            if store.get(entity_id) is not None:
                stats["skipped"] += 1
                continue

            metadata = {
                "thread_id": thread_id,
                "source": "state.sqlite",
                "title": row["title"] or "",
                "cwd": row["cwd"] or "",
                "git_sha": row["git_sha"] or "",
                "git_branch": row["git_branch"] or "",
                "model": row["model"] or row["model_provider"] or "",
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "tokens_used": row["tokens_used"],
                "origin": row["source"] or "",
            }

            content_parts = [f"# {row['title'] or 'Untitled'}"]
            if row["cwd"]:
                content_parts.append(f"\n**CWD**: {row['cwd']}")
            if row["git_branch"]:
                content_parts.append(f"**Git Branch**: {row['git_branch']}")
            if row["git_sha"]:
                content_parts.append(f"**Git SHA**: {row['git_sha']}")
            if row["first_user_message"]:
                content_parts.append(f"\n**First Message**:\n{row['first_user_message']}")

            content = "\n".join(content_parts)

            source = Source(
                type=SourceType.FILE,
                name="codex-state-sqlite",
                url=f"state_5.sqlite:{thread_id}",
            )

            entity = Entity(
                id=entity_id,
                content=content,
                created_by="agent:codex",
                status=EntityStatus.AUTO_CONFIRMED,
                sources=[source],
                confidence=get_config().knowledge.sync_confidence,
                metadata=metadata,
            )
            store.create(entity)
            stats["created"] += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to sync thread %s: %s", row.get("id", "?"), exc)
            stats["failed"] += 1


def _sync_history_jsonl(codex_path: Path, store: KnowledgeStore, stats: dict) -> None:
    """Sync history.jsonl into the store grouped by session."""
    history_path = codex_path / "history.jsonl"
    if not history_path.exists():
        return

    try:
        raw_lines = history_path.read_text(encoding="utf-8").splitlines()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to read history.jsonl: %s", exc)
        stats["failed"] += 1
        return

    sessions: dict[str, dict] = {}
    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        session_id = record.get("session_id")
        if not session_id:
            continue

        if session_id not in sessions:
            sessions[session_id] = {
                "texts": [],
                "timestamps": [],
            }
        sessions[session_id]["texts"].append(record.get("text", ""))
        sessions[session_id]["timestamps"].append(record.get("ts", 0))

    for session_id, data in sessions.items():
        stats["total"] += 1
        try:
            entity_id = _compute_id("history", session_id)

            if store.get(entity_id) is not None:
                stats["skipped"] += 1
                continue

            texts = data["texts"]
            timestamps = data["timestamps"]
            content = "\n\n".join(texts)

            metadata = {
                "session_id": session_id,
                "source": "history.jsonl",
                "message_count": len(texts),
                "time_range": {
                    "min_ts": min(timestamps) if timestamps else 0,
                    "max_ts": max(timestamps) if timestamps else 0,
                },
            }

            source = Source(
                type=SourceType.FILE,
                name="codex-history-jsonl",
                url=f"history.jsonl:{session_id}",
            )

            entity = Entity(
                id=entity_id,
                content=content,
                created_by="agent:codex",
                status=EntityStatus.AUTO_CONFIRMED,
                sources=[source],
                confidence=get_config().knowledge.sync_confidence,
                metadata=metadata,
            )
            store.create(entity)
            stats["created"] += 1
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to sync history session %s: %s", session_id, exc)
            stats["failed"] += 1


class CodexSyncAdapter:
    """Sync adapter for Codex CLI data files."""

    def __init__(self, codex_path: str, store: KnowledgeStore) -> None:
        self.codex_path = Path(codex_path)
        self.store = store

    def sync_to_linglong(self) -> dict:
        """Read all Codex data sources and sync them into the store.

        Returns sync stats ``{"total": N, "created": N, "failed": N, "skipped": N}``.
        """
        stats = {"total": 0, "created": 0, "failed": 0, "skipped": 0}

        if not self.codex_path.exists():
            logger.warning("Codex path does not exist: %s", self.codex_path)
            return stats

        _sync_agents_md(self.codex_path, self.store, stats)
        _sync_state_sqlite(self.codex_path, self.store, stats)
        _sync_history_jsonl(self.codex_path, self.store, stats)

        return stats
