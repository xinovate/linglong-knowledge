"""LintEngine 巡检引擎测试。"""

import sqlite3
import tempfile
from datetime import UTC, datetime, timedelta
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


def test_content_conflict_semantic(lint_setup):
    """向量语义去重检测（相似度 > 0.95）。"""
    store, engine = lint_setup
    e1 = store.create(Entity(
        content="# 标题A\n\nPython 类型提示最佳实践",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))
    e2 = store.create(Entity(
        content="# 标题B\n\nPython type hints best practices",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    # Mock search_similar 返回高相似度结果
    from unittest.mock import patch

    def _fake_search_similar(query, facet=None, limit=5):
        # 当查询 e1 时返回 e2，distance=0.05 -> similarity=0.975
        if e1.id in query or "Python 类型提示" in query:
            e2_copy = e2.model_copy()
            e2_copy.distance = 0.05
            return [e2_copy]
        return []

    with patch.object(store, "search_similar", side_effect=_fake_search_similar):
        results = engine.check_content_conflicts()

    semantic_results = [r for r in results if "语义重复" in r.message]
    assert len(semantic_results) == 1
    assert semantic_results[0].rule == "content_conflict"
    assert semantic_results[0].details["similarity"] == pytest.approx(0.975)
    assert semantic_results[0].details["duplicate_of"] == e2.id


def test_content_conflict_semantic_fallback(lint_setup):
    """向量服务不可用时仅返回标题重复，不崩溃。"""
    store, engine = lint_setup
    store.create(Entity(
        content="# 重复标题\n\n内容1",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))
    store.create(Entity(
        content="# 重复标题\n\n内容2",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    from unittest.mock import patch

    with patch.object(store, "search_similar", side_effect=RuntimeError("embedding service down")):
        results = engine.check_content_conflicts()

    # 标题重复仍应被检测到
    assert len(results) == 1
    assert results[0].rule == "content_conflict"
    assert "标题重复" in results[0].message


def test_stale_content(lint_setup):
    """检测过期内容。"""
    store, engine = lint_setup
    entity = store.create(Entity(
        content="# 旧内容\n\n过期内容",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    # 直接修改数据库中的 updated_at（store.update 会重置为 now）
    old_time = (datetime.now(UTC) - timedelta(days=100)).isoformat()
    with sqlite3.connect(store.db_path) as conn:
        conn.execute(
            "UPDATE entities SET updated_at = ? WHERE id = ?",
            (old_time, entity.id),
        )

    results = engine.check_stale_content(days=90)
    assert len(results) == 1
    assert results[0].rule == "stale_content"
    assert results[0].severity == LintSeverity.INFO


def test_lint_fix_removes_orphan(lint_setup):
    """lint --fix 删除孤立文件。"""
    store, engine = lint_setup
    # 创建一个不在数据库中的文件
    orphan_path = store.wiki_path / "concept" / "orphan-file.md"
    orphan_path.parent.mkdir(parents=True, exist_ok=True)
    orphan_path.write_text("# 孤立文件\n\n不在数据库中")

    results = engine.check_index_consistency()
    assert len(results) == 1
    assert results[0].rule == "index_consistency"

    fixed = engine.fix_all(results)
    assert fixed[0].fixed is True
    assert not orphan_path.exists()


def test_fix_wikilinks_plain(lint_setup):
    """[[死链]] 修复为纯文本。"""
    store, engine = lint_setup
    entity = store.create(Entity(
        content="# 测试\n\n参考 [[不存在的页面]] 和 [[另一个死链]]。",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    results = engine.check_wikilinks()
    assert len(results) == 2

    fixed = engine.fix_all(results)
    assert all(r.fixed for r in fixed)

    updated = store.get(entity.id)
    assert "[[不存在的页面]]" not in updated.content
    assert "[[另一个死链]]" not in updated.content
    assert "参考 不存在的页面 和 另一个死链。" in updated.content


def test_fix_wikilinks_with_display(lint_setup):
    """[[死链|显示文本]] 保留显示文本。"""
    store, engine = lint_setup
    entity = store.create(Entity(
        content="# 测试\n\n参见 [[missing|显示名称]]。",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    results = engine.check_wikilinks()
    assert len(results) == 1

    fixed = engine.fix_all(results)
    assert fixed[0].fixed is True

    updated = store.get(entity.id)
    assert "[[missing|显示名称]]" not in updated.content
    assert "参见 显示名称。" in updated.content


def test_fix_wikilinks_valid_link_untouched(lint_setup):
    """有效链接在修复死链时不受影响。"""
    store, engine = lint_setup
    store.create(Entity(
        content="# 存在的概念\n\n内容",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))
    entity = store.create(Entity(
        content="# 测试\n\n参考 [[存在的概念]] 和 [[不存在的页面]]。",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    results = engine.check_wikilinks()
    assert len(results) == 1
    assert "不存在的页面" in results[0].message

    engine.fix_all(results)

    updated = store.get(entity.id)
    assert "[[存在的概念]]" in updated.content
    assert "[[不存在的页面]]" not in updated.content


def test_orphan_detection(lint_setup):
    """检测孤儿资源。"""
    store, engine = lint_setup
    store.create(Entity(
        content="# 概念A\n\n内容",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))
    store.create(Entity(
        content="# 概念B\n\n参考 [[概念A]]",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    results = engine.check_orphans()
    assert len(results) == 1
    assert results[0].rule == "orphan"
    assert "概念A" not in results[0].message
    assert results[0].entity_id is not None


def test_orphan_exempt_personal_diary(lint_setup):
    """personal facet 下的 diary 和 task-record 不计为孤儿。"""
    store, engine = lint_setup
    store.create(Entity(
        content="# 日记\n\n今天",
        facet=EntityFacet.PERSONAL,
        created_by="agent:claude",
        metadata={"_subdir": "diary"},
    ))
    store.create(Entity(
        content="# 任务记录\n\n任务",
        facet=EntityFacet.PERSONAL,
        created_by="agent:claude",
        metadata={"_subdir": "task-record"},
    ))

    results = engine.check_orphans()
    assert len(results) == 0


def test_orphan_no_false_positive_for_linked(lint_setup):
    """被引用的实体不应被标记为孤儿。"""
    store, engine = lint_setup
    a = store.create(Entity(
        content="# 概念A\n\n内容",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))
    store.create(Entity(
        content="# 概念B\n\n参考 [[概念A]]",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    results = engine.check_orphans()
    orphan_ids = {r.entity_id for r in results}
    assert a.id not in orphan_ids
