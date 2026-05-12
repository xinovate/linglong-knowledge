"""Tests for knowledge store."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from linglong.core.config import LinglongConfig, set_config
from linglong.core.models import Entity, EntityStatus
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
        created_by="agent:violet",
        status=EntityStatus.CONFIRMED,
    )
    entity2 = Entity(
        content="Entity 2",
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
            entity = Entity(content="hello world", created_by="agent:test")
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

        # Mock embeddings so we can control similarity
        def _fake_generate(text):
            # Return deterministic vectors based on text content
            if "python" in text.lower():
                return [1.0, 0.0, 0.0]
            if "javascript" in text.lower():
                return [0.0, 1.0, 0.0]
            return [0.0, 0.0, 1.0]

        with patch(
            "linglong.knowledge.embeddings.EmbeddingGenerator.generate",
            side_effect=_fake_generate,
        ):
            store.create(Entity(content="python tutorial", created_by="agent:test"))
            store.create(Entity(content="javascript guide", created_by="agent:test"))
            store.create(Entity(content="cooking recipes", created_by="agent:test"))

        # Search for python-like content
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
                    created_by="agent:test",
                    status=EntityStatus.AUTO_CONFIRMED,
                )
            )
            store.create(
                Entity(
                    content="python advanced",
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
