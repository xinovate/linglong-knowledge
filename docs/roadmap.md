# 版本路线图

Linglong Knowledge — 跨 Agent 统一知识库的版本演进记录。

## 当前状态

v2.6 已完成。ingest 拆为独立项目 linglong-scout，reviewer/dispatch 移至博客项目。本项目专注知识库核心。

## 版本演进

| 版本 | 主题 | 状态 |
|------|------|------|
| v0.1–v0.9 | MVP 骨架：core + knowledge + CLI + 集成测试 | ✅ |
| v1.0 | 知识库封版：MCP 9 工具 + RRF 混合搜索 + lint 巡检 + 6 facet + group | ✅ |
| v2.3 | 安全加固 + MCP 增强：API Key 认证 + MCP 工具扩展 | ✅ |
| v2.4 | Agent 接入：Claude Code MCP 连通 + GitHub auth | ✅ |
| v2.5 | 并发 + 缓存 + MCP 远程部署 | ✅ |
| v2.6 | MCP 远程上线 + 模块拆分 | ✅ |

## 下一步工作

| # | 任务 | 优先级 | 说明 |
|---|------|--------|------|
| 1 | 拥挤 facet 根目录清理 | 🟡 | concept/methodology/project 根目录未分组条目 |
| 2 | Codex CLI 接入 | 🔴 | 当前仅预留 CodexSyncAdapter，未实际接入 |
| 3 | 跨 Agent 写入冲突解决 | 低 | 多 Agent 同时修改同一 wiki |
| 4 | API 冻结 + mypy strict | 低 | 稳定公开接口 |

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

**决策**: ingest 是信息采集工具，采集结果返回给调用方，不直接写入 KnowledgeStore。
- **原因**: 知识库的价值在于经过思考沉淀的知识。原始数据未经验证，直接入库会稀释质量。
- **现状**: ingest 已拆为独立项目 linglong-scout。

### ADR-007: 模块拆分为独立项目（v2.6）

**决策**: ingest 拆为 linglong-scout，reviewer/dispatch 移至博客项目。本项目（linglong-knowledge）只保留知识库核心。
- **原因**: 各模块职责清晰，独立迭代更高效。知识库是核心底座，采集和发布是外围功能。
- **影响**: 本项目只含 core + knowledge + mcp 三个包，167 个测试。

### ADR-008: 三层存储（Filesystem + SQLite + sqlite-vec）

**决策**: 知识库采用三层存储：Markdown 文件（人类可读 + Git 友好）+ SQLite（元数据查询）+ sqlite-vec（语义搜索）。
- **原因**: 各层互补——文件层便于手动编辑和 Git 版本控制，SQLite 层支持结构化查询和关系图谱，向量层支持语义搜索。

### ADR-009: Review 引擎基于规则而非 LLM

**决策**: 知识库内的 ReviewEngine 用可配置规则（置信度阈值、来源可信度、敏感词检测）而非 LLM 调用。
- **原因**: 规则引擎响应快、确定性高、无 API 成本。LLM 评审适合博客项目的高级文章评审，不适合知识库每次写入都触发。

### ADR-010: MCP 双路径部署（stdio + streamable-http）

**决策**: 本地 Agent 通过 stdio 子进程连接，远程 Agent 通过 streamable-http + Cloudflare Tunnel 连接。
- **原因**: stdio 是 MCP 标准本地模式，零配置。远程需要 HTTP + Token 认证。
- **影响**: `mcp.transport` 配置切换模式，`server.py` 提供 `create_server()` 和 `create_http_app()` 两个入口。
