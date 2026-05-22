"""Tests for cross-day dedup."""

import tempfile
from pathlib import Path

from linglong.core.models import Entity, EntityFacet
from linglong.ingest.dedup import dedup_entities
from linglong.ingest.history import IngestHistory


def _make_entity(title: str, content_suffix: str = "") -> Entity:
    return Entity(
        content=f"# {title}\n\nContent about {title}. {content_suffix}",
        facet=EntityFacet.REFERENCE,
        created_by="agent:web_search",
    )


class TestDedup:
    def test_exact_duplicate_removed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "test_history.db"
            history = IngestHistory(db_path=db)

            entity = _make_entity("OpenAI GPT-5")
            history.write_batch([entity])

            # Same entity again
            result = dedup_entities([entity], history)
            assert len(result) == 0

    def test_different_entity_kept(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "test_history.db"
            history = IngestHistory(db_path=db)

            history.write_batch([_make_entity("OpenAI GPT-5")])

            # Different entity
            new_entity = _make_entity("Completely different news")
            result = dedup_entities([new_entity], history)
            assert len(result) == 1

    def test_similar_title_high_overlap_removed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "test_history.db"
            history = IngestHistory(db_path=db)

            history.write_batch(
                [_make_entity("OpenAI releases GPT-5")], dimension="公司决策"
            )

            # Very similar title
            new = _make_entity("OpenAI releases GPT-5 today")
            result = dedup_entities([new], history, title_threshold=0.5)
            assert len(result) == 0

    def test_partial_overlap_kept(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "test_history.db"
            history = IngestHistory(db_path=db)

            history.write_batch(
                [_make_entity("OpenAI funding round")], dimension="资本决策"
            )

            # Partially related but different
            new = _make_entity("OpenAI new product launch event")
            result = dedup_entities([new], history, title_threshold=0.5)
            # Should be kept — different enough
            assert len(result) == 1

    def test_empty_history_all_kept(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "test_history.db"
            history = IngestHistory(db_path=db)

            entities = [_make_entity(f"item-{i}") for i in range(3)]
            result = dedup_entities(entities, history)
            assert len(result) == 3

    def test_mixed_duplicates_and_new(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "test_history.db"
            history = IngestHistory(db_path=db)

            e1 = _make_entity("Known news A")
            history.write_batch([e1])

            e_new = _make_entity("Brand new topic XYZ")
            result = dedup_entities([e1, e_new], history)
            assert len(result) == 1
            assert "XYZ" in result[0].content
