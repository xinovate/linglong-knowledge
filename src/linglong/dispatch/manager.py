"""Dispatch manager - routes drafts to appropriate publishers."""

import logging
from typing import Any

from linglong.core.config import get_config
from linglong.dispatch.publishers.base import Publisher, PublishResult
from linglong.dispatch.publishers.hexo import HexoPublisher
from linglong.dispatch.publishers.local import LocalPublisher

logger = logging.getLogger(__name__)

_PUBLISHER_REGISTRY: dict[str, type[Publisher]] = {
    "hexo": HexoPublisher,
    "local": LocalPublisher,
}


class DispatchManager:
    """Manages publisher discovery, routing, and execution."""

    def __init__(self) -> None:
        self.config = get_config().dispatch
        self._publishers: dict[str, Publisher] = {}
        self._init_publishers()

    def _init_publishers(self) -> None:
        """Initialize enabled publishers from config."""
        for pub_conf in self.config.publishers:
            if not pub_conf.get("enabled", True):
                continue
            pub_type = pub_conf.get("type")
            pub_name = pub_conf.get("name", pub_type)
            cls = _PUBLISHER_REGISTRY.get(pub_type)
            if cls is None:
                logger.warning("Unknown publisher type: %s", pub_type)
                continue
            self._publishers[pub_name] = cls(pub_conf.get("config", {}))
            logger.info("Initialized publisher: %s", pub_name)

    def publish(self, payload: dict[str, Any], publisher_name: str | None = None) -> PublishResult:
        """Publish a dispatch-ready payload.

        Args:
            payload: dict with ``content``, ``metadata``, ``draft_id``
            publisher_name: Target publisher; defaults to ``DispatchConfig.default_publisher``

        Returns:
            PublishResult: outcome of the publish operation
        """
        name = publisher_name or self.config.default_publisher
        publisher = self._publishers.get(name)
        if publisher is None:
            return PublishResult(
                success=False,
                error=f"Publisher '{name}' not found or not enabled",
            )

        content = payload.get("content", "")
        metadata = payload.get("metadata", {})
        return publisher.publish(content, metadata)

    def health_check(self) -> dict[str, bool]:
        """Run health checks on all initialized publishers."""
        return {
            name: pub.health_check()
            for name, pub in self._publishers.items()
        }

    def list_publishers(self) -> list[str]:
        """Return names of initialized publishers."""
        return list(self._publishers.keys())
