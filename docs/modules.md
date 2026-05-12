# 模块说明

## core（共享基础设施）

### 职责

- 定义共享数据模型
- 管理统一配置
- 提供跨模块工具函数

### 核心组件

#### models.py

定义系统核心数据模型：

- `Entity` — 知识条目
- `Task` — 调度任务
- `Source` — 来源信息
- `AgentID` / `HumanID` — 身份标识

#### config.py

统一配置管理：

- 支持环境变量（前缀 `LL_`）
- 支持 `.env` 文件
- 分层配置（通用 / 模块级）

### 使用示例

```python
from linglong.core.models import Entity, Source, SourceType
from linglong.core.config import get_config

# 创建实体
entity = Entity(
    content="# 标题\n\n内容",
    created_by="agent:violet",
    sources=[
        Source(type=SourceType.RSS, name="techcrunch")
    ],
)

# 读取配置
config = get_config()
print(config.knowledge.wiki_path)
```

---

## ingest（数据获取）

### 职责

- 从 RSS 源获取内容
- 从 API 获取数据
- 接收 AI 任务输出

### 核心组件

#### rss.py

RSS 源获取器：

- `RSSSource` — 单个 RSS 源配置
- `RSSIngestor` — 多源管理器

### 使用示例

```python
from linglong.ingest import RSSIngestor, RSSSource
from linglong.knowledge.store import KnowledgeStore

# 创建存储
store = KnowledgeStore()

# 创建获取器
ingestor = RSSIngestor(store)

# 添加 RSS 源
ingestor.add_source(
    RSSSource(
        name="techcrunch",
        url="https://techcrunch.com/feed/",
        category="tech",
    )
)

# 执行获取
import asyncio
results = asyncio.run(ingestor.ingest_all())
print(f"获取 {results['total']} 条，新建 {results['created']} 条")
```

### 扩展新源

```python
from linglong.ingest.rss import RSSSource

class CustomSource(RSSSource):
    async def fetch(self):
        # 自定义获取逻辑
        pass
```

---

## knowledge（知识库）

### 职责

- 存储知识条目（文件 + SQLite）
- 向量索引（语义搜索）
- 自动 Review 引擎
- 版本历史

### 核心组件

#### store.py

三层存储：

- **文件系统** — Markdown + YAML frontmatter
- **SQLite** — 结构化元数据
- **向量索引** — sqlite-vec（预留）

#### review.py

自动 Review 引擎：

- 规则驱动
- 支持自定义规则
- 自动确认 / 标记待审 / 需人工确认

### 使用示例

```python
from linglong.knowledge.store import KnowledgeStore
from linglong.knowledge.review import ReviewEngine
from linglong.core.models import Entity

# 创建存储
store = KnowledgeStore()

# 创建实体
entity = Entity(
    content="# Python 类型提示\n\nPython 3.11 引入了...",
    created_by="agent:violet",
    confidence=0.92,
)

# Review
engine = ReviewEngine()
entity = engine.review(entity)

# 存储
store.create(entity)

# 检索
results = store.search(status=EntityStatus.AUTO_CONFIRMED)
```

### Review 规则

默认规则：

| 规则 | 条件 | 动作 |
|------|------|------|
| 高置信度+可信来源 | confidence > 0.9 且来源在信任列表 | 自动确认 |
| 低置信度 | confidence < 0.6 | 标记待审 |
| 敏感内容 | 包含密码/API密钥等 | 需人工确认 |
| 内容过短 | 长度 < 50 | 标记待审 |

自定义规则：

```python
from linglong.knowledge.review import ReviewEngine, Rule, Action

engine = ReviewEngine()
engine.add_rule(
    Rule(
        name="my_rule",
        condition=lambda e: "特定关键词" in e.content,
        action=Action.FLAG_FOR_REVIEW,
        priority=200,
    )
)
```

---

## composer（内容生产）

### 职责

- 从知识库读取内容
- 提炼和格式化
- 生成多格式输出（Markdown / PPT / 视频脚本）

### 状态

✅ 已从 `linglong-pipeline` 项目迁移并入 monorepo。

### 核心组件

| 组件 | 路径 | 说明 |
|------|------|------|
| `Composer` | `composer/composer.py` | 编排器：读取 KnowledgeStore → 聚合 → 提炼 → 模板 → 输出 |
| `DraftManager` | `composer/draft.py` | 草稿生命周期管理（保存/列出/发布/废弃） |
| `ComposerState` | `composer/state.py` | 内容哈希去重与状态持久化 |
| `IngestAdapter` | `composer/ingest_adapter.py` | Entity → MemoryFragment 适配层 |
| `DailyAggregator` | `composer/distiller/aggregator.py` | 按天聚合记忆片段 |
| `LLMDistiller` | `composer/distiller/llm_distiller.py` | LLM 智能提炼与主题合并 |
| `BlogTemplate` | `composer/templates/blog.py` | Hexo 博客模板（frontmatter + 正文格式化） |
| `TextAssetGenerator` | `composer/assets/text.py` | 摘要、标签、字数统计等文本资产生成 |

### 设计要点

- 输入：只从 `knowledge` 模块读取（通过 `KnowledgeStore.search()`）
- 输出：返回 `dispatch_ready=True` 的结果，不直接处理发布
- 发布逻辑：已迁移到 `dispatch/_pending_publishers/` 占位，待 dispatch 模块启动

---

## dispatch（分发调度）— 未开始

### 职责

- 多平台适配器（博客 / 公众号 / 抖音 / 小红书 / 知乎）
- 发布调度（定时 / 立即 / 条件触发）
- 反馈收集（阅读量 / 点赞 / 评论）

### 状态

设计中，待 composer 迁移完成后开始。

---

## 模块间协作

```
ingest → knowledge → composer → dispatch
   ↑         ↑          ↑          ↓
   └─────────┴──────────┴──────────┘
              feedback loop
```

**规则**：
- 业务模块不直接通信
- 所有交互通过 `core` 的共享模型和配置
- 每个模块只关注自己的核心逻辑
