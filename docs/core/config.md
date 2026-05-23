# 配置系统

## 概述

Linglong 使用 `.linglong.yaml` 作为主配置文件，基于 Pydantic BaseSettings 实现。

## 配置文件

**搜索路径**（优先级从高到低）：
1. `./.linglong.yaml`（当前目录）
2. `~/.linglong/config.yaml`（用户 home）

**字段优先级**：`.linglong.yaml` > 环境变量（`LL_*`）> 默认值

**首次使用**：
```bash
cp .linglong.yaml.example .linglong.yaml
```

## 配置结构

```yaml
debug: false
log_level: INFO
data_dir: ~/linglong/data

knowledge:      # 知识库配置
ingest:         # 信息采集配置
composer:       # 内容生产配置
dispatch:       # 分发配置
```

完整字段参考 [`.linglong.yaml.example`](../../.linglong.yaml.example)。

## ingest 配置

```yaml
ingest:
  search_engine: searxng       # searxng | zhipu | google | bing_cn | auto
  searxng_url: http://localhost:8088
  search_timeout: 30.0

  packages:                    # 内联包定义列表
    - name: ai-morning-brief
      topic: AI 早报
      schedule: "0 7 * * *"
      output:
        format: morning-brief   # morning-brief | 空（不格式化）
        persist: true
      sources:                  # 顶级数据源（全量采集，不限维度）
        - id: aihot-daily
          type: aihot
          config:
            endpoint: daily
        - id: openai-blog
          type: rss
          config:
            url: https://openai.com/blog/rss.xml
            max_items: 10
        - id: arxiv-ai
          type: arxiv
          config:
            categories: ["cs.AI", "cs.CL", "cs.RO"]
            max_results: 10
        - id: github-trending
          type: github
          config:
            topics: ["ai", "llm", "ai-agent"]
            min_stars: 50
            since_days: 7
            max_results: 10
      search_queries:           # 扁平搜索配置（v1.3 替换 dimensions）
        - keywords: ["OpenAI news May 2026", "Anthropic Claude latest"]
          max_results: 5
          max_age_days: 3
        - keywords: ["AI startup funding round 2026"]
          max_results: 3
          max_age_days: 5
      verification:
        enabled: true
        pass_threshold: 0.6
```

### 支持的数据源类型

| type | 说明 | config 字段 |
|------|------|------------|
| `aihot` | AIHOT AI 新闻聚合 | `endpoint: daily` 或 `items` |
| `arxiv` | ArXiv 论文预印本 | `categories`, `max_results`, `sort_by` |
| `github` | GitHub 开源项目搜索 | `topics`, `min_stars`, `since_days`, `max_results`, `token` |
| `rss` | RSS feed | `url`, `max_items` |
| `web_search` | 搜索引擎 | `queries`, `engine`, `concurrent` |
| `api` | REST API | — |
| `web_fetch` | HTTP 页面抓取 | — |

### ArXiv 配置

```yaml
- id: arxiv-ai
  type: arxiv
  config:
    categories: ["cs.AI", "cs.CL", "cs.RO"]  # ArXiv 分类
    max_results: 10                            # 默认 10
    sort_by: submittedDate                     # submittedDate | relevance
```

常用分类：`cs.AI`（人工智能）、`cs.CL`（计算语言学）、`cs.RO`（机器人）、`cs.LG`（机器学习）、`cs.CV`（计算机视觉）

### GitHub 配置

```yaml
- id: github-trending
  type: github
  config:
    topics: ["ai", "llm", "ai-agent"]  # GitHub topic 筛选
    min_stars: 50                        # 最低 star 数
    since_days: 7                        # 最近 N 天创建
    max_results: 10                      # 默认 10
    token: ""                            # 可选，提升 API 限额
```

### search_queries 配置

```yaml
search_queries:
  - keywords: ["OpenAI news", "Anthropic Claude latest"]
    max_results: 5          # 每组最多采集条数
    max_age_days: 3         # 限制结果时效
```

`search_queries` 替代了 v1.2 的 `dimensions`。维度归属不再由配置决定——由 LLM 根据内容自动判断。

## 环境变量

也支持环境变量，前缀 `LL_`，下划线分隔层级：

| 环境变量 | 对应 YAML 字段 |
|----------|---------------|
| `LL_DEBUG` | `debug` |
| `LL_KNOWLEDGE_WIKI_PATH` | `knowledge.wiki_path` |
| `LL_COMPOSER_LLM_MODEL` | `composer.llm_model` |
| `LL_DISPATCH_DEFAULT_PUBLISHER` | `dispatch.default_publisher` |
| `LL_INGEST_SEARCH_ENGINE` | `ingest.search_engine` |
| `LL_INGEST_SEARXNG_URL` | `ingest.searxng_url` |

## 代码中使用

```python
from linglong.core.config import get_config

config = get_config()
config.knowledge.wiki_path        # 知识库路径
config.ingest.search_engine       # 搜索引擎
config.ingest.packages            # 包定义列表
config.composer.image_assets.enabled  # 图片资产开关
config.dispatch.default_publisher     # 默认发布器
```

YAML 支持 `${ENV_VAR}` 语法引用环境变量：

```yaml
composer:
  llm_api_key: ${ZHIPU_API_KEY}  # 自动从环境变量读取
```

## 相关文件

- `src/linglong/core/config.py` — 配置模型定义
- `.linglong.yaml` — 用户配置（不入库）
