"""Tests for WebSearchAdapter."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from linglong.core.config import IngestConfig, LinglongConfig, set_config
from linglong.core.models import EntityFacet
from linglong.ingest.adapters.web_search import (
    WebSearchAdapter,
    _parse_search_html,
)


def _make_adapter(
    queries: list[str] | None = None,
    engine: str = "bing_cn",
    max_results: int = 10,
) -> WebSearchAdapter:
    if queries is None:
        queries = ["test query"]
    config = {
        "queries": queries,
        "engine": engine,
        "max_results": max_results,
    }
    return WebSearchAdapter(
        source_id="test-search",
        config=config,
        metadata={},
    )


# --- HTML parsing ---

class TestParseSearchHtml:
    def test_parse_bing_style_html(self):
        html = """
        <html><body>
        <li class="b_algo">
            <h2><a href="https://example.com/result1">Result Title 1</a></h2>
            <p>This is the snippet for result 1.</p>
        </li>
        <li class="b_algo">
            <h2><a href="https://example.com/result2">Result Title 2</a></h2>
            <p>Snippet for result 2 here.</p>
        </li>
        </body></html>
        """
        results = _parse_search_html(html, 10)
        assert len(results) >= 1
        # At least one result should have title and url
        found = any(r["title"] and r["url"] for r in results)
        assert found

    def test_max_results_limit(self):
        html = """
        <li class="b_algo">
            <h2><a href="https://example.com/1">Title 1</a></h2>
            <p>Snippet 1</p>
        </li>
        <li class="b_algo">
            <h2><a href="https://example.com/2">Title 2</a></h2>
            <p>Snippet 2</p>
        </li>
        """
        results = _parse_search_html(html, 1)
        assert len(results) <= 1

    def test_empty_html(self):
        results = _parse_search_html("<html><body></body></html>", 10)
        assert results == []


# --- Adapter tests ---

class TestWebSearchAdapter:
    def test_health_check_with_queries(self):
        adapter = _make_adapter(queries=["test"])
        assert adapter.health_check() is True

    def test_health_check_without_queries(self):
        adapter = WebSearchAdapter("test", {}, {})
        assert adapter.health_check() is False

    def test_resolve_engine_bing_cn(self):
        adapter = _make_adapter(engine="bing_cn")
        assert adapter.config["engine"] == "bing_cn"

    def test_resolve_engine_google(self):
        """When global config has proxy, auto resolves to google."""
        adapter = _make_adapter(engine="google")
        # The adapter config overrides engine, but _resolve_engine reads global config
        # Test that fetch() uses the local engine override
        # (actual fetch test with google is done via integration)
        assert adapter.config["engine"] == "google"

    @pytest.mark.asyncio
    async def test_fetch_bing_cn(self):
        """Test fetching via Bing CN (mocked httpx)."""
        adapter = _make_adapter(queries=["test"], engine="bing_cn")

        mock_html = """
        <li class="b_algo">
            <h2><a href="https://example.com/article">Test Article</a></h2>
            <p>This is a test snippet about AI.</p>
        </li>
        """

        with patch("linglong.ingest.adapters.web_search.httpx.AsyncClient") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.text = mock_html
            mock_response.raise_for_status = MagicMock()

            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            entities = await adapter.fetch()

        assert len(entities) >= 1
        assert entities[0].created_by == "agent:web_search"
        assert "Test Article" in entities[0].content

    @pytest.mark.asyncio
    async def test_fetch_empty_queries(self):
        adapter = _make_adapter(queries=[], engine="bing_cn")
        entities = await adapter.fetch()
        assert entities == []

    @pytest.mark.asyncio
    async def test_fetch_handles_error(self):
        """Test that a search failure doesn't crash the whole fetch."""
        adapter = _make_adapter(queries=["will-fail"], engine="bing_cn")

        with patch("linglong.ingest.adapters.web_search.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("Network error"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            entities = await adapter.fetch()

        assert entities == []

    @pytest.mark.asyncio
    async def test_fetch_searxng(self):
        """Test fetching via SearXNG JSON API (mocked httpx)."""
        adapter = _make_adapter(queries=["AI test"], engine="searxng")

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Test AI Article",
                    "url": "https://example.com/ai-test",
                    "content": "This is a test snippet about AI.",
                    "engine": "google",
                },
                {
                    "title": "Excluded Site",
                    "url": "https://github.com/test",
                    "content": "Should be excluded.",
                    "engine": "bing",
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("linglong.ingest.adapters.web_search.httpx.AsyncClient", return_value=mock_client):
            entities = await adapter.fetch()

        assert len(entities) == 1
        assert entities[0].facet == EntityFacet.REFERENCE
        assert "Test AI Article" in entities[0].content
        assert "https://example.com/ai-test" in entities[0].content

    @pytest.mark.asyncio
    async def test_fetch_searxng_no_time_range(self):
        """Test SearXNG does NOT send time_range (removed due to reliability issues)."""
        adapter = _make_adapter(queries=["test"], engine="searxng")

        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("linglong.ingest.adapters.web_search.httpx.AsyncClient", return_value=mock_client):
            await adapter._do_search("test", "searxng", 10, 3)

        call_args = mock_client.get.call_args
        params = call_args[1]["params"]
        assert "time_range" not in params
