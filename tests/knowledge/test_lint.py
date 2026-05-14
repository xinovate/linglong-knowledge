"""LintEngine 巡检引擎测试。"""

import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from linglong.core.config import LinglongConfig, set_config
from linglong.core.models import Entity, EntityFacet
from linglong.knowledge.lint import LintEngine, LintSeverity
from linglong.knowledge.store import KnowledgeStore


@pytest.fixture
def lint_setup():
    """创建带测试数据的临时知识库。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = LinglongConfig(
            data_dir=Path(tmpdir) / "data",
            knowledge=LinglongConfig().knowledge.model_copy(update={
                "wiki_path": Path(tmpdir) / "wiki",
                "db_path": Path(tmpdir) / "knowledge.db",
                "generate_embeddings": False,
            }),
        )
        set_config(config)

        store = KnowledgeStore()
        engine = LintEngine(store)
        yield store, engine


def test_lint_empty_kb(lint_setup):
    """空知识库无问题。"""
    _, engine = lint_setup
    results = engine.run_all()
    assert results == []


def test_wikilinks_dead_link(lint_setup):
    """检测死链。"""
    store, engine = lint_setup
    store.create(Entity(
        content="# 测试\n\n参考 [[不存在的页面]]",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    results = engine.check_wikilinks()
    assert len(results) == 1
    assert results[0].rule == "wikilinks"
    assert "不存在的页面" in results[0].message
    assert results[0].severity == LintSeverity.WARNING


def test_wikilinks_valid_link(lint_setup):
    """有效链接不报错。"""
    store, engine = lint_setup
    store.create(Entity(
        content="# 概念A\n\n内容",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))
    store.create(Entity(
        content="# 测试\n\n参考 [[概念A]]",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    results = engine.check_wikilinks()
    assert len(results) == 0


def test_content_conflict_duplicate_titles(lint_setup):
    """检测标题重复。"""
    store, engine = lint_setup
    store.create(Entity(
        content="# 重复标题\n\n内容1",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))
    store.create(Entity(
        content="# 重复标题\n\n内容2",
        facet=EntityFacet.EXPERIENCE,
        created_by="agent:claude",
    ))

    results = engine.check_content_conflicts()
    assert len(results) == 1
    assert results[0].rule == "content_conflict"


def test_stale_content(lint_setup):
    """检测过期内容。"""
    store, engine = lint_setup
    entity = store.create(Entity(
        content="# 旧内容\n\n过期内容",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    # 直接修改数据库中的 updated_at（store.update 会重置为 now）
    old_time = (datetime.utcnow() - timedelta(days=100)).isoformat()
    with sqlite3.connect(store.db_path) as conn:
        conn.execute(
            "UPDATE entities SET updated_at = ? WHERE id = ?",
            (old_time, entity.id),
        )

    results = engine.check_stale_content(days=90)
    assert len(results) == 1
    assert results[0].rule == "stale_content"
    assert results[0].severity == LintSeverity.INFO
