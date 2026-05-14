# 知识库设计文档创建计划

> 创建日期：2026-05-14
> 状态：进行中

## Context

Linglong knowledge 模块需要一套完整的设计文档，融合两个来源：
- **OpenClaw wiki**（实践验证，13 目录，70+ 篇文章，但不够系统）
- **LLM-Wiki 参考设计**（系统化框架，四层架构，但未经实践验证）

核心架构决策：**Linglong 替代 OpenClaw wiki**，成为所有 Agent 的唯一知识源。Agent 通过 CLI 工具接入。

## 决策汇总

| 决策 | 结论 |
|------|------|
| 知识库架构 | Linglong 替代 OpenClaw wiki，单一知识源 |
| Agent 接入 | CLI 工具（linglong search/read/write/review/lint/index/migrate/stats） |
| 写入方式 | 默认提示确认，CLI `--yes` 跳过确认，配置 `write_mode` |
| 查询方式 | 默认按需查询，CLI `--deep` 返回结果+自动加载完整内容，配置 `search_mode` |
| 索引生成 | 默认写入时自动更新，CLI `--no-index` 跳过，配置 `auto_index`，`linglong index --rebuild` 手动重建 |
| 目录结构 | 方案 C（混合）— 顶层 facet + 子目录保留 OpenClaw 命名 |
| Facet 分类 | 7 个：source / entity / concept / synthesis / experience / methodology / personal |
| 文档深度 | 设计为主，留编码灵活度 |
| 备份机制 | Git 方案后续再做 |

## 默认值 + CLI 覆盖模式

优先级：CLI 参数 > 配置文件 (.linglong.yaml) > 硬编码默认值

| 参数 | 默认值 | 配置文件 key | CLI 覆盖 | 适用场景 |
|------|--------|-------------|----------|----------|
| 写入模式 | `confirm` | `knowledge.write_mode` | `--yes` | 批量导入时跳过确认 |
| 查询模式 | `on_demand` | `knowledge.search_mode` | `--deep` | 需要完整上下文时 |
| 索引更新 | `auto` | `knowledge.auto_index` | `--no-index` | 批量写入时跳过索引更新 |

## 设计文档清单

详见 `docs/knowledge/design/` 目录：
1. `00-overview.md` — 全局架构
2. `01-data-model.md` — 数据模型
3. `02-directory-structure.md` — 目录结构
4. `03-write-path.md` — 写入设计
5. `04-search.md` — 搜索设计
6. `05-lint.md` — 巡检设计
7. `06-agent-integration.md` — Agent 接入
