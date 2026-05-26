# API 文档

## 核心模型

### Entity

知识条目，系统的核心数据单元。

```python
class Entity(BaseModel):
    id: str                          # UUID
    content: str                     # Markdown 内容
    summary: Optional[str]           # AI 生成的摘要
    created_by: AgentID              # 创建者，如 "agent:violet"
    confirmed_by: Optional[HumanID]  # 确认者，如 "human:alice"
    confidence: ConfidenceScore      # 置信度，0.0 ~ 1.0
    status: EntityStatus             # 状态
    sources: List[Source]            # 来源列表
    relations: List[Relation]        # 关系列表
    versions: List[Version]          # 版本历史
    created_at: datetime             # 创建时间
    updated_at: datetime             # 更新时间
    embedding_id: Optional[str]      # 向量索引 ID
```

**状态枚举**：

```python
class EntityStatus(str, Enum):
    RAW = "raw"                      # 刚获取
    PENDING_REVIEW = "pending_review" # 待审核
    CONFIRMED = "confirmed"          # 人工确认
    AUTO_CONFIRMED = "auto_confirmed" # 自动确认
    REJECTED = "rejected"            # 已拒绝
```

### Source

来源信息，追踪数据的出处。

```python
class Source(BaseModel):
    type: SourceType     # rss / memory / api / ai_task / manual
    name: str            # 来源名称，如 "techcrunch"
    url: Optional[str]   # 来源 URL
    metadata: Dict       # 附加元数据
```

### Task

调度任务，用于跨模块编排。

```python
class Task(BaseModel):
    id: str
    project: str         # "ingest" / "knowledge" / "composer" / "dispatch"
    task_type: str       # 任务类型
    status: TaskStatus   # 状态
    scheduled_at: datetime
    entity_id: Optional[str]
    params: Dict
```

---

## 知识库 API

### KnowledgeStore

#### 创建实体

```python
from linglong.knowledge.store import KnowledgeStore
from linglong.core.models import Entity

store = KnowledgeStore()

entity = Entity(
    content="# 标题\n\n内容",
    created_by="agent:violet",
    confidence=0.85,
)
created = store.create(entity)
print(created.id)  # 自动生成的 UUID
```

#### 获取实体

```python
entity = store.get("entity-id")
if entity:
    print(entity.content)
```

#### 搜索实体

```python
# 按状态搜索
results = store.search(status=EntityStatus.AUTO_CONFIRMED)

# 按创建者搜索
results = store.search(created_by="agent:violet")

# 组合条件
results = store.search(
    status=EntityStatus.CONFIRMED,
    created_by="agent:claude",
    limit=10,
)
```

#### 更新实体

```python
entity.content = "更新后的内容"
entity.confidence = 0.95
updated = store.update(entity)
```

#### 删除实体

```python
success = store.delete("entity-id")
```

---

## Review 引擎 API

### ReviewEngine

#### 基本使用

```python
from linglong.knowledge.review import ReviewEngine
from linglong.core.models import Entity

engine = ReviewEngine()

entity = Entity(
    content="内容",
    created_by="agent:violet",
    confidence=0.92,
)

reviewed = engine.review(entity)
print(reviewed.status)  # 根据规则确定状态
```

#### 自定义规则

```python
from linglong.knowledge.review import Rule, Action

engine.add_rule(
    Rule(
        name="custom_rule",
        condition=lambda e: "特定关键词" in e.content,
        action=Action.FLAG_FOR_REVIEW,
        priority=200,
    )
)
```

**内置动作**：

| 动作 | 说明 |
|------|------|
| `AUTO_CONFIRM` | 自动确认 |
| `FLAG_FOR_REVIEW` | 标记待审 |
| `REQUIRE_HUMAN_CONFIRM` | 需人工确认 |
| `REJECT` | 拒绝 |

---

## 配置 API

### 获取配置

```python
from linglong.core.config import get_config

config = get_config()

# 通用配置
print(config.debug)
print(config.log_level)

# 知识库配置
print(config.knowledge.wiki_path)
print(config.knowledge.db_path)

# 获取配置
print(config.ingest.fetch_interval_minutes)
```

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LL_DEBUG` | 调试模式 | `false` |
| `LL_LOG_LEVEL` | 日志级别 | `INFO` |
| `LL_KNOWLEDGE_WIKI_PATH` | Wiki 目录 | `./wiki` |
| `LL_KNOWLEDGE_DB_PATH` | 数据库路径 | `./knowledge.db` |
| `LL_KNOWLEDGE_VECTOR_ENABLED` | 启用向量 | `true` |
| `LL_INGEST_FETCH_INTERVAL_MINUTES` | 获取间隔 | `30` |

---

## Ingest 采集 API

### IngestAgent

```python
from pathlib import Path
from linglong.ingest.agent import IngestAgent
from linglong.ingest.brief_history import BriefHistory
from linglong.ingest.feedback import FeedbackStore
from linglong.ingest.package import SourcePackage
from linglong.core.config import get_config

config = get_config()
packages = [SourcePackage(**p) for p in config.ingest.packages]

feedback_store = FeedbackStore()
brief_history = BriefHistory(Path.home() / "linglong" / "brief_history")
agent = IngestAgent(feedback_store=feedback_store, brief_history=brief_history)

# 生成早报（返回 markdown 字符串）
output = await agent.run(packages[0])
print(output)
```

### CLI

```bash
# 生成 AI 早报
linglong ingest
```

---

## 扩展接口

### 自定义数据源

```python
from linglong.core.models import Entity

class CustomSource:
    async def fetch(self) -> List[Entity]:
        # 实现获取逻辑
        pass
```

### 自定义 Review 规则

```python
from linglong.knowledge.review import Rule, Action

def my_condition(entity: Entity) -> bool:
    return "特定条件" in entity.content

rule = Rule(
    name="my_rule",
    condition=my_condition,
    action=Action.FLAG_FOR_REVIEW,
    priority=100,
)
```

---

## MCP Server API

Linglong 提供 MCP Server，支持 Claude Code 等 MCP Client 通过标准协议读写知识库。

### 工具清单

| 工具 | 功能 | 对应 Store 方法 |
|------|------|----------------|
| `search_wiki` | FTS5 全文搜索，返回摘要/预览 | `store.search()` |
| `search_similar` | 向量语义搜索（失败回退 FTS5） | `store.search_similar()` |
| `search_and_read` | 搜索并自动读取前 N 条完整内容 | `store.search()` + `store.get()` |
| `read_entity` | 读取完整内容+元数据 | `store.get()` |
| `write_entity` | 写入新知识 | `store.create()` |
| `update_entity` | 更新已有条目（替换或追加） | `store.update()` |
| `list_entities` | 浏览最近条目 | `store.search()` |
| `get_template` | 获取 facet 写作模板 | `TemplateManager.get_template()` |
| `list_templates` | 列出所有可用模板 | `TemplateManager.list_templates()` |

### 配置方式

详见下方 [MCP Server 接入配置](#mcp-server-接入配置)。基本方式：

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

### 搜索行为说明

**`search_wiki`** 返回轻量级预览，优先使用 Entity 的 AI 生成摘要（`summary`），否则截取正文前 500 字符。这种分层设计让 Agent 快速判断相关性，避免 Token 浪费。

**`search_and_read`** 是 convenience 工具，内部先搜索再对前 N 个结果调用 `read_entity`，一次调用返回完整内容。适合"详细讲讲 X"这类需要全文的情境。

### write_entity 最佳实践

`write_entity` 的 tool description 会引导 Claude Code：写入前先搜索同类 facet 的文档，参考其 frontmatter 风格和结构，保持知识库格式一致性。也可以通过 `reference_entity_ids` 参数显式传入参考文档 ID。

### 模板体系

**`get_template(facet)`** 返回指定 facet 的写作模板（Markdown 格式，含 YAML frontmatter 和占位符）。Agent 写入前可调用此工具获取结构参考。

当前提供 6 个模板：
- `concept` — 概念类（定义、核心要点、实际应用）
- `experience` — 经验类（背景、问题、解决方案、踩坑记录）
- `project` — 项目类（目标、进度、关键决策、学习笔记）
- `methodology` — 方法论类（流程、检查清单、常见误区）
- `reference` — 参考资料类（外部参考、资料链接、摘录、待验证）
- `personal` — 个人类（偏好、规则、历史变化）

### Ingest 采集工具

| 工具 | 功能 | 参数 |
|------|------|------|
| `fetch_rss` | 采集 RSS feed | `url`, `name?`, `max_items?` |
| `execute_package` | 执行采集包（YAML 文件路径） | `package_path` |
| `generate_brief` | 生成 AI 早报（使用配置中的包） | 无 |
| `search_web` | 网页搜索（SearXNG） | `query`, `max_results?` |
| `record_feedback` | 记录采集偏好 | `content_hash`, `feedback`, `tags?` |

采集工具返回 Entity 列表，Agent 讨论后可通过 `write_entity` 写入知识库。

`generate_brief` 读取 `.linglong.yaml` 中配置的第一个 package，无需文件路径。适合 Agent 在对话中直接触发生成。

`search_web` 提供即时网页搜索能力，不依赖早报流程。适合 Agent 在对话中按需查询。

### MCP Server 接入配置

#### Claude Code

在 `~/.claude/settings.json` 的 `projects` 中添加 MCP 配置，`env` 字段注入 API Key：

```json
{
  "mcpServers": {
    "linglong": {
      "command": "bash",
      "args": ["-c", "cd /path/to/linglong && source venv/bin/activate && python -m linglong.mcp"],
      "env": {
        "SEARXNG_API_KEY": "your-key",
        "RSSHUB_ACCESS_KEY": "your-key",
        "EMBEDDING_API_KEY": "your-key"
      }
    }
  }
}
```

#### 注意事项

- MCP Server 运行在自己的事件循环中，内部使用 `_run_async()`（ThreadPoolExecutor）处理异步调用
- RSSHub `?key=` 仅追加到 `:1200` 端口的 RSSHub URL，不影响直接 RSS 源
- GitHub API 优先使用 `gh auth token` 认证（5000 req/hr），未认证降级到 60 req/hr

```bash
python -m linglong.mcp
```
