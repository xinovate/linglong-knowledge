"""Package executor — orchestrates parallel fetching across all sources in a package."""

import asyncio
import logging
from typing import Any

from linglong.core.models import Entity
from linglong.ingest.adapter import AdapterRegistry, SourceAdapter
from linglong.ingest.package import SourcePackage
from linglong.ingest.verification import TruthVerificationEngine

logger = logging.getLogger(__name__)


class PackageExecutor:
    """Execute a source package: fetch all sources in parallel, verify, return entities."""

    def __init__(
        self,
        verification_engine: TruthVerificationEngine | None = None,
    ) -> None:
        self.verification_engine = verification_engine

    async def execute(self, package: SourcePackage) -> dict[str, Any]:
        """Execute all enabled sources in a package concurrently."""
        if not package.enabled:
            logger.info("Package %s is disabled, skipping", package.name)
            return {"entities": [], "total": 0, "failed": 0, "verified": 0}

        adapters: list[SourceAdapter] = []
        for source_def in package.sources:
            if not source_def.enabled:
                continue
            adapter_cls = AdapterRegistry.get(source_def.type)
            if adapter_cls is None:
                logger.warning("Unknown adapter type: %s", source_def.type)
                continue
            adapter = adapter_cls(
                source_id=source_def.id,
                config=source_def.config,
                metadata=source_def.metadata,
            )
            adapters.append(adapter)

        logger.info("Fetching %d sources for package: %s", len(adapters), package.name)
        fetch_tasks = [self._fetch_with_error_handling(adapter) for adapter in adapters]
        fetch_results = await asyncio.gather(*fetch_tasks)

        all_entities: list[Entity] = []
        seen_ids: set[str] = set()
        for entities in fetch_results:
            for entity in entities:
                if entity.id and entity.id not in seen_ids:
                    all_entities.append(entity)
                    seen_ids.add(entity.id)

        verified_count = len(all_entities)
        if self.verification_engine and package.verification.enabled:
            verification_results = self.verification_engine.verify_batch(all_entities)
            passed_entities = []
            for entity, vresult in zip(all_entities, verification_results):
                if vresult.passed:
                    entity.confidence = min(1.0, float(entity.confidence) + vresult.score * 0.1)
                    passed_entities.append(entity)
                else:
                    logger.info(
                        "Entity %s failed verification: %s",
                        entity.id,
                        "; ".join(vresult.reasons),
                    )
            verified_count = len(passed_entities)
            all_entities = passed_entities

        return {
            "entities": all_entities,
            "total": len(all_entities),
            "failed": sum(1 for r in fetch_results if r is None),
            "verified": verified_count,
        }

    async def _fetch_with_error_handling(self, adapter: SourceAdapter) -> list[Entity]:
        try:
            return await adapter.fetch()
        except Exception as e:
            logger.exception("Failed to fetch from %s: %s", adapter.source_id, e)
            return []
