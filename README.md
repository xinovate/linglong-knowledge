# Linglong

> 个人知识管理平台 —— 从信息获取到知识沉淀，再到内容生产与分发的完整流水线。

## 架构

```
linglong/
├── core/           # 共享基础设施（配置、调度、监控）
├── knowledge/      # 知识库（存储、检索、Review）
├── ingest/         # 数据获取（RSS、API、AI任务）
├── pipeline/       # 内容生产（模板、格式转换）
└── dispatch/       # 多平台分发（博客、公众号、抖音等）
```

## 快速开始

```bash
# 安装
git clone https://github.com/xinovate/linglong.git
cd linglong
pip install -e ".[dev]"

# 启动
docker-compose up -d
```

## 模块说明

| 模块 | 状态 | 说明 |
|------|------|------|
| core | 🚧 开发中 | 共享模型、配置中心、调度器 |
| knowledge | 🚧 开发中 | SQLite+文件存储、向量检索、Review机制 |
| ingest | 🚧 开发中 | RSS源、API接入、AI任务 |
| pipeline | 📋 计划中 | 内容生产（从 linglong-pipeline 迁移） |
| dispatch | 📋 计划中 | 多平台分发 |

## 技术栈

- Python 3.11+
- sqlite-vec（向量存储）
- Pydantic（数据验证）

## License

MIT
