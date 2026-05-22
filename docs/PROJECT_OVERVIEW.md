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

| 版本 | 目标 | 关键交付 | 状态 | 完成时间 |
|------|------|---------|------|----------|
| v0.1 | MVP 骨架 | core + ingest + knowledge 三模块 | ✅ | 2025-04 |
| v0.2 | Composer 迁移 | Composer + LLM Distiller + DailyAggregator + Draft Mode | ✅ | 2026-05-12 |
| v0.3 | 人工审核层 | Git Workflow Publisher + frontmatter YAML | ✅ | 2026-05-12 |
| v0.4 | 知识库统一 | 三 Agent SyncAdapter + 向量搜索 + embedding | ✅ | 2026-05-12 |
| v0.5 | ingest 通用化 | SourceAdapter + SourcePackage + 真值验证 + 多源适配器 | ✅ | 2026-05-12 |
| v0.6 | 多 Agent 接入 | OpenClaw/Claude Code/Codex 三种适配器 | ✅ | 2026-05-12 |
| v0.7 | composer 产品化 | 多模板/封面图/内容验证 | 🟠 延后至 v2.0 | — |
| v0.8 | dispatch 正式化 | DispatchManager + LocalPublisher + HexoPublisher | ✅ | 2026-05-12 |
| v0.9 | 稳定化 | CLI 入口 + 全链路集成测试 | ✅ | 2026-05-12 |
| **v1.0** | **知识库封版** | MCP 9 工具 + RRF 混合搜索 + lint 巡检 + 6 facet + group + DB 先行 + kb sync（276 测试） | ✅ | 2026-05-22 |
| **v1.2** | **ingest 早报** | SearXNG 搜索 + AIHOT 适配器 + 多源聚合 + LLM 解读 + 晨报模板 + 339 测试 | ✅ | 2026-05-22 |
| **v2.0** | **产品化** | 发布队列 + 多模板 + API 冻结 | 🔴 未开始 | — |

---

## 测试覆盖速览

| 模块 | 单元测试 | 集成测试 | E2E | 总评 |
|------|---------|---------|-----|------|
| `core/` | ✅ 25 个 | — | — | ✅ |
| `ingest/` | ✅ 28 个 | ✅ 1 个 | — | ✅ |
| `knowledge/` | ✅ 102 个 | — | — | ✅ |
| `composer/` | ✅ 63 个 | ✅ 1 个 | — | ✅ |
| `dispatch/` | ✅ 19 个 | ✅ 1 个 | — | ✅ |
| `mcp/` | ✅ 20 个 | — | — | ✅ |
| `cli/` | ✅ 26 个 | — | — | ✅ |
| `integration/` | — | — | ✅ 2 个 | ✅ |

**总计：339 个测试**

**图例：** ✅ 已覆盖 / 🔴 空缺（高优） / ⚪ 空缺（低优）

---

## 技术债务 TOP 5

| 问题 | 严重度 | 状态 | 计划版本 | 详情 |
|------|--------|------|----------|------|
| ~~WebSearchAdapter 未实现实际搜索~~ | ~~🟡 中~~ | ✅ 已完成 | v1.2 | SearXNG + ZhiPu + Google + Bing CN 四后端 |
| 发布队列与失败重试 | 🟡 中 | 待实现 | v2.0 | DispatchManager 当前直连发布，无队列和重试 |
| `datetime.utcnow()` 已弃用 | ~~🟡 低~~ | ✅ 已修复 | v1.0 | 全局替换为 `datetime.now(UTC)`，276 测试通过 |
| MCP Server 读写接入 | ~~🟡 中~~ | ✅ 已完成 | v1.0 | 9 个 MCP 工具，Claude Code + OpenClaw 已接入 |
| 向量搜索增强（混合搜索/自动模式） | ~~🟡 低~~ | ✅ 已完成 | v1.0 | RRF 混合搜索 + 自动模式路由，276 测试通过 |
| OpenClaw MCP 集成 | ~~🟡 中~~ | ✅ 已完成 | v1.0 | Phase 0-2 验证通过，MCP CRUD 全链路可用 |
| LIMIT-001 frontmatter 解析失败 | ~~🟡 低~~ | ✅ 已修复 | v1.0 | 2 个文件修复为标准 frontmatter 格式 |

完整债务清单 → [operations.md](operations.md)

---

## 最近 5 次提交

| 提交 | 说明 | 时间 |
|------|------|------|
| `898a343` | feat(knowledge): DB先行写入 + embedding hash守卫 + kb sync | 2026-05-22 |
| `1dc5070` | refactor(knowledge): facet 重分类 7→6 + Entity.group 子目录 | 2026-05-22 |
| `3efed72` | chore: 配置示例 + 清理测试 + 待办更新 | 2026-05-21 |
| `06cf341` | docs: 日志 #17 CLI 重构，PROJECT_OVERVIEW 更新 | 2026-05-21 |
| `47e3440` | docs: CLI 命令迁移到 kb/pipeline 分组格式（24 文件） | 2026-05-21 |
| `23fefcd` | refactor(cli): 子命令分组重构 — kb + pipeline | 2026-05-21 |

---

## 下一步（Next Actions）

按优先级排序：

1. ✅ ~~**v1.0 端到端验证**~~ — ingest → compose → publish 16 篇文章输出正常
2. ✅ ~~**模块边界设计重构**~~ — ingest 不写知识库、output_log、pipeline 移除、9 份文档更新
3. ✅ ~~**BACKLOG-005 facet 重分类**~~ — 7→6 分面 + group 子目录，142 条 LLM 辅助迁移，276 测试通过
4. ✅ ~~**ingest v1.2 早报能力**~~ — SearXNG + AIHOT + 多源聚合 + LLM 解读 + 晨报模板，339 测试通过
5. 🟡 **OpenClaw 观察期收尾** — 确认 MCP 写入质量，禁用 wiki-maintainer，清理旧数据
6. 🔴 **Codex CLI 接入** — 当前仅预留，尚未实际接入
7. 🟡 **拥挤 facet 根目录清理** — concept(9)、methodology(10)、project(7) 根目录仍有未分组条目

**v2.0 延后项**（非阻塞）：
- ~~WebSearchAdapter 实际搜索~~ ✅ v1.2 完成
- 发布队列与失败重试
- 多模板（周报/PPT/视频脚本）
- AI 封面图生成
- 跨 Agent 写入冲突解决
- 多 Agent 更新合并（需交互式 UI）
- Agent hooks 自动同步（需 Agent 侧配合）
- API 冻结、mypy strict

详细计划 → [版本路线图](roadmap.md)
