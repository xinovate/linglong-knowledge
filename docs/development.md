# 开发指南

## 环境准备

### 要求

- Python 3.11+
- Git

### 安装

```bash
# 克隆仓库
git clone https://github.com/xinovate/linglong.git
cd linglong

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装开发依赖
pip install -e ".[dev]"
```

## 项目结构

```
linglong/
├── src/linglong/
│   ├── cli.py                 # CLI 入口（ingest/compose/publish/sync）
│   ├── core/                  # 共享基础设施
│   │   ├── models.py          # 数据模型（Entity, Task, Source）
│   │   └── config.py          # 配置管理（.linglong.yaml）
│   ├── ingest/                # 数据获取
│   │   ├── rss.py             # RSS 源
│   │   ├── adapters/          # API/WebFetch 适配器
│   │   ├── executor.py        # 执行引擎
│   │   ├── package.py         # 源包管理
│   │   └── verification.py    # 真实性验证
│   ├── knowledge/             # 知识库
│   │   ├── store.py           # SQLite + sqlite-vec 存储
│   │   ├── review.py          # Review 引擎
│   │   ├── embeddings.py      # 向量嵌入
│   │   └── sync/              # 跨 Agent 同步（openclaw/claude/codex）
│   ├── composer/              # 内容生产
│   │   ├── composer.py        # 流水线编排
│   │   ├── distiller/         # LLM/规则提炼
│   │   ├── templates/         # 博客模板
│   │   ├── assets/            # 文本/图片资产
│   │   ├── state.py           # 去重状态
│   │   └── draft.py           # 草稿管理
│   └── dispatch/              # 多平台分发
│       ├── manager.py         # 分发编排
│       └── publishers/        # 发布器（hexo/local）
├── tests/                     # 测试
├── docs/                      # 文档
├── .linglong.yaml.example     # 配置模板
└── pyproject.toml             # 项目配置
```

## 开发工作流

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定模块测试
pytest tests/knowledge/

# 运行并显示覆盖率
pytest --cov=linglong --cov-report=html
```

### 代码规范

```bash
# 格式化代码
black src/ tests/

# 检查代码风格
ruff check src/ tests/

# 类型检查
mypy src/
```

### 配置

项目使用 `.linglong.yaml` 作为主配置文件。首次使用复制示例并按需修改：

```bash
cp .linglong.yaml.example .linglong.yaml
```

```yaml
# .linglong.yaml 示例
debug: true
log_level: DEBUG

knowledge:
  wiki_path: ./wiki
  db_path: ./knowledge.db

ingest:
  fetch_interval_minutes: 30
```

完整配置项参考 `.linglong.yaml.example`。也支持环境变量（前缀 `LL_`），但 `.linglong.yaml` 优先级更高。

## 添加新模块

### 1. 创建模块目录

```bash
mkdir src/linglong/mymodule
touch src/linglong/mymodule/__init__.py
```

### 2. 更新 `pyproject.toml`

```toml
[project.optional-dependencies]
dev = [...]
ingest = [...]
knowledge = [...]
mymodule = [
    "依赖包>=版本",
]
```

### 3. 编写测试

```bash
mkdir tests/mymodule
touch tests/mymodule/__init__.py
touch tests/mymodule/test_mymodule.py
```

### 4. 更新文档

在 `docs/modules.md` 中添加新模块说明。

## 调试技巧

### 查看配置

```python
from linglong.core.config import get_config

config = get_config()
print(config.knowledge.wiki_path)
```

### 手动测试存储

```python
from linglong.knowledge.store import KnowledgeStore
from linglong.core.models import Entity

store = KnowledgeStore()
entity = Entity(
    content="# 测试\n\n内容",
    created_by="agent:test",
)
store.create(entity)
```

## 提交规范

```bash
# 1. 运行测试
pytest

# 2. 格式化代码
black src/ tests/

# 3. 提交
git add .
git commit -m "feat(module): 描述"

# 4. 推送
git push origin main
```
