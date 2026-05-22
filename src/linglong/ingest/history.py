"""Ingest history persistence — SQLite table for cross-day dedup."""

import hashlib
import json
import logging
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from linglong.core.models import Entity

logger = logging.getLogger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ingest_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT,
    summary TEXT,
    entities_mentioned TEXT,
    dimension TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    collected_at TEXT NOT NULL
)
"""

_CREATE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_history_hash ON ingest_history(content_hash)
"""

_CREATE_DIMENSION_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_history_dimension ON ingest_history(dimension, collected_at)
"""


class IngestHistory:
    """Persist and query ingest results for cross-day dedup."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            db_path = Path.home() / "linglong" / "data" / "ingest_history.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_table()

    def _ensure_table(self) -> None:
        with self._connect() as conn:
            conn.execute(_CREATE_TABLE_SQL)
            conn.execute(_CREATE_INDEX_SQL)
            conn.execute(_CREATE_DIMENSION_INDEX_SQL)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def content_hash(entity: Entity) -> str:
        """Compute a content hash for dedup."""
        text = entity.content.strip().lower()
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    @staticmethod
    def title_hash(title: str) -> str:
        """Compute a short hash from a title for fuzzy matching."""
        return hashlib.sha256(title.strip().lower().encode()).hexdigest()[:12]

    def write_batch(
        self,
        entities: list[Entity],
        dimension: str = "",
    ) -> int:
        """Write a batch of entities to history. Returns count written."""
        now = datetime.now(UTC).isoformat()
        written = 0

        with self._connect() as conn:
            for entity in entities:
                title = self._extract_title(entity)
                url = self._extract_url(entity)
                summary = self._extract_summary(entity)
                chash = self.content_hash(entity)

                try:
                    conn.execute(
                        "INSERT INTO ingest_history "
                        "(title, url, summary, entities_mentioned, dimension, content_hash, collected_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (title, url, summary, json.dumps([]), dimension, chash, now),
                    )
                    written += 1
                except sqlite3.Error as e:
                    logger.warning("Failed to write history for '%s': %s", title, e)

            conn.commit()

        logger.info("Wrote %d entries to ingest_history (dimension=%s)", written, dimension)
        return written

    def query_recent(
        self,
        days: int = 7,
        dimension: str = "",
    ) -> list[dict[str, Any]]:
        """Query recent history entries within N days."""
        cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()

        with self._connect() as conn:
            if dimension:
                rows = conn.execute(
                    "SELECT * FROM ingest_history WHERE collected_at > ? AND dimension = ? "
                    "ORDER BY collected_at DESC",
                    (cutoff, dimension),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM ingest_history WHERE collected_at > ? "
                    "ORDER BY collected_at DESC",
                    (cutoff,),
                ).fetchall()

        return [dict(r) for r in rows]

    def find_by_hash(self, content_hash: str) -> list[dict[str, Any]]:
        """Find history entries by exact content hash."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM ingest_history WHERE content_hash = ?",
                (content_hash,),
            ).fetchall()
        return [dict(r) for r in rows]

    def find_by_title_similarity(
        self,
        title: str,
        days: int = 7,
        threshold: float = 0.5,
    ) -> list[dict[str, Any]]:
        """Find history entries with similar titles (keyword overlap ratio).

        Uses simple keyword overlap: |intersection| / |union| >= threshold.
        """
        query_words = set(title.lower().split())
        if not query_words:
            return []

        recent = self.query_recent(days=days)
        matches: list[dict[str, Any]] = []

        for entry in recent:
            entry_words = set(entry.get("title", "").lower().split())
            if not entry_words:
                continue
            intersection = query_words & entry_words
            union = query_words | entry_words
            ratio = len(intersection) / len(union) if union else 0
            if ratio >= threshold:
                entry["_similarity"] = ratio
                matches.append(entry)

        matches.sort(key=lambda x: x.get("_similarity", 0), reverse=True)
        return matches

    def _extract_title(self, entity: Entity) -> str:
        for line in entity.content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return entity.content[:100].strip()

    def _extract_url(self, entity: Entity) -> str:
        if entity.sources:
            return entity.sources[0].url or ""
        return ""

    def _extract_summary(self, entity: Entity) -> str:
        lines = entity.content.split("\n")
        past_title = False
        parts: list[str] = []
        for line in lines:
            s = line.strip()
            if not past_title:
                if s.startswith("# "):
                    past_title = True
                continue
            if s.startswith("[Source]") or s.startswith("["):
                break
            if s:
                parts.append(s)
        return " ".join(parts)[:300]
