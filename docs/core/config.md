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
      sources:                  # 顶级数据源
        - id: aihot-daily
          type: aihot
          config:
            endpoint: daily
      dimensions:               # 维度搜索
        - name: 公司决策
          search:
            keywords: ["OpenAI news May 2026", "Anthropic Claude latest"]
            engine: auto
            concurrent: true
          filter:
            max_results: 5
            max_age_days: 3
      verification:
        enabled: true
        pass_threshold: 0.6
```

**支持的数据源类型**：

| type | 说明 |
|------|------|
| `aihot` | AIHOT AI 新闻聚合（`endpoint: daily` 或 `items`） |
| `web_search` | 搜索引擎（SearXNG/ZhiPu/Google/Bing CN） |
| `rss` | RSS feed |
| `api` | REST API |
| `web_fetch` | HTTP 页面抓取 |

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
