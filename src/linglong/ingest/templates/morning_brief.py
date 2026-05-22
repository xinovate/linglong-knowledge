"""Morning brief formatting template — table format matching OpenClaw style."""

from __future__ import annotations

from datetime import date
from typing import Any

from linglong.core.models import Entity

_DIMENSION_EMOJI: dict[str, str] = {
    "研究员观点": "🔬",
    "公司决策": "🏢",
    "资本决策": "💰",
    "国家政策": "📋",
    "开源趋势": "⭐",
    "应用落地": "🚀",
    "AI 动态": "🤖",
}

# Dimension → table column headers
_DIMENSION_COLUMNS: dict[str, list[str]] = {
    "研究员观点": ["观点/动态", "来源人", "解读"],
    "公司决策": ["事件", "公司", "日期", "解读"],
    "资本决策": ["投资事件", "投资方", "金额", "解读"],
    "国家政策": ["政策名称", "发布部门", "解读"],
    "开源趋势": ["项目名", "分类", "Stars", "日期", "解读"],
    "应用落地": ["产品/功能", "公司", "日期", "解读"],
}

_DEFAULT_COLUMNS = ["事件", "解读"]


def format_morning_brief(
    dimension_entities: dict[str, list[Entity]],
    title: str = "AI 早报",
    interpretations: dict[str, list[dict[str, str]]] | None = None,
    top5: list[dict[str, Any]] | None = None,
) -> str:
    """Format entities grouped by dimension into a morning brief.

    Args:
        dimension_entities: dimension name → list of entities
        title: Brief title
        interpretations: dimension name → list of {"title", "interpretation"}
        top5: Top 5 analysis from LLM

    Returns:
        Markdown string with table format
    """
    today = date.today().isoformat()
    lines: list[str] = [
        f"# {title} · {today}",
        "",
    ]

    total = sum(len(ents) for ents in dimension_entities.values())
    if total == 0:
        lines.append("*今日暂无新消息。*")
        return "\n".join(lines)

    # Summary line
    parts = [f"{name} {len(ents)} 条" for name, ents in dimension_entities.items() if ents]
    lines.append(f"> {', '.join(parts)}")
    lines.append("")

    # Per-dimension tables
    for dim_name, entities in dimension_entities.items():
        if not entities:
            continue
        emoji = _DIMENSION_EMOJI.get(dim_name, "📌")
        lines.append(f"## {emoji} {dim_name}")
        lines.append("")

        cols = _DIMENSION_COLUMNS.get(dim_name, _DEFAULT_COLUMNS)
        col_count = len(cols)

        # Table header
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("| " + " | ".join(["---"] * col_count) + " ")

        dim_interps = (interpretations or {}).get(dim_name, [])
        for i, entity in enumerate(entities):
            title_text = _extract_title(entity.content)
            source_url = _extract_source_url(entity)
            interp = ""
            if i < len(dim_interps):
                interp = dim_interps[i].get("interpretation", "")

            if source_url:
                cell_title = f"[{title_text}]({source_url})"
            else:
                cell_title = title_text

            # Fill table row based on column count
            if col_count == 3:
                lines.append(f"| {cell_title} | — | {interp or '—'} |")
            elif col_count == 4:
                lines.append(f"| {cell_title} | — | — | {interp or '—'} |")
            else:
                lines.append(f"| {cell_title} | {interp or '—'} |")

        lines.append("")

    # Top 5 section
    if top5:
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append("")
        lines.append("## 🔥 今日最有价值信息")
        lines.append("")
        for item in top5:
            idx = item.get("index", "?")
            item_title = item.get("title", "")
            dims = item.get("dimensions", {})
            lines.append(f"**{idx}. {item_title}**")
            lines.append("")
            if dims.get("company"):
                lines.append(f"- 公司层面：{dims['company']}")
            if dims.get("strategy"):
                lines.append(f"- 战略层面：{dims['strategy']}")
            if dims.get("technology"):
                lines.append(f"- 技术视角：{dims['technology']}")
            if dims.get("insight"):
                lines.append(f"- 启示：{dims['insight']}")
            lines.append("")

    # Source footer
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    lines.append("📡 数据来源：AIHOT + SearXNG 搜索")

    return "\n".join(lines)


def _extract_title(content: str) -> str:
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    for line in content.split("\n"):
        line = line.strip()
        if line:
            return line[:100]
    return "Untitled"


def _extract_source_url(entity: Entity) -> str:
    if entity.sources:
        return entity.sources[0].url or ""
    return ""
