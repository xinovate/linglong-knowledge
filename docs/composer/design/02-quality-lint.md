# D-02 质量校验设计

> 状态：✅ 已实现 | 最后更新：2026-05-26

---

## 概述

文章生成后、保存草稿前，自动校验内容质量。两层检查：规则层（零成本）+ LLM 层（可选）。

---

## 插入位置

```
BlogTemplate.apply() → QualityLint.check() → DraftManager.save_draft()
```

校验不通过不阻断流程，而是标记草稿为 `needs_review`。

---

## 规则层

| 检查项 | 阈值 | 说明 |
|--------|------|------|
| 正文长度 | > 500 字 | 低于说明内容太薄 |
| 段落数 | >= 3 | 低于说明是碎片拼接 |
| 标题长度 | 10-18 字符 | 复用 BlogTemplate 的规则 |
| 摘要长度 | 30-100 字符 | 过短或过长都不好 |
| 标签数 | 2-8 个 | 过少覆盖不全，过多不聚焦 |
| 重复段落 | 无 | 检测正文中的重复段落 |

实现：遍历检查项，每项返回 passed / warning / error。所有项 passed → lint 通过。

---

## LLM 层（可选）

当 `quality_lint.use_llm: true` 时启用，消耗 token。

Prompt 要求 LLM 评估：
1. 正文是否有核心洞察（不是简单转述片段）
2. 段落之间逻辑是否连贯
3. 标题是否准确反映内容

返回格式：
```json
{
  "score": 4,
  "issues": ["第三段与上下文衔接生硬"]
}
```

score >= 3 视为通过。

---

## LintResult

```python
@dataclass
class LintResult:
    passed: bool
    score: float              # 0-5（规则层通过=3，LLM 层可加分）
    issues: list[str]         # 未通过的原因
    warnings: list[str]       # 警告（不影响通过）
```

---

## 配置

```yaml
composer:
  quality_lint:
    enabled: true
    use_llm: false
    min_content_length: 500
    min_paragraphs: 3
```

---

## 与草稿的关系

| lint 结果 | 草稿状态 | 后续 |
|-----------|---------|------|
| 通过 | `pending` | 等待人工审核后发布 |
| 未通过 | `needs_review` | 人工修改后重新审核 |
