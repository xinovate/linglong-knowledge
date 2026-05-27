# Linglong

> 跨 Agent 知识中枢 —— 统一知识底座，串联信息获取、知识沉淀、文章评审与多平台分发。

## 项目概述

Linglong 解决 AI Agent 知识孤岛问题：OpenClaw、Claude Code、Codex 各自维护独立知识库，互不相通。Linglong 作为统一知识底座，提供完整的 **获取 → 沉淀 → 评审 → 分发** 闭环。

## 架构

```
ingest → knowledge → reviewer → dispatch
```

```
src/linglong/
├── core/           # 共享基础设施（配置、数据模型、LLM 客户端）
├── ingest/         # 数据获取（RSS、API、Web、包管理）
├── knowledge/      # 知识库存储（SQLite + 向量搜索、Review 引擎、跨 Agent 同步）
├── reviewer/       # 文章评审（七维度评分、规则校验、LLM 审稿）
├── dispatch/       # 多平台分发（Hexo 博客、本地文件）
└── cli.py          # CLI 入口（ingest / kb / publish）
```

## 模块状态

| 模块 | 状态 | 说明 |
|------|------|------|
| core | ✅ | 配置中心（`.linglong.yaml`）、共享数据模型、LLM 客户端 |
| ingest | ✅ | RSS/API/Web 数据获取、早报生成 |
| knowledge | ✅ | SQLite + sqlite-vec 存储、Review 引擎、OpenClaw/Claude/Codex 同步 |
| reviewer | ✅ | 七维度评分审稿、规则校验、LLM 评审建议 |
| dispatch | ✅ | Hexo 发布（git workflow）、本地文件输出 |
| mcp | ✅ | MCP Server（14 工具，按模块控制） |

## 快速开始

```bash
git clone https://github.com/xinovate/linglong.git
cd linglong

# 安装依赖
pip install -e ".[dev]"

# 配置
cp .linglong.yaml.example .linglong.yaml
# 编辑 .linglong.yaml 按需修改

# 运行
linglong ingest     # 获取数据
linglong kb write   # 写入知识库
linglong publish    # 发布到博客
```

## 配置

主配置文件为 `.linglong.yaml`（搜索路径：`./.linglong.yaml` → `~/.linglong/config.yaml`）。也支持环境变量（前缀 `LL_`）。

```yaml
# .linglong.yaml 示例
knowledge:
  wiki_path: ~/linglong/wiki
  embedding_url: http://localhost:7997

reviewer:
  llm_model: glm-5.1
  passing_score: 6.0

dispatch:
  default_publisher: hexo
```

完整配置项参考 [`.linglong.yaml.example`](.linglong.yaml.example)。

## 技术栈

- **Python 3.11+**
- **Pydantic** — 数据验证与配置管理
- **SQLite + sqlite-vec** — 本地存储与向量搜索
- **pytest** — 测试框架

## 文档

- [项目总览](docs/PROJECT_OVERVIEW.md) — 版本状态与 Next Actions
- [架构设计](docs/architecture.md) — 系统架构与 Mermaid 流程图
- [开发规范](docs/rules.md) — 代码风格、Git 工作流、Agent 协作
- [版本路线图](docs/roadmap.md) — v0.1–v1.0 演进与 ADR
- [API 文档](docs/api.md) — 公共接口
- 模块文档：[ingest](docs/ingest/) | [knowledge](docs/knowledge/) | [reviewer](docs/reviewer/) | [dispatch](docs/dispatch/)

## License

MIT
