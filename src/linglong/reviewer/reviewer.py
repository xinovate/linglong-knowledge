"""Article reviewer — evaluates article quality across multiple dimensions."""

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from linglong.core.config import get_config

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "review.md"

_WEIGHTS = {
    "格式规范": 0.10,
    "内容丰富度": 0.20,
    "结构完整度": 0.15,
    "表达自然度": 0.20,
    "踩坑覆盖": 0.10,
    "可读性": 0.15,
    "技术准确性": 0.10,
}

_FAIL_THRESHOLD = 3


@dataclass
class DimensionScore:
    name: str
    score: float
    suggestions: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.score > _FAIL_THRESHOLD


@dataclass
class ReviewResult:
    dimensions: list[DimensionScore]
    total_score: float
    passed: bool
    summary: str
    rule_issues: list[str] = field(default_factory=list)


def _load_prompt() -> str:
    return _PROMPT_PATH.read_text(encoding="utf-8")


def _rule_check(content: str) -> list[str]:
    """Rule-based format checks. Returns a list of issues."""
    issues: list[str] = []

    # Check frontmatter
    if not content.startswith("---"):
        issues.append("缺少 frontmatter（文件应以 --- 开头）")
    else:
        fm_end = content.find("---", 3)
        if fm_end < 0:
            issues.append("frontmatter 未闭合（缺少第二个 ---）")
        else:
            fm = content[3:fm_end]
            for field_name in ("title", "date", "tags"):
                if f"{field_name}:" not in fm:
                    issues.append(f"frontmatter 缺少 {field_name} 字段")

    # Check <!-- more -->
    if "<!-- more -->" not in content:
        issues.append("缺少 <!-- more --> 标记（Hexo 摘要截断点）")

    # Check for broken code blocks
    code_block_pattern = re.compile(r"```")
    matches = code_block_pattern.findall(content)
    if len(matches) % 2 != 0:
        issues.append("存在未闭合的代码块（``` 数量为奇数）")

    # Check for empty headings
    if re.search(r"^#{1,6}\s*$", content, re.MULTILINE):
        issues.append("存在空标题")

    # Word count
    text_only = re.sub(r"[#>*`\-\[\]()!|]", "", content)
    text_only = re.sub(r"\s+", "", text_only)
    if len(text_only) < 500:
        issues.append(f"正文过短（约 {len(text_only)} 字，建议 > 500）")

    return issues


class Reviewer:
    """Evaluates article quality using rule-based checks + LLM scoring."""

    def __init__(self) -> None:
        config = get_config()
        rc = config.reviewer
        self._llm_config: dict[str, Any] = {
            "provider": rc.llm_provider,
            "model": rc.llm_model,
            "api_key": rc.llm_api_key,
            "base_url": rc.llm_base_url,
            "temperature": rc.llm_temperature,
            "max_tokens": rc.llm_max_tokens,
            "timeout": 120,
        }
        self._passing_score = rc.passing_score
        self._prompt_template = _load_prompt()

    def review(
        self,
        content: str,
        source_entity_ids: list[str] | None = None,
    ) -> ReviewResult:
        """Review an article and return scored dimensions.

        Args:
            content: Full article markdown (including frontmatter).
            source_entity_ids: Optional knowledge entity IDs for accuracy checks.
        """
        # 1. Rule-based checks
        rule_issues = _rule_check(content)

        # 2. Fetch source entities if provided
        sources_text = ""
        if source_entity_ids:
            sources_text = self._fetch_sources(source_entity_ids)

        # 3. Build prompt
        accuracy_instruction = (
            "对比文章内容与下方提供的知识来源，检查核心声明是否准确。"
            "如发现不一致，在建议中明确指出。"
            if sources_text
            else "未提供知识来源，仅评估文章内部的逻辑一致性。"
        )
        source_section = (
            f"## 知识来源（用于准确性校验）\n\n{sources_text}"
            if sources_text
            else ""
        )

        prompt = self._prompt_template.format(
            content=content,
            accuracy_instruction=accuracy_instruction,
            source_section=source_section,
        )

        # 4. Call LLM
        llm_response = self._call_llm(prompt)

        # 5. Parse response
        dimensions, total_score, passed, summary = self._parse_response(llm_response)

        # 6. Override pass/fail: rule issues that are critical force failure
        critical_issues = [i for i in rule_issues if "未闭合" in i or "frontmatter" in i]
        if critical_issues:
            passed = False

        return ReviewResult(
            dimensions=dimensions,
            total_score=total_score,
            passed=passed,
            summary=summary,
            rule_issues=rule_issues,
        )

    def _fetch_sources(self, entity_ids: list[str]) -> str:
        """Fetch source entities from knowledge store."""
        from linglong.knowledge.store import KnowledgeStore

        store = KnowledgeStore()
        parts: list[str] = []
        for eid in entity_ids:
            entity = store.get(eid)
            if entity:
                title = ""
                for line in entity.content.split("\n"):
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break
                parts.append(f"[来源: {title or eid}]\n{entity.content[:2000]}")
        return "\n\n---\n\n".join(parts)

    def _call_llm(self, prompt: str) -> str:
        """Call LLM for review scoring."""
        from linglong.core.llm.factory import create_llm_client

        client = create_llm_client(self._llm_config)
        return client.chat_with_system(
            user_content=prompt,
            system="你是一位严格但公正的技术博客审稿编辑。按维度打分，给出具体改进建议。严格输出 JSON。",
            temperature=0.3,
            max_tokens=self._llm_config.get("max_tokens", 4096),
        )

    def _parse_response(self, text: str) -> tuple[list[DimensionScore], float, bool, str]:
        """Parse LLM JSON response into structured scores."""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.error("Failed to parse review response: %s", text[:300])
            return [], 0.0, False, "审稿结果解析失败"

        dimensions: list[DimensionScore] = []
        for d in data.get("dimensions", []):
            dimensions.append(
                DimensionScore(
                    name=d.get("name", "未知"),
                    score=float(d.get("score", 0)),
                    suggestions=d.get("suggestions", []),
                )
            )

        total = float(data.get("total_score", 0))
        passed = bool(data.get("passed", False))
        summary = data.get("summary", "")

        # Recalculate total from weights if dimensions exist
        if dimensions:
            weighted = sum(
                _WEIGHTS.get(d.name, 0.1) * d.score for d in dimensions
            )
            # Fail if any dimension is at or below threshold
            any_fail = any(d.score <= _FAIL_THRESHOLD for d in dimensions)
            total = round(weighted, 1)
            passed = total >= self._passing_score and not any_fail

        return dimensions, total, passed, summary
