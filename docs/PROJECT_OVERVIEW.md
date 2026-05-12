# 项目总览

> 本文档是 linglong 项目的**单一真相源**，汇总版本、功能、测试、债务四大维度。
> 每天打开项目，先看这一页。

---

## 项目定位

Linglong 是一个**跨 Agent 知识中枢**。

**核心问题**：OpenClaw、Claude Code、Codex 等 AI Agent 各自维护独立的知识库，互不相通。同一个概念，OpenClaw 知道，Claude Code 不知道；Claude Code 记了，Codex 又记一遍。

**解决方案**：Linglong 作为所有 AI Agent 的统一知识底座，串联信息获取、知识沉淀、内容生产和多平台分发的完整闭环。

```
OpenClaw ──┐
Claude Code ┼──→ Linglong Knowledge Store ←── ingest (多源采集)
Codex ──────┘         ↓
                  composer (知识编译)
                       ↓
                  dispatch (智能分发)
```

---

## 版本进度

| 版本 | 目标 | 状态 | 关键交付 | 完成时间 |
|------|------|------|---------|----------|
| v0.1 | MVP 骨架 | ✅ 已完成 | core + ingest + knowledge 三模块骨架 | 2025-04 |
| v0.2 | Composer 迁移 | ✅ 已完成 | Composer 从 linglong-pipeline 迁移并入，32 个测试通过 | 2026-05-12 |
| v0.3 | 人工审核层 | 🟡 进行中 | Draft Mode、Git Workflow Publisher、AI 封面图生成 | — |
| v0.4 | **知识库统一** | ✅ 已完成 | OpenClaw/Claude Code/Codex 同步、向量搜索落地 | 2026-05-12 |
| v0.5 | **ingest 通用化** | 🔴 未开始 | ai-morning-brief 抽象为通用引擎，支持任意主题采集 | — |
| v0.6 | **多 Agent 接入** | 🟡 部分完成 | Codex 已接入，冲突解决与自动同步待完善 | — |
| v0.7 | composer 产品化 | 🔴 未开始 | 多模板（早报/周报/PPT）、AI 封面图、内容验证 | — |
| v0.8 | dispatch 正式化 | 🔴 未开始 | 发布队列、多平台路由、失败重试 | — |
| v0.9 | 稳定化 | 🔴 未开始 | API 冻结、全链路测试、mypy strict、性能优化 | — |
| **v1.0** | **跨 Agent 知识中枢** | 🔴 未开始 | 完整闭环：任意 Agent 产出 → 统一知识库 → 智能编译 → 多平台分发 | — |

---

## 功能开发时间线

| 功能 | 所属版本 | 状态 | 关联提交 | 完成时间 |
|------|---------|------|---------|----------|
| core（共享模型 + 配置） | v0.1 | ✅ | — | 2025-04 |
| ingest（RSS 获取） | v0.1 | ✅ | — | 2025-04 |
| knowledge（三层存储 + Review） | v0.1 | ✅ | — | 2025-04 |
| Composer 迁移入 monorepo | v0.2 | ✅ | — | 2026-05-12 |
| IngestAdapter（Entity → MemoryFragment） | v0.2 | ✅ | — | 2026-05-12 |
| LLM Distiller（LLM 智能提炼） | v0.2 | ✅ | — | 2026-05-12 |
| DailyAggregator（按天聚合） | v0.2 | ✅ | — | 2026-05-12 |
| BlogTemplate（博客模板） | v0.2 | ✅ | — | 2026-05-12 |
| TextAssetGenerator（文本资产） | v0.2 | ✅ | — | 2026-05-12 |
| ComposerState（内容哈希去重） | v0.2 | ✅ | — | 2026-05-12 |
| Draft Mode（草稿审核） | v0.2 | ✅ | — | 2026-05-12 |
| Git Workflow Publisher | v0.3 | ✅ | — | 2026-05-11 |
| pytest 测试骨架 | v0.2 | ✅ | — | 2026-05-12 |
| ruff/black 格式化 | v0.3 | ✅ | — | 2026-05-12 |
| tests/core/ + tests/ingest/ 补齐 | v0.3 | ✅ | — | 2026-05-12 |
| OpenClawSyncAdapter（wiki → KnowledgeStore） | v0.4 | ✅ | `ccd2011` | 2026-05-12 |
| ClaudeCodeSyncAdapter（memory → KnowledgeStore） | v0.4 | ✅ | `ffb7c10` | 2026-05-12 |
| CodexSyncAdapter（`~/.codex/` → KnowledgeStore） | v0.4 | ✅ | `a11b013` | 2026-05-12 |
| EmbeddingGenerator（OpenClaw 远程 embedding） | v0.4 | ✅ | `8548815` | 2026-05-12 |
| 向量搜索 `search_similar()`（sqlite-vec） | v0.4 | ✅ | `8548815` | 2026-05-12 |

---

## 测试覆盖速览

| 模块 | 单元测试 | 集成测试 | E2E | 总评 |
|------|---------|---------|-----|------|
| `core/` | ✅ 10 个 | — | — | ✅ |
| `ingest/` | ✅ 6 个 | — | — | ✅ |
| `knowledge/` | ✅ 36 个 | — | — | ✅ |
| `composer/` | ✅ 51 个 | — | — | ✅ |
| `dispatch/` | ❌ 未开始 | — | — | ⚪ 低优 |

**图例：** ✅ 已覆盖 / 🔴 空缺（高优） / ⚪ 空缺（低优）

---

## 技术债务 TOP 5

| 问题 | 严重度 | 状态 | 计划版本 | 详情 |
|------|--------|------|----------|------|
| ingest 仅支持 RSS | 🔴 高 | 待扩展 | v0.5 | 需支持 Web Search、爬虫、API 调用 |
| dispatch 模块未启动 | 🟡 中 | 待启动 | v0.8 | `_pending_publishers/` 暂存，需正式化 |
| 短期→长期记忆转换未实现 | 🟡 中 | 待实现 | v0.4+ | MEMORY.md 规则：任务完成后自动迁移到 wiki |
| 向量搜索增强（混合搜索/MMR/时间衰减） | 🟡 低 | 待实现 | v0.7 | 当前仅基础 cosine 相似度 |
| `datetime.utcnow()` 已弃用 | 🟡 低 | 待修复 | v0.9 | Pydantic 和 store.py 多处使用，需替换为 timezone-aware |

完整债务清单 → [30-development/tech-debt.md](30-development/tech-debt.md)

---

## 最近 5 次提交

| 提交 | 说明 | 时间 |
|------|------|------|
| `8548815` | feat(v0.4): vector search with OpenClaw embedding service | 2026-05-12 |
| `fd5c312` | chore: remove completed plan docs/plans/multi-agent-orchestration.md | 2026-05-12 |
| `a11b013` | feat(v0.4): add CodexSyncAdapter for cross-agent knowledge sync | 2026-05-12 |
| `ae3049c` | docs: update agent-orchestration.md — primary-session review preferred | 2026-05-12 |
| `463f8e6` | docs: sync progress status for v0.4 and agent integration roadmap | 2026-05-12 |

---

## 下一步（Next Actions）

按优先级排序，只看最前面 3 条：

1. 🔴 **启动 v0.5：ingest 通用化** — 把 ai-morning-brief 抽象为可配置通用引擎，支持 Web Search / 爬虫 / API
2. 🟡 **AI 封面图生成** — 依赖外部 API，需考虑成本和超时
3. 🟡 **dispatch 模块启动** — 将 `_pending_publishers/` 中的发布器正式接入 dispatch
4. 🟡 **v0.3 收尾** — 审核-发布联动工作流闭环设计
5. 🟡 **v0.6 完善** — 跨 Agent 写入冲突解决、自动同步触发机制

详细计划 → [00-roadmap/v0.3.md](00-roadmap/v0.3.md) | [v1.0 路线图](00-roadmap/v1.0.md)
