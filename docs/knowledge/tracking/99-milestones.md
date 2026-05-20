# 开发里程碑

| 属性 | 值 |
|------|-----|
| 分类 | 方向锚点 |
| 定位 | 阶段里程碑和当前状态。不记录具体任务（去 `97-tasks.md`）、长期规划细节（去 `98-backlog.md`）、已完成工作（去 `journal/`）。 |
| 用途 | AI 会话压缩后阅读本文档可快速恢复项目上下文，避免方向分叉 |
| 最后更新 | 2026-05-20 |

---

## 项目愿景

Linglong 是**跨 Agent 知识中枢**——所有 AI Agent 的统一知识底座。

```
Agent 写入 → KnowledgeStore → Composer 编译 → Dispatch 分发
```

核心价值：消除多 Agent 知识孤岛，一个概念只记一次，所有 Agent 共享。

---

## 设计原则

| 原则 | 含义 | 违反示例 |
|------|------|----------|
| 单一知识源 | 知识只存在 `~/linglong/` 一处 | Agent 维护自己的 wiki 副本 |
| Agent 是客户端 | Agent 通过 CLI 读写，不直接操作文件系统 | OpenClaw 直接改 wiki 文件 |
| Token 经济性 | 两步索引查询，默认返回摘要 | 每次查询返回全量内容 |
| 渐进式迁移 | 分阶段迁移，不强求一步到位 | 要求所有 Agent 同时切换 |
| wiki 是真相源 | Markdown 文件是主数据，SQLite/向量是衍生索引 | 以 SQLite 为主数据 |

---

## 发布历史

> 格式参考 [keepachangelog.com](https://keepachangelog.com)，分类：Added / Changed / Fixed / Deprecated / Removed。
> 按时间倒序排列，最新在前。

### [M4] v0.9 → v1.0 — 知识库独立 — 2026-05-16 ~ 2026-05-18

**目标**：知识库从 OpenClaw 剥离为独立服务，支持子目录分类，实现全量数据同步。

**Added**
- 默认存储路径改为 `~/linglong/`（跨项目共享），init 所有入口统一 `cc79a6d`
- memory 目录同步（310 条）：日记 → `personal/diary/`，任务记录 → `experience/task-record/` `cc79a6d`
- 目录级 facet 覆盖 `_DIR_FACET_OVERRIDE`：`user/` → PERSONAL，`infra/` → PERSONAL 等 `cc79a6d`
- 语义文件名 `{id[:8]}-{slug}.md` 防标题碰撞 `4c576f8`
- OpenClaw type→facet 映射扩展至 33 种类型 `be434b8`
- 设计文档体系重构（D-01 ~ D-10 + backlog + milestones）

**Fixed**
- sync + RSS 保留原始 `created_at`，修复管线数据流 `1f283e7`

**数据结果**：451 条 Entity（wiki 141 + memory 310），7 个 facet 全覆盖

**关键文件**：`sync/openclaw.py`、`store.py`、`init.py`、`docs/knowledge/design/`

---

### [M3] v0.7 ~ v0.9 — 产品化 — 2026-05-13 ~ 2026-05-15

**目标**：CLI 入口、配置外部化、dispatch 正式化、知识库完善。

**Added**
- `linglong` CLI 全命令集：ingest/compose/publish/sync/write/read/search/review/archive/lint/index/stats/init/migrate `4ec1e16` `4f3a96a` `e04e85b` `0cb83e0` `b691839`
- `.linglong.yaml` 配置文件 + 交互式配置向导 `715d3c6` `39dd567`
- DispatchManager + LocalPublisher + HexoPublisher `37673cd` `0e072aa` `df15339`
- 图片资产管线：下载/压缩/EXIF 清理/多尺寸响应式/OSS CDN 上传 `715d3c6` `dadff2d`
- EntityFacet 七分面枚举 + Entity facet/archived_at 字段 `819d789`
- FTS5 全文搜索 + facet/status/since 过滤 `d1e349c`
- Entity 文件按 facet 分目录存储 + YAML frontmatter `fee6974`
- 版本管理 + 版本压缩策略 `66e9830`
- 归档机制 + archive 目录 `37123ff`
- WikiLinks 解析器 `[[target]]` + `[[target|display]]` `3bf313a`
- 索引生成器（主索引 + 7 分面子索引）`2b1b72b`
- 巡检引擎（索引一致性 + WikiLinks + 内容冲突 + 过期检测 + `--fix` 自动修复）`9ffd309` `a3f75c0`
- 文件锁 `fcntl.flock` + SQLite WAL 模式 `5410e34` `c718500`
- ReviewEngine facet 差异化规则 + auto_lint 写入触发 `bed1778`
- 乐观锁 + WikiLinks Relations 自动填充 `9b2d983`
- write_mode 确认模式 + 交互式配置向导 `39dd567`

**Changed**
- `source_auto_confirm` 阈值从 `>= 0.7` 改为 `> 0.7` `a2cb8c2`

**Fixed**
- 2 个预存测试失败（dispatch 日期 + package 源数量）`53a0878`
- `datetime.utcnow()` 替换为 `datetime.now(UTC)` `19549f2`

**关键文件**：`cli.py`、`store.py`、`review.py`、`lint.py`、`indexer.py`、`dispatch/`

---

### [M2] v0.4 ~ v0.6 — 多 Agent 知识统一 — 2026-05-12

**目标**：三种 Agent 知识源同步到 Linglong。

**Added**
- OpenClawSyncAdapter（wiki 模式）`ccd2011`
- ClaudeCodeSyncAdapter `ffb7c10`
- CodexSyncAdapter `a11b013`
- 向量搜索（sqlite-vec + OpenClaw 远程 embedding）`8548815`
- Ingest 泛化：SourceAdapter ABC + AdapterRegistry + PackageExecutor `4721ec9` `6b4fab4` `5f6c43d`
- TruthVerificationEngine 五层验证 `e554106`
- RSS/WebFetch/WebSearch/API 四种 SourceAdapter `257cc7e`
- IngestConfig + SourcePackage YAML 配置模型 `4841fc5` `6b4fab4`
- 端到端集成测试（ingest→knowledge→composer→dispatch）`b6281e6`

**关键文件**：`sync/*.py`、`ingest/adapters/`、`ingest/truth.py`

---

### [M1] v0.1 ~ v0.3 — 基础管线 — 2026-05-12

**目标**：core + ingest + knowledge + composer 四模块骨架，端到端可运行。

**Added**
- Entity/Task/Source 数据模型 `3d7b1e1`
- KnowledgeStore 三层存储（文件 + SQLite + sqlite-vec）`3d7b1e1`
- Composer 日聚合 + BlogTemplate `e51497f`
- Ingest 模块骨架（RSS 采集）`3d7b1e1`
- Frontmatter YAML list 验证 + 测试 `35bc663`
- Makefile + CI workflow `25be4c3`
- 全链路集成测试 `3d7b1e1`

**关键文件**：`core/models.py`、`knowledge/store.py`、`composer/composer.py`、`ingest/`

---

## 明确放弃的方案

| 方案 | 放弃原因 | 替代方案 |
|------|----------|----------|
| 四分面（LLM-Wiki 原设计） | 无法覆盖经验/方法论/个人数据 | 七分面 |
| Push 模式（Agent 推送） | Agent 需要适配 Linglong API | Pull 模式（Linglong 拉取） |
| 纯文件系统存储 | 无全文搜索和向量搜索能力 | 文件 + SQLite + sqlite-vec |
| 项目本地存储（`./linglong/`） | 多项目共享知识库时配置冲突 | `~/linglong/` 统一路径 |
| 纯 slug 文件名 | 标题碰撞时互相覆盖 | ID 前缀 + slug |
| 同时同步 wiki 和默认 wiki | 内容重叠导致重复条目 | 先实现去重策略再支持（见 BACKLOG-002） |

---

## 当前状态

> 最后更新：2026-05-20 | 每次会话有实质进展时更新此节

### 总体进度

| 阶段 | 目标 | 状态 |
|------|------|------|
| M1 基础管线 | core + ingest + knowledge + composer 骨架 | 完成 |
| M2 多 Agent 同步 | 三种 Agent 知识源统一 | 完成 |
| M3 产品化 | CLI + 配置 + dispatch + 知识库完善 | 完成 |
| M4 知识库独立 | 从 OpenClaw 剥离，子目录分类，全量同步 | 完成 |
| M5 博客流水线 | 端到端验证 + 内容质量 | 进行中 |

### 当前聚焦

**任务**：MCP Server 已实现，Claude Code 可通过 MCP 工具读写 Linglong 知识库

**进展**：
- 知识库质量检查全部完成：index_consistency 归零、content_conflict 归零、wikilinks 343 个死链修复、16 个无 slug 文件名处理、Sleep 日志过滤修复
- BACKLOG-001 同步去重策略已实现（双层去重：ID 去重 + Content Hash 去重）
- BACKLOG-004 文件名格式已调整：`{id[:8]}-{slug}.md` → `{slug}-{id[:8]}.md`，331 个文件批量重命名，slug 打头提升可读性
- **MCP Server 已完成**：暴露 `search_wiki`、`search_similar`、`read_entity`、`write_entity`、`list_entities` 5 个工具，Claude Code 可自主查询和写入知识库
- **MCP 工具增强（P0-P3）**：
  - P0：`search_wiki` preview 优先返回 AI summary，无 summary 时扩至 500 字符
  - P1：新增 `search_and_read` 一键搜索+读取（默认截断 2000 字符防 Token 燃烧）
  - P2：`write_entity` docstring 引导 Agent 参考同类文档格式，新增 `reference_entity_ids` 参数
  - P3：新增 `update_entity` 支持替换/追加更新
- **模板体系**：8 个 facet 模板（concept/experience/project/methodology/source/entity/synthesis/personal）+ `get_template` / `list_templates` MCP 工具
- 273 个测试全部通过，lint 输出 "知识库健康，无问题"
- 博客模板已实现，图片管线已通，待端到端验证

### 卡点 / 阻塞项

| 项目 | 状态 | 说明 |
|------|------|------|
| LIMIT-001 frontmatter | 观察 | 2 个文件解析跳过，非关键 |
| BACKLOG-003 索引文件 | 待实现 | `index --rebuild` 生成的索引结构不完整 |

### 下一步

**M5 验证**（当前阶段核心）：
1. [x] 知识库同步质量检查 — 已完成（index_consistency/content_conflict/wikilinks 全部清零）
2. [x] 微调修复同步中发现的问题 — 已完成（Sleep 过滤、无 slug 文件名、lint 递归扫描修复）
3. [ ] 博客流水线端到端跑通（ingest → knowledge → composer → dispatch）
4. [ ] 输出内容质量检查（博客标题、正文、图片、标签）

**基础设施改进**：
5. [x] 同步去重策略（BACKLOG-001）— 已完成
6. [ ] OpenClaw 默认 wiki 路径支持（BACKLOG-002，前置依赖已解除）
7. [ ] 索引文件自动生成（BACKLOG-003）
8. [x] 文件名调整为 slug-ID 后缀格式（BACKLOG-004）— 已完成
9. [ ] CLI write 增加 `--created-by` 参数

---

## 版本变动历史

| 版本 | 日期 | 变动摘要 |
|------|------|----------|
| v1.0 | 2026-05-18 | 初始创建：基于 git 历史重写，keepachangelog 格式，M1-M4 含具体 commit 引用 |
