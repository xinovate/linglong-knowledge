# Linglong

> 个人知识管理平台 —— 从信息获取到知识沉淀，再到内容生产与分发的完整流水线。

## 项目概述

Linglong 是一个面向个人和团队的智能知识管理系统。它通过模块化的架构，将信息获取、知识存储、内容生产和多平台分发串联成一个完整的闭环。

## 架构设计

```
linglong/
├── core/           # 共享基础设施（配置、调度、监控）
├── ingest/         # 数据获取（RSS、API、AI任务）
├── knowledge/      # 知识库（存储、检索、Review）
├── pipeline/       # 内容生产（模板、格式转换）
└── dispatch/       # 多平台分发（博客、公众号、抖音等）
```

## 模块状态

| 模块 | 状态 | 说明 |
|------|------|------|
| core | ✅ 已完成 | 共享模型、配置中心 |
| ingest | ✅ 已完成 | RSS源获取框架 |
| knowledge | ✅ 已完成 | 三层存储、Review引擎 |
| pipeline | 📋 待迁移 | 从 linglong-pipeline 迁移 |
| dispatch | 📋 未开始 | 多平台分发 |

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/xinovate/linglong.git
cd linglong

# 安装依赖
pip install -e ".[dev]"

# 运行测试
pytest
```

## 技术栈

- **Python 3.11+** — 主要开发语言
- **sqlite-vec** — 本地向量存储
- **Pydantic** — 数据验证与配置管理
- **pytest** — 测试框架

## 文档

- [架构设计](docs/architecture.md) — 系统架构与模块划分
- [开发指南](docs/development.md) — 本地开发与测试
- [模块说明](docs/modules.md) — 各模块详细设计
- [API文档](docs/api.md) — 公共接口说明
- [迁移指南](docs/migration.md) — 从 linglong-pipeline 迁移

## License

MIT
