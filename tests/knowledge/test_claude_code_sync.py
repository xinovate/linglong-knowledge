"""Tests for Claude Code memory sync adapter."""

import hashlib
import tempfile
from pathlib import Path

import pytest

from linglong.core.config import LinglongConfig, set_config
from linglong.core.models import EntityStatus, SourceType
from linglong.knowledge.store import KnowledgeStore
from linglong.knowledge.sync.claude_code import ClaudeCodeSyncAdapter


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
def memory_dir(tmp_path):
    """Create a temporary memory directory."""
    return tmp_path / "memory"


def _make_memory_file(memory_dir: Path, filename: str, content: str) -> Path:
    """Helper to create a memory file inside the temporary memory directory."""
    file_path = memory_dir / filename
    memory_dir.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return file_path


def test_sync_single_feedback(temp_store, memory_dir):
    """Sync one feedback type file and verify Entity fields and metadata."""
    content = """---
name: "UX Feedback"
description: "User reported navigation confusion"
type: feedback
originSessionId: "sess-123"
---

# UX Feedback

User found the sidebar confusing.
"""
    _make_memory_file(memory_dir, "ux-feedback.md", content)

    adapter = ClaudeCodeSyncAdapter(str(memory_dir), temp_store)
    stats = adapter.sync_to_linglong()

    assert stats == {"total": 1, "created": 1, "failed": 0, "skipped": 0}

    expected_id = "claude:" + hashlib.sha256(b"ux-feedback.md").hexdigest()[:16]
    entity = temp_store.get(expected_id)
    assert entity is not None
    assert entity.content == content
    assert entity.created_by == "agent:claude"
    assert entity.status == EntityStatus.AUTO_CONFIRMED
    assert float(entity.confidence) == 0.95

    assert entity.metadata.get("name") == "UX Feedback"
    assert entity.metadata.get("description") == "User reported navigation confusion"
    assert entity.metadata.get("type") == "feedback"
    assert entity.metadata.get("originSessionId") == "sess-123"
    assert entity.metadata.get("wiki_directory") == "experiences"
    assert entity.metadata.get("original_filename") == "ux-feedback.md"

    assert len(entity.sources) == 1
    source = entity.sources[0]
    assert source.type == SourceType.FILE
    assert source.name == "claude-code-memory"
    assert source.url == "ux-feedback.md"


def test_sync_single_project(temp_store, memory_dir):
    """Sync one project type file and verify directory mapping in metadata."""
    content = """---
name: "Linglong"
description: "Cross-agent knowledge hub"
type: project
originSessionId: "sess-456"
---

# Linglong

Project notes here.
"""
    _make_memory_file(memory_dir, "linglong.md", content)

    adapter = ClaudeCodeSyncAdapter(str(memory_dir), temp_store)
    stats = adapter.sync_to_linglong()

    assert stats == {"total": 1, "created": 1, "failed": 0, "skipped": 0}

    expected_id = "claude:" + hashlib.sha256(b"linglong.md").hexdigest()[:16]
    entity = temp_store.get(expected_id)
    assert entity is not None
    assert entity.metadata.get("wiki_directory") == "projects"
    assert entity.metadata.get("original_filename") == "linglong.md"


def test_sync_skips_memory_md(temp_store, memory_dir):
    """MEMORY.md is skipped."""
    _make_memory_file(memory_dir, "MEMORY.md", "# Index\n")
    _make_memory_file(memory_dir, "valid.md", "# Valid\n")

    adapter = ClaudeCodeSyncAdapter(str(memory_dir), temp_store)
    stats = adapter.sync_to_linglong()

    assert stats["total"] == 1
    assert stats["created"] == 1
    assert stats["failed"] == 0
    assert stats["skipped"] == 0


def test_sync_skips_existing(temp_store, memory_dir):
    """Existing entity skipped, skipped count incremented."""
    content = "# Existing\n"
    _make_memory_file(memory_dir, "existing.md", content)

    adapter = ClaudeCodeSyncAdapter(str(memory_dir), temp_store)
    adapter.sync_to_linglong()

    stats = adapter.sync_to_linglong()
    assert stats == {"total": 1, "created": 0, "failed": 0, "skipped": 1}


def test_sync_conflict_detection(temp_store, memory_dir):
    """Same ID already exists, not overwritten."""
    content = "# Original\n"
    _make_memory_file(memory_dir, "conflict.md", content)

    adapter = ClaudeCodeSyncAdapter(str(memory_dir), temp_store)
    adapter.sync_to_linglong()

    _make_memory_file(memory_dir, "conflict.md", "# Modified\n")
    stats = adapter.sync_to_linglong()

    assert stats == {"total": 1, "created": 0, "failed": 0, "skipped": 1}

    expected_id = "claude:" + hashlib.sha256(b"conflict.md").hexdigest()[:16]
    entity = temp_store.get(expected_id)
    assert entity.content == "# Original\n"


def test_sync_handles_corrupt_file(temp_store, memory_dir):
    """Invalid UTF-8 counted as failed."""
    _make_memory_file(memory_dir, "valid.md", "# Valid\n")

    corrupt_path = memory_dir / "corrupt.md"
    corrupt_path.write_bytes(b"\x80\x81\x82")

    adapter = ClaudeCodeSyncAdapter(str(memory_dir), temp_store)
    stats = adapter.sync_to_linglong()

    assert stats["total"] == 2
    assert stats["created"] == 1
    assert stats["failed"] == 1
    assert stats["skipped"] == 0


def test_sync_unknown_type(temp_store, memory_dir):
    """File without type maps to concepts/."""
    content = """---
name: "Random Thought"
description: "Something unclassified"
---

# Random Thought

No type specified.
"""
    _make_memory_file(memory_dir, "random.md", content)

    adapter = ClaudeCodeSyncAdapter(str(memory_dir), temp_store)
    stats = adapter.sync_to_linglong()

    assert stats == {"total": 1, "created": 1, "failed": 0, "skipped": 0}

    expected_id = "claude:" + hashlib.sha256(b"random.md").hexdigest()[:16]
    entity = temp_store.get(expected_id)
    assert entity is not None
    assert entity.metadata.get("wiki_directory") == "concepts"
    assert entity.metadata.get("type") is None
