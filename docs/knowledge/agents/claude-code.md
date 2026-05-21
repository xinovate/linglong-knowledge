# Claude Code 接入方案

| 属性 | 值 |
|------|-----|
| Agent | Claude Code |
| 接入方式 | MCP |
| 同步适配器 | `src/linglong/knowledge/sync/claudecode.py` |
| 状态 | ✅ 已接入 |
| 最后更新 | 2026-05-21 |

---

## 1. 现状

### 知识库架构

Claude Code 维护自己的 memory 目录：`~/.claude/projects/{project}/memory/`

```
~/.claude/projects/-Users-wangxin-GithubProjects-linglong/memory/
├── MEMORY.md          # 记忆索引（自动加载到上下文）
├── user_role.md       # 用户画像
├── feedback_*.md      # 反馈记忆
├── project_*.md       # 项目记忆
├── reference_*.md     # 引用记忆
└── codex_*.md         # Codex 相关记忆
```

### 读写机制

- **读取**：MEMORY.md 自动加载到对话上下文
- **写入**：Claude Code 的 auto memory 系统（`/remember` 或自动保存）
- **格式**：自定义 Markdown + YAML frontmatter

### MCP 接入配置

已在 `~/.claude/mcp.json` 中配置：

```json
{
  "mcpServers": {
    "linglong": {
      "command": "bash",
      "args": ["-c", "cd /home/user/projects/linglong && source venv/bin/activate && python -m linglong.mcp"]
    }
  }
}
```

### 同步适配器

`ClaudeCodeSyncAdapter` 读取 memory 目录下的 `.md` 文件，同步到 Linglong：
- 解析 frontmatter（name, description, type）
- 转换为 Entity，`created_by="claude"`
- 已同步部分 memory 文件

---

## 2. 接入方案（已实施）

### MCP 工具使用

Claude Code 在对话中可直接调用 9 个 Linglong MCP 工具：

| 使用场景 | 调用工具 |
|----------|---------|
| 用户提问时检索知识 | `search_wiki` / `search_and_read` |
| 查看某条知识的详情 | `read_entity` |
| 写入新知识 | `write_entity`（写入前自动 `get_template` 参考格式） |
| 更新已有条目 | `update_entity` |
| 浏览最近条目 | `list_entities` |
| 查看模板 | `get_template` / `list_templates` |

### 读取时机

- 用户提问时，调用 `search_wiki` 或 `search_and_read` 检索知识库
- 遇到不确定的概念，搜索 `facet=concept`
- 引用历史决策时，调用 `read_entity`

### 写入时机

- 用户说"记住"、"记录"、"保存到知识库"时
- 解决了一个非 trivial 的问题后
- 做出架构决策时

### 写入最佳实践

```
1. get_template(facet) → 获取模板结构
2. search_wiki(facet) → 搜索同类文档参考格式
3. write_entity(title, content, facet, tags) → 写入
```

---

## 3. 与 auto memory 的关系

Claude Code 有两套记忆系统：

| 系统 | 路径 | 用途 | 生命周期 |
|------|------|------|----------|
| auto memory | `~/.claude/projects/.../memory/` | 会话级偏好、反馈、项目上下文 | 跨会话持久 |
| Linglong MCP | `~/linglong/wiki/` | 知识库级概念、经验、决策 | 跨 Agent 共享 |

**边界**：
- **auto memory**：保存 Claude Code 的工作偏好、用户反馈、项目特定上下文（快速加载到上下文）
- **Linglong**：保存有价值的知识（概念、经验、决策、实体），供所有 Agent 共享

两者不冲突，auto memory 是"工作记忆"，Linglong 是"长期知识"。

---

## 4. 已知问题与优化

| 编号 | 问题 | 严重度 | 状态 |
|------|------|--------|------|
| CC-001 | `search_and_read` 返回量过大烧 Token | 🟢 已解决 | 截断至 2000 字符 |
| CC-002 | 写入格式不一致 | 🟢 已解决 | 模板体系 + docstring 引导 |
| CC-003 | memory 同步去重（Claude Code + OpenClaw 重复） | 🟡 待验证 | content hash 去重已实现 |

---

## 5. 优化记录

| 日期 | 优化项 | 结果 |
|------|--------|------|
| 2026-05-20 | 新增 MCP Server，5 个工具 | Claude Code 可直接查询知识库 |
| 2026-05-20 | 新增 search_and_read，截断控制 | Token 消耗从 120KB 降至 10KB |
| 2026-05-20 | 新增 update_entity | 支持替换/追加两种模式 |
| 2026-05-20 | 新增 get_template / list_templates | 写入格式一致性提升 |
| 2026-05-20 | preview 质量优化 | 优先 summary，fallback 500 字符 |
