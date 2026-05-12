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

## RSS 获取 API

### RSSIngestor

```python
from linglong.ingest import RSSIngestor, RSSSource
from linglong.knowledge.store import KnowledgeStore

store = KnowledgeStore()
ingestor = RSSIngestor(store)

# 添加源
ingestor.add_source(
    RSSSource(
        name="techcrunch",
        url="https://techcrunch.com/feed/",
        category="tech",
    )
)

# 获取
import asyncio
results = asyncio.run(ingestor.ingest_all())
print(results)  # {"total": 50, "created": 10, "failed": 0}
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
