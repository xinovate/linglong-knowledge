"""Composer state management."""

import hashlib
import json
import logging
from pathlib import Path

from linglong.composer.ingest_adapter import MemoryFragment
from linglong.core.config import get_config

logger = logging.getLogger(__name__)


def _default_state_file() -> Path:
    return Path.home() / "linglong" / "state" / "composer_state.json"


class ComposerState:
    """Manage processed fragment state."""

    def __init__(self, state_file: Path | None = None):
        self.state_file = state_file or _default_state_file()
        self._hashes: set[str] = set()
        self._load()

    def _load(self):
        if self.state_file.exists():
            try:
                with open(self.state_file, encoding="utf-8") as f:
                    data = json.load(f)
                self._hashes = set(data.get("processed_hashes", []))
                logger.info(f"已加载 {len(self._hashes)} 条处理记录")
            except Exception as e:
                logger.warning(f"状态文件加载失败: {e}")
                self._hashes = set()
        else:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            self._hashes = set()

    def _save(self):
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(
                    {"processed_hashes": sorted(self._hashes)},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception as e:
            logger.warning(f"状态文件保存失败: {e}")

    @staticmethod
    def _hash_fragment(frag: MemoryFragment) -> str:
        """Compute fragment content hash."""
        raw = f"{frag.source}:{frag.content}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    def is_processed(self, frag: MemoryFragment) -> bool:
        return self._hash_fragment(frag) in self._hashes

    def filter_new(self, fragments: list[MemoryFragment]) -> list[MemoryFragment]:
        """Filter out already-processed fragments."""
        new_frags = []
        for frag in fragments:
            if self.is_processed(frag):
                logger.debug(f"跳过已处理片段: {frag.source}")
            else:
                new_frags.append(frag)
        skipped = len(fragments) - len(new_frags)
        if skipped:
            logger.info(f"跳过 {skipped} 条已处理片段")
        return new_frags

    def mark_processed(self, fragments: list[MemoryFragment]):
        """Mark fragments as processed."""
        for frag in fragments:
            self._hashes.add(self._hash_fragment(frag))
        self._save()
        logger.info(f"标记 {len(fragments)} 条片段为已处理")
