"""Linglong Ingest - Data ingestion from RSS, APIs, and AI tasks."""

from linglong.ingest.adapter import AdapterRegistry, SourceAdapter
from linglong.ingest.adapters.api import APIAdapter
from linglong.ingest.adapters.rss import RSSAdapter
from linglong.ingest.adapters.web_fetch import WebFetchAdapter
from linglong.ingest.adapters.aihot import AIHOTAdapter
from linglong.ingest.adapters.web_search import WebSearchAdapter
from linglong.ingest.executor import PackageExecutor
from linglong.ingest.package import SourcePackage
from linglong.ingest.rss import RSSIngestor, RSSSource
from linglong.ingest.verification import TruthVerificationEngine

# 注册所有内置适配器
AdapterRegistry.register(RSSAdapter)
AdapterRegistry.register(WebFetchAdapter)
AdapterRegistry.register(WebSearchAdapter)
AdapterRegistry.register(APIAdapter)
AdapterRegistry.register(AIHOTAdapter)

__all__ = [
    "AdapterRegistry",
    "AIHOTAdapter",
    "APIAdapter",
    "PackageExecutor",
    "RSSAdapter",
    "RSSIngestor",
    "RSSSource",
    "SourceAdapter",
    "SourcePackage",
    "TruthVerificationEngine",
    "WebFetchAdapter",
    "WebSearchAdapter",
]
