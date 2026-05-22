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

## 环境变量

也支持环境变量，前缀 `LL_`，下划线分隔层级：

| 环境变量 | 对应 YAML 字段 |
|----------|---------------|
| `LL_DEBUG` | `debug` |
| `LL_KNOWLEDGE_WIKI_PATH` | `knowledge.wiki_path` |
| `LL_COMPOSER_LLM_MODEL` | `composer.llm_model` |
| `LL_DISPATCH_DEFAULT_PUBLISHER` | `dispatch.default_publisher` |

## 代码中使用

```python
from linglong.core.config import get_config

config = get_config()
config.knowledge.wiki_path        # 知识库路径
config.composer.image_assets.enabled  # 图片资产开关
config.dispatch.default_publisher     # 默认发布器
config.ingest.search_engine           # 搜索引擎: searxng/zhipu/google/bing_cn
config.ingest.searxng_url             # SearXNG 实例地址
config.ingest.search_timeout          # 搜索超时（秒）
```

YAML 支持 `${ENV_VAR}` 语法引用环境变量：

```yaml
composer:
  llm_api_key: ${ZHIPU_API_KEY}  # 自动从环境变量读取
```

## 相关文件

- `src/linglong/core/config.py` — 配置模型定义
- `.linglong.yaml.example` — 完整配置模板
