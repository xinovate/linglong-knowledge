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
| **v1.3** | **ingest 信源增强** | ArXiv/GitHub/RSS 信源 + LLM 动态标签 + 反馈闭环 | ✅ | 2026-05-23 |
| **v2.0** | **IngestAgent 重构** | LLM Agent 单 prompt 早报 + GitHub Trending 多源 + BriefHistory 去重 + 394 测试 | ✅ | 2026-05-25 |
| **v2.1** | **RSS 数据源** | 6 个 RSS 订阅源 + 交叉去重 + 时效过滤 + 394 测试 | ✅ | 2026-05-25 |
| **v2.2** | **ingest 增强 + 清理** | 融资快照 + 关键人物扩展 + 8 RSS + 健康监控 + LLM 容错 + 去重量化 + legacy 清理（-4164 行）+ 321 测试 | ✅ | 2026-05-25 |

---

## 测试覆盖速览

| 模块 | 单元测试 | 集成测试 | E2E | 总评 |
|------|---------|---------|-----|------|
| `core/` | ✅ 25 个 | — | — | ✅ |
| `ingest/` | ✅ 36 个 | — | — | ✅ |
| `knowledge/` | ✅ 102 个 | — | — | ✅ |
| `composer/` | ✅ 63 个 | ✅ 1 个 | — | ✅ |
| `dispatch/` | ✅ 19 个 | ✅ 1 个 | — | ✅ |
| `mcp/` | ✅ 20 个 | — | — | ✅ |
| `cli/` | ✅ 26 个 | — | — | ✅ |
| `integration/` | — | — | ✅ 1 个 | ✅ |

**总计：321 个测试**

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
| `2cf2d50` | refactor(ingest): 清理 IngestConfig + .linglong.yaml 精简 | 2026-05-25 |
| `a5d8fdf` | refactor(ingest): 移除 v1.x legacy 代码（-4164 行） | 2026-05-25 |
| `e938736` | test(ingest): 新增 13 个测试 — 快照/健康/重试/fallback/去重 | 2026-05-25 |
| `2d0833d` | feat(ingest): 信源健康监控 + LLM 容错 + 去重量化 | 2026-05-25 |
| `268e616` | feat(ingest): 公司融资快照 + 关键人物扩展 + 更多 RSS 源 | 2026-05-25 |

---

## 下一步（Next Actions）

按优先级排序：

1. ✅ ~~**v1.0 端到端验证**~~ — ingest → compose → publish 16 篇文章输出正常
2. ✅ ~~**模块边界设计重构**~~ — ingest 不写知识库、output_log、pipeline 移除、9 份文档更新
3. ✅ ~~**BACKLOG-005 facet 重分类**~~ — 7→6 分面 + group 子目录，142 条 LLM 辅助迁移，276 测试通过
4. ✅ ~~**ingest v1.2 早报能力**~~ — SearXNG + AIHOT + 多源聚合 + LLM 解读 + 晨报模板，339 测试通过
5. ✅ ~~**ingest v2.0 IngestAgent 重构**~~ — LLM Agent 单 prompt 早报 + GitHub Trending + BriefHistory 去重，394 测试通过
6. ✅ ~~**ingest v2.1 RSS 数据源**~~ — 6 个 RSS 订阅源 + 交叉去重 + 时效过滤，394 测试通过
7. ✅ ~~**ingest v2.2 增强**~~ — 公司融资快照 + 关键人物扩展 + 8 RSS 源 + 信源健康 + LLM 容错 + 去重量化，407 测试通过
8. 🟡 **OpenClaw 观察期收尾** — 确认 MCP 写入质量，禁用 wiki-maintainer，清理旧数据
9. 🔴 **Codex CLI 接入** — 当前仅预留，尚未实际接入
10. 🟡 **拥挤 facet 根目录清理** — concept(9)、methodology(10)、project(7) 根目录仍有未分组条目

**v2.3 收尾项**（非阻塞）：
- 发布队列与失败重试
- 多模板（周报/PPT/视频脚本）
- AI 封面图生成
- 跨 Agent 写入冲突解决
- API 冻结 + mypy strict

详细计划 → [版本路线图](roadmap.md)
