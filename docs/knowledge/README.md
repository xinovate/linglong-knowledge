# Knowledge — 跨 Agent 知识库模块

## 职责

- **统一存储**：文件系统（Markdown + YAML frontmatter）+ SQLite（结构化元数据 + FTS5）+ sqlite-vec（向量索引）
- **七分面分类**：source / entity / concept / synthesis / experience / methodology / personal
- **多 Agent 同步**：OpenClaw wiki、Claude Code memory、Codex CLI 通过 SyncAdapter 拉取
- **自动审核**：ReviewEngine 规则驱动，高置信度自动确认、低置信度标记待审
- **巡检修复**：LintEngine 索引一致性 + WikiLinks 完整性 + 内容冲突检测

## 核心组件

| 组件                | 路径 | 说明 |
|-------------------|------|------|
| `KnowledgeStore`  | `knowledge/store.py` | 统一存储接口（CRUD + 搜索 + 向量） |
| `ReviewEngine`    | `knowledge/review.py` | 自动审核引擎（facet 差异化规则） |
| `LintEngine`      | `knowledge/lint.py` | 巡检引擎（索引/WikiLinks/冲突/过期） |
| `Indexer`         | `knowledge/indexer.py` | 索引生成器（主索引 + 7 分面子索引） |
| `WikiLinks`       | `knowledge/wikilinks.py` | WikiLinks 解析器 |
| `EmbeddingService` | `knowledge/embeddings.py` | 向量嵌入服务（远程 embedding） |
| `init`            | `knowledge/init.py` | 知识库初始化（裸初始化/Git/备份/OpenClaw 迁移） |
| `SyncAdapters`      | `knowledge/sync/*.py` | OpenClaw / Claude Code / Codex 同步适配器 |

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
# .linglong.yaml
knowledge:
  wiki_path: ~/linglong/wiki
  db_path: ~/linglong/db/knowledge.db
  write_mode: confirm        # confirm | auto
  vector_enabled: true
  embedding_url: http://localhost:7997
  embedding_model: nomic-embed-text-v1.5
```

## 设计文档

完整设计文档在 [`design/00-overview.md`](design/00-overview.md)，包含子设计索引（D-01 ~ D-10）、依赖关系图、全局设计决策和开发里程碑。
