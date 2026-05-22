"""Tests for dimension filter."""

from datetime import UTC, datetime, timedelta

from linglong.core.models import Entity, EntityFacet
from linglong.ingest.filter import filter_by_dimensions, filter_dimension
from linglong.ingest.package import DimensionConfig, FilterConfig


def _make_entity(title: str, days_ago: int = 0) -> Entity:
    created = (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()
    return Entity(
        content=f"# {title}\n\nSome content",
        facet=EntityFacet.REFERENCE,
        created_by="agent:web_search",
        created_at=created,
    )


class TestFilterDimension:
    def test_max_results_limits_output(self):
        entities = [_make_entity(f"item-{i}") for i in range(10)]
        filt = FilterConfig(max_results=3, max_age_days=7)
        result = filter_dimension(entities, filt, "test")
        assert len(result) == 3

    def test_max_age_days_filters_old(self):
        entities = [
            _make_entity("new", days_ago=1),
            _make_entity("old", days_ago=10),
        ]
        filt = FilterConfig(max_results=10, max_age_days=7)
        result = filter_dimension(entities, filt, "test")
        assert len(result) == 1
        assert "new" in result[0].content

    def test_no_entities(self):
        filt = FilterConfig(max_results=5, max_age_days=7)
        result = filter_dimension([], filt, "test")
        assert result == []

    def test_all_within_limits(self):
        entities = [_make_entity(f"item-{i}") for i in range(3)]
        filt = FilterConfig(max_results=10, max_age_days=7)
        result = filter_dimension(entities, filt, "test")
        assert len(result) == 3


class TestFilterByDimensions:
    def test_filter_multiple_dimensions(self):
        dim_entities = {
            "研究员观点": [_make_entity(f"r-{i}") for i in range(8)],
            "公司决策": [_make_entity(f"c-{i}") for i in range(5)],
        }
        dimensions = [
            DimensionConfig(name="研究员观点", filter=FilterConfig(max_results=3)),
            DimensionConfig(name="公司决策", filter=FilterConfig(max_results=2)),
        ]
        result = filter_by_dimensions(dim_entities, dimensions)
        assert len(result["研究员观点"]) == 3
        assert len(result["公司决策"]) == 2

    def test_unknown_dimension_passes_through(self):
        dim_entities = {"未知维度": [_make_entity("x")]}
        result = filter_by_dimensions(dim_entities, [])
        assert len(result["未知维度"]) == 1

    def test_empty_dimensions(self):
        result = filter_by_dimensions({}, [])
        assert result == {}
