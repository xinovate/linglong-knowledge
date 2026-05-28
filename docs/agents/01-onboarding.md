# Linglong 三方接入指南

> 本文档面向第三方用户，说明如何将 AI Agent 接入 Linglong 知识库。

---

## 前置条件

### 1. 安装 Linglong

```bash
pip install linglong
```

### 2. 初始化知识库

```bash
linglong kb init
```

交互式向导会引导配置：
- Wiki 存储路径（默认 `~/knowledge/wiki/`）
- 数据库路径（默认 `~/knowledge/db/knowledge.db`）
- Embedding 服务（可选，用于语义搜索）

初始化后生成 `~/.knowledge.yml` 配置文件。

### 3. 验证

```bash
linglong kb stats
```

输出知识库状态即表示初始化成功。

---

## Claude Code 接入

### 快速接入（2 步，5 分钟）

MCP 工具注册后即可在对话中按需调用。

**Step 1：注册 MCP Server**

在 `~/.claude/settings.json` 的 `mcpServers` 字段中添加：

```json
{
  "mcpServers": {
    "linglong": {
      "command": "bash",
      "args": ["-c", "cd /path/to/linglong/project && source venv/bin/activate && python -m linglong.mcp"]
    }
  }
}
```

> 如果通过 `pip install` 安装（非源码），命令简化为：
> ```json
> {
>   "command": "python",
>   "args": ["-m", "linglong.mcp"]
> }
> ```

**Step 2：重启 Claude Code**

新会话中即可使用 Linglong 工具。测试：

```
请用 search_wiki 搜索 "测试"
```

**效果**：工具可用，但 Claude Code 不会主动使用 — 需要你手动说"搜一下"、"记住这个"。

---

### 深度接入（+1 步，共 3 步）

在快速接入基础上，让 Claude Code 主动使用 Linglong。

**Step 3：写入全局指令**

在 `~/.claude/CLAUDE.md` 末尾追加：

```markdown
## Linglong 知识库

Linglong 是跨 Agent 共享的知识库，通过 MCP 工具接入。

### 读取时机
- 用户问到历史决策、"之前怎么处理 X" 时，先 search_wiki 再回答
- 遇到不确定的概念，search_wiki(facet="concept") 查一下

### 写入时机
- 用户说"记住"时 → write_entity
- 解决了非 trivial 的 bug 后 → write_entity(facet="experience")
- 做出架构决策时 → write_entity(facet="concept")

### 写入流程
1. search_wiki(query=标题) → 查重，已有则 update_entity 追加
2. get_template(facet) → 获取该 facet 的写作模板
3. write_entity(title, content, facet, tags) → 写入

### 可用 Facet
- concept — 概念知识（架构、设计模式、技术概念）
- experience — 经验总结（踩坑、调试、问题解决）
- methodology — 方法论（流程、规范、最佳实践）
- source — 项目资料（项目文档、参考资料）
- entity — 实体卡片（工具、框架、人物）
- personal — 用户画像（偏好、风格、背景）
- diary — 日记（日常记录、反思）

### 与 auto memory 的边界
- auto memory（~/.claude/projects/.../memory/）：工作偏好、协作反馈，仅 Claude Code 使用
- Linglong（~/knowledge/wiki/）：有价值的知识，所有 Agent 共享
- 两者不冲突，auto memory 是工作记忆，Linglong 是长期知识
```

> 如果只想在某个项目中生效，写入项目根目录的 `CLAUDE.md` 而非全局文件。

**效果**：Claude Code 在所有项目中主动使用 Linglong 进行知识读写。

---

### 移除接入

**快速移除**（保留数据）：

从 `~/.claude/settings.json` 的 `mcpServers` 中删除 `linglong` 条目。

如果做了深度接入，同时删除 `~/.claude/CLAUDE.md` 中追加的 `## Linglong 知识库` 段落。

**完全卸载**：

```bash
pip uninstall linglong
rm -rf ~/knowledge/  # 删除知识库数据
```

---

## OpenClaw 接入

### 快速接入（3 步，10 分钟）

**Step 1：安装 Linglong 并初始化**

```bash
pip install linglong
linglong kb init
```

**Step 2：注册 MCP Server**

```bash
openclaw mcp set linglong '{"command":"bash","args":["-c","cd /path/to/linglong/project && source venv/bin/activate && python -m linglong.mcp"]}'
```

或通过 pip 安装时：

```bash
openclaw mcp set linglong '{"command":"python","args":["-m","linglong.mcp"]}'
```

**Step 3：重启 Gateway**

```bash
openclaw gateway restart
```

在 OpenClaw 对话中测试：

```
请用 search_wiki 搜索 "测试"
```

**效果**：工具可用，violet 能在你说"用 linglong 搜一下"时调用，但不会主动使用。

---

### 深度接入（需改配置文件，30-60 分钟）

在快速接入基础上，让 OpenClaw 主动使用 Linglong。需要修改 OpenClaw 的 Agent 配置文件。

**Step 4：改写 MEMORY.md**

删除旧的 `memory/wiki/` 索引和使用规则，替换为 Linglong 说明：
- 七个 Facet 说明
- MCP 读写指引
- "先 search 再 write" 流程

**Step 5：改写 AGENTS.md**

核心改动：
- 记忆写入规则：`memory/wiki/<category>/` → MCP 工具写入 Linglong
- 知识库使用规则：目录映射表 → Facet 写入时机表
- 知识库读写流程：新增完整规范（查重→模板→写入）

**Step 6：改写 HEARTBEAT.md**

将涉及 `memory/wiki/` 的检查项改为 Linglong 命令：
- 记忆整理 → 通过 MCP 写入 Linglong
- 成长检查 → `search_wiki(facet=personal)`
- Wiki 健康检查 → `linglong kb lint`

**Step 7：适配引用 wiki 路径的技能**

如果 Agent 配置了自定义技能（如 growth-track、task-review 等），将其中的硬编码 `wiki/` 路径替换为 MCP 调用。

**Step 8：验证**

在 OpenClaw 中测试完整工作流：
1. 说"记住 xxx" → 检查是否写入 Linglong（`linglong kb search "xxx"`）
2. 说"我们之前讨论的 xxx" → 检查是否通过 MCP 搜索
3. 触发 HEARTBEAT → 检查是否正常执行

**效果**：OpenClaw 主动使用 Linglong 进行所有知识操作，不再依赖本地 `memory/wiki/`。

> **建议**：`wiki-maintainer` 插件暂不禁用，观察稳定后再处理。`memory/wiki/` 保留作为备份。

---

### 移除接入

**快速移除**：

```bash
openclaw mcp unset linglong
openclaw gateway restart
```

恢复 MEMORY.md / AGENTS.md / HEARTBEAT.md 中被修改的内容（建议改动前备份原文件）。

**完全卸载**：

```bash
pip uninstall linglong
rm -rf ~/knowledge/
```

---

## 其他 MCP 客户端接入

任何支持 MCP stdio 协议的客户端均可接入。

### 通用接入方式

MCP Server 启动命令：

```bash
python -m linglong.mcp
```

将此命令注册到客户端的 MCP 配置中，具体格式参考客户端文档。

### 可用工具（9 个）

| 工具 | 用途 | 参数 |
|------|------|------|
| `search_wiki` | FTS5 全文搜索 | `query`, `facet?`, `limit?` |
| `search_similar` | 向量语义搜索 | `query`, `facet?`, `limit?` |
| `search_and_read` | 搜索+读取（截断） | `query`, `facet?`, `limit?`, `max_content_length?` |
| `read_entity` | 读取完整内容 | `entity_id` |
| `write_entity` | 写入新知识 | `title`, `content`, `facet`, `tags?` |
| `update_entity` | 更新已有条目 | `entity_id`, `content`, `append?` |
| `list_entities` | 浏览最近条目 | `facet?`, `since?`, `limit?` |
| `get_template` | 获取写作模板 | `facet` |
| `list_templates` | 列出所有模板 | — |

### Facet 列表

| Facet | 用途 |
|-------|------|
| `concept` | 概念知识 |
| `experience` | 经验总结 |
| `methodology` | 方法论 |
| `source` | 项目资料 |
| `entity` | 实体卡片 |
| `personal` | 用户画像 |
| `diary` | 日记 |

---

## 接入方案对比

| | Claude Code | OpenClaw | 通用 MCP 客户端 |
|---|---|---|---|
| 快速接入 | 2 步，5 分钟 | 3 步，10 分钟 | 注册 MCP Server |
| 深度接入 | +1 步（改全局 CLAUDE.md） | +4-5 步（改多个配置文件） | 取决于客户端能力 |
| 全局生效 | ✅ `~/.claude/CLAUDE.md` | ❌ 每个 Agent 实例独立 | 取决于客户端 |
| 移除难度 | 删配置即可 | 需恢复多个文件 | 删配置即可 |
| 知识共享 | 所有项目共享 | 当前 Agent 实例 | — |
