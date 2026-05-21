"""Integration test: YAML package → PackageExecutor → KnowledgeStore."""

from unittest.mock import MagicMock

import pytest

from linglong.ingest.executor import PackageExecutor
from linglong.ingest.package import SourcePackage


@pytest.fixture
def mock_store():
    store = MagicMock()
    store.get = MagicMock(return_value=None)
    return store


@pytest.mark.asyncio
async def test_end_to_end_package_execution(mock_store):
    """Full flow: package YAML → executor → store calls."""
    package = SourcePackage.from_yaml("docs/examples/packages/ai-morning-brief.yaml")
    # 禁用 web_fetch 和 api 避免网络调用
    for source in package.sources:
        if source.type != "rss":
            source.enabled = False

    executor = PackageExecutor(store=mock_store)
    result = await executor.execute(package)

    assert "created" in result
    assert "failed" in result
    assert "total" in result
