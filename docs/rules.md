# 开发规范

> 适用范围：linglong 项目所有贡献者（含人类开发者与 AI Agent）

---

## 代码风格

### Python 规范

- **版本**: Python 3.11+
- **命名**: PEP 8（类 `PascalCase`，函数/变量 `snake_case`，常量 `UPPER_SNAKE_CASE`）
- **类型注解**: 所有公共函数必须标注参数类型和返回值类型
- **文档字符串**: Google Style docstring
- **字符串引号**: 双引号 `"`，仅在避免转义时使用单引号

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

### 注释要求

- **语言**: 中文注释
- **必要性**: 复杂逻辑必须注释，自解释代码不需要
- **docstring**: 公共类和方法必须有 docstring

### 日志规范

- 使用 `logging.getLogger(__name__)`，禁止 `print`（CLI 展示除外）
- `DEBUG`: 详细内部状态（Prompt 内容、API 响应原文）
- `INFO`: 用户关心的里程碑（"LLM 提炼完成"）
- `WARNING`: 可恢复异常（"LLM 调用失败，回退到规则模式"）
- `ERROR`: 需要人工介入的错误

### 错误处理

- 外部依赖调用必须包裹 `try/except`
- 关键路径中单组失败不应阻断整批处理，应收集错误后继续

### 测试规范

**文件命名**：`tests/{module}/test_{component}.py`

**类命名**：`Test{ClassName}`（如 `TestReviewer`、`TestKnowledgeStore`）

**方法命名**：`test_{行为描述}`（如 `test_create_entity`、`test_search_by_status`）

**Fixture**：
- 使用 `@pytest.fixture` 管理依赖
- 使用 `tmp_path` 隔离文件系统
- 使用 `set_config()` 注入临时配置，测试结束 `set_config(None)` 重置

```python
@pytest.fixture
def store(tmp_path):
    config = LinglongConfig(data_dir=tmp_path / "data")
    set_config(config)
    yield KnowledgeStore()
    set_config(None)
```

**Mock 原则**：
- 文件系统 → `tmp_path`（不用 mock）
- LLM API → `unittest.mock.patch`
- 网络请求 → `responses` 或 `httpx.MockTransport`
- 禁止在自动化测试中调用真实外部服务

**断言风格**：使用 `assert`，错误信息要清晰

```python
# 好
assert entity.status == EntityStatus.AUTO_CONFIRMED, f"Expected AUTO_CONFIRMED, got {entity.status}"

# 差
assert entity.status == EntityStatus.AUTO_CONFIRMED
```

---

## Git 工作流

### 分支模型

| 分支 | 用途 | 保护规则 |
|------|------|----------|
| `main` | 稳定版本 | 禁止直接推送，需 PR 合并 |
| `feature/*` | 新功能 | 从 main 切出，合并后删除 |
| `fix/*` | 缺陷修复 | 从 main 切出，合并后删除 |
| `docs/*` | 文档更新 | 从 main 切出，合并后删除 |

### 提交格式

```
<type>(<scope>): <中文 subject>
```

- `type` 和 `scope` 用英文（兼容 conventional commits 工具链）
- `subject` 用中文描述

| Type | 含义 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(reviewer): 接入 LLM 七维度评分` |
| `fix` | 缺陷修复 | `fix(ingest): 修复 RSSHub key 追加问题` |
| `docs` | 文档更新 | `docs: 重组文档结构为模块化目录` |
| `refactor` | 重构 | `refactor(config): 提取 ReviewerConfig` |
| `test` | 测试 | `test(reviewer): 增加规则校验测试` |
| `chore` | 构建/工具 | `chore(deps): 增加 watchdog 依赖` |

### Scope 对照

| Scope | 代码目录 |
|-------|---------|
| `core` | `src/linglong/core/` |
| `ingest` | `src/linglong/ingest/` |
| `knowledge` | `src/linglong/knowledge/` |
| `reviewer` | `src/linglong/reviewer/` |
| `dispatch` | `src/linglong/dispatch/` |
| `cli` | CLI 入口 |
| `config` | `config.py` |

---

## 配置管理

- 所有可调参数通过 `core/config.py` 暴露，禁止硬编码业务常量
- 主配置文件：`.knowledge.yml`
- 环境变量前缀：`KB_`，模块级用 `KB_{MODULE}_`

---

## AI Agent 协作规范

### 命名空间

各 Agent 写入知识库时带命名空间前缀：
- `openclaw:` — OpenClaw
- `claude:` — Claude Code
- `codex:` — Codex CLI

### 职责边界

- **Claude Code**: 骨架、流水线编排、核心逻辑
- **OpenClaw**: 上游知识生产
- **Codex**: 辅助知识生产
- 各 Agent 不越界修改对方主责代码

### 信息同步

- 代码同步：Git 提交，commit message 标明 Agent 身份
- 规范同步：修改 config 或 docs 后通知相关 Agent
- 陷阱同步：更新 CLAUDE.md 和 tech-debt.md

---

## 项目结构

```
src/linglong/
├── cli.py              # CLI 入口
├── core/               # 共享基础设施（models, config）
├── ingest/             # 数据获取（RSS, API, Web, 验证）
├── knowledge/          # 知识库存储（SQLite, 向量, Review, 同步）
├── reviewer/           # 文章评审（七维度评分, 规则校验）
└── dispatch/           # 多平台分发（Hexo, Local）
```

---

## 开发命令

```bash
# 安装
pip install -e ".[dev]"

# 测试
pytest                         # 全部
pytest tests/reviewer/ -v      # 指定模块

# 代码质量
black src/ tests/              # 格式化
ruff check src/ tests/         # lint
mypy src/                      # 类型检查

# 配置
cp .knowledge.example.yml .knowledge.yml
```
