"""Tests for OpenClaw wiki sync adapter."""

import hashlib
import tempfile
from pathlib import Path

import pytest

from linglong.core.config import LinglongConfig, set_config
from linglong.core.models import EntityFacet, EntityStatus, SourceType
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
    assert entity.content == "# Test Reference\n\nSome content here."
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


def test_facet_mapping_from_type():
    """OpenClaw type 映射到正确的 EntityFacet。"""
    from linglong.core.models import EntityFacet
    from linglong.knowledge.sync.openclaw import TYPE_TO_FACET, _file_to_entity

    assert TYPE_TO_FACET["concept"] == EntityFacet.CONCEPT
    assert TYPE_TO_FACET["article"] == EntityFacet.SOURCE
    assert TYPE_TO_FACET["tutorial"] == EntityFacet.METHODOLOGY
    assert TYPE_TO_FACET["daily"] == EntityFacet.PERSONAL

    # 带有 type frontmatter 的文件
    with tempfile.TemporaryDirectory() as tmpdir:
        f = Path(tmpdir) / "test.md"
        f.write_text("---\ntype: concept\n---\n# 测试", encoding="utf-8")
        entity = _file_to_entity(f, "test.md")
        assert entity.facet == EntityFacet.CONCEPT

    # 未知 type 回退到 SOURCE
    with tempfile.TemporaryDirectory() as tmpdir:
        f = Path(tmpdir) / "test.md"
        f.write_text("---\ntype: unknown_type\n---\n# 测试", encoding="utf-8")
        entity = _file_to_entity(f, "test.md")
        assert entity.facet == EntityFacet.SOURCE


# ---------------------------------------------------------------------------
# Memory directory sync tests
# ---------------------------------------------------------------------------


@pytest.fixture
def memory_dir(tmp_path):
    """Create a temporary memory directory mimicking OpenClaw structure."""
    mem = tmp_path / "memory"
    mem.mkdir()
    return mem


def _make_memory_file(memory_dir: Path, rel_path: str, content: str) -> Path:
    """Helper to create a file inside the memory directory."""
    file_path = memory_dir / rel_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return file_path


def test_memory_sync_daily_file(temp_store, memory_dir):
    """Top-level daily YYYY-MM-DD.md → PERSONAL/diary/ subdirectory."""
    _make_memory_file(memory_dir, "2026-04-12.md", "# 日记\n\n今天完成了 sync 适配器。")

    adapter = OpenClawSyncAdapter(str(memory_dir), temp_store)
    stats = adapter.sync_to_linglong()

    assert stats == {"total": 1, "created": 1, "failed": 0}

    expected_id = hashlib.sha256(b"2026-04-12.md").hexdigest()[:16]
    entity = temp_store.get(expected_id)
    assert entity is not None
    assert entity.facet == EntityFacet.PERSONAL
    assert entity.metadata.get("type") == "daily"
    assert entity.metadata.get("_subdir") == "diary"
    assert entity.sources[0].name == "openclaw-memory"
    assert entity.created_at is not None

    # 文件落在 wiki/personal/diary/ 子目录
    diary_dir = temp_store.wiki_path / "personal" / "diary"
    assert diary_dir.exists()
    files = list(diary_dir.glob("*.md"))
    assert len(files) == 1


def test_memory_sync_index_file(temp_store, memory_dir):
    """Top-level YYYY-MM-DD-index.md → PERSONAL/diary/ subdirectory."""
    _make_memory_file(memory_dir, "2026-04-07-index.md", "# 任务索引\n\n任务列表")

    adapter = OpenClawSyncAdapter(str(memory_dir), temp_store)
    stats = adapter.sync_to_linglong()

    assert stats == {"total": 1, "created": 1, "failed": 0}

    expected_id = hashlib.sha256(b"2026-04-07-index.md").hexdigest()[:16]
    entity = temp_store.get(expected_id)
    assert entity is not None
    assert entity.facet == EntityFacet.PERSONAL
    assert entity.metadata.get("type") == "daily-index"
    assert entity.metadata.get("_subdir") == "diary"

    # 文件落在 wiki/personal/diary/ 子目录
    idx_dir = temp_store.wiki_path / "personal" / "diary"
    assert idx_dir.exists()
    files = list(idx_dir.glob("*.md"))
    assert len(files) == 1


def test_memory_sync_subdir_file(temp_store, memory_dir):
    """Files inside YYYY-MM-DD/ → EXPERIENCE/task-record/ subdirectory."""
    _make_memory_file(
        memory_dir,
        "2026-04-09/task-completion-summary.md",
        "# 任务完成摘要\n\nACP兼容性测试成功。",
    )

    adapter = OpenClawSyncAdapter(str(memory_dir), temp_store)
    stats = adapter.sync_to_linglong()

    assert stats == {"total": 1, "created": 1, "failed": 0}

    expected_id = hashlib.sha256(b"2026-04-09/task-completion-summary.md").hexdigest()[:16]
    entity = temp_store.get(expected_id)
    assert entity is not None
    assert entity.facet == EntityFacet.EXPERIENCE
    assert entity.metadata.get("type") == "task-record"
    assert entity.metadata.get("_subdir") == "task-record"

    # 文件落在 wiki/experience/task-record/ 子目录
    tr_dir = temp_store.wiki_path / "experience" / "task-record"
    assert tr_dir.exists()
    files = list(tr_dir.glob("*.md"))
    assert len(files) == 1


def test_memory_sync_mixed_files(temp_store, memory_dir):
    """Sync a mix of daily, index, and subdirectory files."""
    _make_memory_file(memory_dir, "2026-04-12.md", "# 日记\n")
    _make_memory_file(memory_dir, "2026-04-07-index.md", "# 索引\n")
    _make_memory_file(memory_dir, "2026-04-09/acp-test.md", "# ACP测试\n")
    _make_memory_file(memory_dir, "2026-04-09/upgrade.md", "# 升级\n")

    adapter = OpenClawSyncAdapter(str(memory_dir), temp_store)
    stats = adapter.sync_to_linglong()

    assert stats == {"total": 4, "created": 4, "failed": 0}

    # 验证各类 facet
    all_entities = temp_store.search(limit=100)
    facets = {e.facet for e in all_entities}
    assert EntityFacet.PERSONAL in facets
    assert EntityFacet.EXPERIENCE in facets


def test_memory_sync_with_frontmatter(temp_store, memory_dir):
    """Memory files with YAML frontmatter should strip it from content."""
    _make_memory_file(
        memory_dir,
        "2026-04-05.md",
        "---\ntitle: Test Diary\ndate: 2026-04-05\n---\n\n# 日记\n\n内容",
    )

    adapter = OpenClawSyncAdapter(str(memory_dir), temp_store)
    stats = adapter.sync_to_linglong()

    assert stats == {"total": 1, "created": 1, "failed": 0}

    expected_id = hashlib.sha256(b"2026-04-05.md").hexdigest()[:16]
    entity = temp_store.get(expected_id)
    assert entity is not None
    # content should not include frontmatter
    assert "---" not in entity.content
    assert "# 日记" in entity.content


def test_detect_mode_memory(memory_dir):
    """_detect_mode returns 'memory' for memory-like directories."""
    from linglong.knowledge.sync.openclaw import _detect_mode

    # Create date-like entries to trigger memory detection
    (memory_dir / "2026-04-05.md").write_text("", encoding="utf-8")
    (memory_dir / "2026-04-06.md").write_text("", encoding="utf-8")
    (memory_dir / "2026-04-07").mkdir()

    assert _detect_mode(memory_dir) == "memory"


def test_detect_mode_wiki(tmp_path):
    """_detect_mode returns 'wiki' for normal directories."""
    from linglong.knowledge.sync.openclaw import _detect_mode

    wiki = tmp_path / "wiki"
    wiki.mkdir()
    (wiki / "concepts").mkdir()
    (wiki / "concepts" / "test.md").write_text("# Test", encoding="utf-8")

    assert _detect_mode(wiki) == "wiki"


def test_detect_mode_memory_by_name(tmp_path):
    """Directory named 'memory' → always memory mode."""
    from linglong.knowledge.sync.openclaw import _detect_mode

    mem = tmp_path / "memory"
    mem.mkdir()
    # Even with no files, name match triggers memory mode
    assert _detect_mode(mem) == "memory"
