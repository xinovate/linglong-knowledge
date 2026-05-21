# 版本路线图

## 愿景

Linglong 作为所有 AI Agent 的统一知识底座，串联 **信息采集 → 讨论沉淀 → 内容生产 → 多平台分发** 的完整闭环。

## 版本演进

| 版本 | 主题 | 状态 |
|------|------|------|
| v0.1 | 项目骨架 | ✅ |
| v0.2 | core + ingest + knowledge + composer 骨架 | ✅ |
| v0.3 | 人工审核层（Draft Mode + Git Workflow Publisher） | ✅ |
| v0.4 | 知识库统一（向量搜索、OpenClaw wiki 同步、跨 Agent Schema） | ✅ |
| v0.5 | ingest 通用化（RSS/API/WebFetch、验证引擎） | ✅ |
| v0.6 | 多 Agent 接入（Claude Code memory、Codex 同步） | ✅ |
| v0.7 | composer 产品化（LLM 提炼、Prompt 外部化） | ✅ |
| v0.8 | dispatch 正式化（DispatchManager、HexoPublisher、LocalPublisher） | ✅ |
| v0.9 | 稳定化（CLI、集成测试、auto-publish、配置外部化） | ✅ |
| **v1.0** | **模块边界对齐 + 知识库封版** | **进行中** |

## v1.0 目标

各模块按新设计思想对齐边界，知识库封版，其他模块轻量调整。

### 知识库（已封版）

- ✅ MCP Server 9 工具
- ✅ RRF 混合搜索 + 自动模式路由
- ✅ lint 巡检增强（孤儿检测 + 语义去重 + 定期调度）
- ✅ Agent 接入（OpenClaw MCP + Claude Code MCP）
- ✅ CLI kb/pipeline 分组重构
- ✅ 277 测试全通过

### ingest v1.0

- 🟡 解耦 KnowledgeStore：ingest 不再写入知识库，结果返回给调用方
- 🟡 CLI 和 MCP 两种调用方式
- 🟡 清理 `agent:ingest` 数据

### composer v1.0

- 🟡 IngestAdapter 改名为 KnowledgeAdapter
- 🟡 新增 output_log 输出追踪

### dispatch v1.0

- 🟡 新增 output_log 表，发布后记录 entity_id + publisher + published_at

## v2.0 延后项

- WebSearchAdapter 实际搜索
- 发布队列与失败重试
- 多模板（早报/周报/PPT/视频脚本）
- AI 封面图生成
- 跨 Agent 写入冲突解决
- API 冻结、mypy strict

---

## 关键架构决策

### ADR-001: Linglong 作为跨 Agent 知识中枢

**决策**: 所有 Agent 通过 KnowledgeStore 统一读写，各自维护独立知识库但通过 Linglong 同步。

### ADR-002: 知识库同步方向

**决策**: 采用 Pull 模式 — Linglong 主动从各 Agent 知识库拉取，而非 Agent 推送到 Linglong。

### ADR-003: 向量搜索双模式

**决策**: 远程 embedding 服务（OpenClaw）+ 本地 sqlite-vec fallback。

### ADR-004: Agent 命名空间前缀

**决策**: Entity 的 `created_by` 字段使用 `agent:xxx` 前缀标识来源。

### ADR-005: Memory 类型映射

**决策**: 各 Agent 的 memory 类型统一映射为 Linglong Entity，保留原始类型信息在 metadata 中。

### ADR-006: ingest 不写知识库（v1.0）

**决策**: ingest 是信息采集工具，采集结果返回给调用方（CLI/MCP/对话），不直接写入 KnowledgeStore。只有人和 Agent 讨论沉淀后的内容才写入知识库。
- **原因**: 知识库的价值在于经过思考沉淀的知识。原始 RSS/API 数据未经验证，直接入库会稀释知识库质量。
- **影响**: `agent:ingest` 作为 created_by 不再存在。数据进入知识库的唯一途径是 Agent 写入（MCP/CLI）或从其他知识库迁移。

### ADR-007: entity 输出追踪 output_log（v1.0）

**决策**: composer + dispatch 发布后，在知识库 SQLite 的 `output_log` 表中记录 entity_id + publisher + published_at。
- **原因**: 避免 composer 重复消费同一批知识产出重复内容。
- **影响**: composer 读取知识库时可跳过已输出的 entity。支持追溯"这篇文章用了哪些知识"。

### ADR-008: 移除 pipeline 子命令分组（v1.0）

**决策**: 移除 `linglong pipeline` 子命令分组。`ingest`、`compose`、`publish` 改为顶层命令。
- **原因**: ingest 与知识库解耦后不再是流水线的一环，中间环节需要人为介入，pipeline 概念不再适用。
- **影响**: `linglong pipeline ingest` → `linglong ingest`，`linglong pipeline compose` → `linglong compose`，`linglong pipeline publish` → `linglong publish`。

---

## 关键架构决策

### ADR-001: Linglong 作为跨 Agent 知识中枢

**决策**: 所有 Agent 通过 KnowledgeStore 统一读写，各自维护独立知识库但通过 Linglong 同步。

### ADR-002: 知识库同步方向

**决策**: 采用 Pull 模式 — Linglong 主动从各 Agent 知识库拉取，而非 Agent 推送到 Linglong。

### ADR-003: 向量搜索双模式

**决策**: 远程 embedding 服务（OpenClaw）+ 本地 sqlite-vec fallback。

### ADR-004: Agent 命名空间前缀

**决策**: Entity 的 `created_by` 字段使用 `agent:xxx` 前缀标识来源。

### ADR-005: Memory 类型映射

**决策**: 各 Agent 的 memory 类型统一映射为 Linglong Entity，保留原始类型信息在 metadata 中。
