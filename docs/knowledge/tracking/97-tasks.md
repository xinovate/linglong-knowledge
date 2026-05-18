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
| 4 | 修复 lint content_conflict 误报 | 已完成 | 30 分钟 | lint | [详情](#4) |
| 5 | OpenClaw sync 过滤 Sleep 日志 | 已完成 | 20 分钟 | sync | [详情](#5) |
| 6 | 调查 16 个无 slug 文件名 | 待处理 | 35 分钟 | sync | [详情](#6) |
| 7 | 修复 wikilinks 死链（概念链接） | 待处理 | 1 小时 | wikilinks | [详情](#7) |
| 8 | 同步去重策略 | 阻塞中 | — | BACKLOG-001 | [详情](#8) |

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

**状态**：待处理

**下一步**：检查原始文件 frontmatter 是否有 title 字段。

---

## 7. 修复 wikilinks 死链

**状态**：待处理

**下一步**：先执行 `linglong lint` 导出完整死链列表，筛选概念类链接。

---

## 8. 同步去重策略

**状态**：阻塞中

**阻塞原因**：等 BACKLOG-001 方案确定。
