"""Linglong Ingest - Data ingestion from RSS, APIs, and AI tasks."""

from linglong.ingest.adapter import AdapterRegistry, SourceAdapter
from linglong.ingest.adapters.aihot import AIHOTAdapter
from linglong.ingest.adapters.api import APIAdapter
from linglong.ingest.adapters.arxiv import ArXivAdapter
from linglong.ingest.adapters.github import GitHubAdapter
from linglong.ingest.adapters.rss import RSSAdapter
from linglong.ingest.adapters.web_fetch import WebFetchAdapter
from linglong.ingest.adapters.web_search import WebSearchAdapter
from linglong.ingest.executor import PackageExecutor
from linglong.ingest.package import SourcePackage
from linglong.ingest.rss import RSSIngestor, RSSSource
from linglong.ingest.verification import TruthVerificationEngine

# 注册所有内置适配器
AdapterRegistry.register(ArXivAdapter)
AdapterRegistry.register(AIHOTAdapter)
AdapterRegistry.register(APIAdapter)
AdapterRegistry.register(GitHubAdapter)
AdapterRegistry.register(RSSAdapter)
AdapterRegistry.register(WebFetchAdapter)
AdapterRegistry.register(WebSearchAdapter)

__all__ = [
    "AdapterRegistry",
    "AIHOTAdapter",
    "APIAdapter",
    "ArXivAdapter",
    "GitHubAdapter",
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
