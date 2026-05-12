# Linglong 架构设计

## 概述

Linglong 是一个个人知识管理平台，采用模块化设计，支持从信息获取到知识沉淀，再到内容生产与分发的完整流水线。

## 模块划分

```
linglong/
├── core/           # 共享基础设施
├── knowledge/      # 知识库（存储、检索、Review）
├── ingest/         # 数据获取（RSS、API、AI任务）
├── pipeline/       # 内容生产（模板、格式转换）
└── dispatch/       # 多平台分发
```

## 核心设计原则

1. **模块化**：每个模块可独立运行和测试
2. **可扩展**：通过接口和插件机制支持新数据源和平台
3. **可观测**：完整的日志、指标和追踪
4. **数据驱动**：所有决策基于数据反馈

## 数据流

```
ingest → knowledge → pipeline → dispatch
   ↑         ↑          ↑          ↓
   └─────────┴──────────┴──────────┘
              feedback loop
```

## 存储设计

### 三层存储

1. **文件系统**：Markdown + YAML frontmatter，人类可读，Git友好
2. **SQLite**：结构化元数据、关系、版本历史
3. **向量索引**：sqlite-vec，语义搜索

### 实体模型

```python
class Entity:
    id: str                    # UUID
    content: str               # Markdown内容
    summary: str               # AI摘要
    created_by: AgentID        # 创建者
    confirmed_by: HumanID      # 确认者
    confidence: float          # 置信度
    status: EntityStatus       # 状态
    sources: List[Source]      # 来源
    relations: List[Relation]  # 关系
    versions: List[Version]    # 版本历史
```

## Review机制

自动规则引擎，支持：

- 高置信度 + 可信来源 → 自动确认
- 低置信度 → 标记待审
- 敏感内容 → 需人工确认
- 自定义规则

## 配置管理

统一配置中心，支持：

- 环境变量
- `.env` 文件
- 代码中默认值

前缀：`LL_`（通用），`LL_KNOWLEDGE_`（知识库），`LL_INGEST_`（获取）
