"""Integration test: YAML package → PackageExecutor → entities."""

import pytest

from linglong.ingest.executor import PackageExecutor
from linglong.ingest.package import SourcePackage


@pytest.mark.asyncio
async def test_end_to_end_package_execution():
    """Full flow: package YAML → executor → entities returned."""
    package = SourcePackage.from_yaml("packages/ai-morning-brief.yaml")
    # 禁用 aihot 避免网络调用
    for source in package.sources:
        source.enabled = False

    executor = PackageExecutor()
    result = await executor.execute(package)

    assert "entities" in result
    assert "failed" in result
    assert "total" in result
