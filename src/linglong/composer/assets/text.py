"""文本素材生成器

自动生成文章摘要、引言、标签等文本素材。
"""

import logging
from typing import List

from ..ingest_adapter import MemoryFragment

logger = logging.getLogger(__name__)


class TextAssetGenerator:
    """文本素材生成器"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.excerpt_length = self.config.get("excerpt_length", 200)

    def generate_excerpt(self, fragments: List[MemoryFragment]) -> str:
        """基于记忆片段生成摘要

        当前实现：拼接所有片段的前 N 个字符。
        未来可接入 LLM 生成更精炼的摘要。
        """
        if not fragments:
            return "今日暂无记录。"

        # 取第一个非空片段的前 excerpt_length 字符
        for frag in fragments:
            content = frag.content.strip()
            if content:
                excerpt = content[:self.excerpt_length]
                if len(content) > self.excerpt_length:
                    excerpt += "..."
                return excerpt.replace("\n", " ")

        return "今日暂无记录。"

    def generate_tags(self, fragments: List[MemoryFragment]) -> List[str]:
        """基于记忆片段生成标签

        当前实现：从 source 和 type 中提取。
        未来可接入 LLM 做主题提取。
        """
        tags = set()
        for frag in fragments:
            tags.add(frag.source)
            frag_type = frag.metadata.get("type")
            if frag_type:
                tags.add(frag_type)
        return sorted(list(tags))

    def generate_intro(self, excerpt: str) -> str:
        """生成引言"""
        if not excerpt or excerpt == "今日暂无记录。":
            return "> 本文记录当日的学习与思考。"
        return f"> {excerpt}"
