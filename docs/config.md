# 配置系统

Linglong 使用 `.knowledge.yml` 作为主配置文件，基于 Pydantic BaseSettings 实现。

## 配置文件

**搜索路径**（优先级从高到低）：
1. `./.knowledge.yml`（当前目录）
2. 项目根目录 `.knowledge.yml`
3. `~/.knowledge/config.yaml`（用户 home）

**字段优先级**：`.knowledge.yml` > 环境变量（`KB_*`）> 默认值

**首次使用**：
```bash
cp .knowledge.example.yml .knowledge.yml
```

## 配置结构

```yaml
debug: false
log_level: INFO
data_dir: ~/knowledge/data

knowledge:       # 知识库配置
  wiki_path: ~/knowledge/wiki
  db_path: ~/knowledge/db/knowledge.db
  vector_enabled: true
  embedding_url: http://localhost:7997
  embedding_model: nomic-embed-text-v1.5
  write_mode: confirm
  auto_lint: false

mcp:             # MCP 服务配置
  transport: stdio
  host: 127.0.0.1
  port: 9900
  redis_url: ""
```

## 环境变量

支持环境变量，前缀 `KB_`，下划线分隔层级：

| 环境变量 | 对应 YAML 字段 |
|----------|---------------|
| `KB_DEBUG` | `debug` |
| `KB_KNOWLEDGE_WIKI_PATH` | `knowledge.wiki_path` |
| `KB_KNOWLEDGE_DB_PATH` | `knowledge.db_path` |
| `KB_KNOWLEDGE_EMBEDDING_URL` | `knowledge.embedding_url` |
| `KB_KNOWLEDGE_EMBEDDING_API_KEY` | `knowledge.embedding_api_key` |
| `KB_MCP_TRANSPORT` | `mcp.transport` |
| `KB_MCP_PORT` | `mcp.port` |
| `KB_MCP_REDIS_URL` | `mcp.redis_url` |
| `KB_MCP_AUTH_TOKEN` | `mcp.auth_token` |

## 代码中使用

```python
from linglong.core.config import get_config

config = get_config()
config.knowledge.wiki_path        # 知识库路径
config.knowledge.vector_enabled   # 向量搜索开关
config.mcp.transport              # MCP 传输协议
config.mcp.redis_url              # Redis Token 认证
```

YAML 支持 `${ENV_VAR}` 语法引用环境变量：

```yaml
knowledge:
  embedding_api_key: ${EMBEDDING_API_KEY}
```

## 相关文件

- `src/linglong/core/config.py` — 配置模型定义
- `.knowledge.yml` — 用户配置（不入库）
