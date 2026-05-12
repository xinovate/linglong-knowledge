"""Tests for OpenClaw wiki sync adapter."""

import hashlib
import tempfile
from pathlib import Path

import pytest

from linglong.core.config import LinglongConfig, set_config
from linglong.core.models import EntityStatus, SourceType
from linglong.knowledge.store import KnowledgeStore
from linglong.knowledge.sync.openclaw import OpenClawSyncAdapter


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
def wiki_dir(tmp_path):
    """Create a temporary wiki directory."""
    return tmp_path / "wiki"


def _make_wiki_file(wiki_dir: Path, rel_path: str, content: str) -> Path:
    """Helper to create a wiki file inside the temporary wiki directory."""
    file_path = wiki_dir / rel_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return file_path


def test_sync_single_file(temp_store, wiki_dir):
    """Sync one wiki file and verify Entity fields."""
    content = """---
type: reference
description: A test description
created: 2026-04-09
---

# Test Reference

Some content here.
"""
    _make_wiki_file(wiki_dir, "concepts/test-reference.md", content)

    adapter = OpenClawSyncAdapter(str(wiki_dir), temp_store)
    stats = adapter.sync_to_linglong()

    assert stats == {"total": 1, "created": 1, "failed": 0}

    expected_id = hashlib.sha256(b"concepts/test-reference.md").hexdigest()[:16]
    entity = temp_store.get(expected_id)
    assert entity is not None
    assert entity.content == content
    assert entity.created_by == "agent:openclaw"
    assert entity.status == EntityStatus.AUTO_CONFIRMED
    assert float(entity.confidence) == 0.95
    entity_meta = entity.metadata
    assert entity_meta.get("type") == "reference"
    assert entity_meta.get("description") == "A test description"
    assert entity_meta.get("created") == "2026-04-09"

    assert len(entity.sources) == 1
    source = entity.sources[0]
    assert source.type == SourceType.FILE
    assert source.name == "openclaw-wiki"
    assert source.url == "concepts/test-reference.md"


def test_sync_skips_index_md(temp_store, wiki_dir):
    """index.md should be skipped during sync."""
    _make_wiki_file(wiki_dir, "index.md", "# Index\n")
    _make_wiki_file(wiki_dir, "concepts/valid.md", "# Valid\n")

    adapter = OpenClawSyncAdapter(str(wiki_dir), temp_store)
    stats = adapter.sync_to_linglong()

    assert stats["total"] == 1
    assert stats["created"] == 1
    assert stats["failed"] == 0


def test_sync_extracts_wikilinks(temp_store, wiki_dir):
    """Verify wikilinks are parsed and deduplicated correctly."""
    content = """---
type: concept
---

# Concept A

See also [[concepts/concept-b|Concept B]] and [[concepts/concept-b]]
and [[references/ref-a|Reference A]].
"""
    _make_wiki_file(wiki_dir, "concepts/concept-a.md", content)

    adapter = OpenClawSyncAdapter(str(wiki_dir), temp_store)
    adapter.sync_to_linglong()

    expected_id = hashlib.sha256(b"concepts/concept-a.md").hexdigest()[:16]
    entity = temp_store.get(expected_id)
    assert entity is not None
    entity_meta = entity.metadata
    assert entity_meta.get("wikilinks") == [
        "concepts/concept-b",
        "references/ref-a",
    ]


def test_sync_stats(temp_store, wiki_dir):
    """Verify returned stats dict after syncing multiple files."""
    _make_wiki_file(wiki_dir, "concepts/a.md", "# A\n")
    _make_wiki_file(wiki_dir, "experiences/b.md", "# B\n")
    _make_wiki_file(wiki_dir, "index.md", "# Index\n")

    adapter = OpenClawSyncAdapter(str(wiki_dir), temp_store)
    stats = adapter.sync_to_linglong()

    assert stats == {"total": 2, "created": 2, "failed": 0}


def test_sync_handles_corrupt_file(temp_store, wiki_dir):
    """A corrupt/unreadable file should increment failed count."""
    _make_wiki_file(wiki_dir, "concepts/valid.md", "# Valid\n")

    corrupt_path = wiki_dir / "concepts/corrupt.md"
    corrupt_path.parent.mkdir(parents=True, exist_ok=True)
    corrupt_path.write_bytes(b"\x80\x81\x82")  # invalid UTF-8

    adapter = OpenClawSyncAdapter(str(wiki_dir), temp_store)
    stats = adapter.sync_to_linglong()

    assert stats["total"] == 2
    assert stats["created"] == 1
    assert stats["failed"] == 1
