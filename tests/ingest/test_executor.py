"""Tests for PackageExecutor."""

import pytest

from linglong.core.models import Entity, EntityFacet
from linglong.ingest.adapter import AdapterRegistry, SourceAdapter
from linglong.ingest.executor import PackageExecutor
from linglong.ingest.package import SourceDefinition, SourcePackage


class MockAdapter(SourceAdapter):
    adapter_type = "mock"

    async def fetch(self) -> list[Entity]:
        return [
            Entity(
                id=f"{self.source_id}-1",
                content=f"Content from {self.source_id}",
                facet=EntityFacet.CONCEPT,
                created_by="test",
                confidence=0.7,
            )
        ]

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
            SourceDefinition(id="s1", type="mock"),
            SourceDefinition(id="s2", type="mock"),
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
            SourceDefinition(id="s1", type="mock"),
            SourceDefinition(id="s2", type="mock", enabled=False),
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
