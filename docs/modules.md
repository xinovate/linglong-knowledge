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

- 支持 `.linglong.yaml` 配置文件（推荐）
- 支持环境变量（前缀 `LL_`）
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

## ingest（信息获取层）

### 职责

- **Web Search**：搜索引擎采集（DuckDuckGo、必应 CN）
- **Web Fetch**：并行抓取预定义网站列表
- **API 调用**：GitHub API、Twitter API、自定义 REST API
- **RSS 源**：RSS feed 获取
- **爬虫**：Playwright / Scrapy 预留接口
- **AI 任务输出**：接收各 Agent 产出的结构化数据

### 核心设计

**可配置信息源**（YAML 定义，继承 ai-morning-brief 能力）：

```yaml
# sources/tech-radar.yaml
name: "AI 技术雷达"
schedule: "0 7 * * *"
sources:
  - type: web_search
    engine: duckduckgo
    queries: ["Karpathy AI", "OpenAI news"]
  - type: web_fetch
    urls: ["https://anthropic.com/news", "https://openai.com/news"]
  - type: api
    endpoint: "https://api.github.com/search/repositories"
    params: { q: "created:>7d ai OR agent", sort: "stars" }
validation:
  cross_reference_min: 2
  max_age_days: 3
```

**真实性验证**（5 层检查）：

| 层级 | 检查方法 | 示例 |
|------|----------|------|
| 多源交叉验证 | 同一事件在≥2个数据源出现 → 可信 | OpenAI 融资在财新+36kr都有报道 |
| 数字合理性 | 融资金额在历史合理范围内 | OpenAI 融资 $40B 合理，$122B 异常 |
| 时间有效性 | 新闻日期在近 3 天内 | 过期内容静默跳过 |
| 源头权威性 | 优先官方渠道 | 工信部政策 > 自媒体解读 |
| 常识判断 | 事件是否符合行业逻辑 | 单周增长 172K stars → 异常 |

### 核心组件（v0.5 通用化架构）

#### adapter.py

SourceAdapter 插件接口：

- `SourceAdapter` — 抽象基类，所有源适配器必须实现 `fetch()` 和 `health_check()`
- `AdapterRegistry` — 适配器注册表，支持运行时发现

#### package.py

YAML 配置模型：

- `SourcePackage` — 主题无关的采集包定义
- `SourceDefinition` — 单个源定义（id / type / config / metadata）
- `VerificationSettings` — 真实性验证配置

#### verification.py

TruthVerificationEngine — 5 层真实性验证：

- 多源交叉验证
- 数字合理性检查
- 时间有效性检查
- 来源权威性加权
- 常识判断启发式

#### executor.py

PackageExecutor — 并行执行引擎：

- 并发抓取包内所有启用源
- 去重（按 entity ID）
- 验证 → 审核 → 存储流水线

#### adapters/

内置适配器：

- `RSSAdapter` — RSS 源（包装现有 RSSSource）
- `WebFetchAdapter` — 并行 HTTP 抓取
- `WebSearchAdapter` — 网页搜索（DuckDuckGo / Bing CN，placeholder）
- `APIAdapter` — REST API 调用（支持 `{date-7d}` 动态参数）

### 使用示例

```python
from linglong.ingest import PackageExecutor, SourcePackage
from linglong.knowledge.store import KnowledgeStore
import asyncio

# 从 YAML 加载采集包
package = SourcePackage.from_yaml("examples/packages/ai-morning-brief.yaml")

# 执行采集
store = KnowledgeStore()
executor = PackageExecutor(store=store)
results = asyncio.run(executor.execute(package))
print(f"获取 {results['total']} 条，新建 {results['created']} 条")
```

### 扩展示例：自定义 Adapter

```python
from linglong.core.models import Entity
from linglong.ingest.adapter import SourceAdapter, AdapterRegistry

class MyAdapter(SourceAdapter):
    adapter_type = "my_source"

    async def fetch(self) -> list[Entity]:
        # 自定义获取逻辑
        return []

    def health_check(self) -> bool:
        return True

AdapterRegistry.register(MyAdapter)
```

---

## knowledge（跨 Agent 知识库）

### 职责

- **统一存储**：兼容 OpenClaw wiki 结构 + Claude Code memory 结构 + Codex 记忆
- **向量索引**：语义搜索（远程 OpenClaw 服务 + 本地 sqlite-vec fallback）
- **混合搜索**：关键词 + 语义 + 时间衰减 + MMR
- **多 Agent 读写**：OpenClaw、Claude Code、Codex 通过 API/文件同步接入
- **WikiLinks 支持**：`[[概念名]]` 自动解析和补全
- **短期→长期转换**：自动判断任务是否有长期价值，有则写入 wiki
- **自动 Review 引擎**
- **版本历史**

### 核心组件

#### store.py

三层存储：

- **文件系统** — Markdown + YAML frontmatter，兼容 OpenClaw wiki/ 目录结构
- **SQLite** — 结构化元数据，支持 Agent 命名空间（`openclaw:`、`claude:`、`codex:`）
- **向量索引** — 远程 OpenClaw embedding 服务（nomic-embed-text-v1.5）+ sqlite-vec 本地 fallback

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

### 跨 Agent 同步

```python
# OpenClaw wiki 同步
from linglong.knowledge.sync import OpenClawSyncAdapter

adapter = OpenClawSyncAdapter(wiki_path="/Users/wangxin/.openclaw/workspace/memory/wiki")
adapter.sync_to_linglong()

# Claude Code memory 同步（预留）
from linglong.knowledge.sync import ClaudeCodeSyncAdapter

adapter = ClaudeCodeSyncAdapter(memory_path="/Users/wangxin/.claude/projects/.../memory")
adapter.sync_to_linglong()
```

---

## composer（知识编译引擎）

### 职责

- 从知识库读取各 Agent 产出的碎片
- **主题聚类**：识别跨天、跨 Agent 的关联内容
- **LLM 提炼**：总结、加解读、生成封面图提示词
- **生成多格式输出**：博客、早报、周报、PPT 大纲、视频脚本
- **内容验证**：检查是否符合模板规范

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
- 输出：返回 `dispatch_ready=True` 的结果；当 `auto_publish=True` 时自动调用 `DispatchManager.publish()`
- 草稿模式：生成内容到 `DraftManager` 等待人工审核

### 编译流程

```
知识库碎片（多 Agent 产出）
           │
           ▼
   ┌───────────────┐
   │  IngestAdapter │  ← 统一读取接口
   └───────┬───────┘
           │
   ┌───────┴───────┐
   │  ThemeAggregator│  ← 按主题聚类（跨天、跨 Agent）
   └───────┬───────┘
           │
   ┌───────┴───────┐
   │  LLM Distiller  │  ← 提炼、总结、加解读
   └───────┬───────┘
           │
   ┌───────┴───────┐
   │  TemplateEngine │  ← 套用博客/早报/PPT/视频脚本模板
   └───────┬───────┘
           │
           ▼
    成品（Markdown / PPT / 视频脚本）
```

---

## dispatch（智能分发器）

### 职责

- **发布队列**：待发布 / 发布中 / 已发布 / 失败（可重试）
- **内容路由**：根据内容类型自动分发到不同平台
  - 博客文章 → Hexo (`linglong.wiki`) → Git Workflow Publisher
  - AI 早报 → 钉钉（复用 OpenClaw dingtalk-connector）
  - 短视频脚本 → 抖音（脚本 + AI 封面图）
  - Twitter 线程 → Twitter/X API
  - 周报 → 邮件 / Notion
- **反馈收集**：阅读量、点赞、评论回流到 knowledge

### 状态

✅ 已完成（v0.8）。DispatchManager + LocalPublisher + HexoPublisher + 集成测试。

### 路由规则示例

```python
routes = [
    {"content_type": "blog", "template": "blog", "publisher": "hexo"},
    {"content_type": "morning_brief", "template": "morning_brief", "publisher": "dingtalk"},
    {"content_type": "short_video_script", "template": "ppt", "publisher": "douyin"},
]
```

---

## CLI（命令行入口）

### 职责

提供可执行的命令行入口，把库级别的模块串联成可操作的流水线。

### 命令列表

```bash
linglong --help
├── ingest              # 执行所有启用的采集包
├── compose [--dry-run|--draft]  # 运行内容生产流水线
├── publish <draft_id>  # 发布草稿到指定发布器
└── sync <openclaw|claude|codex> [--path]  # 同步 Agent 知识
```

### 使用示例

```bash
# 运行采集
linglong ingest

# 试运行内容生产（不实际保存）
linglong compose --dry-run

# 生成草稿等待审核
linglong compose --draft

# 同步 Claude Code memory
linglong sync claude

# 同步指定路径
linglong sync openclaw --path ~/.openclaw/workspace/memory/wiki
```

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
- Agent 通过 knowledge 模块统一读写，避免各自为政
- CLI 层负责编排调用顺序，模块内部保持无状态
