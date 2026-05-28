# Knowledge 模块差异化比对

> 基于 [LLM-Wiki 参考设计](llm-wiki-reference.md) 与 Linglong knowledge 模块实际实现的逐项比对。
> 更新日期：2026-05-14

---

## 总览

| 维度 | LLM-Wiki 参考设计 | Linglong 现状 | 差距 |
|------|-------------------|---------------|------|
| 存储模型 | 文件系统 wiki（Markdown + frontmatter） | 三层：文件 + SQLite + sqlite-vec 向量 | ✅ Linglong 更强 |
| 分面分类 | Sources / Entities / Concepts / Syntheses | 无一等公民分类，仅 metadata 兜底 | 🔴 缺失 |
| 索引系统 | index.md 入口 + index-*.md 分类索引 | 无自动生成索引 | 🔴 缺失 |
| 查询优化 | 两步定位（~2-3K tokens/查询） | 全量 search() 或向量 search_similar() | 🟡 部分（向量可替代语义查询） |
| 审核引擎 | 无（依赖 Agent 自行判断） | ReviewEngine 规则驱动自动审核 | ✅ Linglong 更强 |
| 归档机制 | raw/ → 09-archive/ 已处理归档 | 无归档，仅硬删除 | 🔴 缺失 |
| 操作日志 | log.md 记录每次 ingest/query/lint | 无持久化日志 | 🔴 缺失 |
| 健康巡检 | lint 流程（死链/孤儿/冲突/索引一致性） | 无 | 🔴 缺失 |
| 多 Agent 同步 | 无（单 Agent wiki） | OpenClaw / Claude Code / Codex 三路同步 | ✅ Linglong 更强 |
| 向量搜索 | 无 | sqlite-vec + 远程 embedding 服务 | ✅ Linglong 更强 |
| WikiLinks | `[[概念名]]` 双链解析 | README 提及，代码中未验证 | 🟡 待确认 |

---

## 逐项详细比对

### 1. 分面分类体系

**参考设计**：四分面 — Sources（资料汇编）、Entities（专有名词）、Concepts（抽象知识）、Syntheses（跨源综合）。

**Linglong 现状**：
- `Entity` 模型是平铺结构，所有类型共用同一张表
- `ClaudeCodeSyncAdapter` 按 frontmatter `type` 字段映射到 `metadata["wiki_directory"]`（feedback→experiences, project→projects 等），但这只是元数据，不是一等分类
- 没有 Sources vs Concepts 的语义区分
- 没有 Synthesis（综合分析）的生成机制

**待完善**：
- [ ] Entity 模型增加 `facet` 字段（enum: source / entity / concept / synthesis）
- [ ] 提供 `search(facet=...)` 过滤能力
- [ ] Synthesis 生成：从多次 query 结果中聚合提炼

---

### 2. 分层索引系统

**参考设计**：`index.md`（~500 tokens 总入口）→ `index-sources.md` / `index-entities.md` / `index-concepts.md` / `index-syntheses.md`（分类索引），实现两步定位，查询成本从 ~40K 降至 ~2-3K tokens。

**Linglong 现状**：
- 无自动生成的索引文件
- OpenClaw sync adapter 主动跳过 `index.md`
- 查询依赖 `search()` 全表扫描或 `search_similar()` 向量近邻

**待完善**：
- [ ] 实现 `IndexGenerator`：定期扫描 KnowledgeStore，生成 `index.md` + `index-*.md`
- [ ] 索引格式：每条一行 `| ID | 摘要 | 标签 | 更新时间 |`
- [ ] 索引与 SQLite 保持同步（写入 Entity 时自动更新）

---

### 3. 查询流程优化

**参考设计**：两步定位 — 先读 index.md 判断分类，再读对应 index-*.md 精准定位 2-5 条目标，最后深度阅读。

**Linglong 现状**：
- `search()` 接受 `query` 参数但 **实际未使用**（SQL 中无 WHERE content LIKE）
- `search_similar()` 走向量近邻，语义能力更强但无法精确关键词匹配
- 没有"先索引定位再深度读取"的分步策略

**待完善**：
- [ ] `search()` 实现关键词过滤（SQLite FTS5 或 LIKE）
- [ ] 提供 `search_index(query)` 轻量接口，仅返回 ID + 摘要（不加载全文）
- [ ] 组合查询：`search_index()` → `get()` 按需加载

---

### 4. 归档机制

**参考设计**：原始资料处理后移入 `raw/09-archive/YYYY-MM-DD/`，保留历史可追溯。

**Linglong 现状**：
- 无归档概念
- `delete()` 是硬删除（文件 + SQLite + 向量全部移除）
- Codex sync adapter 读取时过滤 `archived = 0`，但 Linglong 自身不写回归档状态

**待完善**：
- [ ] Entity 增加 `archived_at` 字段
- [ ] `archive(entity_id)` 方法：标记归档而非删除，文件移入 `archive/` 子目录
- [ ] `search()` 增加 `include_archived` 参数（默认 False）

---

### 5. 操作日志

**参考设计**：`log.md` 记录每次操作 — `类型 | 时间 | 详情 | 操作人`。

**Linglong 现状**：
- 仅有 Python `logging` 输出到 stdout/stderr
- sync adapter 返回临时 `stats` dict，不持久化
- 无法审计"谁在什么时候做了什么"

**待完善**：
- [ ] SQLite 增加 `operation_log` 表（operation_type, entity_id, agent, timestamp, details）
- [ ] KnowledgeStore 写操作自动记录
- [ ] 提供 `query_log(entity_id=None, agent=None, since=None)` 查询接口
- [ ] 可选导出为 `log.md` 格式

---

### 6. 健康巡检（Lint）

**参考设计**：三项检查 — 索引一致性、双向链接完整性（死链/孤儿）、认知冲突检测。

**Linglong 现状**：
- knowledge 模块无任何 health-check 方法
- 其他模块（ingest/dispatch）有 `health_check()`，但 knowledge 没有

**待完善**：
- [ ] 实现 `KnowledgeStore.lint()` 方法
- [ ] **索引一致性**：对比 index 文件与实际 Entity 记录
- [ ] **孤儿检测**：`relations` 为空且无其他 Entity 引用的条目
- [ ] **冲突检测**：同 topic 不同 Entity 内容矛盾（可用向量相似度 + LLM 判断）
- [ ] 输出结构化报告（绿灯/黄灯/红灯 + 修复建议）

---

### 7. WikiLinks 双链支持

**参考设计**：`[[概念名]]` 自动解析，创建 source 时自动替换 stub。

**Linglong 现状**：
- README 提及 "WikiLinks 支持"，但代码中未找到解析实现
- Entity 有 `relations` 字段（JSON list），可用于存储链接关系
- 无 stub 自动替换机制

**待完善**：
- [ ] 确认 WikiLinks 解析是否已实现（grep `[[` 相关逻辑）
- [ ] 如未实现：在 Entity 写入时解析 `[[...]]` 并填充 `relations`
- [ ] stub 替换：创建新 Entity 时检查其他 Entity 中的占位链接并更新

---

### 8. ReviewEngine 增强

**Linglong 优势**：ReviewEngine 是参考设计没有的能力，四条内置规则 + 可扩展。

**现有不足**：
- `Action.MERGE` 和 `Action.REJECT` 已定义但 `_apply_action()` 未实现
- 无"内容冲突检测"规则（参考设计 lint 流程中的核心检查项）

**待完善**：
- [ ] 实现 MERGE 动作：合并新旧 Entity 内容
- [ ] 实现 REJECT 动作：标记拒绝原因
- [ ] 增加冲突检测规则：与已有 Entity 向量相似度 > 阈值时触发人工审核

---

## Linglong 独有优势（参考设计不具备）

| 能力 | 说明 |
|------|------|
| **三层存储** | 文件 + SQLite + sqlite-vec，兼顾可读性、结构化查询、语义搜索 |
| **向量语义搜索** | 远程 embedding 服务（nomic-embed-text-v1.5）+ sqlite-vec cosine 距离 |
| **多 Agent 同步** | OpenClaw / Claude Code / Codex 三路 sync adapter，带命名空间隔离 |
| **自动审核引擎** | 规则驱动，可扩展，支持人工确认工作流 |
| **Entity 版本管理** | `versions` 字段 + `current_version`，支持内容演进追溯 |
| **置信度体系** | `confidence` 0.0-1.0 + `EntityStatus` 状态机 |

---

## 优先级建议

按 **投入产出比** 排序：

| 优先级 | 项目 | 理由 |
|--------|------|------|
| **P0** | 分面分类（facet 字段） | 影响查询精度和后续所有功能的基础 |
| **P0** | search() 关键词过滤 | 当前 query 参数未生效，基本功能缺失 |
| **P1** | 操作日志 | 多 Agent 协作场景的审计刚需 |
| **P1** | 归档机制 | 避免硬删除导致数据丢失 |
| **P2** | 分层索引 | 向量搜索可部分替代，但对 LLM 友好度不如索引 |
| **P2** | 健康巡检 | 知识库规模化后的必要能力 |
| **P3** | WikiLinks 解析 | 锦上添花，当前 relations 字段可手动维护 |
| **P3** | ReviewEngine MERGE/REJECT | 当前规则已覆盖主流程，边缘场景可后补 |
