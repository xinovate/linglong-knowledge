# Claude Code 接入方案

| 属性 | 值 |
|------|-----|
| Agent | Claude Code |
| 接入方式 | MCP |
| 同步适配器 | `src/linglong/knowledge/sync/claudecode.py` |
| 状态 | ✅ 已接入 |
| 最后更新 | 2026-05-21 |

---

## 1. 交互架构

### 整体拓扑

```
┌──────────────────────────────────────────────────────────────┐
│  Claude Code                                                │
│                                                              │
│  ┌──────────────┐  ┌──────────────────────────────────────┐ │
│  │  auto memory  │  │  Linglong MCP 工具（对话中直接调用）    │ │
│  │              │  │                                      │ │
│  │ MEMORY.md    │  │  search_wiki / search_similar        │ │
│  │ 自动加载到    │  │  search_and_read / read_entity       │ │
│  │ 对话上下文    │  │  write_entity / update_entity        │ │
│  │              │  │  list_entities                        │ │
│  │ 用途：        │  │  get_template / list_templates       │ │
│  │ 工作偏好      │  │                                      │ │
│  │ 用户反馈      │  │  用途：                               │ │
│  │ 项目上下文    │  │  跨 Agent 共享知识                    │ │
│  └──────────────┘  └────────────┬─────────────────────────┘ │
│                                  │ stdio                      │
│                                  ▼                            │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ ~/.claude/projects/.../memory/                         │  │
│  │ 会话级记忆（仅 Claude Code 使用）                        │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────┐
│  Linglong 知识库                                             │
│                                                              │
│  ~/linglong/wiki/          ← 7 facet 目录（真实数据源）       │
│  ~/linglong/db/knowledge.db ← SQLite 索引（可重建）           │
│                                                              │
│  同时服务：Claude Code + OpenClaw（共享知识库）                │
└──────────────────────────────────────────────────────────────┘
```

### 读写流程

```
── 写入流程 ──────────────────────────────────────────────

用户说"记住 xxx" / 解决了非 trivial 问题 / 做出架构决策
       │
       ▼
  search_wiki(query=标题)  ──→  已存在？
       │                         │
       │ 是                      │ 否
       ▼                         ▼
  update_entity(append)    get_template(facet)
       │                         │
       │                         ▼
       │                   write_entity(title, content, facet, tags)
       │                         │
       └─────────┬───────────────┘
                 ▼
           ~/linglong/wiki/{facet}/xxx.md
                 +
           ~/linglong/db/knowledge.db 索引更新


── 读取流程 ──────────────────────────────────────────────

用户问"之前怎么处理 xxx" / 遇到不确定的概念
       │
       ▼
  search_and_read(query="xxx", max_content_length=2000)
       │
       ▼
  匹配到结果？
       │ 是              │ 否
       ▼                  ▼
  直接使用截断内容    search_similar(query) ← 语义搜索
  回答用户                │
                          ▼
                     仍无结果 → 回答"没找到"


── 巡检流程（CLI 手动触发） ─────────────────────────────

开发者主动执行
       │
       ▼
  linglong lint [--check <项>] [--fix]
       │
       ▼
  检查 5 项：索引一致性 / 死链 / 内容冲突 / 过期 / 孤儿
       │
       ▼
  --fix 自动修复 / 手动处理
```

### 记忆边界

Claude Code 有两套记忆系统：

| 系统 | 路径 | 用途 | 生命周期 | 共享范围 |
|------|------|------|----------|----------|
| auto memory | `~/.claude/projects/.../memory/` | 工作偏好、用户反馈、项目上下文 | 跨会话持久 | 仅 Claude Code |
| Linglong MCP | `~/linglong/wiki/` | 知识库级概念、经验、决策 | 跨 Agent 共享 | Claude Code + OpenClaw |

**原则**：
- auto memory 是"工作记忆" — 快速加载到上下文，指导协作行为
- Linglong 是"长期知识" — 有价值的知识沉淀，所有 Agent 共享
- 两者不冲突，各司其职

---

## 2. MCP 配置

### 注册信息

```json
// ~/.claude/mcp.json
{
  "mcpServers": {
    "linglong": {
      "command": "bash",
      "args": ["-c", "cd /home/user/projects/linglong && source venv/bin/activate && python -m linglong.mcp"]
    }
  }
}
```

### 可用工具（9 个）

| 工具 | 用途 | Claude Code 使用场景 |
|------|------|---------------------|
| `search_wiki` | FTS5 全文搜索 | 查重、查找已有知识 |
| `search_similar` | 向量语义搜索 | 语义查重（降级到 FTS5） |
| `search_and_read` | 搜索+读取全文（截断） | 一步获取知识内容，控制 Token |
| `read_entity` | 读取完整内容 | 读取单条知识详情 |
| `write_entity` | 写入新知识 | 新增知识条目 |
| `update_entity` | 更新已有条目（替换/追加） | 追加补充已有知识 |
| `list_entities` | 浏览最近条目 | 浏览知识库状态 |
| `get_template` | 获取写作模板 | 写入前获取 facet 模板 |
| `list_templates` | 列出所有模板 | 了解可用 facet |

### 写入时机

| 触发点 | 时机 | 写入什么 | Facet |
|--------|------|----------|-------|
| 用户说"记住" | 显式指令 | 用户指定内容 | 根据内容判断 |
| 解决 bug | 问题解决 | 问题 + 原因 + 方案 | `experience` |
| 学到新知识 | 对话中 | 概念 + 例子 | `concept` |
| 做出架构决策 | 设计讨论 | 决策 + 理由 + 替代方案 | `concept` / `methodology` |
| 发现新实体 | 提到新名词 | 实体卡片 | `entity` |

### 写入判断标准

```
✅ 值得写入：将来可能再次需要、跨项目通用、踩坑经验、用户要求
❌ 不值得写：一次性信息、代码本身已表达、临时状态、已存在文档中
```

---

## 3. 同步适配器

`ClaudeCodeSyncAdapter` 读取 memory 目录下的 `.md` 文件，同步到 Linglong：

- 解析 frontmatter（name, description, type）
- 转换为 Entity，`created_by="agent:claude"`
- 当前已同步部分 memory 文件

**与 MCP 的关系**：适配器是历史方案（被动同步），MCP 是当前方案（主动读写）。两者并存，MCP 为主。

---

## 4. 已知问题与风险

| 编号 | 问题 | 严重度 | 状态 |
|------|------|--------|------|
| CC-001 | `search_and_read` 返回量过大烧 Token | 🟢 低 | ✅ 已解决（默认截断至 2000 字符） |
| CC-002 | 写入格式不一致 | 🟢 低 | ✅ 已解决（模板体系 + docstring 引导） |
| CC-003 | memory 同步去重（Claude Code + OpenClaw 重复） | 🟡 中 | content hash 去重已实现，待验证 |

---

## 5. 优化记录

| 日期 | 优化项 | 结果 |
|------|--------|------|
| 2026-05-14 | 新增 MCP Server，5 个基础工具 | Claude Code 可直接查询知识库 |
| 2026-05-20 | 新增 search_and_read，截断控制 | Token 消耗从 ~120KB 降至 ~10KB |
| 2026-05-20 | 新增 update_entity | 支持替换/追加两种模式 |
| 2026-05-20 | 新增 get_template / list_templates | 写入格式一致性提升 |
| 2026-05-20 | preview 质量优化 | 优先 summary，fallback 500 字符 |
