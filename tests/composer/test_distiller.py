"""Distiller and IngestAdapter tests."""

from datetime import datetime

from linglong.core.models import Entity, EntityStatus, Source, SourceType
from linglong.composer.ingest_adapter import IngestAdapter, MemoryFragment
from linglong.composer.distiller.aggregator import DailyAggregator, ArticleMaterial


class TestIngestAdapter:
    def test_adapt_entity(self):
        """Entity should be correctly adapted to MemoryFragment"""
        entity = Entity(
            id="test-123",
            content="# Test\n\nContent",
            created_by="agent:violet",
            confidence=0.92,
            status=EntityStatus.AUTO_CONFIRMED,
            sources=[Source(type=SourceType.RSS, name="techcrunch")],
        )

        frag = IngestAdapter.adapt(entity)

        assert frag.source == "techcrunch"
        assert frag.content == "# Test\n\nContent"
        assert frag.metadata["entity_id"] == "test-123"
        assert frag.metadata["confidence"] == 0.92
        assert frag.metadata["status"] == "auto_confirmed"

    def test_adapt_entity_no_sources(self):
        """Entity without sources should default to 'unknown'"""
        entity = Entity(
            id="test-456",
            content="Content",
            created_by="agent:test",
        )

        frag = IngestAdapter.adapt(entity)
        assert frag.source == "unknown"

    def test_adapt_many(self):
        """Multiple entities should be adapted correctly"""
        entities = [
            Entity(id="1", content="A", created_by="agent:a"),
            Entity(id="2", content="B", created_by="agent:b"),
        ]
        frags = IngestAdapter.adapt_many(entities)
        assert len(frags) == 2
        assert frags[0].content == "A"
        assert frags[1].content == "B"

    def test_content_hash(self):
        """MemoryFragment should provide a content hash"""
        frag = MemoryFragment(
            source="test",
            content="hello",
            timestamp=datetime.now(),
            metadata={},
        )
        h = frag.content_hash
        assert len(h) == 32
        # Same content should give same hash
        frag2 = MemoryFragment(
            source="test",
            content="hello",
            timestamp=datetime.now(),
            metadata={},
        )
        assert frag2.content_hash == h


class TestDailyAggregator:
    def test_aggregate_by_day(self):
        """Fragments should be grouped by day"""
        frags = [
            MemoryFragment(
                source="s1",
                content="c1",
                timestamp=datetime(2026, 5, 11, 10, 0),
                metadata={},
            ),
            MemoryFragment(
                source="s1",
                content="c2",
                timestamp=datetime(2026, 5, 11, 11, 0),
                metadata={},
            ),
            MemoryFragment(
                source="s1",
                content="c3",
                timestamp=datetime(2026, 5, 12, 9, 0),
                metadata={},
            ),
        ]

        agg = DailyAggregator()
        groups = agg.aggregate(frags)

        assert len(groups) == 2
        assert "2026-05-11" in groups
        assert "2026-05-12" in groups
        assert len(groups["2026-05-11"]) == 2
        assert len(groups["2026-05-12"]) == 1

    def test_aggregate_empty(self):
        """Empty list should return empty dict"""
        agg = DailyAggregator()
        groups = agg.aggregate([])
        assert groups == {}


class TestArticleMaterial:
    def test_compile_content(self):
        """ArticleMaterial should compile fragments into content"""
        frags = [
            MemoryFragment(
                source="wiki",
                content="Paragraph 1",
                timestamp=datetime.now(),
                metadata={"type": "note"},
            ),
            MemoryFragment(
                source="rss",
                content="Paragraph 2",
                timestamp=datetime.now(),
                metadata={"type": "article"},
            ),
        ]

        material = ArticleMaterial(date="2026-05-11", fragments=frags)
        content = material.compile_content()

        assert "## note" in content
        assert "Paragraph 1" in content
        assert "## article" in content
        assert "Paragraph 2" in content
