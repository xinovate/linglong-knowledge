# 项目总览

> 本文档是 linglong-knowledge 项目的**单一真相源**，汇总版本、功能、测试、债务四大维度。
> 每天打开项目，先看这一页。

---

## 项目定位

Linglong Knowledge 是**跨 Agent 统一知识库**，为 OpenClaw、Claude Code、Codex 等 AI Agent 提供共享知识底座。

**核心问题**：多个 AI Agent 各自维护独立的知识库，互不相通。同一个概念，OpenClaw 知道，Claude Code 不知道。

**解决方案**：统一知识库 + MCP 接口，所有 Agent 通过同一套 API 读写知识。

```
OpenClaw ──┐
Claude Code ┼──→ Knowledge Store ←── MCP Server
Codex ──────┘     (File + SQLite + sqlite-vec)
```

相关项目：
- **linglong-scout**（独立仓库）：信息采集，结果返回给对话，不写知识库
- **博客项目**：文章评审和发布

---

## 版本进度

| 版本 | 目标 | 关键交付 | 状态 |
|------|------|---------|------|
| v0.1–v0.9 | MVP 骨架 | core + knowledge 三层存储 + CLI + 集成测试 | ✅ |
| v1.0 | 知识库封版 | MCP 9 工具 + RRF 混合搜索 + lint 巡检 + 6 facet + group + DB 先行 + kb sync | ✅ |
| v2.3 | 安全加固 + MCP 增强 | 3 服务 API Key 认证 + nginx 反代 SearXNG + MCP 工具 | ✅ |
| v2.4 | Agent 接入 | Claude Code MCP 连通 + RSSHub key 修复 + GitHub auth | ✅ |
| v2.5 | 并发 + 缓存 + MCP 远程部署 | 三路并发 + 日内缓存 + streamable-http + Token 认证 + systemd | ✅ |
| v2.6 | MCP 远程上线 + 模块拆分 | MCP 双路径路由 + Redis Token + Cloudflare Tunnel + ingest 拆为 linglong-scout + reviewer/dispatch 移至博客项目 | ✅ |

历史版本详情 → [版本路线图](roadmap.md)

---

## 测试覆盖速览

| 模块 | 测试数 | 说明 |
|------|--------|------|
| `core/` | 20 | 模型、配置 |
| `knowledge/` | 102 | store、review、embeddings、indexer、lint、sync、wikilinks、lock |
| `mcp/` | 20 | server、tools |
| `cli` | 22 | CLI 子命令 |
| `integration/` | 1 | 端到端 |
| **总计** | **167** | |

**图例：** ✅ 已覆盖 / 🔴 空缺（高优） / ⚪ 空缺（低优）

---

## 技术债务

| 问题 | 严重度 | 状态 | 详情 |
|------|--------|------|------|
| 发布队列与失败重试 | 🟡 中 | 待实现 | 博客项目负责 |
| OpenClaw MCP 集成 | ~~🟡 中~~ | ✅ 已完成 | Phase 0-2 验证通过 |
| 向量搜索增强（混合搜索/自动模式） | ~~🟡 低~~ | ✅ 已完成 | RRF 混合搜索 + 自动模式路由 |

完整债务清单 → [operations.md](operations.md)

---

## 下一步（Next Actions）

1. 🟡 **拥挤 facet 根目录清理** — concept(9)、methodology(10)、project(7) 根目录仍有未分组条目
2. 🟡 **Codex CLI 接入** — 当前仅预留 CodexSyncAdapter，尚未实际接入
3. 🔵 **文档体系收尾** — 确保 docs/ 所有文档与代码一致

详细计划 → [版本路线图](roadmap.md)
