"""Tests for formatting templates."""

from linglong.core.models import Entity, EntityFacet, Source, SourceType
from linglong.ingest.templates.morning_brief import format_morning_brief


def _make_entity(title: str, snippet: str = "", url: str = "") -> Entity:
    sources = []
    if url:
        sources.append(Source(type=SourceType.WEB_SEARCH, name="test", url=url))
    return Entity(
        content=f"# {title}\n\n{snippet}\n\n[Source]({url})" if url else f"# {title}\n\n{snippet}",
        facet=EntityFacet.REFERENCE,
        created_by="agent:web_search",
        sources=sources,
    )


class TestMorningBrief:
    def test_basic_format(self):
        dim_entities = {
            "研究员观点": [
                _make_entity("Karpathy 发布新框架", "A new AI framework", "https://example.com/1"),
            ],
            "公司决策": [
                _make_entity("OpenAI 发布 GPT-5", "Latest model release", "https://example.com/2"),
                _make_entity("Anthropic Claude 4", "New Claude version", "https://example.com/3"),
            ],
        }
        result = format_morning_brief(dim_entities)

        assert "AI 早报" in result
        assert "研究员观点" in result
        assert "公司决策" in result
        assert "Karpathy" in result
        assert "GPT-5" in result

    def test_empty_entities(self):
        result = format_morning_brief({})
        assert "暂无新消息" in result

    def test_custom_title(self):
        result = format_morning_brief(
            {"测试": [_make_entity("Title", "text", "https://example.com")]},
            title="周报",
        )
        assert "周报" in result

    def test_entity_without_source_url(self):
        dim_entities = {
            "开源趋势": [_make_entity("New Project", "A cool project")],
        }
        result = format_morning_brief(dim_entities)
        assert "New Project" in result

    def test_dimension_with_no_entities_included(self):
        dim_entities = {
            "研究员观点": [_make_entity("Test", "text", "https://example.com")],
            "公司决策": [],
        }
        result = format_morning_brief(dim_entities)
        assert "研究员观点" in result
        # Empty dimension should not produce a section header
        lines = result.split("\n")
        company_sections = [l for l in lines if "公司决策" in l and l.startswith("##")]
        assert len(company_sections) == 0
