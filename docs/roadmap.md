# 版本路线图

## 愿景

Linglong 作为所有 AI Agent 的统一知识底座，串联 **信息获取 → 知识沉淀 → 内容生产 → 多平台分发** 的完整闭环。

## 版本演进

| 版本 | 主题 | 状态 |
|------|------|------|
| v0.1 | 项目骨架 | ✅ |
| v0.2 | core + ingest + knowledge + composer 骨架 | ✅ |
| v0.3 | 人工审核层（Draft Mode + Git Workflow Publisher） | ✅ |
| v0.4 | 知识库统一（向量搜索、OpenClaw wiki 同步、跨 Agent Schema） | ✅ |
| v0.5 | ingest 通用化（RSS/API/WebFetch、验证引擎） | ✅ |
| v0.6 | 多 Agent 接入（Claude Code memory、Codex 同步） | ✅ |
| v0.7 | composer 产品化（LLM 提炼、Prompt 外部化） | ✅ |
| v0.8 | dispatch 正式化（DispatchManager、HexoPublisher、LocalPublisher） | ✅ |
| v0.9 | 稳定化（CLI、集成测试、auto-publish、配置外部化） | ✅ |
| **v1.0** | **博客流水线端到端跑通** | **进行中** |

## v1.0 目标

博客流水线端到端验证：ingest → knowledge → compose → publish，包含图片资产管线。

### 已完成

- ✅ ImageAssetFetcher（下载/压缩/EXIF）
- ✅ ImageAssetSelector（URL 文件解析/随机选择/去重）
- ✅ PageImageResolver（Playwright 页面解析）
- ✅ Composer 集成（background + article_image）
- ✅ BlogTemplate 支持 cover_image 和 article_image
- ✅ `.linglong.yaml` 配置文件支持
- ✅ 文档重组

### 待完成

- 🟡 端到端验证：管道已跑通（sync→ingest→compose→publish），内容质量待改进
  - OpenClaw wiki frontmatter 混入正文
  - RSS ingest 条目 status 为 pending_review，未进入 compose
  - 100 条聚合为 1 篇 927K 字符文章，需截断/摘要策略

## v2.0 延后项

- WebSearchAdapter 实际搜索
- 发布队列与失败重试
- 多模板（早报/周报/PPT/视频脚本）
- AI 封面图生成
- 跨 Agent 写入冲突解决
- API 冻结、mypy strict（datetime.utcnow() 已修复）

---

## 关键架构决策

### ADR-001: Linglong 作为跨 Agent 知识中枢

**决策**: 所有 Agent 通过 KnowledgeStore 统一读写，各自维护独立知识库但通过 Linglong 同步。

### ADR-002: 知识库同步方向

**决策**: 采用 Pull 模式 — Linglong 主动从各 Agent 知识库拉取，而非 Agent 推送到 Linglong。

### ADR-003: 向量搜索双模式

**决策**: 远程 embedding 服务（OpenClaw）+ 本地 sqlite-vec fallback。

### ADR-004: Agent 命名空间前缀

**决策**: Entity 的 `created_by` 字段使用 `agent:xxx` 前缀标识来源。

### ADR-005: Memory 类型映射

**决策**: 各 Agent 的 memory 类型统一映射为 Linglong Entity，保留原始类型信息在 metadata 中。
