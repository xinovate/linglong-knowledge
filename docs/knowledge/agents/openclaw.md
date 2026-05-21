# OpenClaw (violet) 接入方案

| 属性 | 值 |
|------|-----|
| Agent | OpenClaw (violet) |
| 接入方式 | MCP 优先 |
| 同步适配器 | `src/linglong/knowledge/sync/openclaw.py` |
| 状态 | 🟡 规划中 |
| 最后更新 | 2026-05-21 |

---

## 1. 现状

### 知识库架构

OpenClaw 维护自己的 wiki 目录：`~/.openclaw/workspace/memory/wiki/`

```
wiki/
├── concepts/           → concept/
├── projects/           → source/projects/
├── references/         → source/references/
├── problems/           → source/problems/
├── experiences/        → experience/
├── methodologies/      → methodology/
├── user/              → personal/
├── emotion/           → personal/
├── soul/              → personal/diary/
├── infra/             → personal/infra/
├── dashboards/        → 不迁移
├── templates/         → 不迁移（Linglong 有自己的）
└── todo/              → 不迁移
```

### 短期记忆层

除了 wiki/，OpenClaw 还有短期记忆层：

| 内容 | 数量 | 说明 |
|------|------|------|
| `YYYY-MM-DD-index.md` | 16 个 | 任务索引，AGENTS.md 和 HEARTBEAT 依赖 |
| `memory/YYYY-MM-DD/` | 23 个目录 | 任务详情 |
| `memory/YYYY-MM-DD.md` | 18 个 | Dreaming 自动生成（只读） |

### 读写机制

- **写入**：直接创建/修改 `wiki/` 下的 `.md` 文件
- **读取**：文件系统遍历 + `memory_search(corpus=wiki)` 索引
- **模板**：3 个（concept, experience, project）
- **索引**：手动维护 `index.md`
- **链接**：`[[wikilinks]]` 语法

### 依赖的插件技能

| 技能 | 作用 | 接入后处理 |
|------|------|-----------|
| `wiki-maintainer` | 直接操作 wiki/ 目录 | 禁用（Linglong 接管） |
| `obsidian-vault-maintainer` | Obsidian 兼容维护 | 禁用（Linglong 接管） |

---

## 2. 接入方案

### 核心变动

| 层面 | 当前 | 改后 |
|------|------|------|
| 存储路径 | `~/.openclaw/workspace/memory/wiki/` | `~/linglong/wiki/` |
| 读写接口 | 直接文件操作 | MCP 工具调用 |
| 模板 | 3 个 | 8 个（Linglong facet 模板） |
| Agent 配置 | wiki 操作工具 | Linglong MCP 工具 |

### 接入方式：MCP 优先

```json
{
  "mcpServers": {
    "linglong": {
      "command": "bash",
      "args": ["-c", "source /path/to/linglong/venv/bin/activate && python -m linglong.mcp"]
    }
  }
}
```

MCP 优于 CLI 的原因：
- OpenClaw 原生支持 MCP 协议（acp-router skill）
- 不需要 exec 调 CLI 的额外开销
- Claude Code 已在用 MCP，统一接入方式
- 硬编码路径可以全部去掉

### 短期记忆层决策

**选择 A：留在 OpenClaw，不迁移。**

| 内容 | 决策 | 原因 |
|------|------|------|
| `YYYY-MM-DD-index.md` | 留在 OpenClaw | 和会话机制深度绑定 |
| `memory/YYYY-MM-DD/` | 留在 OpenClaw | 短期任务上下文 |
| `memory/YYYY-MM-DD.md` (Dreaming) | 留在 OpenClaw，不同步 | OpenClaw 内部机制，只读 |
| `wiki/` 下有价值内容 | 迁移到 Linglong | 长期知识沉淀 |

已有 `OpenClawSyncAdapter` 拉取了 310 条 memory 数据，长期有价值的自然会被 sync 拉走。

### memory_search 兼容性

**问题**：OpenClaw 的 `memory_search(corpus=wiki)` 能否索引 `~/linglong/wiki/`？

**如果不能**，用户说"上次我们讨论的 xxx"，violet 可能搜不到 Linglong 中的知识。

**解决方案**（优先级排序）：

1. **symlink**（最简单）— 在 `~/.openclaw/workspace/memory/wiki/` 放 symlink 指向 `~/linglong/wiki/`
2. **混合模式** — 主动查询走 MCP，被动记忆靠 `memory_search`
3. **验证后决定** — 先实测 `memory_search` 对 workspace 外目录的索引能力

### HEARTBEAT 改动

接入后 HEARTBEAT.md 需要逐项改写：

| 原逻辑 | 改后 |
|--------|------|
| 读取 wiki/index.md 检查知识库状态 | `list_entities()` 或 `linglong stats` |
| 创建 wiki/ 新文件 | `write_entity()` |
| 更新 wiki/index.md 索引 | 自动（Linglong 接管） |
| 检查 wikilinks 死链 | `linglong lint --check links` |
| 维护模板 | `get_template()` |

### 插件技能处理

| 技能 | 处理 |
|------|------|
| `wiki-maintainer` | 禁用 |
| `obsidian-vault-maintainer` | 禁用 |
| `growth-track` | 改为调用 `search_wiki(facet="personal")` |
| 其他引用 wiki 路径的技能 | 路径替换为 MCP 调用 |

### 回滚方案

如果 MCP 不稳定，快速切回直接文件操作：

1. 保留 `OpenClawSyncAdapter`（定期从 OpenClaw wiki 同步到 Linglong）
2. OpenClaw 恢复直接操作 wiki/ 目录
3. Linglong 退化为被动接收（sync 拉取模式）

---

## 3. 迁移步骤

```bash
# 1. 从 OpenClaw wiki 迁移（预览）
linglong migrate --from ~/.openclaw/workspace/memory/wiki/ --dry-run

# 2. 执行迁移
linglong migrate --from ~/.openclaw/workspace/memory/wiki/

# 3. 重建索引
linglong index --rebuild

# 4. 运行巡检
linglong lint

# 5. 配置 MCP
# 在 OpenClaw 中注册 Linglong MCP Server

# 6. 验证 memory_search 兼容性

# 7. 禁用 wiki-maintainer / obsidian-vault-maintainer

# 8. 改写 HEARTBEAT.md
```

---

## 4. 已知问题与风险

| 编号 | 问题 | 严重度 | 状态 |
|------|------|--------|------|
| OC-001 | `memory_search` 无法索引 Linglong wiki | 🔴 高 | 待验证 |
| OC-002 | HEARTBEAT 改动范围未量化 | 🟡 中 | 待评估 |
| OC-003 | Dreaming 文件可能被误同步 | 🟡 中 | 需过滤 |
| OC-004 | 插件技能禁用后功能缺失 | 🟡 中 | 需逐一确认 |
| OC-005 | MCP 通路稳定性未验证 | 🟡 中 | 需实测 |

---

## 5. 优化记录

| 日期 | 优化项 | 结果 |
|------|--------|------|
| — | — | — |
