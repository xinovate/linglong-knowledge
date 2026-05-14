"""Tests for review engine."""

from linglong.core.models import Entity, EntityFacet, EntityStatus, Source, SourceType
from linglong.knowledge.review import Action, ReviewEngine, Rule


def test_high_confidence_auto_confirm():
    """Test that high confidence + trusted source auto-confirms."""
    engine = ReviewEngine()

    entity = Entity(
        content="High quality content about Python",
        facet=EntityFacet.CONCEPT,
        created_by="agent:violet",
        confidence=0.95,
        sources=[Source(type=SourceType.RSS, name="openclaw")],
    )

    reviewed = engine.review(entity)
    assert reviewed.status == EntityStatus.AUTO_CONFIRMED


def test_low_confidence_flagged():
    """Test that low confidence content is flagged."""
    engine = ReviewEngine()

    entity = Entity(
        content="Low confidence content",
        facet=EntityFacet.CONCEPT,
        created_by="agent:violet",
        confidence=0.5,
    )

    reviewed = engine.review(entity)
    assert reviewed.status == EntityStatus.PENDING_REVIEW


def test_sensitive_content_requires_human():
    """Test that sensitive content requires human confirmation."""
    engine = ReviewEngine()

    entity = Entity(
        content="My password is secret123",
        facet=EntityFacet.CONCEPT,
        created_by="agent:violet",
        confidence=0.9,
    )

    reviewed = engine.review(entity)
    assert reviewed.status == EntityStatus.PENDING_REVIEW


def test_custom_rule():
    """Test adding custom rules."""
    engine = ReviewEngine()

    # 添加自定义规则：拒绝空内容
    engine.add_rule(
        Rule(
            name="no_empty",
            condition=lambda e: len(e.content.strip()) == 0,
            action=Action.REJECT,
            priority=200,
        )
    )

    entity = Entity(
        content="",
        facet=EntityFacet.CONCEPT,
        created_by="agent:violet",
        confidence=0.95,
    )

    reviewed = engine.review(entity)
    assert reviewed.status == EntityStatus.REJECTED
