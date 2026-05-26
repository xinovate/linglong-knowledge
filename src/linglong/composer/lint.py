"""Quality lint for composer output."""

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class LintResult:
    """Result of a quality lint check."""

    passed: bool = True
    score: float = 3.0
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class QualityLint:
    """Two-layer quality checker: rules (free) + optional LLM."""

    def __init__(self, config: dict | None = None):
        cfg = config or {}
        self.min_content_length = cfg.get("min_content_length", 500)
        self.min_paragraphs = cfg.get("min_paragraphs", 3)
        self.min_title_length = cfg.get("min_title_length", 10)
        self.max_title_length = cfg.get("max_title_length", 18)
        self.min_excerpt_length = cfg.get("min_excerpt_length", 30)
        self.max_excerpt_length = cfg.get("max_excerpt_length", 100)
        self.min_tags = cfg.get("min_tags", 2)
        self.max_tags = cfg.get("max_tags", 8)

    def check(self, content: str, metadata: dict) -> LintResult:
        """Run rule-based quality checks on formatted content."""
        result = LintResult()
        body = self._strip_frontmatter(content)

        self._check_content_length(body, result)
        self._check_paragraphs(body, result)
        self._check_title(metadata, result)
        self._check_excerpt(metadata, result)
        self._check_tags(metadata, result)
        self._check_duplicate_paragraphs(body, result)

        result.passed = len(result.issues) == 0
        if result.passed:
            result.score = 3.0
        else:
            result.score = max(0, 3.0 - len(result.issues))

        return result

    def _strip_frontmatter(self, content: str) -> str:
        """Remove YAML frontmatter from content for body analysis."""
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                return parts[2].strip()
        return content

    def _check_content_length(self, body: str, result: LintResult) -> None:
        length = len(body)
        if length < self.min_content_length:
            result.issues.append(
                f"正文长度 {length} 字，低于最低 {self.min_content_length} 字"
            )

    def _check_paragraphs(self, body: str, result: LintResult) -> None:
        paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
        # Exclude blockquotes and HTML comments from paragraph count
        real = [p for p in paragraphs if not p.startswith(">") and not p.startswith("<!--")]
        if len(real) < self.min_paragraphs:
            result.issues.append(
                f"正文仅 {len(real)} 个段落，低于最低 {self.min_paragraphs} 段"
            )

    def _check_title(self, metadata: dict, result: LintResult) -> None:
        title = metadata.get("title", "")
        if not title:
            result.issues.append("缺少标题")
            return
        length = len(title)
        if length < self.min_title_length:
            result.warnings.append(f"标题长度 {length} 字符，建议 >= {self.min_title_length}")
        elif length > self.max_title_length:
            result.warnings.append(f"标题长度 {length} 字符，建议 <= {self.max_title_length}")

    def _check_excerpt(self, metadata: dict, result: LintResult) -> None:
        excerpt = metadata.get("excerpt", "")
        if not excerpt:
            result.warnings.append("缺少摘要")
            return
        length = len(excerpt)
        if length < self.min_excerpt_length:
            result.warnings.append(
                f"摘要长度 {length} 字符，建议 >= {self.min_excerpt_length}"
            )
        elif length > self.max_excerpt_length:
            result.warnings.append(
                f"摘要长度 {length} 字符，建议 <= {self.max_excerpt_length}"
            )

    def _check_tags(self, metadata: dict, result: LintResult) -> None:
        tags = metadata.get("tags", [])
        if not isinstance(tags, list):
            return
        count = len(tags)
        if count < self.min_tags:
            result.issues.append(f"标签数 {count} 个，低于最低 {self.min_tags} 个")
        elif count > self.max_tags:
            result.warnings.append(f"标签数 {count} 个，建议 <= {self.max_tags} 个")

    def _check_duplicate_paragraphs(self, body: str, result: LintResult) -> None:
        paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
        seen: set[str] = set()
        for p in paragraphs:
            normalized = re.sub(r"\s+", " ", p.lower())
            if normalized in seen:
                result.warnings.append("存在重复段落")
                return
            seen.add(normalized)
