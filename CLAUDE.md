# CLAUDE.md — Linglong 项目协作指南

> 本文件面向 Claude Code（及其他 AI 助手），说明项目背景、架构决策和协作规范。

---

## 项目背景

Linglong 是一个**个人知识管理平台**，目标是将信息获取、知识沉淀、内容生产和多平台分发串联成完整闭环。

**当前状态**：
- 骨架已完成（core + knowledge + ingest）
- pipeline 模块待从旧项目迁移
- dispatch 模块尚未开始

**你的任务**：
1. 阅读本文档和 `docs/` 目录
2. 理解现有代码结构
3. 将 `linglong-pipeline` 的核心逻辑迁移到 `src/linglong/composer/`
4. 确保测试通过

---

## 架构决策（必须遵守）

### 1. 模块边界

```
ingest → knowledge → pipeline → dispatch
```

- **pipeline 只从 knowledge 读取**，不直接读文件系统
- **pipeline 不处理发布**，发布逻辑移到 dispatch
- **pipeline 输出到 dispatch 队列**（预留接口）

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

# 写入（pipeline 不需要，但需了解）
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

## 迁移指南

### 从 linglong-pipeline 迁移

**保留**：
- `distiller/` → `src/linglong/composer/distiller/`
- `templates/` → `src/linglong/composer/templates/`
- `assets/` → `src/linglong/composer/assets/`

**移除**：
- `publishers/` — 移到 dispatch 模块
- `sources/` — 由 knowledge 模块替代

**修改**：
- 输入：从 `OpenClawSource` 改为 `KnowledgeStore.search()`
- 输出：从 `HexoPublisher.publish()` 改为写入 dispatch 队列

详见：`docs/migration.md`

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
pytest
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

### Q: pipeline 如何读取知识库？

```python
from linglong.knowledge.store import KnowledgeStore
from linglong.core.models import EntityStatus

store = KnowledgeStore()
entities = store.search(status=EntityStatus.AUTO_CONFIRMED, limit=100)
```

### Q: pipeline 如何输出到 dispatch？

当前预留接口，待 dispatch 模块实现：

```python
# 临时方案：直接返回结果
result = pipeline.process(entities)
# 未来：写入 dispatch 队列
```

### Q: 如何添加新的内容格式？

在 `pipeline/formatter/` 中添加：

```python
class PPTFormatter:
    def format(self, entity: Entity) -> bytes:
        # 生成 PPT
        pass
```

---

## 参考文档

- [架构设计](docs/architecture.md)
- [模块说明](docs/modules.md)
- [API 文档](docs/api.md)
- [开发指南](docs/development.md)
- [迁移指南](docs/migration.md)

---

## 联系

如有疑问，查看 GitHub Issues 或询问王鑫。
