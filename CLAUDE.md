# CLAUDE.md — Linglong Knowledge 项目协作指南

## 项目定位

Linglong Knowledge 是**跨 Agent 统一知识库**，通过 MCP 为 AI Agent 提供共享知识底座。

```
Agent（OpenClaw / Claude Code / Codex）──→ Knowledge Store ──→ MCP Server
                                          (File + SQLite + sqlite-vec)
```

相关项目（独立仓库，本项目不维护）：
- **linglong-scout**：信息采集，结果返回对话，不写知识库
- **博客项目**：文章评审和发布

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

- **知识库只接受讨论沉淀** — 人和 Agent 讨论筛选后通过 MCP/CLI 写入
- **三层存储**：Filesystem（Markdown）+ SQLite（元数据）+ sqlite-vec（向量索引）
- **混合搜索**：FTS5 关键词 + sqlite-vec 语义 + RRF 融合排序
- **Review 引擎**：基于规则的质量控制，自动确认或标记审核

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
- [隐私规约](.claude/rules/privacy.md)
- [文档同步](.claude/rules/docs-sync.md)
