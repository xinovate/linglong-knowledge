# Knowledge — 跨 Agent 知识库模块

## 定位与边界

知识库**只做知识沉淀**，不碰任务管理和 Agent 配置。

| 层 | 归属 | 说明 |
|---|---|---|
| **任务 / 会话状态** | Agent 自己管理 | Claude Code 的 task list、OpenClaw 的 YYYY-MM-DD-index.md |
| **工作偏好** | Agent 自己管理 | Claude Code 的 auto memory、OpenClaw 的 AGENTS.md |
| **共性知识** | **知识库（Linglong）** | 概念、经验、决策、实体、方法论 — 跨 Agent 共享的长期知识 |

知识库不做：
- 任务同步（各 Agent 各管各的）
- Agent 配置下发（各 Agent 自己配）
- 实时协作（知识库是被动存储，不是消息队列）

## 职责

- **统一存储**：文件系统（Markdown + YAML frontmatter）+ SQLite（结构化元数据 + FTS5）+ sqlite-vec（向量索引）
- **六分面分类 + group 子目录**：concept / experience / methodology / project / reference / personal
- **智能搜索**：FTS5 关键词 + 向量语义 + RRF 混合搜索 + 自动模式路由
- **Agent 接入**：MCP Server（9 个工具）+ CLI + SyncAdapter，支持任意 MCP 客户端接入
- **自动审核**：ReviewEngine 规则驱动，高置信度自动确认、低置信度标记待审
- **巡检修复**：LintEngine 索引一致性 + WikiLinks 完整性 + 内容冲突检测

## 核心组件

| 组件                | 路径 | 说明 |
|-------------------|------|------|
| `KnowledgeStore`  | `knowledge/store.py` | 统一存储接口（CRUD + 搜索 + 向量） |
| `ReviewEngine`    | `knowledge/review.py` | 自动审核引擎（facet 差异化规则） |
| `LintEngine`      | `knowledge/lint.py` | 巡检引擎（索引/WikiLinks/冲突/过期） |
| `Indexer`         | `knowledge/indexer.py` | 索引生成器（主索引 + 6 分面子索引） |
| `WikiLinks`       | `knowledge/wikilinks.py` | WikiLinks 解析器 |
| `EmbeddingService` | `knowledge/embeddings.py` | 向量嵌入服务（远程 embedding） |
| `init`            | `knowledge/init.py` | 知识库初始化（裸初始化/Git/备份/OpenClaw 迁移） |
| `SyncAdapters`      | `knowledge/sync/*.py` | OpenClaw / Claude Code / Codex 同步适配器 |
| `MCP Server`       | `mcp/`              | 9 个 MCP 工具，供 Agent 通过标准协议接入 |

## Agent 接入

知识库通过 MCP（Model Context Protocol）标准协议接入各 Agent，提供 9 个工具：

| 工具 | 用途 |
|------|------|
| `search_wiki` / `search_similar` / `search_and_read` | 搜索知识 |
| `read_entity` / `write_entity` / `update_entity` | 读写知识 |
| `list_entities` / `get_template` / `list_templates` | 浏览与模板 |

| Agent | 接入方式 | 状态 |
|-------|----------|------|
| Claude Code | MCP | ✅ 已接入 |
| OpenClaw (violet) | MCP | ✅ 已接入 |
| Codex CLI | CLI | ⚪ 预留 |

详细接入方案见 [三方接入指南](agents/01-onboarding.md)。

### Agent 文档

| 文档 | 内容 |
|------|------|
| [agents/00-overview.md](agents/00-overview.md) | Agent 接入架构总览 |
| [agents/01-onboarding.md](agents/01-onboarding.md) | 三方接入指南（快速/深度/移除） |
| [agents/claude-code.md](agents/claude-code.md) | Claude Code 接入详情 |
| [agents/openclaw.md](agents/openclaw.md) | OpenClaw 接入详情 |

## 快速开始

```python
from linglong.knowledge.store import KnowledgeStore
from linglong.core.models import Entity, EntityFacet, EntityStatus

store = KnowledgeStore()

# 创建（facet 必填）
entity = store.create(Entity(
    content="# Python 类型提示\n\nPython 3.11 引入了...",
    facet=EntityFacet.CONCEPT,
    created_by="agent:claude",
))

# 搜索（FTS5 全文 + facet/status/since 过滤）
results = store.search(query="类型", facet=EntityFacet.CONCEPT)

# 向量搜索
results = store.search_similar(query="语义搜索", facet=EntityFacet.CONCEPT)

# 同步外部知识源
from linglong.knowledge.sync.openclaw import OpenClawSyncAdapter
adapter = OpenClawSyncAdapter(wiki_path="~/.openclaw/workspace/memory/wiki")
adapter.sync_to_linglong()
```

## 配置

```yaml
# .knowledge.yml
knowledge:
  wiki_path: ~/knowledge/wiki
  db_path: ~/knowledge/db/knowledge.db
  write_mode: confirm        # confirm | auto
  vector_enabled: true
  embedding_url: http://localhost:7997
  embedding_model: nomic-ai/nomic-embed-text-v1.5
```

## 设计文档

完整设计文档在 [`design/00-overview.md`](design/00-overview.md)，包含子设计索引（D-01 ~ D-10）、依赖关系图、全局设计决策和开发里程碑。
