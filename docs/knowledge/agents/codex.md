# Codex CLI 接入方案

| 属性 | 值 |
|------|-----|
| Agent | Codex CLI |
| 接入方式 | CLI（预留 MCP） |
| 同步适配器 | `src/linglong/knowledge/sync/codex.py` |
| 状态 | ⚪ 预留 |
| 最后更新 | 2026-05-21 |

---

## 1. 现状

### 数据目录

Codex CLI 的数据分布在多个位置：

| 数据 | 路径 | 说明 |
|------|------|------|
| Agent 定义 | `AGENTS.md` | Agent 配置和指令 |
| 任务历史 | SQLite 数据库 | 执行记录 |
| 对话记录 | `history.jsonl` | 完整对话日志 |

### 同步适配器

`CodexSyncAdapter` 已实现基础同步：
- 读取 `AGENTS.md`、SQLite、`history.jsonl`
- 转换为 Entity，`created_by="codex"`

---

## 2. 接入方案（预留）

接入方式待定，取决于 Codex 的 MCP 支持情况：

- **方案 A**：CLI 调用（`linglong search` / `linglong write`）
- **方案 B**：MCP 接入（如果 Codex 未来支持 MCP）

---

## 3. 已知问题

| 编号 | 问题 | 严重度 | 状态 |
|------|------|--------|------|
| CX-001 | Codex MCP 支持情况未知 | 🟡 中 | 待调研 |

---

## 4. 优化记录

| 日期 | 优化项 | 结果 |
|------|--------|------|
| — | — | — |
