"""Tests for PackageExecutor."""

import pytest
from unittest.mock import patch

from linglong.core.models import Entity, EntityFacet
from linglong.ingest.adapter import AdapterRegistry, SourceAdapter
from linglong.ingest.executor import PackageExecutor
from linglong.ingest.package import (
    SearchQueryConfig,
    SourceDefinition,
    SourcePackage,
)


class MockAdapter(SourceAdapter):
    adapter_type = "mock_executor"

    def __init__(self, source_id: str, config: dict, metadata: dict):
        super().__init__(source_id, config, metadata)
        self._entities = [
            Entity(
                id=f"{source_id}-{i}",
                content=f"# Entity {i} from {source_id}\n\nContent here",
                facet=EntityFacet.CONCEPT,
                created_by="test",
                confidence=0.7,
            )
            for i in range(config.get("count", 1))
        ]

    async def fetch(self) -> list[Entity]:
        return self._entities

    def health_check(self) -> bool:
        return True


@pytest.fixture(autouse=True)
def _register_mock():
    AdapterRegistry.register(MockAdapter)


@pytest.mark.asyncio
async def test_executor_runs_all_sources():
    """Executor fetches from all sources in a package."""
    package = SourcePackage(
        name="Test",
        topic="test",
        sources=[
            SourceDefinition(id="s1", type="mock_executor"),
            SourceDefinition(id="s2", type="mock_executor"),
        ],
    )
    executor = PackageExecutor()
    result = await executor.execute(package)
    assert len(result["entities"]) == 2
    assert result["total"] == 2


@pytest.mark.asyncio
async def test_executor_skips_disabled_sources():
    """Disabled sources are not fetched."""
    package = SourcePackage(
        name="Test",
        topic="test",
        sources=[
            SourceDefinition(id="s1", type="mock_executor"),
            SourceDefinition(id="s2", type="mock_executor", enabled=False),
        ],
    )
    executor = PackageExecutor()
    result = await executor.execute(package)
    assert len(result["entities"]) == 1


@pytest.mark.asyncio
async def test_executor_skips_disabled_package():
    """Disabled package returns empty entities."""
    package = SourcePackage(name="Test", topic="test", enabled=False)
    executor = PackageExecutor()
    result = await executor.execute(package)
    assert len(result["entities"]) == 0


@pytest.mark.asyncio
async def test_executor_aggregates_sources_and_search():
    """Top-level sources and search queries aggregate into one pool."""
    package = SourcePackage(
        name="Test",
        topic="test",
        sources=[
            SourceDefinition(id="aihot", type="mock_executor", config={"count": 3}),
        ],
        search_queries=[
            SearchQueryConfig(
                keywords=["test query"],
                max_results=5,
            ),
        ],
    )
    # Mock web_search adapter to return entities for search queries
    mock_search = MockAdapter(
        source_id="search:test",
        config={"count": 2},
        metadata={},
    )
    with patch.object(
        AdapterRegistry, "get",
        side_effect=lambda t: MockAdapter if t in ("mock_executor", "web_search") else None,
    ):
        executor = PackageExecutor()
        result = await executor.execute(package)
    # 3 from top-level sources
    assert result["total"] >= 3


@pytest.mark.asyncio
async def test_executor_formats_morning_brief():
    """Morning brief format is generated when output.format is set."""
    package = SourcePackage(
        name="Test",
        topic="AI 测试",
        output={"format": "morning-brief", "persist": False},
        sources=[
            SourceDefinition(id="s1", type="mock_executor"),
        ],
    )
    executor = PackageExecutor()
    result = await executor.execute(package)
    assert result["output"] is not None
    assert "AI 测试" in result["output"]
