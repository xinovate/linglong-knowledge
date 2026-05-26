"""LLM 智能提炼器

调用 LLM API 将记忆片段提炼为高质量文章素材。
支持多家 LLM 提供商（通过抽象层切换）。
"""

import json
import logging
from pathlib import Path
from typing import Any

from ..ingest_adapter import MemoryFragment
from ..llm.factory import create_llm_client
from .aggregator import ArticleMaterial

logger = logging.getLogger(__name__)


def _load_prompt(name: str) -> str:
    """从 assets/prompts/blog/ 加载提示词文件。"""
    prompt_dir = Path(__file__).resolve().parent.parent / "assets" / "prompts" / "blog"
    prompt_path = prompt_dir / f"{name}.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


class LLMDistiller:
    """LLM 智能提炼器"""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.llm_client = create_llm_client(config)
        self.system_prompt = _load_prompt("system")
        self.user_prompt_template = _load_prompt("user_template")

    def distill(
        self, date: str, fragments: list[MemoryFragment], topic: str | None = None
    ) -> ArticleMaterial:
        """提炼记忆片段为文章素材

        Args:
            date: 日期字符串或主题名
            fragments: 记忆片段列表
            topic: 可选主题，设置后 LLM 围绕主题提炼并过滤弱相关片段

        Returns:
            ArticleMaterial: 包含 LLM 生成的标题、摘要、正文等
        """
        if not fragments:
            logger.warning(f"{date} 没有记忆片段，返回空素材")
            return ArticleMaterial(date=date, fragments=fragments)

        # 1. 构建 prompt
        fragments_text = self._format_fragments(fragments)
        if topic:
            user_prompt = self._build_topic_prompt(topic, fragments_text)
        else:
            user_prompt = self.user_prompt_template.format(
                date=date,
                fragments_text=fragments_text,
            )

        logger.info(f"调用 LLM 提炼 {date} 的内容，共 {len(fragments)} 条片段")

        # 2. 调用 LLM
        try:
            response = self.llm_client.chat_with_system(
                user_content=user_prompt,
                system=self.system_prompt,
                temperature=self.config.get("temperature", 0.7),
                max_tokens=self.config.get("max_tokens", 4096),
            )
        except Exception as e:
            logger.exception(f"LLM 调用失败，回退到规则模式: {e}")
            return self._fallback(date, fragments)

        # 3. 解析 JSON
        try:
            data = self._parse_json(response)
        except Exception as e:
            logger.error(f"LLM 输出解析失败: {e}\n原始输出:\n{response[:500]}")
            return self._fallback(date, fragments)

        # 4. 组装 ArticleMaterial
        material = ArticleMaterial(
            date=date,
            fragments=fragments,
            title=data.get("title", f"每日回顾 {date}"),
            excerpt=data.get("excerpt", ""),
            tags=data.get("tags", []),
            categories=data.get("categories", ["技术"]),
        )

        # 5. 编译正文（从 outline 构建）
        material.raw_content = self._build_body(data, material.excerpt)

        logger.info(f"LLM 提炼完成: {material.title}")
        return material

    def _format_fragments(self, fragments: list[MemoryFragment]) -> str:
        """将记忆片段格式化为 prompt 输入文本"""
        sections = []
        for i, frag in enumerate(fragments, 1):
            source_label = frag.metadata.get("type", frag.source)
            sections.append(
                f"[片段 {i}] 来源: {source_label}\n"
                f"时间: {frag.timestamp.strftime('%Y-%m-%d %H:%M')}\n"
                f"内容:\n{frag.content[:2000]}"  # 截断避免超出 token 限制
            )
        return "\n\n---\n\n".join(sections)

    def _parse_json(self, text: str) -> dict[str, Any]:
        """从 LLM 输出中提取 JSON"""
        # 去掉可能的 markdown 代码块标记
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        return json.loads(text)

    def group_by_theme(
        self, fragments: list[MemoryFragment], topic: str | None = None
    ) -> dict[str, list[MemoryFragment]]:
        """跨天主题合并：让所有片段过 LLM，按主题分组

        Args:
            fragments: 所有记忆片段（可跨多天）
            topic: 可选语义主题，设置后引导 LLM 围绕该主题分组

        Returns:
            {theme_key: [frag1, frag2, ...], ...}
            theme_key 格式: "主题名称 (最早日期-最晚日期)"
        """
        if not fragments:
            return {}

        logger.info(f"调用 LLM 进行主题分析，共 {len(fragments)} 条片段")

        # 1. 构建 prompt
        fragments_text = self._format_fragments_for_grouping(fragments)
        prompt = self._build_grouping_prompt(fragments_text, topic=topic)

        # 2. 调用 LLM
        try:
            response = self.llm_client.chat_with_system(
                user_content=prompt,
                system=self.system_prompt,
                temperature=0.5,  # 分组用低温度，更稳定
                max_tokens=4096,
            )
        except Exception as e:
            logger.exception(f"主题分析 LLM 调用失败，回退到按天分组: {e}")
            return self._fallback_group_by_day(fragments)

        # 3. 解析 JSON
        try:
            data = self._parse_json(response)
        except Exception as e:
            logger.error(f"主题分析输出解析失败: {e}\n原始输出:\n{response[:500]}")
            return self._fallback_group_by_day(fragments)

        # 4. 按 fragment_indices 重组
        groups = data.get("groups", [])
        if not groups:
            logger.warning("LLM 未返回任何主题分组，回退到按天分组")
            return self._fallback_group_by_day(fragments)

        result = {}
        for group in groups:
            indices = group.get("fragment_indices", [])
            theme = group.get("theme", "未命名主题")
            dates = group.get("dates", [])

            # 构建 theme_key: "主题名称 (最早-最晚)"
            if len(dates) >= 2:
                sorted_dates = sorted(dates)
                date_range = f"{sorted_dates[0]}-{sorted_dates[-1]}"
            elif dates:
                date_range = dates[0]
            else:
                date_range = "unknown"
            theme_key = f"{theme} ({date_range})"

            group_frags = [fragments[i] for i in indices if 0 <= i < len(fragments)]
            if group_frags:
                result[theme_key] = group_frags
                logger.info(f"主题分组: {theme_key} ({len(group_frags)} 条片段)")

        return result

    def _format_fragments_for_grouping(self, fragments: list[MemoryFragment]) -> str:
        """为主题分析格式化所有片段"""
        sections = []
        for i, frag in enumerate(fragments):
            source_label = frag.metadata.get("type", frag.source)
            date_str = frag.timestamp.strftime("%Y-%m-%d")
            sections.append(
                f"[片段 {i}] 日期: {date_str} 来源: {source_label}\n"
                f"内容:\n{frag.content[:1500]}"
            )
        return "\n\n---\n\n".join(sections)

    def _build_grouping_prompt(self, fragments_text: str, topic: str | None = None) -> str:
        """构建主题分析 prompt"""
        topic_instruction = ""
        if topic:
            topic_instruction = f"""
特别要求：用户指定了主题「{topic}」，请围绕此主题进行分组。
优先提取与该主题相关的片段，无关片段归入"其他杂项"。
组名应体现「{topic}」的技术焦点。
"""
        return f"""请分析以下记忆片段，将它们按**技术主题**分组。
同一技术主题可能分散在多天，请识别出来并合并。
{topic_instruction}
记忆片段：
---
{fragments_text}
---

要求：
1. 每个组应有明确的技术焦点（如"MCP协议实战"、"博客流水线架构"）
2. 内容单薄（仅1-2个片段且无技术深度）的组可以归入"其他杂项"
3. 组名要简洁有力，10-15个汉字，不要泛泛的"每日回顾"
4. 返回严格 JSON，不要 markdown 代码块

输出格式：
{{
  "groups": [
    {{
      "theme": "主题名称",
      "dates": ["2026-05-08", "2026-05-09"],
      "fragment_indices": [0, 1, 5],
      "rationale": "简短说明为什么归为一组"
    }}
  ]
}}"""

    def _fallback_group_by_day(
        self, fragments: list[MemoryFragment]
    ) -> dict[str, list[MemoryFragment]]:
        """回退：按天分组"""
        from .aggregator import DailyAggregator

        aggregator = DailyAggregator()
        return aggregator.aggregate(fragments)

    def _build_body(self, data: dict[str, Any], excerpt: str) -> str:
        """从 outline 构建文章正文，增加段落衔接"""
        parts = []

        # 引言
        if excerpt:
            parts.append(f"> {excerpt}")
        else:
            parts.append("> 本文记录了当日的学习与思考。")

        # 过渡句：从引言进入正文
        parts.append("\n<!-- more -->\n")

        outline = data.get("outline", [])
        for i, item in enumerate(outline):
            heading = item.get("heading", "").strip()
            content = item.get("content", "").strip()

            if not heading and not content:
                continue

            # 段落间衔接（非第一段时添加过渡）
            if i > 0 and i < len(outline) - 1:
                # 检查上一段和下一段的 heading 来判断逻辑关系
                prev_heading = outline[i - 1].get("heading", "").lower()
                curr_heading = heading.lower()

                # 在"背景→探索"、"问题→方案"之间添加自然过渡
                if ("背景" in prev_heading or "问题" in prev_heading) and (
                    "探索" in curr_heading or "方案" in curr_heading
                ):
                    parts.append("\n基于以上分析，我开始尝试具体的实现方案。\n")
                elif ("探索" in prev_heading or "实践" in prev_heading) and (
                    "结论" in curr_heading or "总结" in curr_heading
                ):
                    parts.append("\n经过实际验证，以下是几条可以复用的经验。\n")

            if heading:
                parts.append(f"\n{heading}\n")
            if content:
                parts.append(f"{content}")

        return "\n".join(parts)

    def _fallback(self, date: str, fragments: list[MemoryFragment]) -> ArticleMaterial:
        """LLM 失败时的回退：使用规则聚合"""
        from .aggregator import DailyAggregator

        logger.warning(f"{date} 回退到规则聚合模式")
        DailyAggregator()
        material = ArticleMaterial(date=date, fragments=fragments)
        material.compile_content()
        return material

    def _build_topic_prompt(self, topic: str, fragments_text: str) -> str:
        """构建主题提炼 prompt"""
        return f"""请围绕主题「{topic}」，从以下知识片段中提炼一篇博客文章。

**重要**：
1. 只使用与「{topic}」高度相关的片段，丢弃弱相关或无关的内容
2. 不是转述片段，而是提炼出围绕该主题的核心洞察
3. 如果片段不足以支撑一篇完整文章，聚焦最有价值的部分

知识片段：
---
{fragments_text}
---

## 写作要求

### 1. 标题：10-18 个汉字，体现技术判断
### 2. 摘要：30-40 个汉字，包含问题 + 核心结论
### 3. 正文三段式：背景 → 实践/探索 → 结论/洞察
### 4. 标签 3-5 个技术关键词
### 5. 分类 1-2 个

## 输出格式

严格 JSON，不要 markdown 代码块：

{{
  "title": "...",
  "excerpt": "...",
  "tags": ["tag1", "tag2"],
  "categories": ["cat1"],
  "outline": [
    {{"heading": "## 背景", "content": "具体场景引入..."}},
    {{"heading": "## 实践", "content": "过程与关键细节..."}},
    {{"heading": "## 洞察", "content": "可复用的经验提炼..."}}
  ]
}}"""
