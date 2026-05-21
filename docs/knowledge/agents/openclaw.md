# OpenClaw (violet) 接入方案

| 属性 | 值 |
|------|-----|
| Agent | OpenClaw (violet) |
| 接入方式 | MCP |
| 同步适配器 | `src/linglong/knowledge/sync/openclaw.py` |
| 状态 | 🟡 接入中（Phase 0+2 已完成，实战验证中） |
| 最后更新 | 2026-05-21 |

---

## 1. 交互架构

### 整体拓扑

```
┌─────────────────────────────────────────────────────────────┐
│  OpenClaw (violet)                                          │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐ │
│  │MEMORY.md │  │AGENTS.md │  │HEARTBEAT │  │ 3 个技能    │ │
│  │ 读写指引  │  │ 知识流程  │  │ 定期检查  │  │growth-track│ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  │task-review │ │
│       │              │              │        │skill-spec  │ │
│       └──────────────┴──────────────┘        └─────┬──────┘ │
│                      │                              │        │
│                      ▼ MCP 工具调用                  ▼        │
│              ┌───────────────┐                              │
│              │ linglong MCP  │                              │
│              │   Server      │                              │
│              └───────┬───────┘                              │
│                      │ stdio                                │
│                      │                                      │
│  ┌───────────────┐   │   ┌────────────────────────────┐    │
│  │ memory/wiki/  │   │   │ OpenClaw 短期记忆（不动）    │    │
│  │ （留作备份）   │   │   │ YYYY-MM-DD-index.md        │    │
│  └───────────────┘   │   │ YYYY-MM-DD/  任务详情      │    │
│                      │   │ YYYY-MM-DD.md  Dreaming     │    │
│                      │   └────────────────────────────┘    │
└──────────────────────┼─────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────┐
│  Linglong 知识库                                             │
│                                                              │
│  ~/linglong/wiki/          ← 7 facet 目录（真实数据源）       │
│  ~/linglong/db/knowledge.db ← SQLite 索引（可重建）           │
│                                                              │
│  MCP 工具：                                                   │
│  ┌─────────────┐ ┌──────────────┐ ┌────────────────┐        │
│  │ search_wiki  │ │ write_entity │ │ update_entity  │        │
│  │ search_similar│ │ read_entity  │ │ list_entities  │        │
│  │ search_and_read│ │ get_template│ │ list_templates │        │
│  └─────────────┘ └──────────────┘ └────────────────┘        │
│                                                              │
│  同时服务：OpenClaw + Claude Code（共享知识库）                 │
└──────────────────────────────────────────────────────────────┘
```

### 读写流程

```
── 写入流程 ──────────────────────────────────────────────

用户说"记住 xxx"
       │
       ▼
  AGENTS.md 判断写入规则
       │
       ▼
  search_wiki(query=标题)  ──→  已存在？
       │                         │
       │ 是                      │ 否
       ▼                         ▼
  update_entity(append)    get_template(facet)
       │                         │
       │                         ▼
       │                   write_entity(title, content, facet)
       │                         │
       └─────────┬───────────────┘
                 ▼
           ~/linglong/wiki/{facet}/xxx.md
                 +
           ~/linglong/db/knowledge.db 索引更新


── 读取流程 ──────────────────────────────────────────────

用户问"之前怎么处理 xxx"
       │
       ▼
  search_wiki(query="xxx")
       或
  search_similar(query="xxx")  ← 语义搜索，embedding 降级到 FTS5
       │
       ▼
  匹配到结果？
       │ 是              │ 否
       ▼                  ▼
  read_entity(id)     回答"没找到"
       │
       ▼
  返回完整内容给用户


── 巡检流程（HEARTBEAT 触发） ───────────────────────────

HEARTBEAT #8 定期触发
       │
       ▼
  linglong lint
       │
       ▼
  检查 5 项：索引一致性 / 死链 / 内容冲突 / 过期 / 孤儿
       │
       ▼
  生成巡检报告 → 按 Linglong 管理
```

### Facet 映射

| OpenClaw 旧目录 | Linglong Facet | 说明 |
|----------------|----------------|------|
| `wiki/concepts/` | `concept` | 概念知识 |
| `wiki/experiences/` | `experience` | 经验总结 |
| `wiki/projects/` | `source` | 项目资料 |
| `wiki/references/` | `source` | 参考资料 |
| `wiki/problems/` | `source` | 问题记录 |
| `wiki/methodologies/` | `methodology` | 方法论 |
| `wiki/user/` + `wiki/emotion/` | `personal` | 用户画像、情感记忆 |

### 短期记忆层（不迁移）

| 内容 | 位置 | 说明 |
|------|------|------|
| `YYYY-MM-DD-index.md` | OpenClaw memory/ | 任务索引，和会话机制绑定 |
| `YYYY-MM-DD/` | OpenClaw memory/ | 任务详情 |
| `YYYY-MM-DD.md` | OpenClaw memory/ | Dreaming 自动生成，只读 |

---

## 2. 接入验证（Phase 0）

### memory_search 兼容性测试

**日期**：2026-05-21

| 方案 | 结果 | 原因 |
|------|------|------|
| symlink | ❌ | builtin engine 忽略 symlink |
| vault path | ❌ | 只影响 wiki-maintainer，不影响 memory_search |
| extraPaths | 🟡 | 文件被发现（326→659），但 embedding 限速导致索引超时 |
| MCP 工具调用 | ✅ | 全链路通过，search/read/write/update 均正常 |

**决策**：走 MCP 混合模式。memory_search 继续索引 OpenClaw 自身记忆，不依赖它索引 Linglong 内容。

### MCP CRUD 验证

| 工具 | 结果 | 说明 |
|------|------|------|
| `search_wiki(query="MCP")` | ✅ | 返回 5 条结果，含 Linglong 元数据 |
| `get_template(facet="concept")` | ✅ | 模板获取正常 |
| `write_entity(...)` | ✅ | 写入正常，返回 entity_id |
| `read_entity(entity_id=...)` | ✅ | 读取完整内容正常 |
| `update_entity(entity_id=..., append=True)` | ✅ | 追加更新正常 |

---

## 3. OpenClaw 侧改动清单

### 总览

6 个文件，19 处改动。没有动 `memory/wiki/` 目录本身，没有动 `wiki-maintainer` 插件，没有动任何代码。

### 3.1 MEMORY.md（1 处）

| 改动 | 具体内容 |
|------|---------|
| 删除 wiki 索引 | 删掉 ~80 行文章链接（user/projects/concepts/experiences/methodologies/references/emotion 全部索引） |
| 删除旧目录结构 | 13 个 wiki 子目录的说明 |
| 删除旧使用规则 | "长期知识→memory/wiki/" 等旧规则 |
| 删除旧博客流水线 | 重复的旧版博客协作段落 |
| 新增 Linglong 说明 | 七分面说明 + MCP 读写指引 + "先 search 再 write" 流程 |

### 3.2 AGENTS.md（6 处）

| 改动 | 具体内容 |
|------|---------|
| 会话启动 #5 | `wiki/index.md` → 删除，只留 MEMORY.md |
| 注意事项 | `memory/wiki/` 是统一知识库 → 长期知识库在 Linglong |
| 记忆写入规则 | 长期知识→`memory/wiki/<category>/` → 通过 MCP 工具写入 Linglong |
| 记忆系统整章 | 短期+长期双层结构重写，新增"知识库读写流程"完整规范（查重→模板→写入） |
| 知识库使用规则 | 13 个 wiki 目录写入时机表 → 7 个 Linglong facet 写入时机表 |
| 项目启动检查 | `memory/wiki/projects/agent-mastery/startup-checklist.md` → `search_wiki` 搜索 |

### 3.3 HEARTBEAT.md（4 处）

| 改动 | 具体内容 |
|------|---------|
| #1 记忆整理 | "提取到 memory/wiki/" → "通过 MCP 写入 Linglong"；"wiki/ 目录不清理"段落重写为 Linglong 说明 |
| #4 成长检查 | "对比 wiki/user/communication-style.md" → `search_wiki(facet=personal)`；更新步骤改为 MCP 写入 |
| #6 自动成长 | "记录到 wiki/user/growth-auto-log.md" → "Linglong personal 分面" |
| #8 Wiki 健康检查 | 整项重写：手动扫描 wiki 目录 → `linglong lint`，频率改为由 Linglong 管理 |

### 3.4 growth-track 技能（5 处）

| 改动 | 具体内容 |
|------|---------|
| 核心模块表 | 3 行路径全部改为 Linglong personal 分面 |
| 自动检测表 | `wiki/user/growth-auto-log.md` → Linglong personal 分面 |
| 数据来源段落 | 4 个硬编码路径 → `search_wiki(facet="personal")` 搜索 |
| 用户画像更新流程 | "对比 communication-style.md" → `search_wiki` 搜索 + `update_entity`/`write_entity` 写入 |
| 情感记忆更新流程 | "在 emotion-memory.md 中记录" → `search_wiki` 搜索 + MCP 写入 |

### 3.5 task-review 技能（2 处）

| 改动 | 具体内容 |
|------|---------|
| 归档清单 | "更新到 wiki" → "通过 MCP 写入 Linglong 知识库" |
| 经验沉淀表 | 3 行 wiki 目录 → 3 行 Linglong facet + 去重流程说明 |

### 3.6 skill-spec 技能（1 处）

| 改动 | 具体内容 |
|------|---------|
| 执行前检查 | `memory/wiki/user/profile.md` → `search_wiki(facet="personal")` |

---

## 4. MCP 配置

### 注册信息

```json
// ~/.openclaw/openclaw.json → mcp.servers.linglong
{
  "command": "bash",
  "args": ["-c", "cd /home/user/projects/linglong && source venv/bin/activate && python -m linglong.mcp"]
}
```

### 可用工具（9 个）

| 工具 | 用途 | OpenClaw 使用场景 |
|------|------|-------------------|
| `search_wiki` | FTS5 全文搜索 | 查重、查找已有知识 |
| `search_similar` | 向量语义搜索 | 语义查重（降级到 FTS5） |
| `search_and_read` | 搜索+读取全文 | 一步获取完整内容 |
| `read_entity` | 读取完整内容 | 读取单条知识详情 |
| `write_entity` | 写入新知识 | 新增知识条目 |
| `update_entity` | 更新已有条目 | 追加补充已有知识 |
| `list_entities` | 浏览最近条目 | 启动时检查知识库状态 |
| `get_template` | 获取写作模板 | 写入前获取 facet 模板 |
| `list_templates` | 列出所有模板 | 了解可用 facet |

---

## 5. 已知问题与风险

| 编号 | 问题 | 严重度 | 状态 |
|------|------|--------|------|
| OC-001 | `memory_search` 无法索引 Linglong wiki | 🔴 高 | ✅ 已解决（走 MCP 模式） |
| OC-002 | HEARTBEAT 改动范围未量化 | 🟡 中 | ✅ 已完成（4 检查项 + 3 技能适配） |
| OC-003 | Dreaming 文件可能被误同步 | 🟡 中 | 需过滤（Phase 1 待做） |
| OC-004 | 插件技能禁用后功能缺失 | 🟡 中 | 暂不禁用 wiki-maintainer，观察 3-5 天 |
| OC-005 | MCP 通路稳定性未验证 | 🟡 中 | ✅ 已验证（CRUD 全链路通过） |

---

## 6. 回滚方案

如果 MCP 不稳定，快速切回直接文件操作：

1. 保留 `OpenClawSyncAdapter`（定期从 OpenClaw wiki 同步到 Linglong）
2. OpenClaw 恢复直接操作 `memory/wiki/` 目录
3. Linglong 退化为被动接收（sync 拉取模式）
4. `memory/wiki/` 保留作为备份，未删除

---

## 7. 优化记录

| 日期 | 优化项 | 结果 |
|------|--------|------|
| 2026-05-21 | Phase 0 验证（memory_search + MCP） | MCP 全链路通过，走 MCP 混合模式 |
| 2026-05-21 | 注册 Linglong MCP Server 到 OpenClaw | ✅ 配置生效，9 个工具可用 |
| 2026-05-21 | Phase 2 OpenClaw 侧改动 | ✅ 6 文件 19 处改动完成 |
