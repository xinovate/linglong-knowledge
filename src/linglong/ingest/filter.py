"""Dimension-based filtering for ingest results."""

import logging
from datetime import UTC, datetime
from typing import Any

from linglong.core.models import Entity
from linglong.ingest.package import DimensionConfig, FilterConfig

logger = logging.getLogger(__name__)


def filter_dimension(
    entities: list[Entity],
    filt: FilterConfig,
    dimension_name: str,
) -> list[Entity]:
    """Apply filter rules to entities within a single dimension.

    - max_results: keep at most N entities
    - max_age_days: skip entities older than N days (based on created_at)
    """
    now = datetime.now(UTC)
    cutoff = now.timestamp() - filt.max_age_days * 86400

    filtered: list[Entity] = []
    for entity in entities:
        if entity.created_at:
            try:
                if isinstance(entity.created_at, datetime):
                    ts = entity.created_at.timestamp()
                else:
                    ts = datetime.fromisoformat(entity.created_at).timestamp()
                if ts < cutoff:
                    continue
            except (ValueError, TypeError):
                pass
        filtered.append(entity)

    if len(filtered) > filt.max_results:
        filtered = filtered[: filt.max_results]

    logger.info(
        "Dimension '%s': %d → %d (max_results=%d, max_age_days=%d)",
        dimension_name,
        len(entities),
        len(filtered),
        filt.max_results,
        filt.max_age_days,
    )
    return filtered


def filter_by_dimensions(
    dimension_entities: dict[str, list[Entity]],
    dimensions: list[DimensionConfig],
) -> dict[str, list[Entity]]:
    """Apply per-dimension filters to grouped entities.

    Args:
        dimension_entities: dimension name → list of entities
        dimensions: dimension configs with filter rules

    Returns:
        Filtered dimension name → list of entities
    """
    dim_map = {d.name: d for d in dimensions}
    result: dict[str, list[Entity]] = {}

    for dim_name, entities in dimension_entities.items():
        dim_cfg = dim_map.get(dim_name)
        if dim_cfg:
            result[dim_name] = filter_dimension(entities, dim_cfg.filter, dim_name)
        else:
            # No config → pass through
            result[dim_name] = entities

    return result
