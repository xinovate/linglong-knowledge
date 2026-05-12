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
| v0.3 | 人工审核层 | ✅ 已完成 | Draft Mode、Git Workflow Publisher、frontmatter YAML list | 2026-05-12 |
| v0.4 | **知识库统一** | ✅ 已完成 | OpenClaw/Claude Code/Codex 同步、向量搜索落地 | 2026-05-12 |
| v0.5 | **ingest 通用化** | ✅ 已完成 | SourceAdapter、SourcePackage YAML、TruthVerificationEngine、PackageExecutor | 2026-05-12 |
| v0.6 | **多 Agent 接入** | 🟡 部分完成 | Codex 已接入，冲突解决与自动同步待完善 | — |
| v0.7 | composer 产品化 | 🔴 未开始 | 多模板（早报/周报/PPT）、AI 封面图、内容验证 | — |
| v0.8 | **dispatch 正式化** | ✅ 已完成 | DispatchManager、LocalPublisher、HexoPublisher、集成测试 | 2026-05-12 |
| v0.9 | 稳定化 | 🟡 部分完成 | CLI 入口、全链路集成测试、API 冻结待执行 | 2026-05-12 |
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
| DispatchManager（发布器注册/路由/执行） | v0.8 | ✅ | `6b9fc97` | 2026-05-12 |
| LocalPublisher（本地文件输出） | v0.8 | ✅ | `6b9fc97` | 2026-05-12 |
| HexoPublisher（Git/Local 工作流） | v0.8 | ✅ | `6b9fc97` | 2026-05-12 |
| composer → dispatch 集成测试 | v0.8 | ✅ | `6b9fc97` | 2026-05-12 |
| SourceAdapter ABC + AdapterRegistry | v0.5 | ✅ | `4721ec9` | 2026-05-12 |
| SourcePackage YAML 模型 | v0.5 | ✅ | `6b4fab4` | 2026-05-12 |
| TruthVerificationEngine（5 层验证） | v0.5 | ✅ | `e554106` | 2026-05-12 |
| RSS/WebFetch/WebSearch/API Adapters | v0.5 | ✅ | `257cc7e` | 2026-05-12 |
| PackageExecutor（并行执行） | v0.5 | ✅ | `5f6c43d` | 2026-05-12 |
| Composer 自动发布（auto_publish → DispatchManager） | v0.8+ | ✅ | `be08313` | 2026-05-12 |
| 全链路集成测试（ingest→knowledge→composer→dispatch） | v0.9 | ✅ | `b6281e6` | 2026-05-12 |
| CLI 入口（linglong ingest/compose/publish/sync） | v0.9 | ✅ | `4ec1e16` | 2026-05-12 |

---

## 测试覆盖速览

| 模块 | 单元测试 | 集成测试 | E2E | 总评 |
|------|---------|---------|-----|------|
| `core/` | ✅ 10 个 | — | — | ✅ |
| `ingest/` | ✅ 20 个 | ✅ 1 个 | — | ✅ |
| `knowledge/` | ✅ 36 个 | — | — | ✅ |
| `composer/` | ✅ 53 个 | ✅ 1 个 | — | ✅ |
| `dispatch/` | ✅ 8 个 | ✅ 1 个 | — | ✅ |
| `integration/` | — | — | ✅ 1 个 | ✅ |

**图例：** ✅ 已覆盖 / 🔴 空缺（高优） / ⚪ 空缺（低优）

---

## 技术债务 TOP 5

| 问题 | 严重度 | 状态 | 计划版本 | 详情 |
|------|--------|------|----------|------|
| WebSearchAdapter 未实现实际搜索 | 🟡 中 | 待实现 | v0.5+ | DuckDuckGo/Bing CN 搜索需外部依赖 |
| 短期→长期记忆转换未实现 | 🟡 中 | 待实现 | v0.4+ | MEMORY.md 规则：任务完成后自动迁移到 wiki |
| 发布队列与失败重试 | 🟡 中 | 待实现 | v0.8+ | DispatchManager 当前直连发布，无队列和重试 |
| 向量搜索增强（混合搜索/MMR/时间衰减） | 🟡 低 | 待实现 | v0.7 | 当前仅基础 cosine 相似度 |
| `datetime.utcnow()` 已弃用 | 🟡 低 | 待修复 | v0.9 | Pydantic 和 store.py 多处使用，需替换为 timezone-aware |

完整债务清单 → [30-development/tech-debt.md](30-development/tech-debt.md)

---

## 最近 5 次提交

| 提交 | 说明 | 时间 |
|------|------|------|
| `4ec1e16` | feat(cli): add linglong CLI with ingest/compose/publish/sync commands | 2026-05-12 |
| `b6281e6` | test(integration): add end-to-end ingest→knowledge→composer→dispatch test | 2026-05-12 |
| `be08313` | feat(composer): auto-publish dispatch-ready articles via DispatchManager | 2026-05-12 |
| `e54c4d2` | feat(config): extract P0/P1 hardcoded values to config and add AI HOT RSS source | 2026-05-12 |
| `289f33e` | docs(ingest): update modules.md and roadmap for v0.5 generalization | 2026-05-12 |

---

## 下一步（Next Actions）

按优先级排序，只看最前面 3 条：

1. 🟡 **v0.7 启动：composer 产品化** — 多模板（早报/周报/PPT/视频脚本）、AI 封面图
2. 🟡 **v0.6 完善** — 跨 Agent 写入冲突解决、自动同步触发机制
3. 🟡 **WebSearchAdapter 实现** — DuckDuckGo/Bing CN 实际搜索能力（需外部依赖）
4. 🟡 **发布队列与失败重试** — 为 DispatchManager 增加异步队列和重试机制
5. 🟡 **v0.9 收尾** — API 冻结、mypy strict、性能优化、替换 datetime.utcnow() 弃用警告

详细计划 → [00-roadmap/v0.3.md](00-roadmap/v0.3.md) | [v1.0 路线图](00-roadmap/v1.0.md)
