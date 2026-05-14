"""Tests for core models."""

from linglong.core.models import Entity, EntityFacet, EntityStatus, Source, SourceType


def test_entity_creation():
    """Test basic entity creation."""
    entity = Entity(
        id="test-123",
        content="# Test\n\nThis is a test.",
        facet=EntityFacet.CONCEPT,
        created_by="agent:violet",
        confidence=0.9,
    )

    assert entity.id == "test-123"
    assert entity.status == EntityStatus.RAW
    assert float(entity.confidence) == 0.9


def test_entity_with_source():
    """Test entity with source information."""
    entity = Entity(
        id="test-456",
        content="Test content",
        facet=EntityFacet.SOURCE,
        created_by="agent:violet",
        sources=[
            Source(
                type=SourceType.RSS,
                name="techcrunch",
                url="https://techcrunch.com/test",
            )
        ],
    )

    assert len(entity.sources) == 1
    assert entity.sources[0].type == SourceType.RSS


def test_entity_facet_values():
    """EntityFacet 包含 7 个分面值。"""
    expected = {"source", "entity", "concept", "synthesis", "experience", "methodology", "personal"}
    actual = {f.value for f in EntityFacet}
    assert actual == expected


def test_entity_has_facet_field():
    """Entity 模型包含 facet 字段。"""
    e = Entity(
        content="测试",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    )
    assert e.facet == EntityFacet.CONCEPT


def test_entity_facet_required():
    """facet 字段没有默认值，必须提供。"""
    import pytest

    with pytest.raises(Exception):
        Entity(
            content="测试",
            created_by="agent:claude",
        )


def test_entity_archived_at_default_none():
    """archived_at 默认为 None。"""
    e = Entity(
        content="测试",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    )
    assert e.archived_at is None
