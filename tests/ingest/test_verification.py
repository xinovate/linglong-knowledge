"""Tests for TruthVerificationEngine."""

from datetime import datetime, timedelta

from linglong.core.models import Entity, EntityFacet, Source
from linglong.ingest.verification import TruthVerificationEngine, VerificationConfig


def test_cross_reference_pass():
    """Two entities with same content pass cross-reference."""
    config = VerificationConfig(cross_reference_min=2)
    engine = TruthVerificationEngine(config)
    entities = [
        Entity(id="e1", content="OpenAI raises funding round", facet=EntityFacet.CONCEPT, created_by="test"),
        Entity(id="e2", content="OpenAI raises funding round", facet=EntityFacet.CONCEPT, created_by="test"),
    ]
    results = engine.verify_batch(entities)
    assert results[0].checks["cross_reference"] is True
    assert results[0].score >= 0.25


def test_numeric_sanity_fail():
    """Unreasonable numeric value fails."""
    config = VerificationConfig(numeric_ranges={"funding": (1_000_000, 100_000_000_000)})
    engine = TruthVerificationEngine(config)
    entity = Entity(content="OpenAI funding $999T announced today", facet=EntityFacet.CONCEPT, created_by="test")
    result = engine.verify_batch([entity])[0]
    assert result.checks["numeric_sanity"] is False
    assert "funding" in result.reasons[0].lower()


def test_time_validity_fail():
    """Old content fails time check."""
    config = VerificationConfig(max_age_days=3, fallback_max_age_days=7)
    engine = TruthVerificationEngine(config)
    old_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    entity = Entity(content=f"News on {old_date}", facet=EntityFacet.CONCEPT, created_by="test")
    result = engine.verify_batch([entity])[0]
    assert result.checks["time_validity"] is False


def test_authority_score_high():
    """High authority source gets good score."""
    config = VerificationConfig(authority_weights={"high": 1.0})
    engine = TruthVerificationEngine(config)
    entity = Entity(
        content="Test",
        facet=EntityFacet.CONCEPT,
        created_by="test",
        sources=[Source(type="rss", name="test", metadata={"authority": "high"})],
    )
    result = engine.verify_batch([entity])[0]
    assert result.checks["source_authority"] is True
