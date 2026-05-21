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
| v0.6 | **多 Agent 接入** | ✅ 已完成 | OpenClaw/Claude Code/Codex 三种 SyncAdapter 已实现 | 2026-05-12 |
| v0.7 | composer 产品化 | 🟠 v2.0 | 多模板（早报/周报/PPT）、AI 封面图、内容验证 | — |
| v0.8 | **dispatch 正式化** | ✅ 已完成 | DispatchManager、LocalPublisher、HexoPublisher、集成测试 | 2026-05-12 |
| v0.9 | 稳定化 | ✅ 已完成 | CLI 入口、全链路集成测试、composer→dispatch 流水线 | 2026-05-12 |
| **v1.0** | **博客流水线 + 知识库成熟** | 🟡 收官中 | MCP Server 9 工具、RRF 混合搜索、lint 巡检增强、Agent 接入、图片管线、OSS CDN | — |
| **v2.0** | **产品化** | 🔴 未开始 | WebSearchAdapter、发布队列与重试、多模板、AI 封面图、API 冻结 | — |

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
| 多尺寸响应式图片（thumb/medium/large 变体生成） | v1.0 | ✅ | — | 2026-05-13 |
| BlogTemplate 响应式 `<img srcset>` 输出 | v1.0 | ✅ | — | 2026-05-13 |
| OSSUploader（阿里云 OSS 图片 CDN 上传） | v1.0 | ✅ | — | 2026-05-13 |
| DispatchManager OSS 上传集成 | v1.0 | ✅ | — | 2026-05-13 |
| background/background_image 命名一致性修复 | v1.0 | ✅ | — | 2026-05-13 |
| MCP Server（Claude Code 读写接入） | v1.0 | ✅ | `0c285f2` | 2026-05-20 |
| MCP search_and_read + update_entity 工具 | v1.0 | ✅ | — | 2026-05-20 |
| MCP 搜索返回质量优化（summary 优先 + 500 字符） | v1.0 | ✅ | — | 2026-05-20 |
| MCP 模板体系（9 个 facet 模板 + get_template） | v1.0 | ✅ | — | 2026-05-20 |
| 文件名格式 slug-ID 后缀调整 | v1.0 | ✅ | `8b7a84f` | 2026-05-20 |
| Lint 巡检增强（孤儿检测 + 语义去重 + 定期调度 + --check 过滤） | v1.0 | ✅ | `2ab07ec` | 2026-05-21 |
| RRF 混合搜索 + 自动模式路由 + 变动日志增强 | v1.0 | ✅ | `e10403b` | 2026-05-21 |
| OpenClaw MCP 集成 Phase 0-2（extraPaths + MCP CRUD + 配置迁移） | v1.0 | ✅ | `0c79114` | 2026-05-21 |
| Agent 三方接入指南（快速/深度/移除） | v1.0 | ✅ | `0c79114` | 2026-05-21 |
| OpenClawSyncAdapter 移除 memory 模式（只保留 wiki 同步） | v1.0 | ✅ | `e10403b` | 2026-05-21 |
| index --rebuild 增加向量化重建 | v1.0 | ✅ | `e10403b` | 2026-05-21 |
| v1.0 端到端验证（ingest → compose → publish 16 篇） | v1.0 | ✅ | — | 2026-05-21 |
| write --force + update --from-file | v1.0 | ✅ | `b657ec3` | 2026-05-21 |
| 设计文档审计对齐（D-03~D-10 全部 ✅） | v1.0 | ✅ | `b657ec3` | 2026-05-21 |

---

## 测试覆盖速览

| 模块 | 单元测试 | 集成测试 | E2E | 总评 |
|------|---------|---------|-----|------|
| `core/` | ✅ 25 个 | — | — | ✅ |
| `ingest/` | ✅ 20 个 | ✅ 1 个 | — | ✅ |
| `knowledge/` | ✅ 102 个 | — | — | ✅ |
| `composer/` | ✅ 63 个 | ✅ 1 个 | — | ✅ |
| `dispatch/` | ✅ 19 个 | ✅ 1 个 | — | ✅ |
| `mcp/` | ✅ 20 个 | — | — | ✅ |
| `cli/` | ✅ 26 个 | — | — | ✅ |
| `integration/` | — | — | ✅ 2 个 | ✅ |

**总计：277 个测试**

**图例：** ✅ 已覆盖 / 🔴 空缺（高优） / ⚪ 空缺（低优）

---

## 技术债务 TOP 5

| 问题 | 严重度 | 状态 | 计划版本 | 详情 |
|------|--------|------|----------|------|
| WebSearchAdapter 未实现实际搜索 | 🟡 中 | 待实现 | v2.0 | DuckDuckGo/Bing CN 搜索需外部依赖 |
| 发布队列与失败重试 | 🟡 中 | 待实现 | v2.0 | DispatchManager 当前直连发布，无队列和重试 |
| `datetime.utcnow()` 已弃用 | ~~🟡 低~~ | ✅ 已修复 | v1.0 | 全局替换为 `datetime.now(UTC)`，277 测试通过 |
| MCP Server 读写接入 | ~~🟡 中~~ | ✅ 已完成 | v1.0 | 9 个 MCP 工具，Claude Code + OpenClaw 已接入 |
| 向量搜索增强（混合搜索/自动模式） | ~~🟡 低~~ | ✅ 已完成 | v1.0 | RRF 混合搜索 + 自动模式路由，277 测试通过 |
| OpenClaw MCP 集成 | ~~🟡 中~~ | ✅ 已完成 | v1.0 | Phase 0-2 验证通过，MCP CRUD 全链路可用 |

完整债务清单 → [operations.md](operations.md)

---

## 最近 5 次提交

| 提交 | 说明 | 时间 |
|------|------|------|
| `b657ec3` | feat(cli): write --force + update --from-file；设计文档审计对齐 | 2026-05-21 |
| `343b698` | docs: 合并 tracking/ 到 journal + design，更新 PROJECT_OVERVIEW | 2026-05-21 |
| `e10403b` | feat(search): RRF 混合搜索 + 自动模式，变动日志增强，SyncAdapter 精简 | 2026-05-21 |
| `aab2cce` | docs(knowledge): 新增知识库定位与边界、Agent 接入概述 | 2026-05-21 |
| `0c79114` | docs(agents): OpenClaw Phase 0+2 验证记录、三方接入指南、文档规整 | 2026-05-21 |

---

## 下一步（Next Actions）

按优先级排序：

1. ✅ ~~**v1.0 端到端验证**~~ — ingest → compose → publish 16 篇文章输出正常
2. 🟡 **OpenClaw 观察期收尾** — 确认 MCP 写入质量，禁用 wiki-maintainer，清理旧数据
3. 🔴 **Codex CLI 接入** — 当前仅预留，尚未实际接入

**v2.0 延后项**（非阻塞）：
- WebSearchAdapter 实际搜索
- 发布队列与失败重试
- 多模板（早报/周报/PPT/视频脚本）
- AI 封面图生成
- 跨 Agent 写入冲突解决
- 多 Agent 更新合并（需交互式 UI）
- Agent hooks 自动同步（需 Agent 侧配合）
- API 冻结、mypy strict

详细计划 → [版本路线图](roadmap.md)
