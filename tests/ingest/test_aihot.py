"""Tests for AIHOT adapter."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from linglong.core.models import EntityFacet
from linglong.ingest.adapters.aihot import AIHOTAdapter


def _make_adapter(config: dict | None = None) -> AIHOTAdapter:
    return AIHOTAdapter(
        source_id="aihot-test",
        config=config or {},
        metadata={},
    )


def _mock_httpx_client(json_data: dict) -> tuple[MagicMock, AsyncMock]:
    """Create a properly mocked httpx.AsyncClient."""
    mock_response = MagicMock()
    mock_response.json.return_value = json_data
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    # Make async context manager work
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    return mock_cm, mock_client


class TestAIHOTItems:
    @pytest.mark.asyncio
    async def test_fetch_items(self):
        mock_cm, mock_client = _mock_httpx_client({
            "count": 2,
            "items": [
                {
                    "title": "GPT-5 Released",
                    "summary": "OpenAI releases GPT-5",
                    "url": "https://example.com/gpt5",
                    "source": "TechNews",
                    "category": "ai-models",
                    "publishedAt": "2026-05-22T10:00:00Z",
                },
                {
                    "title": "Claude 4 Launch",
                    "summary": "Anthropic launches Claude 4",
                    "url": "https://example.com/claude4",
                    "source": "AINews",
                    "category": "ai-models",
                    "publishedAt": "2026-05-22T11:00:00Z",
                },
            ],
        })

        with patch("linglong.ingest.adapters.aihot.httpx.AsyncClient", return_value=mock_cm):
            adapter = _make_adapter({"endpoint": "items", "mode": "selected", "limit": 10})
            entities = await adapter.fetch()

        assert len(entities) == 2
        assert entities[0].content.startswith("# GPT-5 Released")
        assert entities[0].facet == EntityFacet.REFERENCE
        assert entities[0].created_by == "agent:aihot"
        assert entities[0].sources[0].url == "https://example.com/gpt5"
        assert entities[1].content.startswith("# Claude 4 Launch")

    @pytest.mark.asyncio
    async def test_fetch_items_with_category(self):
        mock_cm, mock_client = _mock_httpx_client({"count": 0, "items": []})

        with patch("linglong.ingest.adapters.aihot.httpx.AsyncClient", return_value=mock_cm):
            adapter = _make_adapter({"category": "ai-models"})
            await adapter.fetch()

        call_args = mock_client.get.call_args
        params = call_args[1]["params"]
        assert params["category"] == "ai-models"


class TestAIHOTDaily:
    @pytest.mark.asyncio
    async def test_fetch_daily(self):
        mock_cm, mock_client = _mock_httpx_client({
            "date": "2026-05-22",
            "sections": [
                {
                    "label": "模型发布/更新",
                    "items": [
                        {
                            "title": "Aleph 2.0",
                            "summary": "Runway releases Aleph 2.0",
                            "url": "https://example.com/aleph",
                            "source": "Runway",
                        },
                    ],
                },
                {
                    "label": "行业动态",
                    "items": [
                        {
                            "title": "FSD enters China",
                            "summary": "Tesla FSD in China",
                            "url": "https://example.com/fsd",
                            "source": "X",
                        },
                    ],
                },
            ],
        })

        with patch("linglong.ingest.adapters.aihot.httpx.AsyncClient", return_value=mock_cm):
            adapter = _make_adapter({"endpoint": "daily"})
            entities = await adapter.fetch()

        assert len(entities) == 2
        assert entities[0].content.startswith("# Aleph 2.0")
        assert entities[0].sources[0].metadata.get("section") == "模型发布/更新"
        assert entities[1].sources[0].metadata.get("section") == "行业动态"

    @pytest.mark.asyncio
    async def test_fetch_daily_empty_sections(self):
        mock_cm, _ = _mock_httpx_client({"date": "2026-05-22", "sections": []})

        with patch("linglong.ingest.adapters.aihot.httpx.AsyncClient", return_value=mock_cm):
            adapter = _make_adapter({"endpoint": "daily"})
            entities = await adapter.fetch()
        assert entities == []


class TestAIHOTAdapterMisc:
    def test_adapter_type(self):
        assert AIHOTAdapter.adapter_type == "aihot"

    def test_health_check(self):
        adapter = _make_adapter()
        assert adapter.health_check() is True

    def test_registered(self):
        from linglong.ingest.adapter import AdapterRegistry

        assert AdapterRegistry.get("aihot") is AIHOTAdapter

    @pytest.mark.asyncio
    async def test_default_endpoint_is_items(self):
        mock_cm, mock_client = _mock_httpx_client({"count": 0, "items": []})

        with patch("linglong.ingest.adapters.aihot.httpx.AsyncClient", return_value=mock_cm):
            adapter = _make_adapter({})
            await adapter.fetch()

        call_args = mock_client.get.call_args
        url = call_args[0][0]
        assert url.endswith("/items")
