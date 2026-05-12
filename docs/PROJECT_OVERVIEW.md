# 项目总览

> 本文档是 linglong 项目的**单一真相源**，汇总版本、功能、测试、债务四大维度。
> 每天打开项目，先看这一页。

---

## 版本进度

| 版本 | 目标 | 状态 | 关键交付 | 完成时间 |
|------|------|------|---------|----------|
| v0.1 | MVP 骨架 | ✅ 已完成 | core + ingest + knowledge 三模块骨架 | 2025-04 |
| v0.2 | Composer 迁移 | ✅ 已完成 | Composer 从 linglong-pipeline 迁移并入，32 个测试通过 | 2026-05-12 |
| v0.3 | 人工审核层 | 🟡 进行中 | Draft Mode（已完成）、Git Workflow Publisher（已完成）、AI 封面图生成 | — |

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

---

## 测试覆盖速览

| 模块 | 单元测试 | 集成测试 | E2E | 总评 |
|------|---------|---------|-----|------|
| `core/` | ❌ 待补充 | — | — | 🔴 高优 |
| `ingest/` | ❌ 待补充 | — | — | 🔴 高优 |
| `knowledge/` | ✅ 部分覆盖 | — | — | 🟡 进行中 |
| `composer/` | ✅ 32 个 | — | — | ✅ |
| `dispatch/` | ❌ 未开始 | — | — | ⚪ 低优 |

**图例：** ✅ 已覆盖 / 🔴 空缺（高优） / ⚪ 空缺（低优）

---

## 技术债务 TOP 5

| 问题 | 严重度 | 状态 | 计划版本 | 详情 |
|------|--------|------|----------|------|
| 缺少 lint / format 工具 | 🟡 中 | 待引入 | v0.3 | `pyproject.toml` 待配置 ruff / mypy |
| `tests/core/` 和 `tests/ingest/` 为空 | 🟡 中 | 待补充 | v0.3 | — |
| frontmatter 不支持复杂 YAML list | 🟡 中 | 待修复 | v0.3 | `templates/blog.py` |
| LLM Prompt 硬编码在 Python 中 | 🟡 低 | 待外部化 | v0.3 | `distiller/llm_distiller.py` |
| Composer State 使用 content_hash 而非 entity_id | 🟡 低 | 待升级 | v0.3 | `state.py` |

完整债务清单 → [30-development/tech-debt.md](30-development/tech-debt.md)

---

## 最近 5 次提交

| 提交 | 说明 | 时间 |
|------|------|------|
| `8692188` | SSH 远程触发和文档同步 | 2026-05-12 |
| `54f0dc2` | Git Workflow Publisher：含代理支持 | 2026-05-11 |
| `4600e04` | Composer 集成测试 + State 隔离 bug 修复 | 2026-05-11 |
| `4a95b11` | 修复技术债务：标题长度 50→18、分隔符冲突 | 2026-05-11 |
| `b4b9083` | 新增 PROJECT_OVERVIEW.md 单一真相源看板 | 2026-05-11 |

---

## 下一步（Next Actions）

按优先级排序，只看最前面 3 条：

1. 🔴 **补充 core 和 ingest 模块测试** — 当前 `tests/core/` 和 `tests/ingest/` 为空，需建立基础测试骨架
2. 🔴 **引入 lint / format 工具** — ruff / mypy 配置，保证代码风格一致性
3. 🟡 **LLM Prompt 外部化** — 将 `llm_distiller.py` 中的 Prompt 提取到 `assets/prompts/` 目录
4. 🟡 **frontmatter 复杂 YAML 支持** — tags/categories 的 list 格式完善
5. 🟡 **dispatch 模块启动** — 将 `_pending_publishers/` 中的发布器正式接入 dispatch

详细计划 → [00-roadmap/v0.3.md](00-roadmap/v0.3.md)
