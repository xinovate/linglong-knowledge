# Knowledge — 跨 Agent 知识库模块

## 职责

- **统一存储**：兼容 OpenClaw wiki + Claude Code memory + Codex 记忆
- **向量索引**：语义搜索（远程 embedding 服务 + 本地 sqlite-vec fallback）
- **混合搜索**：关键词 + 语义 + 时间衰减 + MMR
- **多 Agent 读写**：通过 API/文件同步接入
- **自动 Review 引擎**：规则驱动，自动确认/标记待审
- **WikiLinks 支持**：`[[概念名]]` 自动解析

## 存储架构

```mermaid
graph TD
    subgraph Knowledge 三层存储
        A[文件系统<br/>Markdown + YAML frontmatter] --> D[KnowledgeStore API]
        B[SQLite<br/>结构化元数据 + Agent 命名空间] --> D
        C[向量索引<br/>sqlite-vec + embedding 服务] --> D
    end

    D --> E[search / get / create / update]

    subgraph Agent 同步
        F[OpenClaw wiki] -->|OpenClawSyncAdapter| D
        G[Claude Code memory] -->|ClaudeCodeSyncAdapter| D
        H[Codex CLI] -->|CodexSyncAdapter| D
    end
```

## 核心组件

| 组件 | 路径 | 说明 |
|------|------|------|
| `KnowledgeStore` | `knowledge/store.py` | 统一存储接口（SQLite + sqlite-vec） |
| `ReviewEngine` | `knowledge/review.py` | 自动审核引擎 |
| `EmbeddingService` | `knowledge/embeddings.py` | 向量嵌入服务 |
| `OpenClawSyncAdapter` | `knowledge/sync/openclaw.py` | OpenClaw wiki 同步 |
| `ClaudeCodeSyncAdapter` | `knowledge/sync/claude_code.py` | Claude Code memory 同步 |
| `CodexSyncAdapter` | `knowledge/sync/codex.py` | Codex CLI 同步 |

## Review 规则

| 规则 | 条件 | 动作 |
|------|------|------|
| 高置信度+可信来源 | confidence > 0.9 且来源在信任列表 | 自动确认 |
| 低置信度 | confidence < 0.6 | 标记待审 |
| 敏感内容 | 包含密码/API密钥 | 需人工确认 |
| 内容过短 | 长度 < 50 | 标记待审 |

## 使用示例

```python
from linglong.knowledge.store import KnowledgeStore
from linglong.core.models import Entity, EntityStatus

store = KnowledgeStore()

# 创建
entity = Entity(content="# Python 类型提示\n\nPython 3.11 引入了...", created_by="agent:claude")
store.create(entity)

# 检索
results = store.search(status=EntityStatus.AUTO_CONFIRMED, limit=100)

# 跨 Agent 同步
from linglong.knowledge.sync import OpenClawSyncAdapter
adapter = OpenClawSyncAdapter(wiki_path="~/.openclaw/workspace/memory/wiki")
adapter.sync_to_linglong()
```

## 配置

```yaml
# .linglong.yaml
knowledge:
  wiki_path: ~/linglong/wiki
  db_path: ~/linglong/db/knowledge.db
  vector_enabled: true
  embedding_url: http://localhost:7997
  embedding_model: nomic-embed-text-v1.5
  sync_confidence: 0.95
```

## 相关文档

- [跨 Agent 同步协议](sync-adapters.md)
