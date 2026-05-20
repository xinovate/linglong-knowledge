# 当前任务

> **定位**：短期可执行任务（35 分钟 ~ 2 小时可完成）。
> **不记录**：长期规划（去 `98-backlog.md`）、阶段方向（去 `99-milestones.md`）、已完成工作（去 `journal/`）。
> **更新时机**：任务完成打勾、新任务加入、优先级调整。

---

## 任务索引

| # | 任务 | 状态 | 预估 | 关联 | 详情 |
|---|------|------|------|------|------|
| 1 | 处理 34 个 index_consistency | 已完成 | 1 小时 | lint | [详情](#1) |
| 2 | 清理 Sleep 日志重复（Light/Deep/REM） | 已完成 | 30 分钟 | sync | [详情](#2) |
| 3 | 清理重复标题（源码分析工作流 + 迁移阿里云） | 已完成 | 20 分钟 | sync | [详情](#3) |
| 3.1 | 清理僵尸记录（源码分析工作流 v2.0） | 已完成 | 5 分钟 | db | [详情](#3) |
| 4 | 修复 lint content_conflict 误报 | 已完成 | 30 分钟 | lint | [详情](#4) |
| 5 | OpenClaw sync 过滤 Sleep 日志 | 已完成 | 20 分钟 | sync | [详情](#5) |
| 6 | 调查 16 个无 slug 文件名 | 已完成 | 35 分钟 | sync | [详情](#6) |
| 7 | 修复 wikilinks 死链（343 个） | 已完成 | 1 小时 | lint | [详情](#7) |
| 8 | 同步去重策略 | 已完成 | — | BACKLOG-001 | [详情](#8) |

---

## 1. 处理 34 个 index_consistency

**状态**：已完成

**操作**：运行 `linglong lint --fix`，自动删除 34 个孤立文件。

**结果**：index_consistency 归零。

---

## 2. 清理 Sleep 日志重复

**状态**：已完成

**操作**：
1. 删除文件：` Light Sleep` × 25、`Deep Sleep` × 25、`REM Sleep` × 25
2. 清理数据库记录：57 条

**结果**：
- content_conflict：216 → 144
- 总条目：457 → 375

---

## 3. 清理重复标题

**状态**：已完成

**操作**：
1. 删除 `experience/task-record/` 下的 2 个 `源码分析工作流 v2.0` 重复
2. 删除 `experience/task-record/` 下的 2 个 `openclaw 迁移阿里云 vps 完整记录` 重复
3. 保留 `source/projects/` 下的正确分类版本

**结果**：content_conflict 144 → 140

---

## 4. 修复 lint content_conflict 误报

**状态**：已完成

**操作**：修改 `lint.py`，对 `_subdir` 为 `diary` 或 `task-record` 的文件豁免标题重复检测。

**原因**：memory 同步的日记和任务记录标题重复是正常行为（每天日记标题都是日期）。

**结果**：content_conflict 140 → 1

---

## 5. OpenClaw sync 过滤 Sleep 日志

**状态**：已完成

**操作**：修改 `openclaw.py`，`_memory_file_to_entity()` 中检测标题为 `Light Sleep` / `Deep Sleep` / `REM Sleep` 时返回 `None`，`sync_to_linglong()` 跳过并计入 `skipped`。

**关联**：`src/linglong/knowledge/sync/openclaw.py`

---

## 6. 调查 16 个无 slug 文件名

**状态**：已完成

**调查**：
- 16 个文件中：8 个 `## Light Sleep`（OpenClaw 内部日志）、4 个无价值草稿/记忆、2 个空内容、2 个有价值但无标题
- 根因：源文件无一级标题 `# 标题`，`_save_to_filesystem()` 无法提取 slug
- 发现 bug：`openclaw.py` Sleep 过滤只检查一级标题，漏过 `## Light Sleep`

**处理**：
- 删除 11 个无价值文件（Sleep 日志 + 草稿 + 系统日志）
- 保留 2 个有价值的，补 `# 标题` 并重命名为正确 slug
- 修复 `openclaw.py`：Sleep 过滤支持多级标题
- 修复 `lint.py`：`check_index_consistency` 递归扫描子目录，正确处理 `{id[:8]}-{slug}.md` 命名

**关联**：`src/linglong/knowledge/sync/openclaw.py`、`src/linglong/knowledge/lint.py`

---

## 7. 修复 wikilinks 死链

**状态**：已完成

**操作**：
1. 调查：343 次引用 → 132 个唯一目标。分类：OpenClaw 内部常量(40) / 相对路径(44) / 占位符(16) / 概念链接(243)
2. 确认：相对路径目标全部不存在；绝大多数概念链接目标也不存在
3. 实现：`lint.py` 的 `fix_all()` 增加 `_fix_wikilinks()` 方法，批量把 `[[死链]]` 还原为纯文本
4. 执行：`linglong lint --fix`，343 个死链全部修复
5. 连带修复：过程中发现并清理 18 个新的 index_consistency 孤立文件

**结果**：wikilinks 归零，lint 输出 "知识库健康，无问题"

**关联**：`src/linglong/knowledge/lint.py`

---

## 8. 同步去重策略

**状态**：已完成

**方案**：双层去重
- **ID 去重**（源级）：同一文件路径同步多次 → 幂等跳过或更新
- **Content Hash 去重**（跨源）：不同路径但内容完全相同 → 返回已有实体
- 语义相近的留给 `lint content_conflict` 人工处理

**实现**：
1. `store.py`：`create()` 增加去重检查；`_init_database()` 新增 `content_hash` 列
2. `openclaw.py`：`sync_to_linglong()` stats 增加 `updated`，adapter 层预检查
3. 新增 5 个测试覆盖幂等性、内容更新、跨源去重

**关联**：`src/linglong/knowledge/store.py`、`src/linglong/knowledge/sync/openclaw.py`

---

## 9. MCP Server 工具增强（P0-P3）

**状态**：已完成

**P0 search 质量**：
- `_entity_to_preview` 优先返回 `entity.summary`（AI 生成摘要），否则 preview 从 120 字符扩至 500 字符
- Agent 能更快判断相关性，减少盲目 `read_entity` 调用

**P1 search_and_read**：
- 新增一键搜索+读取工具，内部先 `search` 再对前 N 个结果 `read`
- 默认截断 2000 字符防 Token 燃烧，超长标注 `... [truncated]`，返回 `truncated: true`
- 适合"详细讲讲 X"类需要全文的情境，减少 Agent 往返

**P2 write 风格引导**：
- `write_entity` docstring 引导 Agent 写入前先搜索同类 facet 参考格式
- 新增可选 `reference_entity_ids` 参数，显式传入参考文档 ID

**P3 update_entity**：
- 新增更新工具，支持替换模式（默认）和追加模式（`append=True`）
- 让 Agent 可以更新已有条目，而不只是新建

**结果**：MCP 工具从 5 个增至 7 个，测试 17/17 通过，全量 270/270 通过

**关联**：`src/linglong/mcp/tools.py`、`src/linglong/mcp/server.py`
