"""Truth verification engine for multi-source validation."""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from linglong.core.models import Entity


@dataclass
class VerificationResult:
    """Result of truth verification for an entity."""

    entity_id: str
    passed: bool
    score: float
    checks: dict[str, bool] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)


@dataclass
class VerificationConfig:
    """Configuration for truth verification."""

    cross_reference_min: int = 1
    max_age_days: int = 7
    fallback_max_age_days: int = 14
    authority_weights: dict[str, float] = field(
        default_factory=lambda: {"high": 1.0, "medium": 0.7, "low": 0.4}
    )
    numeric_ranges: dict[str, tuple[float, float]] = field(default_factory=dict)
    custom_validators: list[Callable[[Entity], tuple[bool, str]]] = field(default_factory=list)

    # Layer weights (must sum to 1.0)
    layer_weights: dict[str, float] = field(
        default_factory=lambda: {
            "cross_reference": 0.25,
            "numeric_sanity": 0.2,
            "time_validity": 0.2,
            "source_authority": 0.2,
            "common_sense": 0.15,
        }
    )
    pass_threshold: float = 0.6
    signature_length: int = 100
    max_star_count: int = 500_000


class TruthVerificationEngine:
    """5-layer truth verification engine.

    Layers:
    1. Cross-reference: same event in >= N sources
    2. Numeric reasonableness: values within historical ranges
    3. Time validity: content within max_age_days
    4. Source authority: weighted by source trustworthiness
    5. Common sense: plausibility heuristics
    """

    def __init__(self, config: VerificationConfig | None = None) -> None:
        self.config = config or VerificationConfig()

    def verify_batch(self, entities: list[Entity]) -> list[VerificationResult]:
        """Verify a batch of entities, enabling cross-reference checks."""
        signature_index: dict[str, list[str]] = {}
        for entity in entities:
            sig = self._content_signature(entity)
            signature_index.setdefault(sig, []).append(entity.id or "")

        return [self._verify_single(entity, signature_index) for entity in entities]

    def _verify_single(
        self, entity: Entity, signature_index: dict[str, list[str]]
    ) -> VerificationResult:
        checks: dict[str, bool] = {}
        reasons: list[str] = []
        score = 0.0

        w = self.config.layer_weights

        # Layer 1: Cross-reference
        sig = self._content_signature(entity)
        ref_count = len(signature_index.get(sig, []))
        cross_ref_pass = ref_count >= self.config.cross_reference_min
        checks["cross_reference"] = cross_ref_pass
        if cross_ref_pass:
            score += w.get("cross_reference", 0.25)
        else:
            reasons.append(f"Only {ref_count} source(s) for this event")

        # Layer 2: Numeric reasonableness
        numeric_pass, numeric_reason = self._check_numeric_sanity(entity)
        checks["numeric_sanity"] = numeric_pass
        if numeric_pass:
            score += w.get("numeric_sanity", 0.2)
        elif numeric_reason:
            reasons.append(numeric_reason)

        # Layer 3: Time validity
        time_pass, time_reason = self._check_time_validity(entity)
        checks["time_validity"] = time_pass
        if time_pass:
            score += w.get("time_validity", 0.2)
        elif time_reason:
            reasons.append(time_reason)

        # Layer 4: Source authority
        authority_score = self._compute_authority_score(entity)
        checks["source_authority"] = authority_score >= 0.5
        score += authority_score * w.get("source_authority", 0.2)

        # Layer 5: Common sense
        common_pass, common_reason = self._check_common_sense(entity)
        checks["common_sense"] = common_pass
        if common_pass:
            score += w.get("common_sense", 0.15)
        elif common_reason:
            reasons.append(common_reason)

        # Custom validators
        for validator in self.config.custom_validators:
            ok, reason = validator(entity)
            if not ok and reason:
                reasons.append(reason)

        passed = score >= self.config.pass_threshold
        return VerificationResult(
            entity_id=entity.id or "",
            passed=passed,
            score=score,
            checks=checks,
            reasons=reasons,
        )

    def _content_signature(self, entity: Entity) -> str:
        content = entity.content.lower()
        content = re.sub(r"https?://\S+", "", content)
        content = re.sub(r"\d+", "", content)
        content = re.sub(r"[^\w\s]", "", content)
        return content[: self.config.signature_length].strip()

    def _check_numeric_sanity(self, entity: Entity) -> tuple[bool, str]:
        for field_name, (min_val, max_val) in self.config.numeric_ranges.items():
            pattern = rf"{field_name}\s*[:$]?\s*([0-9,.]+[KMBT]?)"
            matches = re.findall(pattern, entity.content, re.IGNORECASE)
            for match in matches:
                try:
                    val = self._parse_number(match)
                    if not (min_val <= val <= max_val):
                        return False, f"{field_name} value {val} outside range"
                except ValueError:
                    continue
        return True, ""

    def _parse_number(self, s: str) -> float:
        s = s.replace(",", "").upper()
        multipliers = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}
        for suffix, mult in multipliers.items():
            if s.endswith(suffix):
                return float(s[:-1]) * mult
        return float(s)

    def _check_time_validity(self, entity: Entity) -> tuple[bool, str]:
        entity_date = entity.metadata.get("published") or entity.metadata.get("date")
        if not entity_date:
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", entity.content)
            if date_match:
                try:
                    entity_date = datetime.strptime(date_match.group(1), "%Y-%m-%d")
                except ValueError:
                    pass

        if isinstance(entity_date, str):
            try:
                entity_date = datetime.fromisoformat(entity_date.replace("Z", "+00:00"))
            except ValueError:
                return True, ""

        if isinstance(entity_date, datetime):
            age = datetime.now(entity_date.tzinfo or None) - entity_date
            if age.days <= self.config.max_age_days:
                return True, ""
            if age.days <= self.config.fallback_max_age_days:
                return True, ""
            return False, f"Content is {age.days} days old"

        return True, ""

    def _compute_authority_score(self, entity: Entity) -> float:
        if not entity.sources:
            return 0.0
        scores = []
        for source in entity.sources:
            authority = source.metadata.get("authority", "medium")
            weight = self.config.authority_weights.get(authority, 0.5)
            scores.append(weight)
        return max(scores) if scores else 0.0

    def _check_common_sense(self, entity: Entity) -> tuple[bool, str]:
        content = entity.content.lower()
        star_match = re.search(r"(\d+(?:\.\d+)?[KMB]?)\s*stars?", content)
        if star_match:
            stars = self._parse_number(star_match.group(1))
            if stars > self.config.max_star_count:
                return False, f"Suspicious star count: {star_match.group(1)}"
        return True, ""
