"""Review engine for automatic quality control."""

import re
from collections.abc import Callable
from enum import Enum

from linglong.core.config import get_config
from linglong.core.models import Entity, EntityStatus, EntityFacet


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

    def __init__(self):
        self.rules: list[Rule] = []
        self._config = get_config().knowledge
        self._setup_default_rules()

    def _setup_default_rules(self) -> None:
        """Setup default review rules."""
        cfg = self._config
        trusted = set(cfg.review_trusted_sources)

        # 规则 1：高置信度 + 可信来源 → 自动确认
        self.rules.append(
            Rule(
                name="high_confidence_trusted",
                condition=lambda e: (
                    float(e.confidence) > cfg.review_high_confidence_threshold
                    and any(s.name in trusted for s in e.sources)
                ),
                action=Action.AUTO_CONFIRM,
                priority=100,
            )
        )

        # 规则 2：低置信度 → 标记待审核
        self.rules.append(
            Rule(
                name="low_confidence",
                condition=lambda e: float(e.confidence) < cfg.review_low_confidence_threshold,
                action=Action.FLAG_FOR_REVIEW,
                priority=90,
            )
        )

        # 规则 3：敏感内容 → 需要人工确认
        self.rules.append(
            Rule(
                name="sensitive_content",
                condition=self._contains_sensitive_info,
                action=Action.REQUIRE_HUMAN_CONFIRM,
                priority=95,
            )
        )

        # 规则 4：内容过短 → 标记待审核
        self.rules.append(
            Rule(
                name="too_short",
                condition=lambda e: len(e.content) < cfg.review_min_content_length,
                action=Action.FLAG_FOR_REVIEW,
                priority=50,
            )
        )

        # 规则 5：personal 分面 → 需人工确认（隐私相关）
        self.rules.append(
            Rule(
                name="personal_requires_review",
                condition=lambda e: (
                    hasattr(e, 'facet') and e.facet == EntityFacet.PERSONAL
                ),
                action=Action.REQUIRE_HUMAN_CONFIRM,
                priority=80,
            )
        )

        # 规则 6：source 分面高置信度 → 自动确认
        self.rules.append(
            Rule(
                name="source_auto_confirm",
                condition=lambda e: (
                    hasattr(e, 'facet')
                    and e.facet == EntityFacet.REFERENCE
                    and float(e.confidence) >= 0.7
                ),
                action=Action.AUTO_CONFIRM,
                priority=85,
            )
        )

        # 按优先级排序（高优先）
        self.rules.sort(key=lambda r: r.priority, reverse=True)

    def review(self, entity: Entity) -> Entity:
        """Review an entity and update its status."""
        for rule in self.rules:
            action = rule.evaluate(entity)
            if action:
                entity = self._apply_action(entity, action, rule.name)
                break
        else:
            # 无规则匹配，保持待审核
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
            # 添加元数据标记需要人工确认
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

        # 检查敏感关键词
        for category in self._config.review_sensitive_categories:
            if category in content_lower:
                return True

        # 检查可能的密码/密钥
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
