# CLAUDE.md — Linglong 项目协作指南

> 本文件面向 Claude Code（及其他 AI 助手），说明项目背景、架构决策和协作规范。

---

## 项目背景

Linglong 是一个**跨 Agent 知识中枢**。

**核心问题**：OpenClaw、Claude Code、Codex 等 AI Agent 各自维护独立的知识库，互不相通。同一个概念，OpenClaw 知道，Claude Code 不知道；Claude Code 记了，Codex 又记一遍。

**解决方案**：Linglong 作为所有 AI Agent 的统一知识底座，串联信息获取、知识沉淀、内容生产和多平台分发的完整闭环。

**当前状态**：
- v0.2 已完成：core + ingest + knowledge + composer 四模块骨架，composer 从旧项目迁移并入
- v0.3 进行中：人工审核层、Git Workflow Publisher、frontmatter 复杂 YAML 支持
- v0.4 即将启动：知识库统一（OpenClaw wiki 接入、向量搜索、跨 Agent 同步协议）
- dispatch 模块已启动（`_pending_publishers/` 暂存发布器逻辑）

**你的任务**：
1. 阅读本文档和 `docs/` 目录（尤其是 `PROJECT_OVERVIEW.md`、`architecture.md`、`modules.md`、`00-roadmap/v1.0.md`）
2. 按 `docs/` 流程执行工作（roadmap → ADR → development → testing）
3. 优先处理 `PROJECT_OVERVIEW.md` Next Actions 列表
4. 确保测试通过

**关键上下文**：
- OpenClaw 的 wiki 在 `~/.openclaw/workspace/memory/wiki/`，Claude Code 的 memory 在 `~/.claude/projects/.../memory/`
- OpenClaw 的 embedding 服务在 `http://localhost:7997`，模型 `nomic-embed-text-v1.5`
- 各 Agent 写入知识库时带命名空间前缀：`openclaw:`、`claude:`、`codex:`

---

## 架构决策（必须遵守）

### 1. 模块边界

```
ingest → knowledge → composer → dispatch
```

- **composer 只从 knowledge 读取**，不直接读文件系统
- **composer 不处理发布**，发布逻辑在 dispatch
- **composer 输出标记为 `dispatch_ready=True`**，由 dispatch 消费

### 2. 数据模型

所有模块共享 `core/models.py` 中的模型：

- `Entity` — 知识条目（核心）
- `Task` — 调度任务
- `Source` — 来源信息

**关键字段**：
- `created_by` — 标记创建者（如 `agent:claude`）
- `confirmed_by` — 人工确认标记
- `confidence` — AI 置信度
- `status` — 审核状态

### 3. 存储抽象

KnowledgeStore 提供统一接口：

```python
store = KnowledgeStore()

# 读取
entity = store.get(entity_id)
entities = store.search(status=EntityStatus.AUTO_CONFIRMED)

# 写入（composer 不需要，但需了解）
store.create(entity)
store.update(entity)
```

### 4. 配置管理

使用 `core/config.py`，环境变量前缀 `LL_`：

```python
from linglong.core.config import get_config

config = get_config()
config.knowledge.wiki_path  # Wiki 目录
```

---

## 模块说明

### `src/linglong/composer/`（内容生产编排）

- `distiller/` — LLM 智能提炼（Prompt 已外部化至 `assets/prompts/blog/*.md`）
- `templates/` — 博客模板引擎
- `assets/` — 文本资产生成器
- `state.py` — 内容哈希去重状态管理
- `draft.py` — 草稿审核模式

### `src/linglong/dispatch/_pending_publishers/`（待正式化）

- `git_workflow.py` — Git Workflow Publisher（v0.3 已完成）
- 待 dispatch 模块正式接入后移入 `src/linglong/dispatch/`

---

## 代码规范

### 导入顺序

```python
# 1. 标准库
import json
from datetime import datetime

# 2. 第三方库
import feedparser
from pydantic import BaseModel

# 3. 本项目模块
from linglong.core.models import Entity
from linglong.knowledge.store import KnowledgeStore
```

### 类型注解

必须添加类型注解：

```python
def process(entity: Entity) -> ProcessedResult:
    pass
```

### 错误处理

使用异常而非返回错误码：

```python
try:
    store.create(entity)
except StorageError as e:
    logger.error(f"Failed to store: {e}")
    raise
```

---

## 测试要求

### 运行测试

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行全部测试
pytest

# 运行 composer 测试
pytest tests/composer/ -v
```

### 新增测试

每个模块需要：
- `tests/{module}/test_{component}.py`
- 使用 `pytest` 框架
- 使用 fixtures 管理依赖

### 测试示例

```python
import pytest
from linglong.knowledge.store import KnowledgeStore

@pytest.fixture
def store():
    # 创建临时存储
    pass

def test_create_entity(store):
    entity = Entity(content="test", created_by="agent:test")
    created = store.create(entity)
    assert created.id is not None
```

---

## 常见问题

### Q: composer 如何读取知识库？

```python
from linglong.knowledge.store import KnowledgeStore
from linglong.core.models import EntityStatus

store = KnowledgeStore()
entities = store.search(status=EntityStatus.AUTO_CONFIRMED, limit=100)
```

### Q: composer 如何输出到 dispatch？

当前返回结果并标记 `dispatch_ready=True`，dispatch 模块消费：

```python
result = composer.process(entities)
# result.dispatch_ready == True 时，dispatch 负责实际发布
```

### Q: 如何添加新的内容格式？

在 `composer/formatter/` 中添加：

```python
class PPTFormatter:
    def format(self, entity: Entity) -> bytes:
        # 生成 PPT
        pass
```

### Q: 当前优先工作是什么？

查看 `docs/PROJECT_OVERVIEW.md` 的 **Next Actions** 列表，按优先级执行：
1. frontmatter 复杂 YAML 支持（tags/categories 的 list 格式完善，v0.3 收尾）
2. 启动 v0.4：知识库统一 —— 设计 OpenClaw wiki 与 Linglong knowledge 的同步协议，定义跨 Agent 知识存储 schema
3. 启动 v0.5：ingest 通用化 —— 把 ai-morning-brief 抽象为可配置通用引擎，支持 Web Search / 爬虫 / API
4. AI 封面图生成（依赖外部 API，需考虑成本和超时）
5. dispatch 模块启动（将 `_pending_publishers/` 中的发布器正式接入 dispatch）

---

## 参考文档

- [项目总览 / 单一真相源](docs/PROJECT_OVERVIEW.md)
- [架构设计](docs/architecture.md)
- [模块说明](docs/modules.md)
- [API 文档](docs/api.md)
- [开发指南](docs/development.md)
- [迁移指南](docs/migration.md)

---

## 联系

如有疑问，查看 GitHub Issues 或询问王鑫。
