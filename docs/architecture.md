# Linglong 架构设计

## 概述

Linglong 是一个个人知识管理平台，采用模块化设计，支持从信息获取到知识沉淀，再到内容生产与分发的完整流水线。

## 设计原则

1. **模块化**：每个模块可独立运行、测试和部署
2. **可扩展**：通过接口和插件机制支持新数据源和平台
3. **可观测**：完整的日志、指标和追踪
4. **数据驱动**：所有决策基于数据反馈
5. **渐进式**：从简单开始，逐步增强

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    linglong                                  │
│                                                              │
│  ┌─────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐  │
│  │ ingest  │ → │ knowledge│ → │ pipeline │ → │ dispatch │  │
│  │ 获取    │   │ 知识库   │   │ 生产     │   │ 分发     │  │
│  └─────────┘   └──────────┘   └──────────┘   └──────────┘  │
│       ↑             ↑             ↑              ↓          │
│       └─────────────┴─────────────┴──────────────┘          │
│                    feedback loop                             │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ core（共享基础设施：模型、配置、工具）                │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 模块详解

### core（共享基础设施）

**职责**：
- 定义共享数据模型（Entity、Task、Source 等）
- 管理统一配置（环境变量、.env 文件）
- 提供跨模块工具函数

**设计要点**：
- 不依赖任何业务模块
- 使用 Pydantic 保证类型安全
- 配置分层：通用 / 模块级

### ingest（数据获取）

**职责**：
- 从 RSS 源获取文章
- 从 API 获取数据
- 接收 AI 任务输出

**设计要点**：
- 只负责"拉数据"，不做处理
- 输出原始数据到 knowledge
- 支持异步并发获取

### knowledge（知识库）

**职责**：
- 存储知识条目
- 向量索引与语义搜索
- 自动 Review 引擎
- 版本历史追踪

**存储设计（三层）**：

```yaml
storage:
  filesystem:     # Markdown + YAML frontmatter
    - 人类可读
    - Git 友好
    - 便于手动编辑

  sqlite:         # 结构化数据
    - 元数据查询
    - 关系图谱
    - 版本历史

  vector:         # 语义索引
    - sqlite-vec 扩展
    - 相似度搜索
    - 自动更新
```

**Review 机制**：

```
┌─────────┐    ┌──────────┐    ┌──────────┐
│  获取   │ →  │ Review   │ →  │  存储    │
│ 原始数据│    │ 引擎     │    │ 知识库   │
└─────────┘    └──────────┘    └──────────┘
                    │
                    ↓
               ┌──────────┐
               │ 规则评估  │
               │ - 置信度  │
               │ - 来源    │
               │ - 敏感词  │
               └──────────┘
```

### pipeline（内容生产）

**职责**：
- 从知识库读取内容
- 提炼、格式化
- 生成多格式输出

**设计要点**：
- 输入：只从 knowledge 读取
- 输出：写入 dispatch 队列
- 不直接处理发布

### dispatch（分发调度）

**职责**：
- 多平台适配器
- 发布调度
- 反馈收集

**设计要点**：
- 平台适配器插件化
- 支持定时/条件触发
- 反馈数据回流到 knowledge

## 数据流

### 正常流程

```
ingest → knowledge → pipeline → dispatch
```

### 反馈流程

```
dispatch → 反馈数据 → knowledge（更新实体状态）
```

### 审核流程

```
ingest → Review引擎 → [自动确认] → knowledge
                ↓
         [标记待审] → 人工确认 → knowledge
```

## 模块间协作规则

1. **单向依赖**：业务模块依赖 core，core 不依赖业务模块
2. **不直接通信**：业务模块间不直接调用，通过数据流转
3. **接口隔离**：每个模块暴露清晰的接口
4. **数据一致性**：通过 Entity 模型保证数据格式统一

## 技术选型

| 层面 | 技术 | 理由 |
|------|------|------|
| 语言 | Python 3.11+ | AI 生态、开发效率 |
| 数据验证 | Pydantic | 类型安全、序列化 |
| 配置管理 | pydantic-settings | 环境变量支持 |
| 向量存储 | sqlite-vec | 轻量、无依赖 |
| 测试 | pytest | 生态成熟 |
| 打包 | hatchling | 现代标准 |

## 扩展点

### 添加新数据源

```python
class CustomSource:
    async def fetch(self) -> List[Entity]:
        pass
```

### 添加新平台

```python
class CustomPlatform:
    async def publish(self, content: str) -> bool:
        pass
    
    async def collect_feedback(self) -> Dict:
        pass
```

### 添加 Review 规则

```python
engine.add_rule(
    Rule(
        name="custom",
        condition=lambda e: ...,
        action=Action.FLAG_FOR_REVIEW,
    )
)
```

## 部署架构

### 开发环境

```bash
pip install -e ".[dev]"
pytest
```

### 生产环境

```bash
pip install linglong[all]
```

### Docker（未来）

```yaml
version: '3'
services:
  linglong:
    image: linglong:latest
    volumes:
      - ./data:/data
      - ./wiki:/wiki
    environment:
      - LL_KNOWLEDGE_WIKI_PATH=/wiki
```

## 演进路线

### Phase 1（当前）
- core：共享模型、配置
- knowledge：文件 + SQLite 存储
- ingest：RSS 获取

### Phase 2
- knowledge：向量索引、语义搜索
- ingest：更多数据源、AI 任务接入
- pipeline：从旧项目迁移

### Phase 3
- dispatch：多平台适配器
- feedback：反馈收集与优化
- scheduler：任务调度

### Phase 4
- 更多平台支持
- 智能推荐
- 协作功能

## 参考

- [模块说明](modules.md)
- [API 文档](api.md)
- [开发指南](development.md)
- [迁移指南](migration.md)
