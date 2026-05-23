"""Tests for GitHubAdapter."""

import pytest

from linglong.ingest.adapters.github import GitHubAdapter

_MOCK_RESPONSE = {
    "total_count": 3,
    "items": [
        {
            "full_name": "openai/codex",
            "description": "Lightweight coding agent",
            "html_url": "https://github.com/openai/codex",
            "stargazers_count": 5200,
            "language": "Python",
            "topics": ["ai", "agent", "coding"],
            "created_at": "2026-05-20T10:00:00Z",
        },
        {
            "full_name": "anthropic/claude-sdk",
            "description": "Official Claude SDK",
            "html_url": "https://github.com/anthropic/claude-sdk",
            "stargazers_count": 3100,
            "language": "TypeScript",
            "topics": ["ai", "llm"],
            "created_at": "2026-05-18T12:00:00Z",
        },
    ],
}


@pytest.fixture
def adapter():
    return GitHubAdapter(
        source_id="test-github",
        config={"topics": ["ai", "llm"], "min_stars": 50, "since_days": 7, "max_results": 10},
        metadata={},
    )


def test_adapter_type():
    assert GitHubAdapter.adapter_type == "github"


def test_health_check(adapter):
    assert adapter.health_check() is True


def test_item_to_entity(adapter):
    entity = adapter._item_to_entity(_MOCK_RESPONSE["items"][0])
    assert "openai/codex" in entity.content
    assert entity.created_by == "agent:github"
    assert entity.sources[0].metadata["stars"] == 5200
    assert entity.sources[0].metadata["language"] == "Python"
    assert entity.sources[0].url == "https://github.com/openai/codex"


def test_item_with_no_description(adapter):
    item = {
        "full_name": "test/empty",
        "description": None,
        "html_url": "https://github.com/test/empty",
        "stargazers_count": 100,
        "language": None,
        "topics": [],
        "created_at": "2026-05-20T00:00:00Z",
    }
    entity = adapter._item_to_entity(item)
    assert "test/empty" in entity.content
    assert entity.sources[0].metadata["language"] == "?"


@pytest.mark.asyncio
async def test_fetch_with_mock(adapter):
    import httpx
    from unittest.mock import AsyncMock, patch

    mock_response = httpx.Response(
        200,
        json=_MOCK_RESPONSE,
        request=httpx.Request("GET", "http://test"),
    )
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        entities = await adapter.fetch()
    assert len(entities) == 2
    assert "openai/codex" in entities[0].content
