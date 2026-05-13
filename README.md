# Linglong

> 跨 Agent 知识中枢 —— 统一知识底座，串联信息获取、知识沉淀、内容生产与多平台分发。

## 项目概述

Linglong 解决 AI Agent 知识孤岛问题：OpenClaw、Claude Code、Codex 各自维护独立知识库，互不相通。Linglong 作为统一知识底座，提供完整的 **获取 → 沉淀 → 生产 → 分发** 闭环。

## 架构

```
ingest → knowledge → composer → dispatch
```

```
src/linglong/
├── core/           # 共享基础设施（配置、数据模型）
├── ingest/         # 数据获取（RSS、API、Web、包管理）
├── knowledge/      # 知识库存储（SQLite + 向量搜索、Review 引擎、跨 Agent 同步）
├── composer/       # 内容生产（LLM 提炼、模板引擎、图片资产、草稿管理）
├── dispatch/       # 多平台分发（Hexo 博客、本地文件）
└── cli.py          # CLI 入口（ingest / compose / publish / sync）
```

## 模块状态

| 模块 | 状态 | 说明 |
|------|------|------|
| core | ✅ | 配置中心（`.linglong.yaml`）、共享数据模型 |
| ingest | ✅ | RSS/API/Web 数据获取、真实性验证引擎 |
| knowledge | ✅ | SQLite + sqlite-vec 存储、Review 引擎、OpenClaw/Claude/Codex 同步 |
| composer | ✅ | LLM/规则提炼、博客模板、图片资产管线、草稿审核 |
| dispatch | ✅ | Hexo 发布（git workflow）、本地文件输出 |
| cli | ✅ | `linglong` CLI：ingest / compose / publish / sync |

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
linglong compose    # 生成文章
linglong publish    # 发布到博客
linglong sync       # 同步 Agent 知识库
```

## 配置

主配置文件为 `.linglong.yaml`（搜索路径：`./.linglong.yaml` → `~/.linglong/config.yaml`）。也支持环境变量（前缀 `LL_`）。

```yaml
# .linglong.yaml 示例
knowledge:
  wiki_path: ~/linglong/wiki
  embedding_url: http://localhost:7997

composer:
  llm_model: gpt-4
  image_assets:
    enabled: true
    sources:
      - name: tuchong
        url_file: ~/Downloads/resource.txt
        resolve_via: playwright

dispatch:
  default_publisher: hexo
```

完整配置项参考 [`.linglong.yaml.example`](.linglong.yaml.example)。

## 技术栈

- **Python 3.11+**
- **Pydantic** — 数据验证与配置管理
- **SQLite + sqlite-vec** — 本地存储与向量搜索
- **Playwright** — 页面图片解析（可选）
- **Pillow** — 图片处理
- **pytest** — 测试框架

## 文档

- [项目总览](docs/PROJECT_OVERVIEW.md) — 版本状态与 Next Actions
- [架构设计](docs/architecture.md) — 系统架构与 Mermaid 流程图
- [开发规范](docs/rules.md) — 代码风格、Git 工作流、Agent 协作
- [版本路线图](docs/roadmap.md) — v0.1–v1.0 演进与 ADR
- [API 文档](docs/api.md) — 公共接口
- 模块文档：[ingest](docs/ingest/) | [knowledge](docs/knowledge/) | [composer](docs/composer/) | [dispatch](docs/dispatch/)

## License

MIT
