# API 文档

Linglong 知识库的 Python API、MCP 工具接口和配置说明。

## 核心模型

### Entity

知识条目，系统的核心数据单元。

```python
from linglong.core.models import Entity, EntityFacet, EntityStatus

entity = Entity(
    content="# Python Type Hints\n\n...",
    facet=EntityFacet.CONCEPT,
    created_by="agent:claude",
    confidence=0.92,
    status=EntityStatus.AUTO_CONFIRMED,
)
```

主要字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | `str` | UUID，自动生成 |
| `content` | `str` | Markdown 内容 |
| `facet` | `EntityFacet` | 六分面分类 |
| `group` | `str \| None` | facet 下的语义子目录 |
| `summary` | `str \| None` | AI 生成的摘要 |
| `created_by` | `AgentID` | 创建者（如 `agent:claude`） |
| `confirmed_by` | `HumanID \| None` | 确认者（如 `human:alice`） |
| `confidence` | `ConfidenceScore` | AI 置信度，0.0–1.0 |
| `status` | `EntityStatus` | 生命周期状态 |
| `sources` | `list[Source]` | 来源列表 |
| `relations` | `list[Relation]` | 关系列表 |
| `versions` | `list[Version]` | 版本历史 |
| `embedding_id` | `str \| None` | sqlite-vec 索引 ID |

状态枚举：

| 状态 | 说明 |
|------|------|
| `RAW` | 刚创建 |
| `PENDING_REVIEW` | 待审核 |
| `CONFIRMED` | 人工确认 |
| `AUTO_CONFIRMED` | 自动确认（ReviewEngine） |
| `REJECTED` | 已拒绝 |

六分面分类：

| Facet | 说明 |
|-------|------|
| `concept` | 概念 |
| `experience` | 经验 |
| `methodology` | 方法论 |
| `project` | 项目 |
| `reference` | 参考资料 |
| `personal` | 个人 |

---

## 知识库 API

### KnowledgeStore

三层存储的统一接口：Filesystem（Markdown）+ SQLite（元数据）+ sqlite-vec（向量索引）。

```python
from linglong.knowledge.store import KnowledgeStore

store = KnowledgeStore()
```

#### 创建实体

```python
from linglong.core.models import Entity, EntityFacet

entity = Entity(
    content="# 标题\n\n内容",
    facet=EntityFacet.CONCEPT,
    created_by="agent:violet",
    confidence=0.85,
)
created = store.create(entity)
print(created.id)
```

#### 读取实体

```python
entity = store.get("entity-id")
```

#### 搜索

```python
# 自动选择最佳模式（关键词/向量/混合）
results = store.search_auto(query="machine learning", limit=10)

# 语义向量搜索
results = store.search_similar(query="embedding model", limit=5)

# 按条件搜索
results = store.search(facet=EntityFacet.CONCEPT, limit=20)
results = store.search(since="2025-01-01", limit=10)
```

#### 更新实体

```python
entity.content = "更新后的内容"
updated = store.update(entity)
```

#### 删除实体

```python
success = store.delete("entity-id")
```

#### 同步与索引

```python
# 从外部 Agent 目录同步
store.sync()

# 重建向量索引
store.rebuild_embeddings()
```

---

## Review 引擎

自动质量控制，基于规则评估实体状态。

```python
from linglong.knowledge.review import ReviewEngine, Rule, Action

engine = ReviewEngine()

reviewed = engine.review(entity)
print(reviewed.status)  # AUTO_CONFIRMED / PENDING_REVIEW / REJECTED
```

### 内置规则

| 规则 | 条件 | 动作 |
|------|------|------|
| `high_confidence_trusted` | 置信度 > 0.9 + 可信来源 | `AUTO_CONFIRM` |
| `low_confidence` | 置信度 < 0.6 | `FLAG_FOR_REVIEW` |
| `sensitive_content` | 包含敏感词/密码/API key | `REQUIRE_HUMAN_CONFIRM` |
| `too_short` | 内容 < 50 字符 | `FLAG_FOR_REVIEW` |
| `personal_requires_review` | personal facet | `REQUIRE_HUMAN_CONFIRM` |
| `source_auto_confirm` | reference facet + 置信度 ≥ 0.7 | `AUTO_CONFIRM` |

### 自定义规则

```python
engine.add_rule(
    Rule(
        name="custom_rule",
        condition=lambda e: "特定关键词" in e.content,
        action=Action.FLAG_FOR_REVIEW,
        priority=200,
    )
)
```

动作类型：

| 动作 | 说明 |
|------|------|
| `AUTO_CONFIRM` | 自动确认 |
| `FLAG_FOR_REVIEW` | 标记待审 |
| `REQUIRE_HUMAN_CONFIRM` | 需人工确认 |
| `REJECT` | 拒绝 |
| `MERGE` | 合并 |

---

## 跨 Agent 同步

三个 Sync Adapter，从各 Agent 本地目录 pull 知识到 KnowledgeStore。

```python
from linglong.knowledge.sync import OpenClawSyncAdapter, ClaudeCodeSyncAdapter, CodexSyncAdapter

# OpenClaw wiki → KnowledgeStore
adapter = OpenClawSyncAdapter()
entities = adapter.pull()

# Claude Code memory → KnowledgeStore
adapter = ClaudeCodeSyncAdapter()
entities = adapter.pull()
```

---

## MCP Server

FastMCP Server，提供 8 个知识库工具，Agent 通过 MCP 协议读写知识库。

### 工具清单

| 工具 | 功能 | 核心参数 |
|------|------|----------|
| `search_wiki` | 自动选择最佳搜索模式 | `query`, `facet?`, `limit?` |
| `search_similar` | 语义向量搜索（不可用退化为 FTS5） | `query`, `facet?`, `limit?` |
| `search_and_read` | 搜索 + 读取 Top-N 完整内容 | `query`, `facet?`, `limit?`, `max_content_length?` |
| `read_entity` | 按 ID 读取完整实体 | `entity_id` |
| `write_entity` | 创建新实体 | `title`, `content`, `facet`, `group?`, `tags?` |
| `update_entity` | 更新实体（替换或追加） | `entity_id`, `content`, `append?` |
| `list_entities` | 按时间线浏览 | `facet?`, `since?`, `limit?` |
| `get_template` | 获取 facet 写作模板 | `facet` |
| `list_templates` | 列出所有可用模板 | 无 |
| `rebuild` | 重建索引或向量 | `mode` (`embeddings`/`sync`/`index`) |

### 工具行为说明

**搜索工具返回轻量预览**：优先使用 Entity 的 `summary` 字段，否则截取正文前 500 字符。Agent 可先搜索判断相关性，再用 `read_entity` 获取全文。

**`search_and_read`** 是组合工具，一次调用返回搜索结果的完整内容（支持截断）。适合"详细讲讲 X"这类需要全文的场景。

**`write_entity`** 写入前自动检测 facet 拥挤度——如果 facet 根目录下未分组实体过多，返回 warning 建议指定 group。

### 部署模式

#### stdio（本地）

```bash
python -m linglong.mcp
```

Claude Code 等本地 Agent 通过子进程连接。

#### streamable-http（远程）

```bash
pip install linglong[server]
python -m linglong.mcp --transport streamable-http --port 9900
```

通过 Cloudflare Tunnel 暴露，路由为 `/mcp/knowledge`。

### 接入配置

```json
{
  "mcpServers": {
    "linglong-knowledge": {
      "command": "/path/to/linglong/.venv/bin/python",
      "args": ["-m", "linglong.mcp"]
    }
  }
}
```

远程接入（需要 Token 认证）：

```json
{
  "mcpServers": {
    "linglong-knowledge": {
      "url": "https://your-domain.com/mcp/knowledge",
      "headers": { "Authorization": "Bearer your-token" }
    }
  }
}
```

### Token 认证

远程 MCP 支持 Redis 动态 Token 认证。Token 格式：`knowledge-{random}`。

```bash
# 新增 token
redis-cli SET knowledge-abc123 active

# 查看所有 token
redis-cli KEYS 'knowledge-*'

# 删除 token
redis-cli DEL knowledge-abc123
```

配置 `mcp.redis_url` 启用 Redis 认证，不配置则降级为静态 `auth_token`。

---

## 配置

### Python API

```python
from linglong.core.config import get_config

config = get_config()

# 知识库配置
print(config.knowledge.wiki_path)
print(config.knowledge.db_path)
print(config.knowledge.vector_enabled)

# MCP 配置
print(config.mcp.transport)
print(config.mcp.port)
```

### 配置文件 `.knowledge.yml`

```yaml
knowledge:
  wiki_path: ~/knowledge/wiki
  db_path: ~/knowledge/db/knowledge.db
  generate_embeddings: true
  write_mode: confirm
  auto_lint: false
  max_versions: 10
  db_mode: wal

mcp:
  transport: stdio
  host: 127.0.0.1
  port: 9900
  redis_url: ""
  auth_token: null
```

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `KB_DEBUG` | 调试模式 | `false` |
| `KB_LOG_LEVEL` | 日志级别 | `INFO` |
| `KB_KNOWLEDGE_WIKI_PATH` | Wiki 目录 | `~/knowledge/wiki` |
| `KB_KNOWLEDGE_DB_PATH` | 数据库路径 | `~/knowledge/db/knowledge.db` |
| `KB_KNOWLEDGE_VECTOR_ENABLED` | 启用向量搜索 | `true` |
| `KB_KNOWLEDGE_EMBEDDING_URL` | Embedding 服务地址 | `http://localhost:7997` |
| `KB_KNOWLEDGE_EMBEDDING_API_KEY` | Embedding API Key | `None` |
| `KB_MCP_TRANSPORT` | 传输协议 | `stdio` |
| `KB_MCP_HOST` | HTTP 监听地址 | `127.0.0.1` |
| `KB_MCP_PORT` | HTTP 监听端口 | `9900` |
| `KB_MCP_REDIS_URL` | Redis URL（动态 Token） | `""` |
| `KB_MCP_AUTH_TOKEN` | 静态认证 Token | `None` |
