"""Tests for LLM interpreter — batch per dimension via Anthropic API."""

import json
from unittest.mock import MagicMock, patch

from linglong.core.models import Entity, EntityFacet
from linglong.ingest.interpreter import (
    _entity_snippet,
    _entity_title,
    generate_top5,
    interpret_dimension,
)


def _make_entity(title: str, snippet: str = "Test content here") -> Entity:
    return Entity(
        content=f"# {title}\n\n{snippet}\n\n[Source](https://example.com)",
        facet=EntityFacet.REFERENCE,
        created_by="agent:web_search",
    )


class TestHelpers:
    def test_entity_title(self):
        e = _make_entity("OpenAI GPT-5 Release", "Details here")
        assert _entity_title(e) == "OpenAI GPT-5 Release"

    def test_entity_snippet(self):
        e = _make_entity("Test", "This is the snippet text")
        assert _entity_snippet(e) == "This is the snippet text"

    def test_entity_title_no_heading(self):
        e = Entity(
            content="Just some text without heading",
            facet=EntityFacet.REFERENCE,
            created_by="agent:test",
        )
        assert _entity_title(e) == "Just some text without heading"


class TestInterpretDimension:
    @patch("linglong.ingest.interpreter._call_llm")
    def test_batch_interpretation(self, mock_call):
        mock_call.return_value = json.dumps({
            "items": [
                {"index": 1, "interpretation": "GPT-5发布，AI能力再次跃升"},
                {"index": 2, "interpretation": "Claude 4发布，竞争加剧"},
            ]
        })
        entities = [
            _make_entity("OpenAI releases GPT-5"),
            _make_entity("Anthropic Claude 4"),
        ]
        results = interpret_dimension(entities)
        assert len(results) == 2
        assert results[0]["interpretation"] == "GPT-5发布，AI能力再次跃升"
        assert results[1]["interpretation"] == "Claude 4发布，竞争加剧"
        assert mock_call.call_count == 1

    def test_empty_entities(self):
        results = interpret_dimension([])
        assert results == []

    @patch("linglong.ingest.interpreter._call_llm")
    def test_llm_failure_falls_back(self, mock_call):
        mock_call.side_effect = Exception("LLM unavailable")
        entities = [_make_entity("Test news")]
        results = interpret_dimension(entities)
        assert len(results) == 1
        assert results[0]["interpretation"] == ""

    @patch("linglong.ingest.interpreter._call_llm")
    def test_uses_glm51_model(self, mock_call):
        mock_call.return_value = '{"items": []}'
        entities = [_make_entity("Test")]
        interpret_dimension(entities)
        # _call_llm called with system prompt containing batch template
        call_args = mock_call.call_args
        assert "资深分析师" in call_args[0][0]


class TestGenerateTop5:
    @patch("linglong.ingest.interpreter._call_llm")
    def test_with_mock_llm(self, mock_call):
        top5_response = {
            "top5": [
                {
                    "index": 1,
                    "title": "OpenAI GPT-5",
                    "dimensions": {
                        "company": "OpenAI从产品公司向科研机构转型",
                        "strategy": "AI科研范式重构",
                        "technology": "多模态能力突破",
                        "insight": "关注AI基础研究",
                    },
                }
            ]
        }
        mock_call.return_value = json.dumps(top5_response)
        items = [
            {"title": "OpenAI GPT-5", "interpretation": "Big release", "dimension": "公司决策"},
            {"title": "Figure AI funding", "interpretation": "Robotics boom", "dimension": "资本决策"},
        ]
        results = generate_top5(items)
        assert len(results) == 1
        assert results[0]["title"] == "OpenAI GPT-5"
        assert "company" in results[0]["dimensions"]

    @patch("linglong.ingest.interpreter._call_llm")
    def test_llm_failure_returns_empty(self, mock_call):
        mock_call.side_effect = Exception("Failed")
        results = generate_top5([{"title": "Test", "interpretation": "test"}])
        assert results == []

    def test_empty_items_returns_empty(self):
        results = generate_top5([])
        assert results == []
