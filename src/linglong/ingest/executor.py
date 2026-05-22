"""Package executor — orchestrates parallel fetching across all sources in a package."""

import asyncio
import logging
from typing import Any

from linglong.core.models import Entity
from linglong.ingest.adapter import AdapterRegistry, SourceAdapter
from linglong.ingest.dedup import dedup_entities
from linglong.ingest.filter import filter_by_dimensions
from linglong.ingest.history import IngestHistory
from linglong.ingest.package import DimensionConfig, SourcePackage
from linglong.ingest.templates import get_template
from linglong.ingest.verification import TruthVerificationEngine

logger = logging.getLogger(__name__)


class PackageExecutor:
    """Execute a source package: fetch, verify, dedup, filter, interpret, format, persist."""

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

        # Phase 1: Fetch from legacy sources (non-dimension)
        all_entities: list[Entity] = []
        if package.sources:
            source_entities = await self._fetch_sources(package.sources)
            all_entities.extend(source_entities)

        # Phase 2: Fetch from dimensions (search + sources per dimension)
        dimension_entities: dict[str, list[Entity]] = {}
        if package.dimensions:
            dimension_entities = await self._fetch_dimensions(package.dimensions)
            for dim_entities in dimension_entities.values():
                all_entities.extend(dim_entities)

        total = len(all_entities)

        # Phase 3: Verification
        if self.verification_engine and package.verification.enabled:
            all_entities, _ = self._verify(all_entities)

        # Phase 4: Cross-day dedup
        dedup_count = total
        if self.history and dimension_entities:
            deduped_dims: dict[str, list[Entity]] = {}
            for dim_name, dim_ents in dimension_entities.items():
                deduped = dedup_entities(
                    dim_ents,
                    self.history,
                    lookback_days=self.dedup_lookback_days,
                    dimension=dim_name,
                )
                deduped_dims[dim_name] = deduped
            dimension_entities = deduped_dims
            all_entities = []
            for dim_ents in dimension_entities.values():
                all_entities.extend(dim_ents)
            dedup_count = len(all_entities)

        # Phase 5: Dimension-based filtering
        filtered_count = dedup_count
        if dimension_entities:
            dimension_entities = filter_by_dimensions(
                dimension_entities, package.dimensions
            )
            all_entities = []
            for dim_ents in dimension_entities.values():
                all_entities.extend(dim_ents)
            filtered_count = len(all_entities)

        # Phase 6: LLM interpretation
        interpretations: dict[str, list[dict[str, str]]] = {}
        top5: list[dict[str, Any]] = []
        if self.llm_config and package.output.format == "morning-brief":
            try:
                from linglong.ingest.interpreter import generate_top5, interpret_dimension

                all_items_for_top5: list[dict[str, str]] = []
                for dim_name, dim_ents in dimension_entities.items():
                    if dim_ents:
                        dim_interps = interpret_dimension(dim_ents, self.llm_config)
                        interpretations[dim_name] = dim_interps
                        for interp in dim_interps:
                            interp["dimension"] = dim_name
                            all_items_for_top5.append(interp)

                if all_items_for_top5:
                    top5 = generate_top5(all_items_for_top5, self.llm_config)
            except Exception as e:
                logger.warning("LLM interpretation failed (non-fatal): %s", e)

        # Phase 7: Persist to history
        if self.history and package.output.persist:
            for dim_name, dim_ents in dimension_entities.items():
                self.history.write_batch(dim_ents, dimension=dim_name)

        # Phase 8: Formatting
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
            "filtered": filtered_count,
            "failed": 0,
            "output": output_text,
        }

    async def _fetch_sources(
        self, sources: list[Any]
    ) -> list[Entity]:
        """Fetch from legacy source definitions."""
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

    async def _fetch_dimensions(
        self, dimensions: list[DimensionConfig]
    ) -> dict[str, list[Entity]]:
        """Fetch from all dimensions in parallel."""
        result: dict[str, list[Entity]] = {}

        async def _fetch_one_dim(dim: DimensionConfig) -> tuple[str, list[Entity]]:
            entities: list[Entity] = []

            # Search-based sources
            if dim.search.keywords:
                search_adapter_cls = AdapterRegistry.get("web_search")
                if search_adapter_cls:
                    adapter = search_adapter_cls(
                        source_id=f"search:{dim.name}",
                        config={
                            "queries": dim.search.keywords,
                            "engine": dim.search.engine,
                            "concurrent": dim.search.concurrent,
                            "max_results": dim.filter.max_results * 2,
                            "max_age_days": dim.filter.max_age_days,
                        },
                        metadata={"dimension": dim.name},
                    )
                    try:
                        entities.extend(await adapter.fetch())
                    except Exception as e:
                        logger.warning("Dimension '%s' search failed: %s", dim.name, e)

            # Configured sources within dimension
            if dim.sources:
                entities.extend(await self._fetch_sources(dim.sources))

            return dim.name, entities

        tasks = [_fetch_one_dim(d) for d in dimensions]
        dim_results = await asyncio.gather(*tasks)
        for dim_name, entities in dim_results:
            result[dim_name] = entities

        return result

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
