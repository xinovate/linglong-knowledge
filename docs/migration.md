# 迁移指南：从 linglong-pipeline 迁移

## 概述

本指南说明如何将现有的 `linglong-pipeline` 项目迁移到新的 `linglong` 平台架构中。

## 迁移原则

1. **保留核心逻辑** — pipeline 的提炼、模板、格式化能力保留
2. **去除发布逻辑** — 发布功能移到 `dispatch` 模块
3. **适配新接口** — 从 `knowledge` 模块读取，向 `dispatch` 模块输出

## 现有 linglong-pipeline 结构

```
linglong-pipeline/
├── src/linglong_pipeline/
│   ├── sources/          # 记忆源适配器
│   ├── distiller/        # 提炼层
│   ├── assets/           # 素材层
│   ├── templates/        # 模板系统
│   └── publishers/       # 发布层 ← 移到 dispatch
├── config/
├── templates/
├── tests/
└── docs/
```

## 迁移步骤

### 1. 移动核心模块到 linglong

```bash
# 在 linglong 项目中创建 composer 模块
mkdir src/linglong/composer

# 迁移文件（保留 Git 历史）
# distiller/ → src/linglong/composer/distiller/
# templates/ → src/linglong/composer/templates/
# assets/ → src/linglong/composer/assets/
```

### 2. 修改输入接口

**原代码**（从文件系统读取）：
```python
# linglong-pipeline 旧方式
from linglong_pipeline.sources.openclaw import OpenClawSource

source = OpenClawSource("/path/to/wiki")
fragments = source.read()
```

**新代码**（从 knowledge 模块读取）：
```python
# linglong 新方式
from linglong.knowledge.store import KnowledgeStore

store = KnowledgeStore()
entities = store.search(status=EntityStatus.AUTO_CONFIRMED)
```

### 3. 修改输出接口

**原代码**（直接发布）：
```python
# linglong-pipeline 旧方式
from linglong_pipeline.publishers.hexo import HexoPublisher

publisher = HexoPublisher(config)
publisher.publish(article)
```

**新代码**（写入 dispatch 队列）：
```python
# linglong 新方式
from linglong.composer import PipelineOutput

output = PipelineOutput(
    content=article,
    format="markdown",
    target_platforms=["blog", "wechat"],
)
# 写入 dispatch 队列（待实现）
```

### 4. 保留的组件

| 组件 | 状态 | 说明 |
|------|------|------|
| Distiller | ✅ 保留 | 内容提炼逻辑 |
| Templates | ✅ 保留 | 模板渲染系统 |
| Assets | ✅ 保留 | 素材聚合（图虫等） |
| HexoPublisher | ❌ 移除 | 移到 dispatch |
| GitPublisher | ❌ 移除 | 移到 dispatch |

### 5. 新增适配

```python
# src/linglong/composer/__init__.py
from linglong.composer.distiller import Distiller
from linglong.composer.templates import TemplateEngine
from linglong.composer.formatter import Formatter

__all__ = ["Distiller", "TemplateEngine", "Formatter"]
```

## 配置迁移

**原配置**（`pipeline.yaml`）：
```yaml
sources:
  - type: openclaw
    path: /path/to/wiki

publishers:
  - type: hexo
    path: /path/to/blog
```

**新配置**（环境变量）：
```env
# composer 不再需要 source 配置，从 knowledge 读取
LL_KNOWLEDGE_WIKI_PATH=./wiki

# dispatch 配置（未来）
LL_DISPATCH_BLOG_PATH=./blog
```

## 测试迁移

```bash
# 原测试
pytest linglong-pipeline/tests/

# 新测试
pytest linglong/tests/composer/
```

## 迁移检查清单

- [ ] Distiller 模块迁移完成
- [ ] Templates 模块迁移完成
- [ ] Assets 模块迁移完成
- [ ] 输入接口改为从 knowledge 读取
- [ ] 输出接口改为向 dispatch 写入
- [ ] 移除所有 Publisher 相关代码
- [ ] 测试用例迁移并通过
- [ ] 文档更新

## 参考

- [linglong-pipeline 原始仓库](../linglong-pipeline/)
- [模块说明](modules.md)
- [架构设计](architecture.md)
