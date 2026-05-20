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
| **v1.0** | **博客流水线** | 🟡 开发中 | 多尺寸响应式图片、OSS CDN 上传、URL 列表驱动、随机选择+去重 | — |
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

---

## 测试覆盖速览

| 模块 | 单元测试 | 集成测试 | E2E | 总评 |
|------|---------|---------|-----|------|
| `core/` | ✅ 10 个 | — | — | ✅ |
| `ingest/` | ✅ 20 个 | ✅ 1 个 | — | ✅ |
| `knowledge/` | ✅ 36 个 | — | — | ✅ |
| `composer/` | ✅ 63 个 | ✅ 1 个 | — | ✅ |
| `dispatch/` | ✅ 20 个 | ✅ 1 个 | — | ✅ |
| `mcp/` | ✅ 16 个 | — | — | ✅ |
| `integration/` | — | — | ✅ 1 个 | ✅ |

**图例：** ✅ 已覆盖 / 🔴 空缺（高优） / ⚪ 空缺（低优）

---

## 技术债务 TOP 5

| 问题 | 严重度 | 状态 | 计划版本 | 详情 |
|------|--------|------|----------|------|
| WebSearchAdapter 未实现实际搜索 | 🟡 中 | 待实现 | v2.0 | DuckDuckGo/Bing CN 搜索需外部依赖 |
| 短期→长期记忆转换未实现 | 🟡 中 | 待实现 | v2.0 | MEMORY.md 规则：任务完成后自动迁移到 wiki |
| 发布队列与失败重试 | 🟡 中 | 待实现 | v2.0 | DispatchManager 当前直连发布，无队列和重试 |
| 向量搜索增强（混合搜索/MMR/时间衰减） | 🟡 低 | 待实现 | v2.0 | 当前仅基础 cosine 相似度 |
| `datetime.utcnow()` 已弃用 | ~~🟡 低~~ | ✅ 已修复 | v1.0 | 全局替换为 `datetime.now(UTC)`，237 测试通过 |
| MCP Server 读写接入 | 🟡 中 | ✅ 已完成 | v1.0 | Claude Code 通过 MCP 工具查询/写入知识库 |

完整债务清单 → [operations.md](operations.md)

---

## 最近 5 次提交

| 提交 | 说明 | 时间 |
|------|------|------|
| `715d3c6` | feat(composer): add image asset pipeline and .linglong.yaml config support | 2026-05-13 |
| `7ce12fc` | docs: sync PROJECT_OVERVIEW, modules.md, v1.0 roadmap for pipeline completion | 2026-05-12 |
| `4ec1e16` | feat(cli): add linglong CLI with ingest/compose/publish/sync commands | 2026-05-12 |
| `b6281e6` | test(integration): add end-to-end ingest→knowledge→composer→dispatch test | 2026-05-12 |
| `be08313` | feat(composer): auto-publish dispatch-ready articles via DispatchManager | 2026-05-12 |

> 本地未提交变更：多尺寸图片管线、OSS CDN 上传、响应式 HTML 输出、命名一致性修复

---

## 下一步（Next Actions）

按优先级排序：

1. ✅ **v1.0 配图系统** — ImageAssetFetcher + ImageAssetSelector + PageImageResolver 已集成
2. ✅ **v1.0 多尺寸图片** — thumb/medium/large 变体生成 + 响应式 srcset 输出
3. ✅ **v1.0 OSS CDN** — OSSUploader 阿里云图片上传 + CDN URL 替换
4. ✅ **v1.0 文档更新** — CLAUDE.md、README.md、docs 重组、tech-debt 等已同步
5. 🟡 **v1.0 端到端验证** — 跑通完整链路：sync → ingest → compose → publish（管道已通，内容质量待改进）

**v2.0 延后项**（非阻塞）：
- WebSearchAdapter 实际搜索
- 发布队列与失败重试
- 多模板（早报/周报/PPT/视频脚本）
- AI 封面图生成
- 跨 Agent 写入冲突解决
- API 冻结、mypy strict（datetime.utcnow() 已修复）
- MCP Server 扩展更多工具（update_entity、delete_entity）

详细计划 → [版本路线图](roadmap.md)
