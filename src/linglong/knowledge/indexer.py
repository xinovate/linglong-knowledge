"""Knowledge index generator — scans wiki/ and generates index files."""

import json
import logging
from datetime import datetime
from pathlib import Path

from linglong.core.models import EntityFacet

logger = logging.getLogger(__name__)

_FACET_LABELS = {
    EntityFacet.SOURCE: "原始资料",
    EntityFacet.ENTITY: "专有名词",
    EntityFacet.CONCEPT: "抽象知识",
    EntityFacet.SYNTHESIS: "跨源综合",
    EntityFacet.EXPERIENCE: "实战经验",
    EntityFacet.METHODOLOGY: "方法论",
    EntityFacet.PERSONAL: "个人数据",
}


class IndexGenerator:
    """Generate index.md and per-facet index files from wiki directory."""

    def __init__(self, wiki_path: Path):
        self.wiki_path = wiki_path

    def generate_all(self) -> dict[str, int]:
        """Generate all index files. Returns {filename: entry_count}."""
        stats = {}
        per_facet: dict[EntityFacet, list[dict]] = {}

        for facet in EntityFacet:
            facet_dir = self.wiki_path / facet.value
            entries = self._scan_facet_dir(facet_dir)
            per_facet[facet] = entries
            count = self._write_facet_index(facet, entries)
            index_name = f"index-{facet.value}.md"
            stats[index_name] = count

        # 主索引
        total = self._write_main_index(per_facet)
        stats["index.md"] = total
        return stats

    def generate_facet(self, facet: EntityFacet) -> int:
        """Generate index for a single facet. Returns entry count."""
        facet_dir = self.wiki_path / facet.value
        entries = self._scan_facet_dir(facet_dir)
        return self._write_facet_index(facet, entries)

    def _scan_facet_dir(self, facet_dir: Path) -> list[dict]:
        """Scan a facet directory and extract entry metadata."""
        if not facet_dir.exists():
            return []

        entries = []
        for md_file in sorted(facet_dir.glob("*.md")):
            meta = self._parse_frontmatter(md_file)
            entries.append({
                "id": meta.get("id", md_file.stem),
                "title": self._extract_title(md_file),
                "facet": meta.get("type", "concept"),
                "status": meta.get("status", "raw"),
                "created_by": meta.get("created_by", "unknown"),
                "updated_at": meta.get("updated_at", ""),
                "path": str(md_file.relative_to(self.wiki_path)),
            })

        return entries

    def _parse_frontmatter(self, path: Path) -> dict:
        """Parse JSON frontmatter from markdown file."""
        content = path.read_text(encoding="utf-8")
        if not content.startswith("---"):
            return {}
        try:
            end = content.index("---", 3)
            fm_text = content[3:end].strip()
            return json.loads(fm_text)
        except (ValueError, json.JSONDecodeError):
            return {}

    def _extract_title(self, path: Path) -> str:
        """Extract first # heading or use filename."""
        content = path.read_text(encoding="utf-8")
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
        return path.stem

    def _write_facet_index(self, facet: EntityFacet, entries: list[dict]) -> int:
        """Write per-facet index file."""
        label = _FACET_LABELS.get(facet, facet.value)
        lines = [
            f"# {label}索引",
            "",
            f"> 分类：{facet.value} | 共 {len(entries)} 条",
            "",
        ]

        for e in entries:
            lines.append(
                f"- [[{e['title']}]] ({e['status']}) — "
                f"{e['updated_at'][:10] if e['updated_at'] else 'N/A'}"
            )

        if not entries:
            lines.append("（暂无条目）")

        lines.append("")
        output_path = self.wiki_path / f"index-{facet.value}.md"
        output_path.write_text("\n".join(lines), encoding="utf-8")
        return len(entries)

    def _write_main_index(self, per_facet: dict[EntityFacet, list[dict]]) -> int:
        """Write main index.md."""
        total = sum(len(entries) for entries in per_facet.values())
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M")

        lines = [
            "# 知识库索引",
            "",
            f"> 最后更新：{now} | 共 {total} 条",
            "",
        ]

        for facet in EntityFacet:
            label = _FACET_LABELS.get(facet, facet.value)
            count = len(per_facet.get(facet, []))
            lines.append(f"## [{label}](index-{facet.value}.md) ({count})")
            lines.append("")
            for e in per_facet.get(facet, [])[:10]:
                lines.append(
                    f"- [[{e['title']}]] ({e['status']}) — "
                    f"{e['updated_at'][:10] if e['updated_at'] else 'N/A'}"
                )
            if count > 10:
                lines.append(
                    f"- ... 共 {count} 条，查看 [完整索引](index-{facet.value}.md)"
                )
            lines.append("")

        output_path = self.wiki_path / "index.md"
        output_path.write_text("\n".join(lines), encoding="utf-8")
        return total
