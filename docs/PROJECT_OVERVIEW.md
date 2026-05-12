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
| v0.4 | **知识库统一** | 🔴 未开始 | OpenClaw wiki 接入、跨 Agent 同步协议、向量搜索兼容 | — |
| v0.5 | **ingest 通用化** | 🔴 未开始 | ai-morning-brief 抽象为通用引擎，支持任意主题采集 | — |
| v0.6 | **多 Agent 接入** | 🔴 未开始 | Claude Code memory 同步、Codex 接入方案 | — |
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

---

## 测试覆盖速览

| 模块 | 单元测试 | 集成测试 | E2E | 总评 |
|------|---------|---------|-----|------|
| `core/` | ✅ 9 个 | — | — | ✅ |
| `ingest/` | ✅ 7 个 | — | — | ✅ |
| `knowledge/` | ✅ 部分覆盖 | — | — | 🟡 进行中 |
| `composer/` | ✅ 32 个 | — | — | ✅ |
| `dispatch/` | ❌ 未开始 | — | — | ⚪ 低优 |

**图例：** ✅ 已覆盖 / 🔴 空缺（高优） / ⚪ 空缺（低优）

---

## 技术债务 TOP 5

| 问题 | 严重度 | 状态 | 计划版本 | 详情 |
|------|--------|------|----------|------|
| knowledge 向量搜索未落地 | 🔴 高 | 待实现 | v0.4 | sqlite-vec 预留，需兼容 OpenClaw embedding 服务 |
| 缺少跨 Agent 同步协议 | 🔴 高 | 待设计 | v0.4 | OpenClaw/Claude Code/Codex 各自为政 |
| ingest 仅支持 RSS | 🔴 高 | 待扩展 | v0.5 | 需支持 Web Search、爬虫、API 调用 |
| dispatch 模块未启动 | 🟡 中 | 待启动 | v0.8 | `_pending_publishers/` 暂存，需正式化 |
| frontmatter 不支持复杂 YAML list | 🟡 中 | 待修复 | v0.3 | `templates/blog.py` |

完整债务清单 → [30-development/tech-debt.md](30-development/tech-debt.md)

---

## 最近 5 次提交

| 提交 | 说明 | 时间 |
|------|------|------|
| `8026443` | chore: apply ruff/black formatting and add test skeleton | 2026-05-12 |
| `d9568c8` | docs: sync CLAUDE.md and workflow with v0.3 status | 2026-05-12 |
| `8692188` | SSH 远程触发和文档同步 | 2026-05-12 |
| `54f0dc2` | Git Workflow Publisher：含代理支持 | 2026-05-11 |
| `4600e04` | Composer 集成测试 + State 隔离 bug 修复 | 2026-05-11 |

---

## 下一步（Next Actions）

按优先级排序，只看最前面 3 条：

1. 🔴 **frontmatter 复杂 YAML 支持** — tags/categories 的 list 格式完善（v0.3 收尾）
2. 🔴 **启动 v0.4：知识库统一** — 设计 OpenClaw wiki 与 Linglong knowledge 的同步协议，定义跨 Agent 知识存储 schema
3. 🔴 **启动 v0.5：ingest 通用化** — 把 ai-morning-brief 抽象为可配置通用引擎，支持 Web Search / 爬虫 / API
4. 🟡 **AI 封面图生成** — 依赖外部 API，需考虑成本和超时
5. 🟡 **dispatch 模块启动** — 将 `_pending_publishers/` 中的发布器正式接入 dispatch

详细计划 → [00-roadmap/v0.3.md](00-roadmap/v0.3.md) | [v1.0 路线图](00-roadmap/v1.0.md)
