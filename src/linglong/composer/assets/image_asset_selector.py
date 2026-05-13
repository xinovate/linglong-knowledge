"""Image asset selector — parse URL files, random selection, dedup.

Supports two URL file formats:

Inline format:
    URL # tag1,tag2 [background|article_image|both]

Multi-line format (tag on separate line):
    # 风光
    https://tuchong.com/xxx/yyy/
    https://tuchong.com/zzz/www/
    # 城市
    https://tuchong.com/aaa/bbb/

Selects images by usage, tracks recently used URLs to avoid repeats.
"""

import json
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ImageAssetSelector:
    """Select images from URL list files by usage type with dedup."""

    def __init__(self, config: dict[str, Any]):
        self.sources: list[dict[str, Any]] = config.get("sources", [])
        self.dedup_days: int = config.get("selection", {}).get("dedup_days", 30)
        self._state_path = Path.home() / "linglong" / "state" / "image_dedup.json"
        self._state: dict[str, list[str]] = self._load_state()

    def select(self, usage: str, count: int = 1) -> list[str]:
        """Select image URLs matching the given usage type.

        Args:
            usage: "background" or "article_image"
            count: Number of images to select

        Returns:
            List of selected URL strings (may be fewer than count if pool exhausted).
        """
        all_urls = self._collect_urls(usage)
        if not all_urls:
            logger.warning("No URLs available for usage: %s", usage)
            return []

        # Dedup: exclude recently used
        recent = self._recent_urls()
        available = [u for u in all_urls if u not in recent]
        if not available:
            logger.info("Dedup pool exhausted for %s, resetting", usage)
            available = all_urls

        selected = random.sample(available, min(count, len(available)))
        logger.info("Selected %d image(s) for %s: %s", len(selected), usage, selected)
        return selected

    def record_used(self, urls: list[str]) -> None:
        """Record URLs as recently used for dedup."""
        today = datetime.now().strftime("%Y-%m-%d")
        for url in urls:
            if url not in self._state:
                self._state[url] = []
            if today not in self._state[url]:
                self._state[url].append(today)
        self._save_state()

    def _collect_urls(self, usage: str) -> list[str]:
        """Collect URLs from all sources matching the given usage."""
        urls: list[str] = []
        for source in self.sources:
            file_path = Path(source["url_file"]).expanduser()
            if not file_path.exists():
                logger.warning("URL file not found: %s", file_path)
                continue
            default_usage = source.get("default_usage", "both")
            urls.extend(self._parse_url_file(file_path, usage, default_usage))
        return urls

    def _parse_url_file(
        self, file_path: Path, target_usage: str, default_usage: str
    ) -> list[str]:
        """Parse a URL file, filtering by usage.

        Supports two formats:

        Inline:
            URL # tag1,tag2 [background|article_image|both]

        Multi-line (tag on separate line):
            # 风光
            https://tuchong.com/xxx/yyy/
            # 城市 [background]
            https://tuchong.com/aaa/bbb/
        """
        urls: list[str] = []
        current_tag: str = ""
        current_usage: str = default_usage
        try:
            for line in file_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue

                # Multi-line format: tag line starts with # (but not a URL with #anchor)
                if line.startswith("#") and not line.startswith("# http"):
                    tag_line = line.lstrip("#").strip()
                    current_tag, current_usage = self._parse_tag_line(
                        tag_line, default_usage
                    )
                    continue

                # URL line
                url = line
                usage = default_usage
                tags: list[str] = []

                # Check for inline format: URL # tags [usage]
                if "#" in url:
                    parts = url.split("#", 1)
                    url = parts[0].strip()
                    if len(parts) > 1:
                        comment = parts[1].strip()
                        # Check for usage marker at end
                        if "[" in comment and comment.endswith("]"):
                            bracket_start = comment.rfind("[")
                            usage_tag = comment[bracket_start + 1 : -1].strip().lower()
                            if usage_tag in ("background", "article_image", "both"):
                                usage = usage_tag
                            comment = comment[:bracket_start].strip()
                        if comment:
                            tags = [t.strip() for t in comment.split(",") if t.strip()]

                if not url.startswith("http"):
                    continue

                # Multi-line format: inherit tag and usage from previous tag line
                if not tags and current_tag:
                    tags = [current_tag]
                    usage = current_usage

                # Filter by target usage
                if usage == "both" or usage == target_usage:
                    urls.append(url)
        except Exception as e:
            logger.error("Failed to parse URL file %s: %s", file_path, e)
        return urls

    def _parse_tag_line(self, tag_line: str, default_usage: str) -> tuple[str, str]:
        """Parse a tag line like '风光' or '风光 [background]'.

        Returns (tag, usage).
        """
        usage = default_usage
        tag = tag_line
        if "[" in tag_line and tag_line.endswith("]"):
            bracket_start = tag_line.rfind("[")
            usage_tag = tag_line[bracket_start + 1 : -1].strip().lower()
            if usage_tag in ("background", "article_image", "both"):
                usage = usage_tag
            tag = tag_line[:bracket_start].strip()
        return tag, usage

    def _recent_urls(self) -> set[str]:
        """Get set of URLs used within the dedup window."""
        cutoff = (datetime.now() - timedelta(days=self.dedup_days)).strftime("%Y-%m-%d")
        recent: set[str] = set()
        for url, dates in self._state.items():
            if any(d >= cutoff for d in dates):
                recent.add(url)
        return recent

    def _load_state(self) -> dict[str, list[str]]:
        """Load dedup state from disk."""
        if self._state_path.exists():
            try:
                return json.loads(self._state_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed to load dedup state: %s", e)
        return {}

    def _save_state(self) -> None:
        """Save dedup state to disk."""
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._state_path.write_text(
                json.dumps(self._state, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.error("Failed to save dedup state: %s", e)
