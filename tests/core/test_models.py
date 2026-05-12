"""Tests for core models."""

import pytest
from datetime import datetime
from linglong.core.models import Entity, EntityStatus, Source, SourceType, AgentID


def test_entity_creation():
    """Test basic entity creation."""
    entity = Entity(
        id="test-123",
        content="# Test\n\nThis is a test.",
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
