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
reviewer:       # 文章评审配置
dispatch:       # 分发配置
```

完整字段参考 [`.linglong.yaml.example`](../../.linglong.yaml.example)。

## ingest 配置

```yaml
ingest:
  searxng_url: http://localhost:8088
  search_timeout: 30.0

  rss_sources:                 # RSS 订阅源
    - name: AIHOT
      url: https://aihot.virxact.com/feed

  packages:                    # 内联包定义列表
    - name: ai-morning-brief
      topic: AI 早报
      output:
        format: morning-brief
        persist: true
      search_queries:
        - keywords: ["OpenAI news May 2026", "Anthropic Claude latest"]
          max_results: 5
          max_age_days: 3
```

### search_queries 配置

```yaml
search_queries:
  - keywords: ["OpenAI news", "Anthropic Claude latest"]
    max_results: 5          # 每组最多采集条数
    max_age_days: 3         # 限制结果时效
```

## 环境变量

也支持环境变量，前缀 `LL_`，下划线分隔层级：

| 环境变量 | 对应 YAML 字段 |
|----------|---------------|
| `LL_DEBUG` | `debug` |
| `LL_KNOWLEDGE_WIKI_PATH` | `knowledge.wiki_path` |
| `LL_REVIEWER_LLM_MODEL` | `reviewer.llm_model` |
| `LL_DISPATCH_DEFAULT_PUBLISHER` | `dispatch.default_publisher` |
| `LL_INGEST_SEARXNG_URL` | `ingest.searxng_url` |
| `LL_MCP_REDIS_URL` | `mcp.redis_url` |

## 代码中使用

```python
from linglong.core.config import get_config

config = get_config()
config.knowledge.wiki_path        # 知识库路径
config.ingest.searxng_url         # SearXNG 地址
config.ingest.rss_sources         # RSS 订阅源
config.ingest.packages            # 包定义列表
config.reviewer.llm_model         # 评审 LLM 模型
config.reviewer.passing_score     # 评审及格分
config.dispatch.default_publisher # 默认发布器
```

YAML 支持 `${ENV_VAR}` 语法引用环境变量：

```yaml
reviewer:
  llm_api_key: ${ZHIPU_API_KEY}  # 自动从环境变量读取
```

## 相关文件

- `src/linglong/core/config.py` — 配置模型定义
- `.linglong.yaml` — 用户配置（不入库）
