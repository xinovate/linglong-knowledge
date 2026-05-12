"""Package executor — orchestrates parallel fetching across all sources in a package."""

from typing import Any

from linglong.core.models import Entity
from linglong.ingest.adapter import AdapterRegistry, SourceAdapter
from linglong.ingest.package import SourcePackage
from linglong.ingest.verification import TruthVerificationEngine
from linglong.knowledge.review import ReviewEngine
from linglong.knowledge.store import KnowledgeStore


class PackageExecutor:
    """Execute a source package: fetch all sources in parallel, verify, review, store."""

    def __init__(
        self,
        store: KnowledgeStore,
        review_engine: ReviewEngine | None = None,
        verification_engine: TruthVerificationEngine | None = None,
    ) -> None:
        self.store = store
        self.review_engine = review_engine or ReviewEngine()
        self.verification_engine = verification_engine

    async def execute(self, package: SourcePackage) -> dict[str, Any]:
        """Execute all enabled sources in a package concurrently."""
        raise NotImplementedError("PackageExecutor.execute() will be implemented in Task 6")
