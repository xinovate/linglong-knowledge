"""BriefHistory — per-dimension dedup for morning briefs.

Stores each day's output sections as JSON, loads past N days per dimension
to inject as "already reported" context for the next run.
"""

import json
import logging
from datetime import date, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

_DEDUP_WINDOWS: dict[str, int] = {
    "关键人物": 14,
    "公司动态": 7,
    "政策动态": 14,
    "应用落地": 7,
}

_DIMENSION_KEYS: dict[str, str] = {
    "关键人物": "关键人物",
    "公司动态": "公司动态",
    "政策动态": "政策动态",
    "应用落地": "应用落地",
}


def parse_sections(output: str) -> dict[str, str]:
    """Parse LLM output into per-dimension sections by ## headers."""
    sections: dict[str, str] = {}
    current_dim: str | None = None
    current_lines: list[str] = []

    for line in output.split("\n"):
        if line.startswith("## "):
            if current_dim and current_lines:
                sections[current_dim] = "\n".join(current_lines).strip()
            dim = line[3:].strip()
            # Normalize: strip emoji prefix for matching
            for key in _DEDUP_WINDOWS:
                if key in dim:
                    current_dim = key
                    break
            else:
                current_dim = dim
            current_lines = []
        elif line.startswith("━━"):
            if current_dim and current_lines:
                sections[current_dim] = "\n".join(current_lines).strip()
            break
        elif current_dim:
            current_lines.append(line)

    if current_dim and current_lines:
        sections[current_dim] = "\n".join(current_lines).strip()

    return sections


class BriefHistory:
    """Per-dimension brief history for deduplication."""

    def __init__(self, history_dir: Path) -> None:
        self.history_dir = history_dir
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, str]:
        """Load recent history per dimension.

        Returns {dimension: combined_text_with_dates} for dimensions that have history.
        """
        today = date.today()
        result: dict[str, str] = {}

        for dim, window in _DEDUP_WINDOWS.items():
            sections: list[str] = []
            for i in range(1, window + 1):
                d = today - timedelta(days=i)
                path = self.history_dir / f"{d.isoformat()}.json"
                if not path.exists():
                    continue
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if dim in data and data[dim]:
                        sections.append(f"【{d.isoformat()}】\n{data[dim]}")
                except Exception as e:
                    logger.warning("Failed to read history %s: %s", path, e)

            if sections:
                result[dim] = "\n\n".join(sections)

        return result

    def format_for_prompt(self) -> str:
        """Format history as prompt injection text."""
        history = self.load()
        if not history:
            return ""

        lines = ["## 近期已播报内容（请勿重复报道相同事件）", ""]
        for dim, text in history.items():
            window = _DEDUP_WINDOWS.get(dim, 7)
            lines.append(f"### {dim}（近 {window} 天）")
            lines.append(text)
            lines.append("")

        return "\n".join(lines)

    def save(self, date_str: str, sections: dict[str, str]) -> None:
        """Save per-dimension sections for a given date."""
        path = self.history_dir / f"{date_str}.json"
        path.write_text(
            json.dumps(sections, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Brief history saved: %s (%d dimensions)", path, len(sections))

    def cleanup(self, max_days: int = 16) -> None:
        """Remove history files older than max_days."""
        cutoff = (date.today() - timedelta(days=max_days)).isoformat()
        removed = 0
        for f in self.history_dir.glob("*.json"):
            if f.stem < cutoff:
                f.unlink()
                removed += 1
        if removed:
            logger.info("Cleaned up %d old history files", removed)
