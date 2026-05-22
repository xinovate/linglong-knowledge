"""Tests for ingest history persistence."""

import tempfile
from pathlib import Path
from datetime import UTC, datetime, timedelta

from linglong.core.models import Entity, EntityFacet
from linglong.ingest.history import IngestHistory


def _make_entity(title: str, content_suffix: str = "") -> Entity:
    return Entity(
        content=f"# {title}\n\nSome content about {title}. {content_suffix}",
        facet=EntityFacet.REFERENCE,
        created_by="agent:web_search",
    )


class TestIngestHistory:
    def test_write_and_query(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "test_history.db"
            history = IngestHistory(db_path=db)

            entities = [
                _make_entity("OpenAI releases GPT-5"),
                _make_entity("Anthropic Claude 4"),
            ]
            written = history.write_batch(entities, dimension="公司决策")
            assert written == 2

            recent = history.query_recent(days=1)
            assert len(recent) == 2
            assert recent[0]["dimension"] == "公司决策"

    def test_query_by_dimension(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "test_history.db"
            history = IngestHistory(db_path=db)

            history.write_batch([_make_entity("item-a")], dimension="研究员观点")
            history.write_batch([_make_entity("item-b")], dimension="公司决策")

            r1 = history.query_recent(days=1, dimension="研究员观点")
            assert len(r1) == 1
            assert r1[0]["title"] == "item-a"

    def test_find_by_hash(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "test_history.db"
            history = IngestHistory(db_path=db)

            entity = _make_entity("unique-title")
            chash = IngestHistory.content_hash(entity)
            history.write_batch([entity])

            matches = history.find_by_hash(chash)
            assert len(matches) == 1
            assert matches[0]["title"] == "unique-title"

    def test_find_by_hash_no_match(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "test_history.db"
            history = IngestHistory(db_path=db)

            matches = history.find_by_hash("nonexistent")
            assert matches == []

    def test_find_by_title_similarity(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "test_history.db"
            history = IngestHistory(db_path=db)

            history.write_batch(
                [_make_entity("OpenAI releases GPT-5 model")],
                dimension="公司决策",
            )

            # Similar title
            matches = history.find_by_title_similarity(
                "OpenAI GPT-5 model release", days=1, threshold=0.3
            )
            assert len(matches) >= 1

            # Very different title
            matches2 = history.find_by_title_similarity(
                "completely unrelated topic", days=1, threshold=0.3
            )
            assert len(matches2) == 0

    def test_content_hash_deterministic(self):
        e = _make_entity("test")
        h1 = IngestHistory.content_hash(e)
        h2 = IngestHistory.content_hash(e)
        assert h1 == h2

    def test_content_hash_different_content(self):
        e1 = _make_entity("title-a")
        e2 = _make_entity("title-b")
        assert IngestHistory.content_hash(e1) != IngestHistory.content_hash(e2)
