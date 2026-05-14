"""WikiLinks parser for Markdown content."""

import re
from dataclasses import dataclass


@dataclass
class WikiLink:
    """A parsed wiki link."""
    target: str       # 链接目标（页面名）
    display: str      # 显示文本（可能与 target 不同）
    position: int     # 在原文中的起始位置


class WikiLinksParser:
    """Parse [[target]] and [[target|display]] links from Markdown."""

    # 匹配 [[...]] 但排除代码块内的
    _WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
    _CODE_BLOCK_RE = re.compile(r"(`{3,}.*?`{3,}|`[^`]+`)", re.DOTALL)

    def parse(self, content: str) -> list[WikiLink]:
        """Extract all wiki links from content, skipping code blocks."""
        # 找到所有代码块的范围
        code_ranges = [
            (m.start(), m.end())
            for m in self._CODE_BLOCK_RE.finditer(content)
        ]

        links = []
        for m in self._WIKILINK_RE.finditer(content):
            # 检查是否在代码块内
            if any(start <= m.start() < end for start, end in code_ranges):
                continue

            raw = m.group(1)
            if "|" in raw:
                target, display = raw.split("|", 1)
            else:
                target = display = raw

            links.append(WikiLink(
                target=target.strip(),
                display=display.strip(),
                position=m.start(),
            ))

        return links

    def extract_targets(self, content: str) -> list[str]:
        """Extract unique link targets from content."""
        links = self.parse(content)
        seen = set()
        targets = []
        for link in links:
            if link.target not in seen:
                seen.add(link.target)
                targets.append(link.target)
        return targets
