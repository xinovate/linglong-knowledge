"""Review engine for automatic quality control."""

import re
from collections.abc import Callable
from enum import Enum

from linglong.core.models import Entity, EntityStatus


class Action(Enum):
    """Review actions."""

    AUTO_CONFIRM = "auto_confirm"
    FLAG_FOR_REVIEW = "flag_for_review"
    REQUIRE_HUMAN_CONFIRM = "require_human_confirm"
    MERGE = "merge"
    REJECT = "reject"


class Rule:
    """Review rule."""

    def __init__(
        self,
        name: str,
        condition: Callable[[Entity], bool],
        action: Action,
        priority: int = 0,
    ):
        self.name = name
        self.condition = condition
        self.action = action
        self.priority = priority

    def evaluate(self, entity: Entity) -> Action | None:
        """Evaluate rule against entity."""
        try:
            if self.condition(entity):
                return self.action
        except Exception:
            pass
        return None


class ReviewEngine:
    """Automatic review engine with configurable rules."""

    # Trusted sources that can auto-confirm
    TRUSTED_SOURCES = {"openclaw", "claude-code", "codex"}

    # Sensitive categories requiring human confirmation
    SENSITIVE_CATEGORIES = {"personal", "financial", "health", "password", "secret"}

    def __init__(self):
        self.rules: list[Rule] = []
        self._setup_default_rules()

    def _setup_default_rules(self) -> None:
        """Setup default review rules."""

        # Rule 1: High confidence + trusted source = auto confirm
        self.rules.append(
            Rule(
                name="high_confidence_trusted",
                condition=lambda e: (
                    float(e.confidence) > 0.9
                    and any(s.name in self.TRUSTED_SOURCES for s in e.sources)
                ),
                action=Action.AUTO_CONFIRM,
                priority=100,
            )
        )

        # Rule 2: Low confidence = flag for review
        self.rules.append(
            Rule(
                name="low_confidence",
                condition=lambda e: float(e.confidence) < 0.6,
                action=Action.FLAG_FOR_REVIEW,
                priority=90,
            )
        )

        # Rule 3: Sensitive content = require human confirm
        self.rules.append(
            Rule(
                name="sensitive_content",
                condition=self._contains_sensitive_info,
                action=Action.REQUIRE_HUMAN_CONFIRM,
                priority=95,
            )
        )

        # Rule 4: Very short content = flag
        self.rules.append(
            Rule(
                name="too_short",
                condition=lambda e: len(e.content) < 50,
                action=Action.FLAG_FOR_REVIEW,
                priority=50,
            )
        )

        # Sort by priority (highest first)
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def review(self, entity: Entity) -> Entity:
        """Review an entity and update its status."""
        for rule in self.rules:
            action = rule.evaluate(entity)
            if action:
                entity = self._apply_action(entity, action, rule.name)
                break
        else:
            # No rule matched, keep as pending
            entity.status = EntityStatus.PENDING_REVIEW

        return entity

    def _apply_action(self, entity: Entity, action: Action, rule_name: str) -> Entity:
        """Apply review action to entity."""
        if action == Action.AUTO_CONFIRM:
            entity.status = EntityStatus.AUTO_CONFIRMED
        elif action == Action.FLAG_FOR_REVIEW:
            entity.status = EntityStatus.PENDING_REVIEW
        elif action == Action.REQUIRE_HUMAN_CONFIRM:
            entity.status = EntityStatus.PENDING_REVIEW
            # Add metadata indicating human confirmation required
            entity.sources.append(
                type(
                    "Source",
                    (),
                    {
                        "type": "review",
                        "name": f"requires_human_confirm:{rule_name}",
                    },
                )()
            )
        elif action == Action.REJECT:
            entity.status = EntityStatus.REJECTED

        return entity

    def _contains_sensitive_info(self, entity: Entity) -> bool:
        """Check if entity contains sensitive information."""
        content_lower = entity.content.lower()

        # Check for sensitive keywords
        for category in self.SENSITIVE_CATEGORIES:
            if category in content_lower:
                return True

        # Check for potential passwords/secrets
        if re.search(r"password\s*[:=]\s*\S+", content_lower):
            return True
        if re.search(r"api[_-]?key\s*[:=]\s*\S+", content_lower):
            return True
        if re.search(r"secret\s*[:=]\s*\S+", content_lower):
            return True

        return False

    def add_rule(self, rule: Rule) -> None:
        """Add a custom rule."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
