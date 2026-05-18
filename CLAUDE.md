# CLAUDE.md — Linglong 项目协作指南

> 本文件面向 Claude Code（及其他 AI 助手），说明项目背景、架构决策和协作规范。

---

## 项目背景

Linglong 是一个**跨 Agent 知识中枢**。

**核心问题**：OpenClaw、Claude Code、Codex 等 AI Agent 各自维护独立的知识库，互不相通。同一个概念，OpenClaw 知道，Claude Code 不知道；Claude Code 记了，Codex 又记一遍。

**解决方案**：Linglong 作为所有 AI Agent 的统一知识底座，串联信息获取、知识沉淀、内容生产和多平台分发的完整闭环。

**当前状态**：
- v0.1–v0.9 已完成：core + ingest + knowledge + composer + dispatch 五模块完整流水线，CLI 入口，图片资产管线
- v1.0 进行中：博客流水线端到端跑通（image assets 集成、Playwright 解析、YAML 配置）
- 知识库模块已完成（M1-M4）：7 Facet 分类、FTS5 全文搜索、版本管理、归档、CLI 命令、索引+巡检、文件锁+WAL

**你的任务**：
1. 阅读本文档和 `docs/` 目录（尤其是 `PROJECT_OVERVIEW.md`、`roadmap.md`、`rules.md`）
2. 按 `docs/` 流程执行工作（roadmap → architecture → rules → testing）
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
from linglong.knowledge.store import KnowledgeStore
from linglong.core.models import Entity, EntityFacet, EntityStatus

store = KnowledgeStore()

# 写入（WikiLinks [[目标]] 自动填充 relations）
entity = store.create(Entity(
    content="# 标题\n\n参考 [[已有概念]]",
    facet=EntityFacet.CONCEPT,
    created_by="agent:claude",
))

# 读取
entity = store.get(entity_id)

# 搜索（FTS5 全文 + facet/status/since 过滤）
results = store.search(query="关键词", facet=EntityFacet.CONCEPT)
results = store.search(status=EntityStatus.AUTO_CONFIRMED, limit=100)
results = store.search(query="更新", since="2026-05-01")

# 向量搜索（支持 facet 过滤）
results = store.search_similar(query="语义搜索", facet=EntityFacet.CONCEPT)

# 更新（乐观锁防并发覆盖，替换产生新版本，追加不产生）
entity.content = "新内容"
store.update(entity)  # 版本 +1，并发冲突抛 ConcurrentModificationError

# 归档
store.archive(entity_id)
```

### 4. 知识库 CLI

知识库提供完整的 CLI 命令集：

```bash
linglong init                              # 初始化知识库
linglong init --interactive                # 交互式配置向导
linglong init --from-git URL               # 从 Git 仓库初始化
linglong write --facet concept --title "标题" --content "内容" --yes
linglong read <entity_id>
linglong search "关键词" --facet concept --deep --format json
linglong search "更新" --since 2026-05-01 --created-by agent:claude
linglong update <entity_id> --append "补充内容"
linglong update <entity_id> --history      # 查看版本历史
linglong review --list-pending             # 审核管理
linglong archive <entity_id>
linglong lint                              # 巡检健康检查
linglong lint --fix                        # 自动修复
linglong index --rebuild                   # 生成索引
linglong stats                             # 统计信息
linglong migrate --from /path/to/wiki      # 从外部 wiki 迁移
```

### 5. 配置管理

使用 `.linglong.yaml` 作为主配置文件（搜索路径：CWD → home）：

```bash
linglong init              # 自动生成模板
linglong init -i           # 交互式配置向导
```

也支持环境变量（前缀 `LL_`），但 `.linglong.yaml` 优先级更高。

```python
from linglong.core.config import get_config

config = get_config()
config.knowledge.wiki_path  # Wiki 目录
config.knowledge.max_versions  # 版本上限（默认 10）
config.knowledge.db_mode  # SQLite 模式（默认 wal）
config.knowledge.write_mode  # 写入模式：confirm/auto
config.knowledge.auto_lint  # 写入后自动巡检（默认 False）
config.composer.image_assets.enabled  # 图片资产开关
```

---

## 模块说明

### `src/linglong/composer/`（内容生产编排）

- `distiller/` — LLM 智能提炼（Prompt 已外部化至 `assets/prompts/blog/*.md`）
- `templates/` — 博客模板引擎（`base.py` + `blog.py`）
- `assets/` — 资产生成器
  - `text.py` — 文本资产（摘要、标签、引言）
  - `image_asset_fetcher.py` — 图片下载/压缩/EXIF 清理
  - `image_asset_selector.py` — URL 文件解析 + 随机选择 + 去重
  - `page_image_resolver.py` — Playwright 页面 → 图片 URL 解析
- `state.py` — 内容哈希去重状态管理
- `draft.py` — 草稿审核模式

### `src/linglong/dispatch/`（多平台分发）

- `manager.py` — DispatchManager 编排
- `publishers/` — 发布器
  - `base.py` — 发布器基类
  - `hexo.py` — Hexo 博客发布（支持 git workflow）
  - `local.py` — 本地文件输出

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

### 文档同步（pre-commit hook）

项目配置了 pre-commit hook，提交代码时自动检查是否需要同步更新文档：

- 映射配置：`docs/doc-map.yaml`（代码路径 → 文档路径）
- 检查脚本：`scripts/doc-check.py`
- hook 文件：`scripts/hooks/pre-commit`
- 安装方式：`bash scripts/install-hooks.sh`（clone 后首次需执行）

提交时如果看到黄色警告 `⚠️ doc-check`，说明代码改动对应的文档没有更新，请检查后再提交。

---

## 测试要求

### 运行测试

```bash
source venv/bin/activate
pytest                    # 全部测试
pytest tests/composer/ -v # composer 模块
pytest tests/core/ -v     # core 模块
```

### 新增测试

每个模块需要：
- `tests/{module}/test_{component}.py`
- 使用 `pytest` 框架
- 使用 fixtures 管理依赖

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

```python
from linglong.composer.composer import Composer

composer = Composer()
result = composer.run(dry_run=False, draft=False)
# result.success == True 时，result.articles 中每项含 dispatch_ready=True
# 若 config.auto_publish=True，composer 会自动调用 DispatchManager 发布
```

### Q: 如何添加新的内容模板？

在 `composer/templates/` 中添加，继承 `BaseTemplate`：

```python
from linglong.composer.templates.base import BaseTemplate

class NewsletterTemplate(BaseTemplate):
    def apply(self, content: str, metadata: dict) -> str:
        # 生成 newsletter 格式
        pass
```

### Q: 当前优先工作是什么？

查看 `docs/PROJECT_OVERVIEW.md` 的 **Next Actions** 列表。当前重点是 v1.0 博客流水线端到端验证。

---

## 参考文档

- [项目总览](docs/PROJECT_OVERVIEW.md)
- [架构设计](docs/architecture.md)
- [开发规范](docs/rules.md)
- [版本路线图](docs/roadmap.md)
- [API 文档](docs/api.md)
- 模块文档：[ingest](docs/ingest/) | [knowledge](docs/knowledge/) | [composer](docs/composer/) | [dispatch](docs/dispatch/)

---

## 联系

如有疑问，查看 GitHub Issues 或询问王鑫。
