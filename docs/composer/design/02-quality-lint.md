# D-02 质量校验设计

> 状态：✅ 已实现 | 最后更新：2026-05-26 | 依赖：[D-01 流水线](01-pipeline.md)

---

## 概述

文章生成后、保存草稿前，自动校验内容质量。两层检查：规则层（零成本）+ LLM 层（可选）。校验不通过不阻断流程，而是标记草稿为 `needs_review`。

---

## 校验流程图

```mermaid
flowchart TD
    START(["BlogTemplate.apply() 完成"]) --> LINT{"quality_lint<br/>enabled?"}
    LINT -->|false| SKIP["跳过校验<br/>默认 pending"]
    LINT -->|true| STRIP["strip_frontmatter()<br/>去除 YAML 头部"]

    STRIP --> RULES

    subgraph RULES["规则层校验（零成本）"]
        R1{"正文长度<br/>> 500 字?"}
        R2{"段落数<br/>>= 3?"}
        R3{"标题长度<br/>10-18 字?"}
        R4{"摘要长度<br/>30-100 字?"}
        R5{"标签数<br/>2-8 个?"}
        R6{"重复段落?"}

        R1 --> R2 --> R3 --> R4 --> R5 --> R6
    end

    R6 --> LLM_CHECK{"use_llm?"}

    LLM_CHECK -->|true| LLM["LLM 层校验<br/>洞察/连贯/标题匹配<br/>score >= 3 通过"]
    LLM_CHECK -->|false| SCORE["计算 score<br/>通过=3 / 每个 issue -1"]

    LLM --> RESULT
    SCORE --> RESULT

    subgraph RESULT["判定结果"]
        PASSED["passed + score=3<br/>status=pending"]
        FAILED["未通过 + score<3<br/>status=needs_review"]
    end

    RESULT --> DRAFT["DraftManager.save_draft()"]

    style RULES fill:#4CAF50,color:#fff
    style LLM fill:#2196F3,color:#fff
    style PASSED fill:#4CAF50,color:#fff
    style FAILED fill:#FF9800,color:#fff
```

---

## 规则层检查时序

```mermaid
sequenceDiagram
    participant Composer
    participant Lint as QualityLint
    participant Result as LintResult

    Composer->>Lint: check(content, metadata)
    Lint->>Lint: _strip_frontmatter(content)

    Lint->>Lint: _check_content_length(body)
    Note right of Lint: < 500 → issue

    Lint->>Lint: _check_paragraphs(body)
    Note right of Lint: 排除引用和注释块<br/>< 3 段 → issue

    Lint->>Lint: _check_title(metadata)
    Note right of Lint: 缺标题 → issue<br/>超范围 → warning

    Lint->>Lint: _check_excerpt(metadata)
    Note right of Lint: 缺摘要 → warning<br/>超范围 → warning

    Lint->>Lint: _check_tags(metadata)
    Note right of Lint: < 2 → issue<br/>> 8 → warning

    Lint->>Lint: _check_duplicate_paragraphs(body)
    Note right of Lint: 归一化后去重检测<br/>重复 → warning

    Lint->>Result: 计算 passed / score
    Note right of Result: issues 为空 → passed=true<br/>score = 3 - len(issues)
    Result-->>Composer: LintResult
```

---

## 规则层检查项

| 检查项 | 阈值 | 通过 | 不通过 |
|--------|------|------|--------|
| 正文长度 | > 500 字 | — | issue |
| 段落数 | >= 3（排除引用/注释） | — | issue |
| 标题长度 | 10-18 字符 | — | 缺标题=issue，超范围=warning |
| 摘要长度 | 30-100 字符 | — | 缺摘要=warning，超范围=warning |
| 标签数 | 2-8 个 | — | < 2=issue，> 8=warning |
| 重复段落 | 无 | — | warning |

**判定规则**：`issues` 为空 → `passed=true`，`score = 3.0 - len(issues)`。

---

## LLM 层（可选）

当 `quality_lint.use_llm: true` 时启用，消耗 token。

```mermaid
sequenceDiagram
    participant Lint as QualityLint
    participant LLM as LLM API

    Lint->>LLM: 提交正文 + 标题<br/>评估洞察/连贯/标题匹配
    LLM-->>Lint: {"score": 1-5, "issues": [...]}

    Note over Lint: score >= 3 视为通过
    Note over Lint: LLM score 叠加到规则层 score
```

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

## LintResult 数据模型

```python
@dataclass
class LintResult:
    passed: bool              # issues 为空 → True
    score: float              # 规则层通过=3，LLM 层可加分
    issues: list[str]         # 未通过的原因（阻断发布）
    warnings: list[str]       # 警告（不阻断）
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

## 与草稿状态的关系

| lint 结果 | score | 草稿状态 | 后续 |
|-----------|-------|---------|------|
| 通过（无 issues） | 3.0 | `pending` | 等待人工审核后发布 |
| 未通过（有 issues） | < 3.0 | `needs_review` | 人工修改后重新审核 |
| 校验禁用 | — | `pending` | 直接进审核队列 |

---

## 关键文件

| 文件 | 说明 |
|------|------|
| `src/linglong/composer/lint.py` | QualityLint + LintResult |
| `src/linglong/composer/composer.py` | `_process_day()` 中调用 lint |
