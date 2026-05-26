# D-03 审查流程设计

> 状态：✅ 已实现 | 最后更新：2026-05-26 | 依赖：[D-01 流水线](01-pipeline.md)

---

## 概述

composer 生成的文章**不直接发布**，强制走草稿 → 审核 → 发布流程。

---

## 草稿生命周期

```mermaid
stateDiagram-v2
    [*] --> 生成文章
    生成文章 --> QualityLint

    QualityLint --> pending: lint 通过
    QualityLint --> needs_review: lint 未通过

    pending --> published: 人工审核通过<br/>publish_draft()
    pending --> discarded: 人工审核不通过<br/>discard_draft()

    needs_review --> pending: 修改后重新提交
    needs_review --> discarded: 放弃

    published --> [*]
    discarded --> [*]
```

---

## 审查流程图

```mermaid
flowchart TD
    START([文章生成完成]) --> LINT{"QualityLint.check()"}
    LINT -->|通过| SAVE_P["save_draft(status=pending)"]
    LINT -->|未通过| SAVE_R["save_draft(status=needs_review)"]

    SAVE_P --> REVIEW_P["生成 review.md<br/>审核检查项清单"]
    SAVE_R --> REVIEW_R["生成 review.md<br/>标注质量问题"]

    REVIEW_P --> HUMAN["人工审核"]
    REVIEW_R --> FIX["人工修改 article.md"]

    HUMAN -->|通过| PUBLISH["publish_draft()<br/>→ DispatchManager"]
    HUMAN -->|不通过| DISCARD["discard_draft()"]

    FIX --> RESUBMIT["更新 status=pending"]
    RESUBMIT --> HUMAN

    PUBLISH --> LOG["OutputLog.append()"]
    LOG --> DONE([完成])

    DISCARD --> DONE2([完成])

    style LINT fill:#FF9800,color:#fff
    style PUBLISH fill:#4CAF50,color:#fff
    style DISCARD fill:#f44336,color:#fff
```

---

## 草稿目录结构

```
~/linglong/data/drafts/
├── state.json              # 草稿元数据索引
├── abc123/                 # 草稿 ID
│   ├── article.md          # 文章正文
│   ├── metadata.json       # 元数据（标题、标签、封面等）
│   └── review.md           # 审核摘要（检查项清单）
├── def456/
└── discard/                # 废弃草稿（可选保留）
    └── xyz789/
```

---

## 审核检查项（review.md 自动生成）

- [ ] 标题长度 10-18 汉字
- [ ] 摘要质量 30-40 汉字
- [ ] 标签准确、不重复
- [ ] 正文有核心洞察，非简单拼接
- [ ] 封面图适配（如有）

---

## 关键文件

| 文件 | 说明 |
|------|------|
| `src/linglong/composer/draft.py` | `DraftManager` 草稿 CRUD |
| `src/linglong/composer/composer.py` | `_process_day()` 中决定 draft/publish |
