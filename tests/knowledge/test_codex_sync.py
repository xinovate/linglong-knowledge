"""Tests for Codex CLI sync adapter."""

import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from linglong.core.config import LinglongConfig, set_config
from linglong.core.models import EntityStatus, SourceType
from linglong.knowledge.store import KnowledgeStore
from linglong.knowledge.sync.codex import CodexSyncAdapter


@pytest.fixture
def temp_store():
    """Create a temporary knowledge store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = LinglongConfig(
            data_dir=Path(tmpdir) / "data",
            knowledge=LinglongConfig().knowledge.model_copy(
                update={
                    "wiki_path": Path(tmpdir) / "wiki",
                    "db_path": Path(tmpdir) / "knowledge.db",
                }
            ),
        )
        set_config(config)
        store = KnowledgeStore()
        yield store


@pytest.fixture
def codex_dir(tmp_path):
    """Create a temporary Codex directory."""
    return tmp_path / "codex"


def _make_agents_md(codex_dir: Path, content: str) -> Path:
    """Helper to create an AGENTS.md file."""
    file_path = codex_dir / "AGENTS.md"
    codex_dir.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return file_path


def _make_state_sqlite(codex_dir: Path, rows: list[dict]) -> Path:
    """Helper to create a state_5.sqlite file with threads data."""
    codex_dir.mkdir(parents=True, exist_ok=True)
    db_path = codex_dir / "state_5.sqlite"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE threads (
            id TEXT PRIMARY KEY,
            title TEXT,
            cwd TEXT,
            git_sha TEXT,
            git_branch TEXT,
            model TEXT,
            created_at INTEGER,
            updated_at INTEGER,
            first_user_message TEXT,
            archived INTEGER DEFAULT 0,
            tokens_used INTEGER DEFAULT 0,
            source TEXT,
            model_provider TEXT
        )
        """)
    for row in rows:
        cursor.execute(
            """
            INSERT INTO threads
            (id, title, cwd, git_sha, git_branch, model, created_at, updated_at,
             first_user_message, archived, tokens_used, source, model_provider)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row.get("id"),
                row.get("title"),
                row.get("cwd"),
                row.get("git_sha"),
                row.get("git_branch"),
                row.get("model"),
                row.get("created_at", 0),
                row.get("updated_at", 0),
                row.get("first_user_message"),
                row.get("archived", 0),
                row.get("tokens_used", 0),
                row.get("source"),
                row.get("model_provider"),
            ),
        )
    conn.commit()
    conn.close()
    return db_path


def _make_history_jsonl(codex_dir: Path, records: list[dict]) -> Path:
    """Helper to create a history.jsonl file."""
    codex_dir.mkdir(parents=True, exist_ok=True)
    file_path = codex_dir / "history.jsonl"
    lines = [json.dumps(r, ensure_ascii=False) for r in records]
    file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return file_path


def test_sync_agents_md(temp_store, codex_dir):
    """Sync AGENTS.md and verify Entity fields and metadata."""
    content = """<claude-mem-context>
# Memory Context

# $CMEM test-project 2026-05-12 3:00pm GMT+8

Legend: 🎯session 🔴bugfix 🟣feature
Format: ID TIME TYPE TITLE

Stats: 42 obs (5,000t read) | 100,000t work | 95% savings

### May 12, 2026
100 3:00p 🔵 First observation
101 3:01p 🟣 Second observation
</claude-mem-context>
"""
    _make_agents_md(codex_dir, content)

    adapter = CodexSyncAdapter(str(codex_dir), temp_store)
    stats = adapter.sync_to_linglong()

    assert stats == {"total": 1, "created": 1, "failed": 0, "skipped": 0}

    expected_id = "codex:agents-md-" + hashlib.sha256(b"AGENTS.md").hexdigest()[:12]
    entity = temp_store.get(expected_id)
    assert entity is not None
    assert entity.content == content
    assert entity.created_by == "agent:codex"
    assert entity.status == EntityStatus.AUTO_CONFIRMED
    assert float(entity.confidence) == 0.95

    meta = entity.metadata
    assert meta.get("project") == "test-project"
    assert meta.get("last_updated") == "2026-05-12 3:00pm GMT+8"
    assert meta.get("obs_count") == 42
    assert meta.get("original_filename") == "AGENTS.md"
    assert meta.get("raw_observations") == [
        "100 3:00p 🔵 First observation",
        "101 3:01p 🟣 Second observation",
    ]

    assert len(entity.sources) == 1
    source = entity.sources[0]
    assert source.type == SourceType.FILE
    assert source.name == "codex-agents-md"
    assert source.url == "AGENTS.md"


def test_sync_state_sqlite(temp_store, codex_dir):
    """Sync state_5.sqlite threads and verify each row becomes an Entity."""
    rows = [
        {
            "id": "thread-abc",
            "title": "Fix Login Bug",
            "cwd": "/home/user/project",
            "git_sha": "abc123",
            "git_branch": "main",
            "model": "gpt-4",
            "created_at": 1700000000,
            "updated_at": 1700000100,
            "first_user_message": "Login is broken",
            "archived": 0,
            "tokens_used": 1500,
            "source": "exec",
            "model_provider": "openai",
        },
        {
            "id": "thread-def",
            "title": "Add Feature",
            "cwd": "/home/user/project2",
            "git_sha": "def456",
            "git_branch": "feature/x",
            "model": "gpt-4",
            "created_at": 1700001000,
            "updated_at": 1700001100,
            "first_user_message": "Add dark mode",
            "archived": 0,
            "tokens_used": 2000,
            "source": "exec",
            "model_provider": "openai",
        },
    ]
    _make_state_sqlite(codex_dir, rows)

    adapter = CodexSyncAdapter(str(codex_dir), temp_store)
    stats = adapter.sync_to_linglong()

    assert stats == {"total": 2, "created": 2, "failed": 0, "skipped": 0}

    expected_id_1 = "codex:thread-" + hashlib.sha256(b"thread-abc").hexdigest()[:12]
    entity_1 = temp_store.get(expected_id_1)
    assert entity_1 is not None
    assert entity_1.metadata.get("title") == "Fix Login Bug"
    assert entity_1.metadata.get("cwd") == "/home/user/project"
    assert entity_1.metadata.get("git_branch") == "main"
    assert "Login is broken" in entity_1.content

    expected_id_2 = "codex:thread-" + hashlib.sha256(b"thread-def").hexdigest()[:12]
    entity_2 = temp_store.get(expected_id_2)
    assert entity_2 is not None
    assert entity_2.metadata.get("title") == "Add Feature"


def test_sync_state_sqlite_skips_archived(temp_store, codex_dir):
    """Archived threads should not be synced."""
    rows = [
        {
            "id": "thread-active",
            "title": "Active",
            "archived": 0,
        },
        {
            "id": "thread-archived",
            "title": "Archived",
            "archived": 1,
        },
    ]
    _make_state_sqlite(codex_dir, rows)

    adapter = CodexSyncAdapter(str(codex_dir), temp_store)
    stats = adapter.sync_to_linglong()

    assert stats["total"] == 1
    assert stats["created"] == 1

    archived_id = "codex:thread-" + hashlib.sha256(b"thread-archived").hexdigest()[:12]
    assert temp_store.get(archived_id) is None


def test_sync_history_jsonl(temp_store, codex_dir):
    """Sync history.jsonl and verify aggregation by session."""
    records = [
        {"session_id": "sess-1", "ts": 1700000000, "text": "Hello"},
        {"session_id": "sess-1", "ts": 1700000001, "text": "World"},
        {"session_id": "sess-2", "ts": 1700001000, "text": "Another session"},
    ]
    _make_history_jsonl(codex_dir, records)

    adapter = CodexSyncAdapter(str(codex_dir), temp_store)
    stats = adapter.sync_to_linglong()

    assert stats == {"total": 2, "created": 2, "failed": 0, "skipped": 0}

    expected_id_1 = "codex:history-" + hashlib.sha256(b"sess-1").hexdigest()[:12]
    entity_1 = temp_store.get(expected_id_1)
    assert entity_1 is not None
    assert "Hello" in entity_1.content
    assert "World" in entity_1.content
    assert entity_1.metadata.get("message_count") == 2
    assert entity_1.metadata.get("time_range") == {"min_ts": 1700000000, "max_ts": 1700000001}

    expected_id_2 = "codex:history-" + hashlib.sha256(b"sess-2").hexdigest()[:12]
    entity_2 = temp_store.get(expected_id_2)
    assert entity_2 is not None
    assert entity_2.content == "Another session"
    assert entity_2.metadata.get("message_count") == 1


def test_sync_skips_existing(temp_store, codex_dir):
    """Existing entities should be skipped."""
    _make_agents_md(codex_dir, "# AGENTS\n")

    adapter = CodexSyncAdapter(str(codex_dir), temp_store)
    adapter.sync_to_linglong()

    stats = adapter.sync_to_linglong()
    assert stats == {"total": 1, "created": 0, "failed": 0, "skipped": 1}


def test_sync_handles_missing_path(temp_store):
    """Non-existent path returns empty stats."""
    adapter = CodexSyncAdapter("/nonexistent/path", temp_store)
    stats = adapter.sync_to_linglong()

    assert stats == {"total": 0, "created": 0, "failed": 0, "skipped": 0}


def test_sync_handles_corrupt_sqlite(temp_store, codex_dir):
    """Corrupt SQLite should count as failed but not crash."""
    _make_agents_md(codex_dir, "# AGENTS\n")

    corrupt_path = codex_dir / "state_5.sqlite"
    corrupt_path.write_bytes(b"\x80\x81\x82")  # invalid SQLite

    adapter = CodexSyncAdapter(str(codex_dir), temp_store)
    stats = adapter.sync_to_linglong()

    # AGENTS.md succeeds (1), SQLite fails (0 created for that source)
    assert stats["total"] == 1
    assert stats["created"] == 1
    assert stats["failed"] == 1
    assert stats["skipped"] == 0
