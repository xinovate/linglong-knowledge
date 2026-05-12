"""Tests for PackageExecutor."""

from unittest.mock import MagicMock

import pytest

from linglong.core.models import Entity
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
                created_by="test",
                confidence=0.7,
            )
        ]

    def health_check(self) -> bool:
        return True


@pytest.fixture(autouse=True)
def _register_mock():
    AdapterRegistry.register(MockAdapter)


@pytest.fixture
def mock_store():
    store = MagicMock()
    store.get = MagicMock(return_value=None)
    return store


@pytest.mark.asyncio
async def test_executor_runs_all_sources(mock_store):
    """Executor fetches from all sources in a package."""
    package = SourcePackage(
        name="Test",
        topic="test",
        sources=[
            SourceDefinition(id="s1", type="mock"),
            SourceDefinition(id="s2", type="mock"),
        ],
    )
    executor = PackageExecutor(store=mock_store)
    result = await executor.execute(package)
    assert result["created"] == 2
    assert result["total"] == 2


@pytest.mark.asyncio
async def test_executor_skips_disabled_sources(mock_store):
    """Disabled sources are not fetched."""
    package = SourcePackage(
        name="Test",
        topic="test",
        sources=[
            SourceDefinition(id="s1", type="mock"),
            SourceDefinition(id="s2", type="mock", enabled=False),
        ],
    )
    executor = PackageExecutor(store=mock_store)
    result = await executor.execute(package)
    assert result["created"] == 1


@pytest.mark.asyncio
async def test_executor_skips_disabled_package(mock_store):
    """Disabled package returns zeros."""
    package = SourcePackage(name="Test", topic="test", enabled=False)
    executor = PackageExecutor(store=mock_store)
    result = await executor.execute(package)
    assert result["created"] == 0
