"""Composer integration tests.

Verify Composer.run() reads from KnowledgeStore and produces dispatch-ready output.
"""

import tempfile
import uuid
from datetime import datetime
from pathlib import Path

import pytest

from linglong.composer.composer import Composer, ComposerResult
from linglong.core.config import LinglongConfig, set_config
from linglong.core.models import Entity, EntityFacet, EntityStatus, Source, SourceType
from linglong.knowledge.store import KnowledgeStore


@pytest.fixture
def composer():
    """Create a Composer with isolated temporary storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = LinglongConfig(
            data_dir=Path(tmpdir) / "data",
            knowledge=LinglongConfig().knowledge.model_copy(
                update={
                    "wiki_path": Path(tmpdir) / "wiki",
                    "db_path": Path(tmpdir) / "knowledge.db",
                }
            ),
            composer=LinglongConfig().composer.model_copy(
                update={"drafts_dir": Path(tmpdir) / "drafts"}
            ),
        )
        set_config(config)
        yield Composer()


@pytest.fixture
def store(composer):
    """Create a KnowledgeStore using the same config as composer."""
    return KnowledgeStore()


def _create_entity(content: str, date: datetime, source_name: str = "openclaw") -> Entity:
    """Helper to create an AUTO_CONFIRMED entity."""
    return Entity(
        id=str(uuid.uuid4()),
        content=content,
        facet=EntityFacet.CONCEPT,
        created_by="agent:test",
        confidence=0.92,
        status=EntityStatus.AUTO_CONFIRMED,
        sources=[Source(type=SourceType.MEMORY, name=source_name)],
        created_at=date,
    )


class TestComposerRun:
    """Composer.run() core path tests."""

    def test_run_daily_success(self, composer, store):
        """Normal run should process entities and return dispatch-ready result."""
        store.create(_create_entity("测试内容 1", datetime(2026, 5, 11, 10, 0)))
        store.create(_create_entity("测试内容 2", datetime(2026, 5, 11, 11, 0)))

        result = composer.run()

        assert result.success is True
        assert len(result.articles) == 1
        article = result.articles[0]
        assert article["title"] == "每日回顾 2026-05-11"
        assert article["fragments_count"] == 2
        assert article["date"] == "2026-05-11"
        assert article["dispatch_ready"] is True
        assert article["status"] == "dispatch_ready"

    def test_run_dry_run(self, composer, store):
        """dry_run=True should not mark processed or save drafts."""
        store.create(_create_entity("测试内容", datetime(2026, 5, 11, 10, 0)))

        result = composer.run(dry_run=True)

        assert result.success is True
        assert len(result.articles) == 1
        article = result.articles[0]
        assert article["status"] == "dry_run"
        assert article["dispatch_ready"] is False

        # 再次运行应仍能找到该实体（未标记为已处理）
        result2 = composer.run(dry_run=True)
        assert len(result2.articles) == 1

    def test_run_no_fragments(self, composer):
        """Empty store should return empty result without error."""
        result = composer.run()

        assert result.success is True
        assert len(result.articles) == 0

    def test_run_all_already_processed(self, composer, store):
        """Second run should skip already-processed entities."""
        store.create(_create_entity("测试内容", datetime(2026, 5, 11, 10, 0)))

        result1 = composer.run()
        assert len(result1.articles) == 1

        result2 = composer.run()
        assert result2.success is True
        assert len(result2.articles) == 0

    def test_run_draft_mode(self, composer, store):
        """draft=True should save to DraftManager instead of dispatch-ready."""
        store.create(_create_entity("草稿测试内容", datetime(2026, 5, 11, 10, 0)))

        result = composer.run(draft=True)

        assert result.success is True
        assert len(result.articles) == 1
        article = result.articles[0]
        assert article["status"] == "draft_saved"
        assert "draft_id" in article

        # 验证草稿存在
        draft_id = article["draft_id"]
        from linglong.composer.draft import DraftManager

        dm = DraftManager()
        entry = dm.get_draft(draft_id)
        assert entry is not None
        assert entry.status in ("pending", "needs_review")

    def test_run_since_filter(self, composer, store):
        """since parameter should filter entities by timestamp."""
        store.create(_create_entity("旧内容", datetime(2026, 5, 10, 10, 0)))
        store.create(_create_entity("新内容", datetime(2026, 5, 12, 10, 0)))

        result = composer.run(since=datetime(2026, 5, 11, 0, 0))

        assert result.success is True
        assert len(result.articles) == 1
        # 只有较新的实体应被处理
        assert result.articles[0]["fragments_count"] == 1


class TestComposerResult:
    """ComposerResult data structure tests."""

    def test_result_defaults(self):
        """Default state should be success with empty lists."""
        result = ComposerResult()
        assert result.success is True
        assert result.articles == []
        assert result.errors == []

    def test_result_add_error_marks_failure(self):
        """Adding error should set success to False."""
        result = ComposerResult()
        result.add_error("something went wrong")
        assert result.success is False
        assert len(result.errors) == 1

    def test_result_add_article(self):
        """Adding article should be tracked correctly."""
        result = ComposerResult()
        result.add_article({"title": "测试", "date": "2026-05-11"})
        assert len(result.articles) == 1
        assert result.success is True
