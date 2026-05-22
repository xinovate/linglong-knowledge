"""Integration test: inline package → PackageExecutor → entities."""

import pytest

from linglong.ingest.executor import PackageExecutor
from linglong.ingest.package import SourcePackage


@pytest.mark.asyncio
async def test_end_to_end_package_execution():
    """Full flow: inline package config → executor → entities returned."""
    package = SourcePackage(
        name="test-integration",
        topic="test",
        sources=[
            {"id": "aihot", "type": "aihot", "enabled": False, "config": {"endpoint": "daily"}},
        ],
        dimensions=[],
    )

    executor = PackageExecutor()
    result = await executor.execute(package)

    assert "entities" in result
    assert "failed" in result
    assert "total" in result
