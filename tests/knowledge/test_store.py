"""Tests for knowledge store."""

import tempfile
from pathlib import Path

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
