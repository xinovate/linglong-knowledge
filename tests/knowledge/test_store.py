"""Tests for knowledge store."""

import tempfile
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
            data_dir=Path(tmpdir) / "data",
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
            data_dir=Path(tmpdir) / "data",
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
            data_dir=Path(tmpdir) / "data",
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
            data_dir=Path(tmpdir) / "data",
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

    path = temp_store.wiki_path / "experience" / f"{created.id}.md"
    assert path.exists()
    content = path.read_text()
    assert '"type": "experience"' in content
    assert '"created_by": "agent:claude"' in content
