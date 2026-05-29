# Linglong Knowledge

> 跨 Agent 统一知识库 —— 通过 MCP 为 AI Agent 提供共享知识底座。

## 项目概述

Linglong Knowledge 是跨 Agent 统一知识库，解决 OpenClaw、Claude Code、Codex 等 Agent 知识孤岛问题。通过 MCP 协议提供知识读写能力，支持关键词搜索、语义向量搜索和混合搜索。

## 架构

```
Agent（OpenClaw / Claude Code / Codex）──→ Knowledge Store ──→ MCP Server
                                          (File + SQLite + sqlite-vec)
```

```
src/linglong/
├── core/           # 配置、数据模型、LLM 客户端
├── knowledge/      # 知识库存储（SQLite + sqlite-vec、Review 引擎、Lint、同步）
├── mcp/            # MCP Server（10 工具，stdio / HTTP）
└── cli.py          # CLI 入口
```

## 模块状态

| 模块 | 状态 | 说明 |
|------|------|------|
| core | ✅ | 配置中心（`.knowledge.yml`）、共享数据模型、LLM 客户端 |
| knowledge | ✅ | SQLite + sqlite-vec 存储、Review 引擎、Lint 巡检、OpenClaw 同步 |
| mcp | ✅ | MCP Server（10 工具），支持 stdio 和 HTTP 部署 |

> **注意**：ingest（数据获取）、reviewer（文章评审）、dispatch（多平台分发）已拆分为独立项目。

## 快速开始

```bash
git clone https://github.com/xinovate/linglong-knowledge.git
cd linglong-knowledge

# 安装依赖
pip install -e ".[dev]"

# 配置
cp .knowledge.example.yml .knowledge.yml
# 编辑 .knowledge.yml 按需修改

# CLI 使用
linglong kb lint       # 巡检知识库
linglong kb sync       # 同步数据
linglong kb rebuild    # 重建索引

# MCP Server
ll-knowledge-mcp       # stdio 模式（供 Claude Code 等本地 Agent 使用）
```

### MCP 注册（Claude Code）

```bash
claude mcp add ll-knowledge -- /path/to/.venv/bin/ll-knowledge-mcp
```

## 配置

主配置文件为 `.knowledge.yml`（搜索路径：`./.knowledge.yml` → `~/.knowledge/config.yaml`）。也支持环境变量（前缀 `KB_`）。

```yaml
# .knowledge.yml 示例
knowledge:
  wiki_path: ~/knowledge/wiki
  db_path: ~/knowledge/db/knowledge.db
  generate_embeddings: true
  embedding_url: http://localhost:7997
  embedding_model: nomic-ai/nomic-embed-text-v1.5

mcp:
  transport: stdio
  host: 127.0.0.1
  port: 9900
```

完整配置项参考 [`.knowledge.example.yml`](.knowledge.example.yml) 或 [配置文档](docs/config.md)。

## 技术栈

- **Python 3.11+**
- **Pydantic** — 数据验证与配置管理
- **SQLite + sqlite-vec** — 本地存储与向量搜索
- **FastMCP** — MCP 协议实现
- **pytest** — 测试框架

## 文档

- [项目总览](docs/PROJECT_OVERVIEW.md) — 版本状态与 Next Actions
- [架构设计](docs/architecture.md) — 系统架构与模块依赖
- [API 文档](docs/api.md) — MCP 工具接口与配置说明
- [知识库模块](docs/knowledge.md) — 设计、Agent 接入、参考资料
- [开发规范](docs/rules.md) — 代码风格、测试、安全
- [版本路线图](docs/roadmap.md) — 演进计划与 ADR

## License

MIT
