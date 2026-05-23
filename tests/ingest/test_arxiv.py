"""Tests for ArXivAdapter."""

import pytest

from linglong.ingest.adapters.arxiv import ArXivAdapter

_MOCK_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Vector Policy Optimization: Training for Diversity</title>
    <id>http://arxiv.org/abs/2605.22817v1</id>
    <summary>Language models must now generalize out of the box to novel environments.</summary>
    <published>2026-05-23T08:00:00Z</published>
    <category term="cs.AI"/>
    <category term="cs.CL"/>
  </entry>
  <entry>
    <title>MOSS: Self-Evolution in Autonomous Agents</title>
    <id>http://arxiv.org/abs/2605.22000v1</id>
    <summary>Autonomous agentic systems are largely static after deployment.</summary>
    <published>2026-05-23T06:00:00Z</published>
    <category term="cs.AI"/>
  </entry>
</feed>
"""


@pytest.fixture
def adapter():
    return ArXivAdapter(
        source_id="test-arxiv",
        config={"categories": ["cs.AI", "cs.CL"], "max_results": 10},
        metadata={},
    )


def test_adapter_type():
    assert ArXivAdapter.adapter_type == "arxiv"


def test_health_check(adapter):
    assert adapter.health_check() is True


def test_parse_xml(adapter):
    entities = adapter._parse(_MOCK_XML)
    assert len(entities) == 2

    e1 = entities[0]
    assert "Vector Policy Optimization" in e1.content
    assert e1.created_by == "agent:arxiv"
    assert e1.sources[0].metadata["arxiv_id"] == "2605.22817v1"
    assert e1.sources[0].metadata["categories"] == "cs.AI/cs.CL"
    assert e1.sources[0].metadata["published_at"] == "2026-05-23"

    e2 = entities[1]
    assert "MOSS" in e2.content
    assert e2.sources[0].metadata["arxiv_id"] == "2605.22000v1"


def test_parse_empty_xml(adapter):
    entities = adapter._parse('<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>')
    assert len(entities) == 0


@pytest.mark.asyncio
async def test_fetch_with_mock(adapter):
    import httpx
    from unittest.mock import AsyncMock, patch

    mock_response = httpx.Response(200, text=_MOCK_XML, request=httpx.Request("GET", "http://test"))
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        entities = await adapter.fetch()
    assert len(entities) == 2
