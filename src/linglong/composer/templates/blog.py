import re
from typing import Any

import yaml

from .base import Template, ValidationResult


class BlogTemplate(Template):
    """
    博客模板

    规范来源: /Users/wangxin/Hermes/wiki/blog-pipeline/STYLE_GUIDE.md

    强制规则:
    1. frontmatter 必须包含: title, date, tags, categories
    2. 引言格式: > 一句话概括
    3. 必须包含 <!-- more --> 折叠标签
    4. 标题长度不超过 18 字符（对应博客规范 10–18 个汉字）
    5. 配图需要 alt 文本
    """

    REQUIRED_FRONTMATTER = ["title", "date", "tags", "categories"]
    MAX_TITLE_LENGTH = 18

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        # 从外部风格指南加载规则（如果提供）
        self.style_guide_path = config.get("style_guide_path")

    def validate(self, content: str) -> ValidationResult:
        """验证博客内容是否符合规范"""
        errors = []
        warnings = []

        # 1. 检查 frontmatter
        frontmatter = self._extract_frontmatter(content)
        if not frontmatter:
            errors.append("缺少 frontmatter")
        else:
            for field in self.REQUIRED_FRONTMATTER:
                if field not in frontmatter:
                    errors.append(f"frontmatter 缺少必需字段: {field}")

            # 检查 tags 和 categories 是否为列表
            if "tags" in frontmatter and not isinstance(frontmatter["tags"], list):
                warnings.append("tags 应为列表格式（YAML list）")
            if "categories" in frontmatter and not isinstance(frontmatter["categories"], list):
                warnings.append("categories 应为列表格式（YAML list）")

        # 2. 检查标题长度
        if frontmatter and "title" in frontmatter:
            if len(frontmatter["title"]) > self.MAX_TITLE_LENGTH:
                warnings.append(f"标题长度超过 {self.MAX_TITLE_LENGTH} 字符")

        # 3. 检查 <!-- more --> 标签
        if "<!-- more -->" not in content:
            errors.append("缺少 <!-- more --> 折叠标签")

        # 4. 检查引言格式
        intro_pattern = re.compile(r"^\s*>\s*.+", re.MULTILINE)
        if not intro_pattern.search(content):
            warnings.append("缺少引言（> 一句话概括）")

        # 5. 检查图片 alt 文本（markdown 格式 和 HTML img 格式）
        img_pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
        for match in img_pattern.finditer(content):
            alt_text = match.group(1)
            if not alt_text.strip():
                warnings.append(f"图片缺少 alt 文本: {match.group(2)}")

        html_img_pattern = re.compile(r'<img\s[^>]*?alt="([^"]*?)"')
        for match in html_img_pattern.finditer(content):
            alt_text = match.group(1)
            if not alt_text.strip():
                warnings.append("HTML img 标签缺少 alt 文本")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def apply(self, content: str, metadata: dict[str, Any]) -> str:
        """
        将内容和元数据格式化为博客文章

        Args:
            content: 原始 Markdown 内容
            metadata: 必需字段: title, date, tags, categories
                     可选字段: excerpt, cover_image, article_image
        """
        # 构建 frontmatter
        frontmatter = self._build_frontmatter(metadata)

        # 确保有引言
        body = self._ensure_intro(content, metadata.get("excerpt", ""))

        # 插入文章配图
        if "article_image" in metadata and metadata["article_image"]:
            body = self._insert_article_image(body, metadata["article_image"])

        # 确保有 <!-- more -->
        body = self._ensure_more_tag(body)

        return f"{frontmatter}\n\n{body}"

    def get_required_metadata(self) -> list[str]:
        """返回必需的元数据字段"""
        return self.REQUIRED_FRONTMATTER.copy()

    def _extract_frontmatter(self, content: str) -> dict[str, Any]:
        """提取 frontmatter 内容"""
        pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
        match = pattern.match(content)

        if not match:
            return {}

        try:
            return yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            return {}

    def _build_frontmatter(self, metadata: dict[str, Any]) -> str:
        """构建 frontmatter 字符串（支持 YAML list）"""
        frontmatter = {}

        for field in self.REQUIRED_FRONTMATTER:
            frontmatter[field] = metadata.get(field, "")

        # 可选字段
        if "excerpt" in metadata:
            frontmatter["excerpt"] = metadata["excerpt"]

        if "cover_image" in metadata:
            frontmatter["cover_image"] = self._resolve_image_value(metadata["cover_image"])

        # background_image → cover_image (from image asset pipeline)
        if "background_image" in metadata:
            frontmatter["cover_image"] = self._resolve_image_value(metadata["background_image"])

        yaml_str = yaml.dump(
            frontmatter,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
        )
        return f"---\n{yaml_str}---"

    def _resolve_image_value(self, value: Any) -> str:
        """Extract a single image path from value (str or dict of variants).

        For dicts, returns the "medium" variant (good balance of quality/size).
        """
        if isinstance(value, dict):
            return value.get("medium", value.get("large", value.get("thumb", "")))
        return str(value)

    def _ensure_intro(self, content: str, excerpt: str) -> str:
        """确保内容有引言"""
        # 如果已经有引言，直接返回
        intro_pattern = re.compile(r"^\s*>\s*.+", re.MULTILINE)
        if intro_pattern.search(content):
            return content

        # 否则添加引言
        if excerpt:
            intro = f"> {excerpt}\n\n"
        else:
            intro = "> 本文摘要待补充...\n\n"

        return intro + content

    def _ensure_more_tag(self, content: str) -> str:
        """确保内容有 <!-- more --> 标签"""
        if "<!-- more -->" in content:
            return content

        # 在第一个段落后面插入 more 标签
        paragraphs = content.split("\n\n")
        if len(paragraphs) >= 2:
            # 在引言后的第一个段落插入
            insert_index = 1
            for i, p in enumerate(paragraphs):
                if p.strip().startswith(">"):
                    insert_index = i + 1
                    break

            paragraphs.insert(insert_index, "<!-- more -->")
            return "\n\n".join(paragraphs)

        return content + "\n\n<!-- more -->"

    def _insert_article_image(self, content: str, image_data: Any) -> str:
        """在引言区块后插入文章配图。

        Args:
            content: Markdown 正文
            image_data: 字符串（单路径）或 dict（多尺寸变体 {name: path}）
        """
        lines = content.split("\n")
        # 找到引言区块结束位置（以 > 开头的行）
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(">"):
                insert_idx = i + 1
            elif insert_idx > 0:
                # 引言后的第一个非引言行
                insert_idx = i
                break
        else:
            insert_idx = len(lines)

        # 根据数据类型生成图片标记
        if isinstance(image_data, dict):
            # 多尺寸变体 → 响应式 <img srcset>
            img_html = self._build_responsive_img(image_data)
        else:
            # 单路径 → 标准 markdown 图片
            img_html = f"\n![配图]({image_data})\n"

        lines.insert(insert_idx, img_html)
        return "\n".join(lines)

    def _build_responsive_img(self, variants: dict[str, str]) -> str:
        """从多尺寸变体构建带 srcset 的响应式 <img> 标签。

        Args:
            variants: {尺寸名: 文件路径}，如 {"thumb": "/path/400.jpg", ...}
        """
        # 构建 srcset 条目："path 400w, path 800w, path 1200w"
        size_map = {"thumb": 400, "medium": 800, "large": 1200}
        srcset_parts = []
        for name, width in size_map.items():
            if name in variants:
                srcset_parts.append(f"{variants[name]} {width}w")

        # 默认 src 使用 medium（兜底选最大可用）
        src = variants.get("medium", variants.get("large", variants.get("thumb", "")))

        srcset = ", ".join(srcset_parts)
        sizes = "(max-width: 600px) 400px, (max-width: 1000px) 800px, 1200px"

        return (
            f'\n<img src="{src}" srcset="{srcset}" sizes="{sizes}" '
            f'loading="lazy" alt="配图" />\n'
        )
