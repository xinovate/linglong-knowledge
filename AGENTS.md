# AGENTS.md — Linglong 仓库协作指南

> 本文件面向所有贡献者（人类和 AI Agent），说明项目结构、开发命令、代码规范和协作约定。

---

## 项目结构

```
src/linglong/
├── core/          # 共享基础设施：配置中心（LinglongConfig）、数据模型（Entity、Task、Source）
├── ingest/        # 数据获取：RSS、API、Web、SourcePackage、验证引擎、并行执行器
├── knowledge/     # 知识库存储：SQLite + sqlite-vec、Review 引擎、lint 巡检、索引生成
│   └── sync/      # 跨 Agent 同步：openclaw.py、claude_code.py、codex.py
├── composer/      # 内容生产：LLM 提炼、博客模板、图片资产管线、草稿审核
├── dispatch/      # 多平台分发：DispatchManager、HexoPublisher、LocalPublisher
└── cli.py         # CLI 入口（linglong 命令）
tests/             # 测试镜像 src/ 结构：tests/core/、tests/knowledge/、tests/composer/ 等
docs/              # 架构设计、路线图、API 文档、模块文档
wiki/              # 知识库 Markdown 内容
```

配置文件为 `.linglong.yaml`（搜索路径：`./` → `~/.linglong/`），模板见 `.linglong.yaml.example`。

---

## 构建、测试与开发命令

所有命令基于项目 venv：

```bash
make install    # 安装依赖（pip install -e ".[dev,ingest,knowledge]"）
make lint       # Ruff 检查 + Black 格式检查（只读）
make format     # Ruff 自动修复 + Black 格式化
make test       # 运行全部测试（pytest -q）
make check      # lint + test，完整 CI 门禁
```

单独运行某个模块的测试：

```bash
venv/bin/pytest tests/knowledge/ -v
```

CLI 直接运行：

```bash
venv/bin/linglong --help
```

---

## 代码规范

### 格式化与检查

- **Black**：行宽 100，目标 Python 3.11
- **Ruff**：规则集 E/F/I/W/UP，E501 忽略
- **mypy**：strict 模式，所有公开函数必须加类型注解
- **Docstring**：Google 风格

### 导入顺序

```python
# 1. 标准库
import json
from datetime import datetime

# 2. 第三方库
from pydantic import BaseModel

# 3. 本项目模块
from linglong.core.models import Entity
from linglong.knowledge.store import KnowledgeStore
```

### 命名约定

- 函数/变量：`snake_case`
- 类：`PascalCase`
- 测试函数：`test_` 前缀
- 测试文件中中文注释是标准做法

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

## 测试规范

- **框架**：pytest，使用 `tmp_path` / `tempfile.TemporaryDirectory` 做隔离
- **文件位置**：`tests/<module>/test_<component>.py`，与 `src/linglong/<module>/` 镜像对应
- **端到端测试**：放在 `tests/integration/`
- **每个新功能必须附带测试**

---

## 提交与 PR 规范

### Commit 消息格式

```
<type>(<scope>): <简短描述>
```

- **type**：`feat`、`fix`、`docs`、`test`、`style`、`refactor`
- **scope**：模块名，如 `store`、`cli`、`sync+init`、`composer`
- **示例**：`feat(store): search_similar 增加 facet 过滤`、`fix: source_auto_confirm 阈值修复`

### PR 要求

- 通过 `make check`（lint + 测试）
- 描述清楚变更内容和关联版本
- 关联 `docs/PROJECT_OVERVIEW.md` 中的相关条目

---

## 架构要点

- 流水线单向流动：**ingest → knowledge → composer → dispatch**，composer 不直接读文件系统，composer 不处理发布
- `KnowledgeStore` 使用 SQLite WAL 模式 + `fcntl.flock` 文件锁保护并发写入
- Entity 按 7 个 facet 分类：`concept`、`decision`、`task`、`bug`、`insight`、`reference`、`note`
- 跨 Agent 同步适配器将各 Agent 原生格式映射为统一的 Entity 模型，命名空间前缀：`openclaw:`、`claude:`、`codex:`

---

## 参考文档

- [项目总览](docs/PROJECT_OVERVIEW.md)
- [架构设计](docs/architecture.md)
- [开发规范](docs/rules.md)
- [版本路线图](docs/roadmap.md)
- [API 文档](docs/api.md)
- 模块文档：[ingest](docs/ingest/) | [knowledge](docs/knowledge/) | [composer](docs/composer/) | [dispatch](docs/dispatch/)
