"""Tests for the reviewer module."""

import json
from unittest.mock import MagicMock, patch

import pytest

from linglong.reviewer.reviewer import ReviewResult, Reviewer, _rule_check


class TestRuleCheck:
    """Tests for rule-based format checks."""

    def test_valid_article_no_issues(self):
        content = """---
title: Test Article
date: 2026-05-26
tags: [test]
---

> excerpt

<!-- more -->

## Section 1

Body text with enough content to pass the word count check.
Adding more text here to ensure we cross the five hundred character threshold.
This is a test article about something technical and interesting that has depth.
The content should be long enough to not trigger the minimum length check.
Let us add even more text to be safe about the character count requirement.
Some more filler text to reach the minimum requirement easily and reliably.
We need to make sure this passes all the rule checks without any issues at all.
Adding a few more sentences here to definitely exceed the five hundred char mark.
This should be more than enough content for the word count validation to pass.
"""
        issues = _rule_check(content)
        assert len(issues) == 0

    def test_missing_frontmatter(self):
        issues = _rule_check("Just some text without frontmatter")
        assert any("frontmatter" in i.lower() for i in issues)

    def test_missing_more_tag(self):
        content = """---
title: Test
date: 2026-05-26
tags: [test]
---

Some content without the more tag but long enough otherwise.
Adding more text to ensure we have enough content for the word count.
More filler text to pass the minimum length requirement easily.
"""
        issues = _rule_check(content)
        assert any("more" in i.lower() for i in issues)

    def test_unclosed_code_block(self):
        content = """---
title: Test
date: 2026-05-26
tags: [test]
---

<!-- more -->

```
some code without closing
"""
        issues = _rule_check(content)
        assert any("代码块" in i for i in issues)

    def test_too_short(self):
        content = """---
title: Test
date: 2026-05-26
tags: [test]
---

<!-- more -->

Short.
"""
        issues = _rule_check(content)
        assert any("过短" in i for i in issues)

    def test_missing_frontmatter_field(self):
        content = """---
title: Test
---

<!-- more -->

Body text with enough content to pass checks normally.
More text to reach the 500 character minimum threshold.
Adding even more filler content here for safety.
"""
        issues = _rule_check(content)
        assert any("date" in i for i in issues)


class TestReviewer:
    """Tests for the Reviewer class with mocked LLM."""

    @pytest.fixture(autouse=True)
    def _setup_config(self):
        from linglong.core.config import set_config, LinglongConfig
        set_config(LinglongConfig())
        yield
        set_config(None)

    @patch("linglong.reviewer.reviewer.Reviewer._call_llm")
    def test_review_passes(self, mock_llm):
        mock_llm.return_value = json.dumps({
            "dimensions": [
                {"name": "格式规范", "score": 8, "suggestions": []},
                {"name": "内容丰富度", "score": 7, "suggestions": []},
                {"name": "结构完整度", "score": 7, "suggestions": []},
                {"name": "表达自然度", "score": 7, "suggestions": []},
                {"name": "踩坑覆盖", "score": 6, "suggestions": []},
                {"name": "可读性", "score": 8, "suggestions": []},
                {"name": "技术准确性", "score": 7, "suggestions": []},
            ],
            "total_score": 7.1,
            "passed": True,
            "summary": "Good article",
        })

        content = """---
title: Test Article
date: 2026-05-26
tags: [test]
categories: [tech]
excerpt: A test article
---

> A test article

<!-- more -->

## Introduction

Some body text with enough content to pass the minimum length requirement.
Adding more detailed technical content here for the review to evaluate.
The article covers interesting technical topics with code examples.

```python
def hello():
    print("world")
```

## Conclusion

Final thoughts here.
"""
        reviewer = Reviewer()
        result = reviewer.review(content)

        assert result.passed is True
        assert result.total_score > 0
        assert len(result.dimensions) == 7

    @patch("linglong.reviewer.reviewer.Reviewer._call_llm")
    def test_review_fails_low_score(self, mock_llm):
        mock_llm.return_value = json.dumps({
            "dimensions": [
                {"name": "格式规范", "score": 8, "suggestions": []},
                {"name": "内容丰富度", "score": 3, "suggestions": ["内容空洞"]},
                {"name": "结构完整度", "score": 4, "suggestions": []},
                {"name": "表达自然度", "score": 5, "suggestions": []},
                {"name": "踩坑覆盖", "score": 2, "suggestions": ["没有踩坑内容"]},
                {"name": "可读性", "score": 4, "suggestions": []},
                {"name": "技术准确性", "score": 5, "suggestions": []},
            ],
            "total_score": 4.4,
            "passed": False,
            "summary": "Needs improvement",
        })

        content = "---\ntitle: T\ndate: 2026\ntags: []\n---\n\n<!-- more -->\n\nShort."
        reviewer = Reviewer()
        result = reviewer.review(content)

        assert result.passed is False
        assert result.total_score < 6.0

    @patch("linglong.reviewer.reviewer.Reviewer._call_llm")
    def test_review_returns_suggestions(self, mock_llm):
        mock_llm.return_value = json.dumps({
            "dimensions": [
                {"name": "格式规范", "score": 5, "suggestions": ["建议添加 <!-- more -->"]},
                {"name": "内容丰富度", "score": 4, "suggestions": ["第三段缺少数据"]},
                {"name": "结构完整度", "score": 5, "suggestions": ["需要架构图"]},
                {"name": "表达自然度", "score": 3, "suggestions": ["AI 痕迹明显", "套话多"]},
                {"name": "踩坑覆盖", "score": 2, "suggestions": ["完全没有踩坑内容"]},
                {"name": "可读性", "score": 6, "suggestions": []},
                {"name": "技术准确性", "score": 7, "suggestions": []},
            ],
            "total_score": 4.5,
            "passed": False,
            "summary": "表达自然度和踩坑覆盖需要改进",
        })

        content = "---\ntitle: T\ndate: 2026\ntags: []\n---\n\n<!-- more -->\n\nBody."
        reviewer = Reviewer()
        result = reviewer.review(content)

        assert len(result.dimensions) == 7
        total_suggestions = sum(len(d.suggestions) for d in result.dimensions)
        assert total_suggestions > 0
