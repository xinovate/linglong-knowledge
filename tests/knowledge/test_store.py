"""Tests for knowledge store."""

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from linglong.core.config import LinglongConfig, set_config
from linglong.core.models import Entity, EntityFacet, EntityStatus
from linglong.knowledge.store import KnowledgeStore


@pytest.fixture
def temp_store():
    """Create a temporary knowledge store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = LinglongConfig(
            knowledge=LinglongConfig().knowledge.model_copy(
                update={
                    "wiki_path": Path(tmpdir) / "wiki",
                    "db_path": Path(tmpdir) / "knowledge.db",
                    "generate_embeddings": False,
                }
            ),
        )
        set_config(config)
        store = KnowledgeStore()
        yield store


def test_create_and_get(temp_store):
    """Test creating and retrieving an entity."""
    entity = Entity(
        content="# Test Entity\n\nThis is a test.",
        facet=EntityFacet.CONCEPT,
        created_by="agent:violet",
        confidence=0.85,
    )

    created = temp_store.create(entity)
    assert created.id is not None

    retrieved = temp_store.get(created.id)
    assert retrieved is not None
    assert retrieved.content == entity.content
    assert retrieved.created_by == "agent:violet"


def test_search_by_status(temp_store):
    """Test searching entities by status."""
    entity1 = Entity(
        content="Entity 1",
        facet=EntityFacet.CONCEPT,
        created_by="agent:violet",
        status=EntityStatus.CONFIRMED,
    )
    entity2 = Entity(
        content="Entity 2",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
        status=EntityStatus.RAW,
    )

    temp_store.create(entity1)
    temp_store.create(entity2)

    results = temp_store.search(status=EntityStatus.CONFIRMED)
    assert len(results) == 1
    assert results[0].content == "Entity 1"


def test_update_entity(temp_store):
    """Test updating an entity."""
    entity = Entity(
        content="Original content",
        facet=EntityFacet.CONCEPT,
        created_by="agent:violet",
    )

    created = temp_store.create(entity)
    created.content = "Updated content"
    created.confidence = 0.95

    updated = temp_store.update(created)
    assert updated.content == "Updated content"
    assert float(updated.confidence) == 0.95

    retrieved = temp_store.get(created.id)
    assert retrieved.content == "Updated content"


def test_delete_entity(temp_store):
    """Test deleting an entity."""
    entity = Entity(
        content="To be deleted",
        facet=EntityFacet.CONCEPT,
        created_by="agent:violet",
    )

    created = temp_store.create(entity)
    assert temp_store.delete(created.id) is True
    assert temp_store.get(created.id) is None


def test_create_entity_with_embedding():
    """Entity create triggers embedding generation when enabled."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = LinglongConfig(
            knowledge=LinglongConfig().knowledge.model_copy(
                update={
                    "wiki_path": Path(tmpdir) / "wiki",
                    "db_path": Path(tmpdir) / "knowledge.db",
                    "generate_embeddings": True,
                    "vector_dimensions": 768,
                }
            ),
        )
        set_config(config)
        store = KnowledgeStore()

        with patch(
            "linglong.knowledge.embeddings.EmbeddingGenerator.generate",
            return_value=[0.1] * 768,
        ):
            entity = Entity(content="hello world", facet=EntityFacet.CONCEPT, created_by="agent:test")
            created = store.create(entity)

        assert created.embedding_id is not None

        retrieved = store.get(created.id)
        assert retrieved.embedding_id == created.embedding_id


def test_search_similar_returns_results():
    """Vector similarity search returns relevant entities."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = LinglongConfig(
            knowledge=LinglongConfig().knowledge.model_copy(
                update={
                    "wiki_path": Path(tmpdir) / "wiki",
                    "db_path": Path(tmpdir) / "knowledge.db",
                    "generate_embeddings": True,
                    "vector_dimensions": 3,
                }
            ),
        )
        set_config(config)
        store = KnowledgeStore()

        # mock 嵌入以控制相似度
        def _fake_generate(text):
            # 基于文本内容返回确定性向量
            if "python" in text.lower():
                return [1.0, 0.0, 0.0]
            if "javascript" in text.lower():
                return [0.0, 1.0, 0.0]
            return [0.0, 0.0, 1.0]

        with patch(
            "linglong.knowledge.embeddings.EmbeddingGenerator.generate",
            side_effect=_fake_generate,
        ):
            store.create(Entity(content="python tutorial", facet=EntityFacet.CONCEPT, created_by="agent:test"))
            store.create(Entity(content="javascript guide", facet=EntityFacet.CONCEPT, created_by="agent:test"))
            store.create(Entity(content="cooking recipes", facet=EntityFacet.CONCEPT, created_by="agent:test"))

        # 搜索类似 python 的内容
        with patch(
            "linglong.knowledge.embeddings.EmbeddingGenerator.generate",
            return_value=[1.0, 0.0, 0.0],
        ):
            results = store.search_similar("python", limit=3)

        assert len(results) >= 1
        assert results[0].content == "python tutorial"


def test_search_similar_with_status_filter():
    """Vector search respects status filter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = LinglongConfig(
            knowledge=LinglongConfig().knowledge.model_copy(
                update={
                    "wiki_path": Path(tmpdir) / "wiki",
                    "db_path": Path(tmpdir) / "knowledge.db",
                    "generate_embeddings": True,
                    "vector_dimensions": 3,
                }
            ),
        )
        set_config(config)
        store = KnowledgeStore()

        with patch(
            "linglong.knowledge.embeddings.EmbeddingGenerator.generate",
            return_value=[1.0, 0.0, 0.0],
        ):
            store.create(
                Entity(
                    content="python tutorial",
                    facet=EntityFacet.CONCEPT,
                    created_by="agent:test",
                    status=EntityStatus.AUTO_CONFIRMED,
                )
            )
            store.create(
                Entity(
                    content="python advanced",
                    facet=EntityFacet.CONCEPT,
                    created_by="agent:test",
                    status=EntityStatus.RAW,
                )
            )

        with patch(
            "linglong.knowledge.embeddings.EmbeddingGenerator.generate",
            return_value=[1.0, 0.0, 0.0],
        ):
            results = store.search_similar("python", status=EntityStatus.AUTO_CONFIRMED, limit=3)

        assert len(results) == 1
        assert results[0].status == EntityStatus.AUTO_CONFIRMED


def test_create_entity_stores_facet(temp_store):
    """创建 Entity 时 facet 正确存入 SQLite。"""
    entity = Entity(
        content="微服务架构设计",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    )
    created = temp_store.create(entity)
    retrieved = temp_store.get(created.id)
    assert retrieved.facet == EntityFacet.CONCEPT


def test_search_by_facet(temp_store):
    """按 facet 过滤搜索。"""
    temp_store.create(Entity(
        content="概念文章", facet=EntityFacet.CONCEPT, created_by="agent:claude"
    ))
    temp_store.create(Entity(
        content="踩坑记录", facet=EntityFacet.EXPERIENCE, created_by="agent:claude"
    ))

    concepts = temp_store.search(facet=EntityFacet.CONCEPT)
    assert len(concepts) == 1
    assert concepts[0].facet == EntityFacet.CONCEPT


def test_fts5_fulltext_search(temp_store):
    """FTS5 全文搜索能匹配内容关键词。"""
    temp_store.create(Entity(
        content="SQLite 向量搜索使用 sqlite-vec 扩展",
        facet=EntityFacet.EXPERIENCE,
        created_by="agent:claude",
    ))
    temp_store.create(Entity(
        content="Python 类型提示的最佳实践",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    results = temp_store.search(query="sqlite-vec")
    assert len(results) == 1
    assert "sqlite-vec" in results[0].content

    results2 = temp_store.search(query="Python 类型")
    assert len(results2) == 1
    assert "Python" in results2[0].content


def test_create_entity_saves_to_facet_directory(temp_store):
    """创建 Entity 时文件存入 wiki/{facet}/ 目录。"""
    entity = Entity(
        content="测试内容",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    )
    created = temp_store.create(entity)

    # 文件应在 wiki/concept/ 目录下
    wiki_path = temp_store.wiki_path
    facet_files = list((wiki_path / "concept").glob("*.md"))
    assert len(facet_files) == 1
    assert created.id in facet_files[0].name


def test_entity_file_has_frontmatter(temp_store):
    """Entity 文件包含正确的 YAML frontmatter。"""
    entity = Entity(
        content="测试内容",
        facet=EntityFacet.EXPERIENCE,
        created_by="agent:claude",
    )
    created = temp_store.create(entity)

    # 语义文件名：从内容标题提取
    path = temp_store.wiki_path / "experience" / f"{created.id}.md"
    assert path.exists()
    content = path.read_text()
    assert "type: experience" in content
    assert "created_by: agent:claude" in content


def test_update_content_creates_version(temp_store):
    """替换内容时产生新版本。"""
    entity = temp_store.create(Entity(
        content="v1 内容",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))
    assert entity.current_version == 1
    assert len(entity.versions) == 0

    # 更新内容
    entity.content = "v2 内容"
    updated = temp_store.update(entity)

    assert updated.current_version == 2
    assert len(updated.versions) == 1
    assert updated.versions[0]["version"] == 1
    assert updated.versions[0]["content"] == "v1 内容"


def test_update_appends_no_new_version(temp_store):
    """追加内容不产生新版本。"""
    entity = temp_store.create(Entity(
        content="原始内容",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    # 追加（通过 metadata 标记）
    entity.metadata["update_mode"] = "append"
    entity.content = "原始内容\n\n追加内容"
    updated = temp_store.update(entity)

    assert updated.current_version == 1
    assert len(updated.versions) == 0
    assert "追加内容" in updated.content


def test_version_compaction(temp_store):
    """版本超过上限时自动压缩。"""
    # 设置低版本上限
    temp_store.config.max_versions = 3

    entity = temp_store.create(Entity(
        content="v1",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    for i in range(2, 6):
        entity.content = f"v{i}"
        entity = temp_store.update(entity)

    # 应保留首版摘要 + 最近版本，总版本数不超过 max_versions
    assert entity.current_version == 5
    assert len(entity.versions) <= 4  # max_versions + 1（首版压缩占一个位置）
    # 首个版本条目应被压缩
    assert entity.versions[0]["content"] == "(compressed)"


def test_archive_entity(temp_store):
    """归档 Entity 设置 archived_at 并移入 archive 目录。"""
    entity = temp_store.create(Entity(
        content="待归档内容",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    archived = temp_store.archive(entity.id)

    assert archived.archived_at is not None

    # 原 facet 目录文件应不存在
    original_path = temp_store._get_entity_path(entity.id, "concept")
    assert not original_path.exists()

    # archive 目录应有文件
    archive_files = list((temp_store.wiki_path / "archive").rglob("*.md"))
    assert len(archive_files) == 1


def test_archived_entity_not_in_search(temp_store):
    """归档的 Entity 不出现在默认搜索结果中。"""
    entity = temp_store.create(Entity(
        content="将被归档",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))
    temp_store.archive(entity.id)

    # 默认搜索不包含已归档
    results = temp_store.search(query="将被归档")
    assert len(results) == 0

    # include_archived=True 可搜到
    results = temp_store.search(query="将被归档", include_archived=True)
    assert len(results) == 1


def test_search_since_filter(temp_store):
    """按日期过滤搜索结果。"""
    e1 = temp_store.create(Entity(
        content="旧条目",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))
    # 手动修改 updated_at 为 10 天前
    try:
        import sqlean.dbapi2 as _sqlite3
    except ImportError:
        import sqlite3 as _sqlite3
    with _sqlite3.connect(str(temp_store.db_path)) as conn:
        old_time = (datetime.now(UTC) - timedelta(days=10)).isoformat()
        conn.execute("UPDATE entities SET updated_at = ? WHERE id = ?", (old_time, e1.id))
        conn.commit()

    e2 = temp_store.create(Entity(
        content="新条目",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    cutoff = (datetime.now(UTC) - timedelta(days=5)).strftime("%Y-%m-%d")
    results = temp_store.search(since=cutoff)
    assert len(results) == 1
    assert results[0].content == "新条目"


def test_optimistic_lock(temp_store):
    """乐观锁检测并发修改冲突。"""
    from linglong.knowledge.store import ConcurrentModificationError

    entity = temp_store.create(Entity(
        content="v1",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    # 模拟另一个进程先修改
    current = temp_store.get(entity.id)
    current.content = "v2 by other"
    temp_store.update(current)

    # 原进程用过时对象更新 → 应抛异常
    entity.content = "v2 by me"
    with pytest.raises(ConcurrentModificationError):
        temp_store.update(entity)


def test_wikilinks_auto_relations(temp_store):
    """创建带 [[link]] 的 Entity 时自动填充 relations。"""
    target = temp_store.create(Entity(
        content="# 概念A\n\n描述",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    entity = temp_store.create(Entity(
        content="# 引用方\n\n参考 [[概念A]]",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    assert len(entity.relations) == 1
    assert entity.relations[0].target_id == target.id
    assert entity.relations[0].relation_type == "wikilink"


def test_search_similar_with_facet():
    """向量搜索支持 facet 过滤。"""
    import tempfile
    from linglong.core.config import LinglongConfig, set_config

    with tempfile.TemporaryDirectory() as tmpdir:
        config = LinglongConfig(
            knowledge=LinglongConfig().knowledge.model_copy(update={
                "wiki_path": Path(tmpdir) / "wiki",
                "db_path": Path(tmpdir) / "knowledge.db",
                "generate_embeddings": True,
                "vector_dimensions": 4,
            }),
        )
        set_config(config)

        store = KnowledgeStore()

        # Mock embedding generator
        from unittest.mock import patch

        def fake_generate(text):
            if "概念" in text:
                return [0.1, 0.2, 0.3, 0.4]
            return [0.9, 0.8, 0.7, 0.6]

        with patch.object(store._embedding_generator, 'generate', side_effect=fake_generate):
            store.create(Entity(
                content="# 概念文章",
                facet=EntityFacet.CONCEPT,
                created_by="agent:claude",
            ))
            store.create(Entity(
                content="# 经验记录",
                facet=EntityFacet.EXPERIENCE,
                created_by="agent:claude",
            ))

            results = store.search_similar(
                query="概念", facet=EntityFacet.CONCEPT, limit=10
            )
            assert all(e.facet == EntityFacet.CONCEPT for e in results)


def test_auto_lint_on_write(temp_store):
    """auto_lint=True 时写入后自动触发巡检。"""
    import logging

    temp_store.config.auto_lint = True

    # 写入时不应报错
    entity = temp_store.create(Entity(
        content="# 正常内容\n\n无问题",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))
    assert entity is not None


def test_create_dedup_same_id_same_content(temp_store):
    """Same ID + same content → return existing entity (idempotent)."""
    entity = Entity(
        id="test-dedup-001",
        content="# Title\n\nContent",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    )
    first = temp_store.create(entity)
    second = temp_store.create(entity)

    assert first.id == second.id
    assert first.created_at == second.created_at


def test_create_dedup_same_id_different_content(temp_store):
    """Same ID + different content → update without version bump."""
    entity = Entity(
        id="test-dedup-002",
        content="# Title\n\nOriginal",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    )
    temp_store.create(entity)

    entity.content = "# Title\n\nUpdated"
    updated = temp_store.create(entity)

    assert updated.content == "# Title\n\nUpdated"
    assert updated.current_version == 1  # no version bump (append mode)


def test_create_dedup_cross_source_same_content(temp_store):
    """Different ID + same content → return existing entity (cross-source dedup)."""
    entity1 = Entity(
        id="source-a-001",
        content="# Shared Content\n\nSame text",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    )
    first = temp_store.create(entity1)

    entity2 = Entity(
        id="source-b-001",
        content="# Shared Content\n\nSame text",
        facet=EntityFacet.CONCEPT,
        created_by="agent:openclaw",
    )
    second = temp_store.create(entity2)

    # Should return the existing entity, not create a new one
    assert second.id == first.id
    assert second.created_by == "agent:claude"  # keeps original metadata
