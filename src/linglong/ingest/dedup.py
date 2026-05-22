"""Cross-day dedup for ingest results."""

import logging
from typing import Any

from linglong.core.models import Entity
from linglong.ingest.history import IngestHistory

logger = logging.getLogger(__name__)


class DedupResult:
    """Result of dedup check for a single entity."""

    def __init__(
        self,
        entity: Entity,
        is_duplicate: bool,
        reason: str = "",
        similarity: float = 0.0,
    ) -> None:
        self.entity = entity
        self.is_duplicate = is_duplicate
        self.reason = reason
        self.similarity = similarity


def dedup_entities(
    entities: list[Entity],
    history: IngestHistory,
    lookback_days: int = 7,
    title_threshold: float = 0.5,
    dimension: str = "",
) -> list[Entity]:
    """Deduplicate entities against ingest history.

    Strategy:
    1. Exact match: content_hash match → skip (old duplicate)
    2. Fuzzy match: title keyword overlap ≥ threshold → keep as '进展' or skip

    Returns non-duplicate entities.
    """
    results: list[Entity] = []

    for entity in entities:
        check = _check_duplicate(entity, history, lookback_days, title_threshold, dimension)
        if check.is_duplicate:
            logger.info(
                "Dedup skip: '%s' — %s (similarity=%.2f)",
                _entity_title(entity)[:50],
                check.reason,
                check.similarity,
            )
        else:
            results.append(entity)

    logger.info(
        "Dedup: %d → %d (lookback=%d days)",
        len(entities),
        len(results),
        lookback_days,
    )
    return results


def _check_duplicate(
    entity: Entity,
    history: IngestHistory,
    lookback_days: int,
    title_threshold: float,
    dimension: str,
) -> DedupResult:
    """Check if a single entity is a duplicate of something in history."""
    # 1. Exact content hash match
    chash = history.content_hash(entity)
    exact_matches = history.find_by_hash(chash)
    if exact_matches:
        return DedupResult(entity, True, "exact_hash_match", 1.0)

    # 2. Title similarity match
    title = _entity_title(entity)
    if not title:
        return DedupResult(entity, False)

    similar = history.find_by_title_similarity(title, days=lookback_days, threshold=title_threshold)
    if similar:
        best = similar[0]
        sim = best.get("_similarity", 0)
        # High similarity → likely same event
        if sim >= 0.7:
            return DedupResult(entity, True, f"title_similar({sim:.2f}): '{best.get('title', '')[:30]}'", sim)
        # Medium similarity → could be follow-up, keep it
        if sim >= title_threshold:
            return DedupResult(entity, False, f"title_partial_match({sim:.2f})", sim)

    return DedupResult(entity, False)


def _entity_title(entity: Entity) -> str:
    """Extract title from entity content."""
    for line in entity.content.split("\n"):
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return entity.content[:80].strip()
