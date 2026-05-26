# D-01 流水线设计

> 状态：✅ 已实现 | 最后更新：2026-05-26

---

## 概述

`Composer.run()` 是一条完整的内容生产流水线，从知识库提取实体到输出可发布文章。支持无差别拉取和语义查询两种模式。

---

## 完整流程图

```mermaid
flowchart TD
    START([Composer.run]) --> TOPIC{topic?}

    TOPIC -->|有| SEMANTIC["KnowledgeStore.search_similar<br/>query=topic<br/>向量语义搜索"]
    TOPIC -->|无| FULL["KnowledgeStore.search<br/>status=AUTO_CONFIRMED<br/>全量拉取 limit=100"]

    SEMANTIC --> ADAPT["IngestAdapter.adapt_many<br/>Entity → MemoryFragment"]
    FULL --> ADAPT

    ADAPT --> EXTRACT

    subgraph EXTRACT["1. 提取实体"]
        E1["KnowledgeStore"]
        E2["IngestAdapter.adapt_many<br/>Entity → MemoryFragment"]
    end

    EXTRACT --> DEDUP["2. ComposerState.filter_new<br/>MD5 哈希去重"]
    DEDUP --> CHECK_EMPTY{有新片段?}
    CHECK_EMPTY -->|否| EMPTY([返回空结果])
    CHECK_EMPTY -->|是| GROUP

    subgraph GROUP["3. 分组策略"]
        G1{distiller_use_llm?}
        G1 -->|false| G2["DailyAggregator<br/>按天聚合"]
        G1 -->|true| G3["LLMDistiller<br/>按主题分组"]
    end

    GROUP --> PROCESS

    subgraph PROCESS["4. 逐组处理 _process_day()"]
        P1["提炼素材<br/>LLM 或 规则模式"]
        P2["BlogTemplate.apply<br/>frontmatter + 引言 + 配图"]
        P3{"QualityLint<br/>质量校验"}
        P3 -->|通过| P4["DraftManager.save_draft<br/>status=pending"]
        P3 -->|未通过| P5["DraftManager.save_draft<br/>status=needs_review"]

        P1 --> P2 --> P3
    end

    PROCESS --> PUBLISH{auto_publish?}
    PUBLISH -->|是| DISPATCH["DispatchManager.publish"]
    PUBLISH -->|否| LOG

    DISPATCH --> LOG["OutputLog.append<br/>溯源记录"]
    LOG --> RESULT([ComposerResult])

    style EXTRACT fill:#4CAF50,color:#fff
    style GROUP fill:#2196F3,color:#fff
    style PROCESS fill:#FF9800,color:#fff
    style DISPATCH fill:#9C27B0,color:#fff
```

---

## 分组策略对比

| | 按天聚合 | 按主题分组 |
|---|---|---|
| 配置 | `distiller_use_llm: false` | `distiller_use_llm: true` |
| 实现 | `DailyAggregator` | `LLMDistiller` |
| 成本 | 零 | LLM 调用 |
| 效果 | 每天一篇 | 跨天合并同主题 |
| 适用 | 碎片化记录 | 有明确主题线索的内容 |

---

## 语义查询模式

`Composer.run(topic="agent-mastery 项目实战")` 触发语义查询模式：

```mermaid
sequenceDiagram
    participant User
    participant Composer
    participant Store as KnowledgeStore
    participant Adapter as IngestAdapter

    User->>Composer: run(topic="agent-mastery 项目实战")
    Composer->>Store: search_similar(query=topic)<br/>status=AUTO_CONFIRMED, limit=50
    Store->>Store: 向量相似度匹配<br/>vec_distance_cosine 排序
    Store-->>Composer: 相关 Entity 列表
    Composer->>Adapter: adapt_many(entities)
    Adapter-->>Composer: MemoryFragment 列表

    Note over Composer: 后续流程同标准模式
```

与标准模式的区别：

| | 标准模式 | 语义查询模式 |
|---|---|---|
| 触发 | `run()` / `run(since=...)` | `run(topic="...")` |
| 知识库查询 | `search(status=..., limit=100)` | `search_similar(query=topic, limit=50)` |
| 匹配方式 | 全量拉取 | 向量余弦相似度 |
| LLM 分组 | 自动发现主题 | 围绕指定主题分组 |
| 适用场景 | 定期全量编排 | 按需生成专题文章 |

---

## _process_day 详细流程

```mermaid
sequenceDiagram
    participant Composer
    participant Distiller as Distiller (LLM/规则)
    participant Template as BlogTemplate
    participant Lint as QualityLint
    participant Draft as DraftManager
    participant Dispatch as DispatchManager
    participant Log as OutputLog

    Composer->>Distiller: distill(date, fragments)
    Distiller-->>Composer: ArticleMaterial

    Composer->>Template: apply(content, metadata)
    Template-->>Composer: formatted markdown

    Composer->>Lint: check(formatted, metadata)
    Lint-->>Composer: LintResult

    alt draft=true
        alt lint 通过
            Composer->>Draft: save_draft(status=pending)
        else lint 未通过
            Composer->>Draft: save_draft(status=needs_review)
        end
    else auto_publish=true
        Composer->>Dispatch: publish(article)
        Dispatch-->>Composer: PublishResult
        Composer->>Log: append(entity_ids, article_id)
    end
```

---

## MemoryFragment 模型

```python
@dataclass
class MemoryFragment:
    source: str           # 来源标识（entity 的 source name）
    content: str          # 内容正文
    timestamp: datetime   # 实体创建时间
    metadata: dict        # entity_id, confidence, status, created_by
    raw_path: str = ""
```

---

## ArticleMaterial 模型

```python
class ArticleMaterial:
    date: str                         # 日期或主题 key
    fragments: list[MemoryFragment]   # 原始片段
    title: str                        # 文章标题
    excerpt: str                      # 摘要
    tags: list[str]                   # 标签
    categories: list[str]             # 分类
    raw_content: str                  # 编译后的正文
```

---

## 关键文件

| 文件 | 说明 |
|------|------|
| `src/linglong/composer/composer.py` | 编排器，`Composer.run()` 和 `_process_day()` |
| `src/linglong/composer/ingest_adapter.py` | `IngestAdapter` Entity → MemoryFragment |
| `src/linglong/composer/state.py` | `ComposerState` 哈希去重 |
| `src/linglong/composer/distiller/aggregator.py` | `DailyAggregator` + `ArticleMaterial` |
| `src/linglong/composer/distiller/llm_distiller.py` | `LLMDistiller` 智能提炼 + 主题分组 |
| `src/linglong/composer/assets/prompts/blog/` | LLM prompt 模板（system.md, user_template.md） |
