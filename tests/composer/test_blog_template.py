"""Tests for BlogTemplate frontmatter and formatting."""

import pytest

from linglong.composer.templates.blog import BlogTemplate


@pytest.fixture
def template():
    """Create a BlogTemplate instance."""
    return BlogTemplate({})


class TestBuildFrontmatter:
    """Tests for _build_frontmatter method."""

    def test_build_frontmatter_with_list_tags_and_categories(self, template):
        """tags and categories should be rendered as YAML lists."""
        metadata = {
            "title": "测试标题",
            "date": "2024-01-01",
            "tags": ["python", "ai", "agent"],
            "categories": ["技术", "AI"],
        }
        frontmatter = template._build_frontmatter(metadata)

        assert frontmatter.startswith("---\n")
        assert frontmatter.endswith("---")
        # YAML block list format
        assert "\n- python\n" in frontmatter
        assert "\n- ai\n" in frontmatter
        assert "\n- agent\n" in frontmatter
        assert "\n- 技术\n" in frontmatter
        assert "\n- AI\n" in frontmatter

    def test_build_frontmatter_with_single_item_list(self, template):
        """Single-item lists should still render as YAML lists."""
        metadata = {
            "title": "单标签测试",
            "date": "2024-01-01",
            "tags": ["python"],
            "categories": ["回顾"],
        }
        frontmatter = template._build_frontmatter(metadata)

        assert "\n- python\n" in frontmatter
        assert "\n- 回顾\n" in frontmatter

    def test_build_frontmatter_with_empty_lists(self, template):
        """Empty lists should render as empty YAML lists."""
        metadata = {
            "title": "空标签测试",
            "date": "2024-01-01",
            "tags": [],
            "categories": [],
        }
        frontmatter = template._build_frontmatter(metadata)

        assert "tags: []" in frontmatter or "tags:\n" in frontmatter

    def test_build_frontmatter_with_optional_fields(self, template):
        """Optional fields excerpt and cover_image should be included."""
        metadata = {
            "title": "测试",
            "date": "2024-01-01",
            "tags": ["a"],
            "categories": ["b"],
            "excerpt": "这是一段摘要",
            "cover_image": "https://example.com/cover.jpg",
        }
        frontmatter = template._build_frontmatter(metadata)

        assert "excerpt: 这是一段摘要" in frontmatter
        assert "cover_image: https://example.com/cover.jpg" in frontmatter

    def test_build_frontmatter_missing_required_uses_empty_string(self, template):
        """Missing required fields should default to empty string."""
        metadata = {
            "title": "测试",
            "date": "2024-01-01",
            # missing tags and categories
        }
        frontmatter = template._build_frontmatter(metadata)

        assert "tags: ''" in frontmatter or "tags:" in frontmatter
        assert "categories: ''" in frontmatter or "categories:" in frontmatter


class TestExtractFrontmatter:
    """Tests for _extract_frontmatter method."""

    def test_extract_frontmatter_with_lists(self, template):
        """Should parse YAML lists correctly."""
        content = """---
title: 测试标题
date: 2024-01-01
tags:
  - python
  - ai
categories:
  - 技术
---

正文内容
"""
        frontmatter = template._extract_frontmatter(content)

        assert frontmatter["title"] == "测试标题"
        # yaml.safe_load converts YYYY-MM-DD to datetime.date
        from datetime import date

        assert frontmatter["date"] == date(2024, 1, 1)
        assert frontmatter["tags"] == ["python", "ai"]
        assert frontmatter["categories"] == ["技术"]

    def test_extract_frontmatter_with_inline_lists(self, template):
        """Should parse inline YAML lists correctly."""
        content = """---
title: 测试
date: 2024-01-01
tags: [python, ai]
categories: [技术]
---

正文
"""
        frontmatter = template._extract_frontmatter(content)

        assert frontmatter["tags"] == ["python", "ai"]
        assert frontmatter["categories"] == ["技术"]

    def test_extract_frontmatter_no_frontmatter(self, template):
        """Should return empty dict when no frontmatter present."""
        content = "# Just a heading\n\nSome text."
        frontmatter = template._extract_frontmatter(content)

        assert frontmatter == {}

    def test_extract_frontmatter_invalid_yaml(self, template):
        """Should return empty dict for invalid YAML."""
        content = "---\ninvalid: yaml: : :\n---\n\n正文"
        frontmatter = template._extract_frontmatter(content)

        assert frontmatter == {}


class TestFrontmatterRoundTrip:
    """Tests for build -> extract round-trip preservation."""

    def test_round_trip_preserves_lists(self, template):
        """Building then extracting should preserve list structure."""
        original = {
            "title": "测试标题",
            "date": "2024-01-01",
            "tags": ["python", "ai", "agent"],
            "categories": ["技术", "AI"],
            "excerpt": "摘要",
        }
        built = template._build_frontmatter(original)
        # Simulate full article content
        content = f"{built}\n\n正文内容"
        extracted = template._extract_frontmatter(content)

        assert extracted["title"] == "测试标题"
        # yaml.dump outputs string dates with quotes, so safe_load returns str
        assert extracted["date"] == "2024-01-01"
        assert extracted["tags"] == ["python", "ai", "agent"]
        assert extracted["categories"] == ["技术", "AI"]
        assert extracted["excerpt"] == "摘要"


class TestValidate:
    """Tests for validate method."""

    def test_validate_valid_content(self, template):
        """Valid content should pass validation."""
        content = """---
title: 测试标题
date: 2024-01-01
tags:
  - python
  - ai
categories:
  - 技术
---

> 这是一段引言

正文内容

<!-- more -->

更多内容
"""
        result = template.validate(content)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_missing_frontmatter(self, template):
        """Missing frontmatter should fail validation."""
        content = "# 标题\n\n正文"
        result = template.validate(content)

        assert result.is_valid is False
        assert any("缺少 frontmatter" in e for e in result.errors)

    def test_validate_missing_required_fields(self, template):
        """Missing required fields should fail validation."""
        content = """---
title: 测试
---

> 引言

正文

<!-- more -->
"""
        result = template.validate(content)

        assert result.is_valid is False
        assert any("缺少必需字段" in e for e in result.errors)

    def test_validate_missing_more_tag(self, template):
        """Missing <!-- more --> should fail validation."""
        content = """---
title: 测试标题
date: 2024-01-01
tags:
  - python
categories:
  - 技术
---

> 引言

正文内容
"""
        result = template.validate(content)

        assert result.is_valid is False
        assert any("<!-- more -->" in e for e in result.errors)

    def test_validate_tags_not_list(self, template):
        """tags as string instead of list should produce a warning."""
        content = """---
title: 测试标题
date: 2024-01-01
tags: python, ai
categories:
  - 技术
---

> 引言

正文

<!-- more -->
"""
        result = template.validate(content)

        # Should be valid but with a warning about tags type
        assert any("tags" in w and "列表" in w for w in result.warnings)

    def test_validate_categories_not_list(self, template):
        """categories as string instead of list should produce a warning."""
        content = """---
title: 测试标题
date: 2024-01-01
tags:
  - python
categories: 技术
---

> 引言

正文

<!-- more -->
"""
        result = template.validate(content)

        assert any("categories" in w and "列表" in w for w in result.warnings)

    def test_validate_title_too_long(self, template):
        """Title exceeding MAX_TITLE_LENGTH should produce a warning."""
        content = """---
title: 这是一个非常长的标题超过了十八个字符的限制
date: 2024-01-01
tags:
  - python
categories:
  - 技术
---

> 引言

正文

<!-- more -->
"""
        result = template.validate(content)

        assert any("标题长度超过" in w for w in result.warnings)

    def test_validate_missing_intro(self, template):
        """Missing intro should produce a warning."""
        content = """---
title: 测试标题
date: 2024-01-01
tags:
  - python
categories:
  - 技术
---

正文内容

<!-- more -->
"""
        result = template.validate(content)

        assert any("引言" in w for w in result.warnings)

    def test_validate_missing_alt_text(self, template):
        """Images without alt text should produce a warning."""
        content = """---
title: 测试标题
date: 2024-01-01
tags:
  - python
categories:
  - 技术
---

> 引言

![](https://example.com/image.jpg)

<!-- more -->
"""
        result = template.validate(content)

        assert any("alt 文本" in w for w in result.warnings)
