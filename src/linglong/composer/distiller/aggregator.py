"""记忆聚合器

按日期或主题聚合 MemoryFragment，为文章生成提供结构化素材。
"""

import logging
from collections import defaultdict

from ..ingest_adapter import MemoryFragment

logger = logging.getLogger(__name__)


class DailyAggregator:
    """按天聚合记忆片段"""

    def __init__(self, config: dict = None):
        self.config = config or {}

    def aggregate(self, fragments: list[MemoryFragment]) -> dict[str, list[MemoryFragment]]:
        """按天分组

        Returns:
            { "2026-05-11": [frag1, frag2], ... }
        """
        groups = defaultdict(list)
        for frag in fragments:
            date_key = frag.timestamp.strftime("%Y-%m-%d")
            groups[date_key].append(frag)

        # 按日期倒序
        return dict(sorted(groups.items(), key=lambda x: x[0], reverse=True))


class ArticleMaterial:
    """文章素材"""

    def __init__(
        self,
        date: str,
        fragments: list[MemoryFragment],
        title: str = "",
        excerpt: str = "",
        tags: list[str] = None,
        categories: list[str] = None,
    ):
        self.date = date
        self.fragments = fragments
        self.title = title or f"每日回顾 {date}"
        self.excerpt = excerpt
        self.tags = tags or []
        self.categories = categories or ["回顾"]
        self.raw_content = ""

    def compile_content(self) -> str:
        """将记忆片段编译成文章正文"""
        sections = []
        for frag in self.fragments:
            source_label = frag.metadata.get("type", frag.source)
            sections.append(f"## {source_label}\n\n{frag.content}\n")

        self.raw_content = "\n\n----\n\n".join(sections)
        return self.raw_content
