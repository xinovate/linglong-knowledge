# CLAUDE.md — Linglong 项目协作指南

## 项目定位

Linglong 是**跨 Agent 知识中枢**，串联信息采集 → 讨论沉淀 → 博客输出。

```
ingest（采集，不写知识库）→ 用户阅读思考 → 知识库 → 博客项目（评审+发布）
```

> reviewer 和 dispatch 功能暂时由博客项目承担，本项目不维护。

---

## 执行前检查（每次任务开始时必须遵守）

**文档驱动开发：先更新文档，再写代码。**

1. **读 `journal/今天.md`** — 了解当日上下文、待办、已有进度
2. **判断任务影响范围** — 以下文档是否需要更新：
   - 今日日志 `journal/今天.md` — 新增任务/状态变化 → **先更新再动手**
   - 设计文档 `docs/*/design/` — 架构/接口变更 → **先更新设计再实现**
   - 路线图 `docs/roadmap.md` — 新增功能/版本规划 → **先记录再开始**
3. **代码改完后**，按 `.claude/rules/docs-sync.md` 补全受影响的文档

---

## 架构规则

- **ingest 不写知识库** — 采集结果返回给对话，写入由人决定
- **知识库只接受讨论沉淀** — 人和 Agent 讨论筛选后通过 MCP/CLI 写入
- **评审和发布由博客项目负责**，本项目暂不维护 reviewer / dispatch

关键模型字段：`facet`（六分面）| `confidence`（AI 置信度）| `status`（审核状态）| `created_by`（`agent:claude`/`agent:openclaw`）

---

## 每日工作

- 日志在 `journal/YYYY-MM-DD.md`：开始前读上下文，完成后更新记录
- 优先处理 `PROJECT_OVERVIEW.md` Next Actions
- 参考文档：[项目总览](docs/PROJECT_OVERVIEW.md) | [架构](docs/architecture.md) | [路线图](docs/roadmap.md) | [API](docs/api.md) | [运维](docs/operations.md)

---

## 详细规则

代码风格、测试、API 设计、安全、文档同步的详细规则见 `.claude/rules/`：

- [代码风格](.claude/rules/code-style.md)
- [测试约定](.claude/rules/testing.md)
- [API 设计](.claude/rules/api-design.md)
- [安全要求](.claude/rules/security.md)
- [文档同步](.claude/rules/docs-sync.md)
