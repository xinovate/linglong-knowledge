"""Package executor — orchestrates parallel fetching across all sources in a package."""

import asyncio
import logging
from typing import Any

from linglong.core.models import Entity
from linglong.ingest.adapter import AdapterRegistry, SourceAdapter
from linglong.ingest.dedup import dedup_entities
from linglong.ingest.history import IngestHistory
from linglong.ingest.package import SearchQueryConfig, SourcePackage
from linglong.ingest.templates import get_template
from linglong.ingest.verification import TruthVerificationEngine

logger = logging.getLogger(__name__)


class PackageExecutor:
    """Execute a source package: fetch all sources → aggregate → tag → interpret → format."""

    def __init__(
        self,
        verification_engine: TruthVerificationEngine | None = None,
        history: IngestHistory | None = None,
        dedup_lookback_days: int = 7,
        llm_config: dict[str, Any] | None = None,
    ) -> None:
        self.verification_engine = verification_engine
        self.history = history
        self.dedup_lookback_days = dedup_lookback_days
        self.llm_config = llm_config

    async def execute(self, package: SourcePackage) -> dict[str, Any]:
        """Execute all enabled sources in a package concurrently."""
        if not package.enabled:
            logger.info("Package %s is disabled, skipping", package.name)
            return _empty_result()

        # Phase 1: Fetch ALL sources in parallel
        all_entities: list[Entity] = []

        # 1a. Top-level sources (AIHOT, ArXiv, GitHub, RSS, etc.)
        if package.sources:
            source_entities = await self._fetch_sources(package.sources)
            all_entities.extend(source_entities)

        # 1b. Search queries
        if package.search_queries:
            search_entities = await self._fetch_search_queries(package.search_queries)
            all_entities.extend(search_entities)

        total = len(all_entities)

        # Phase 2: Verification
        if self.verification_engine and package.verification.enabled:
            all_entities, _ = self._verify(all_entities)

        # Phase 3: Cross-day dedup
        dedup_count = total
        if self.history:
            all_entities = dedup_entities(
                all_entities,
                self.history,
                lookback_days=self.dedup_lookback_days,
            )
            dedup_count = len(all_entities)

        # Phase 4: LLM auto-tag (dimension classification)
        dimension_entities: dict[str, list[Entity]] = {}
        if self.llm_config and all_entities:
            try:
                from linglong.ingest.interpreter import auto_tag

                dimension_entities = auto_tag(all_entities, self.llm_config)
            except Exception as e:
                logger.warning("Auto-tag failed (non-fatal): %s", e)
                dimension_entities = {"AI 动态": all_entities}
        elif all_entities:
            dimension_entities = {"AI 动态": all_entities}

        # Phase 5: LLM interpretation + Top 5
        interpretations: dict[str, list[dict[str, str]]] = {}
        top5: list[dict[str, Any]] = []
        if self.llm_config and package.output.format == "morning-brief" and all_entities:
            try:
                from linglong.ingest.interpreter import generate_top5, interpret_dimension

                all_interps = interpret_dimension(all_entities, self.llm_config)

                # Map interpretations back to dimensions
                interp_idx = 0
                for dim_name, dim_ents in dimension_entities.items():
                    dim_interps = all_interps[interp_idx:interp_idx + len(dim_ents)]
                    interp_idx += len(dim_ents)
                    interpretations[dim_name] = dim_interps

                if all_interps:
                    top5 = generate_top5(all_interps, self.llm_config)
            except Exception as e:
                logger.warning("LLM interpretation failed (non-fatal): %s", e)

        # Phase 6: Persist to history
        if self.history and package.output.persist:
            for dim_name, dim_ents in dimension_entities.items():
                self.history.write_batch(dim_ents, dimension=dim_name)

        # Phase 7: Formatting
        output_text: str | None = None
        if package.output.format and dimension_entities:
            template_fn = get_template(package.output.format)
            if template_fn:
                output_text = template_fn(
                    dimension_entities,
                    title=package.topic,
                    interpretations=interpretations or None,
                    top5=top5 or None,
                )

        return {
            "entities": all_entities,
            "total": total,
            "filtered": dedup_count,
            "failed": 0,
            "output": output_text,
        }

    async def _fetch_sources(
        self, sources: list[Any]
    ) -> list[Entity]:
        """Fetch from source definitions."""
        adapters: list[SourceAdapter] = []
        for source_def in sources:
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

        fetch_tasks = [self._fetch_with_error_handling(a) for a in adapters]
        fetch_results = await asyncio.gather(*fetch_tasks)

        entities: list[Entity] = []
        for result in fetch_results:
            entities.extend(result)
        return entities

    async def _fetch_search_queries(
        self, queries: list[SearchQueryConfig]
    ) -> list[Entity]:
        """Fetch from search query groups."""
        search_adapter_cls = AdapterRegistry.get("web_search")
        if not search_adapter_cls:
            return []

        async def _fetch_one(query: SearchQueryConfig) -> list[Entity]:
            adapter = search_adapter_cls(
                source_id=f"search:{query.keywords[0][:20]}",
                config={
                    "queries": query.keywords,
                    "engine": "auto",
                    "concurrent": True,
                    "max_results": query.max_results * 2,
                    "max_age_days": query.max_age_days,
                },
                metadata={},
            )
            try:
                return await adapter.fetch()
            except Exception as e:
                logger.warning("Search query failed: %s", e)
                return []

        tasks = [_fetch_one(q) for q in queries]
        results = await asyncio.gather(*tasks)

        entities: list[Entity] = []
        for result in results:
            entities.extend(result)
        return entities

    async def _fetch_with_error_handling(self, adapter: SourceAdapter) -> list[Entity]:
        try:
            return await adapter.fetch()
        except Exception as e:
            logger.exception("Failed to fetch from %s: %s", adapter.source_id, e)
            return []

    def _verify(
        self, entities: list[Entity]
    ) -> tuple[list[Entity], int]:
        """Apply truth verification. Returns (passed_entities, passed_count)."""
        if not self.verification_engine:
            return entities, len(entities)

        verification_results = self.verification_engine.verify_batch(entities)
        passed: list[Entity] = []
        for entity, vresult in zip(entities, verification_results):
            if vresult.passed:
                entity.confidence = min(1.0, float(entity.confidence) + vresult.score * 0.1)
                passed.append(entity)
            else:
                logger.info(
                    "Entity %s failed verification: %s",
                    entity.id,
                    "; ".join(vresult.reasons),
                )
        return passed, len(passed)


def _empty_result() -> dict[str, Any]:
    return {
        "entities": [],
        "total": 0,
        "filtered": 0,
        "failed": 0,
        "output": None,
    }
