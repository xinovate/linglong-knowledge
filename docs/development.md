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
├── src/linglong/          # 源代码
│   ├── __init__.py
│   ├── core/              # 共享基础设施
│   │   ├── __init__.py
│   │   ├── models.py      # 数据模型
│   │   └── config.py      # 配置管理
│   ├── ingest/            # 数据获取
│   │   ├── __init__.py
│   │   └── rss.py         # RSS源
│   └── knowledge/         # 知识库
│       ├── __init__.py
│       ├── store.py       # 存储层
│       └── review.py      # Review引擎
├── tests/                 # 测试
│   ├── core/
│   ├── ingest/
│   └── knowledge/
├── docs/                  # 文档
└── pyproject.toml         # 项目配置
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

### 配置环境变量

创建 `.env` 文件：

```env
# 通用配置
LL_DEBUG=true
LL_LOG_LEVEL=DEBUG

# 知识库配置
LL_KNOWLEDGE_WIKI_PATH=./wiki
LL_KNOWLEDGE_DB_PATH=./knowledge.db

# 获取配置
LL_INGEST_FETCH_INTERVAL_MINUTES=30
```

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
