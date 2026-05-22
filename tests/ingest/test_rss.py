"""Tests for RSS ingestion module."""

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from linglong.core.models import EntityStatus, SourceType
from linglong.ingest.rss import RSSIngestor, RSSSource


class FakeFeedEntry:
    """Mock feedparser entry for testing."""

    def __init__(self, title, link, summary="", published="", tags=None):
        self.title = title
        self.link = link
        self.summary = summary
        self.published = published
        self.tags = tags or []


@pytest.fixture
def rss_source():
    """Create a test RSS source."""
    return RSSSource(name="test-feed", url="https://example.com/feed.xml")


@pytest.mark.asyncio
async def test_rss_source_fetch(rss_source):
    """Test RSSSource.fetch parses entries into entities."""
    mock_response = MagicMock()
    mock_response.text = "<rss></rss>"

    fake_entries = [
        FakeFeedEntry(
            title="Test Article",
            link="https://example.com/article/1",
            summary="Summary of article 1",
            published="Mon, 01 Jan 2024 00:00:00 GMT",
            tags=[MagicMock(term="python")],
        ),
    ]

    with (
        patch("httpx.AsyncClient") as mock_client_cls,
        patch("feedparser.parse") as mock_parse,
    ):
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        mock_feed = MagicMock()
        mock_feed.entries = fake_entries
        mock_parse.return_value = mock_feed

        entities = await rss_source.fetch()

    assert len(entities) == 1
    entity = entities[0]
    assert entity.id == hashlib.sha256(b"https://example.com/article/1").hexdigest()[:16]
    assert "Test Article" in entity.content
    assert entity.created_by == "agent:rss"
    assert float(entity.confidence) == 0.7
    assert len(entity.sources) == 1
    assert entity.sources[0].type == SourceType.RSS
    assert entity.sources[0].name == "test-feed"


@pytest.mark.asyncio
async def test_rss_source_fetch_multiple_entries(rss_source):
    """Test RSSSource.fetch handles multiple entries."""
    mock_response = MagicMock()
    mock_response.text = "<rss></rss>"

    fake_entries = [
        FakeFeedEntry(title=f"Article {i}", link=f"https://example.com/{i}") for i in range(3)
    ]

    with (
        patch("httpx.AsyncClient") as mock_client_cls,
        patch("feedparser.parse") as mock_parse,
    ):
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        mock_feed = MagicMock()
        mock_feed.entries = fake_entries
        mock_parse.return_value = mock_feed

        entities = await rss_source.fetch()

    assert len(entities) == 3


@pytest.mark.asyncio
async def test_rss_source_respects_max_items():
    """Test RSSSource respects max_items limit."""
    source = RSSSource(name="test", url="https://example.com/feed.xml", max_items=2)

    mock_response = MagicMock()
    mock_response.text = "<rss></rss>"

    fake_entries = [
        FakeFeedEntry(title=f"Article {i}", link=f"https://example.com/{i}") for i in range(10)
    ]

    with (
        patch("httpx.AsyncClient") as mock_client_cls,
        patch("feedparser.parse") as mock_parse,
    ):
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        mock_feed = MagicMock()
        mock_feed.entries = fake_entries
        mock_parse.return_value = mock_feed

        entities = await source.fetch()

    assert len(entities) == 2


@pytest.mark.asyncio
async def test_rss_ingestor_collects_all():
    """Test RSSIngestor collects entities from multiple sources."""
    source1 = RSSSource(name="feed1", url="https://example.com/1.xml")
    source2 = RSSSource(name="feed2", url="https://example.com/2.xml")

    ingestor = RSSIngestor()
    ingestor.add_source(source1)
    ingestor.add_source(source2)

    fake_entity1 = MagicMock()
    fake_entity1.id = "test-id-1"
    fake_entity2 = MagicMock()
    fake_entity2.id = "test-id-2"

    with (
        patch.object(source1, "fetch", new_callable=AsyncMock) as mock_fetch1,
        patch.object(source2, "fetch", new_callable=AsyncMock) as mock_fetch2,
    ):
        mock_fetch1.return_value = [fake_entity1]
        mock_fetch2.return_value = [fake_entity2]

        entities = await ingestor.ingest_all()

    assert len(entities) == 2


@pytest.mark.asyncio
async def test_rss_ingestor_handles_failure():
    """Test RSSIngestor handles source fetch failures gracefully."""
    source = RSSSource(name="feed1", url="https://example.com/1.xml")

    ingestor = RSSIngestor()
    ingestor.add_source(source)

    with patch.object(source, "fetch", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.side_effect = Exception("Network error")

        entities = await ingestor.ingest_all()

    assert len(entities) == 0
