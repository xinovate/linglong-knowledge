# 版本路线图

## 愿景

Linglong 作为所有 AI Agent 的统一知识底座，串联 **信息采集 → 讨论沉淀 → 内容生产 → 多平台分发** 的完整闭环。

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
| v1.0 | 模块边界对齐 + 知识库封版 | ✅ |
| **v1.2** | **ingest 早报能力（SearXNG + AIHOT + LLM 解读 + 晨报）** | **✅** |
| **v1.3** | **ingest 信源增强 + 动态标签 + 反馈闭环** | **✅** |
| **v2.0** | **IngestAgent LLM 早报重构 + GitHub Trending + BriefHistory 去重** | **✅** |
| **v2.1** | **早报数据源 RSS 化 + 产品化（多模板 + 发布队列）** | **🔴 未开始** |

## v1.0 已完成

### 知识库（已封版）

- ✅ MCP Server 9 工具
- ✅ RRF 混合搜索 + 自动模式路由
- ✅ lint 巡检增强（孤儿检测 + 语义去重 + 定期调度）
- ✅ Agent 接入（OpenClaw MCP + Claude Code MCP）
- ✅ CLI kb/pipeline 分组重构
- ✅ facet 重分类 7→6 + Entity.group 子目录
- ✅ DB 先行写入 + embedding hash 守卫 + kb sync
- ✅ 276 测试全通过

### ingest v1.1（解耦 + MCP 化）

- ✅ 解耦 KnowledgeStore
- ✅ 新增 ingest MCP 工具（共 11 个）
- ✅ CLI 扁平化

## v1.2 已完成（ingest 早报）

- ✅ SearXNG 自托管搜索（Docker 部署，JSON API）
- ✅ WebSearchAdapter 四后端（SearXNG/ZhiPu/Google/Bing CN）
- ✅ AIHOT 适配器（daily digest + items API）
- ✅ 多源聚合架构（所有源聚合后统一 LLM 解读）
- ✅ LLM 批量解读（glm-5.1, Anthropic Messages API）
- ✅ Top 5 四维精选（公司/战略/技术/启示）
- ✅ ingest_history 持久化 + 跨天去重
- ✅ 晨报 Markdown 模板
- ✅ 包配置合并到 .linglong.yaml（ingest.packages）
- ✅ 搜索关键词优化（英文关键词效果远好于中文）
- ✅ 端到端实测通过（AIHOT 26 条 + SearXNG 116 条 → 47 条精选 → LLM 解读 → Top 5）
- ✅ 339 测试全通过

## 下一步工作

### v2.0 已完成（IngestAgent 重构）

| # | 任务 | 模块 | 状态 |
|---|------|------|------|
| 1 | IngestAgent：预搜索 SearXNG + 单次 LLM prompt → 直接输出 markdown | ingest | ✅ |
| 2 | GitHub Trending 多源 fallback（OpenGithubs → wangchujiang → Search API） | ingest | ✅ |
| 3 | 开源趋势日/周/月三段分层（日5 + 周3 + 月3） | ingest | ✅ |
| 4 | 5 维度优化：关键人物(原研究员观点)、公司动态(+融资+股价)、政策动态(+日期)、开源趋势、应用落地 | ingest | ✅ |
| 5 | 中英文混合搜索 + 12 家头部公司关键词（美5 + 中7） | ingest | ✅ |
| 6 | BriefHistory 维度去重（关键人物/政策 14d，公司/应用 7d） | ingest | ✅ |
| 7 | MCP record_feedback 工具 | ingest | ✅ |
| 8 | 387 测试全通过 | ingest | ✅ |

### v2.1 待做（早报数据源 RSS 化）

| # | 任务 | 模块 | 优先级 | 说明 |
|---|------|------|--------|------|
| 1 | 为关键人物/公司动态/政策动态/应用落地找国内可用的高质量 RSS 源 | ingest | **高** | 机器之心、36氪、TechCrunch 等 |
| 2 | RSS 源接入 IngestAgent prompt（复用现有 rss.py） | ingest | **高** | 按维度配置 RSS feed |
| 3 | 公司融资快照（JSON 数据文件 + prompt 注入） | ingest | 中 | 避免 LLM 编造融资数据 |
| 4 | 关键人物关键词扩展（更多国内外 AI 领袖） | ingest | 中 | 持续补充 |

### v2.2 收尾项

| # | 任务 | 模块 | 优先级 | 说明 |
|---|------|------|--------|------|
| 1 | OpenClaw 观察期收尾 | agent | 🟡 | 确认 MCP 写入质量，禁用 wiki-maintainer |
| 2 | Codex CLI 接入 | agent | 🔴 | 当前仅预留，未实际接入 |
| 3 | 拥挤 facet 根目录清理 | knowledge | 🟡 | concept/methodology/project 根目录未分组条目 |
| 4 | IngestAdapter → KnowledgeAdapter 重命名 | composer | 低 | 名称与 ingest 模块混淆 |
| 5 | output_log 输出追踪 | knowledge | 中 | 发布后记录 entity_id + publisher |
| 6 | 发布队列 + 失败重试 | dispatch | 中 | DispatchManager 当前直连发布 |
| 7 | 多模板（周报/PPT/视频脚本） | composer | 中 | 当前只有博客模板 |
| 8 | AI 封面图生成 | composer | 低 | 图片资产管线已搭建，缺 AI 生成 |
| 9 | 跨 Agent 写入冲突解决 | knowledge | 低 | 多 Agent 同时修改同一 wiki |
| 10 | API 冻结 + mypy strict | core | 低 | 稳定公开接口 |

### ingest 已知问题（v2.0）

- 政策动态/应用落地维度条目偏少，根因是 SearXNG 通用搜索对细分领域覆盖不足 → v2.1 通过 RSS 专用数据源解决
- 公司融资/股价数据依赖搜索结果，无数据时 LLM 可能不填 → v2.1 通过融资快照数据文件解决
- BriefHistory 去重基于历史输出段落注入 prompt，LLM 理解"不重复"指令，但无法 100% 保证不重复

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

### ADR-006: ingest 不写知识库（v1.0）

**决策**: ingest 是信息采集工具，采集结果返回给调用方，不直接写入 KnowledgeStore。
- **原因**: 知识库的价值在于经过思考沉淀的知识。原始数据未经验证，直接入库会稀释质量。

### ADR-007: entity 输出追踪 output_log（v1.0）

**决策**: composer + dispatch 发布后记录 entity_id + publisher + published_at，避免重复消费。

### ADR-008: 移除 pipeline 子命令分组（v1.0）

**决策**: 移除 `linglong pipeline` 子命令分组。`ingest`、`compose`、`publish` 改为顶层命令。
- **原因**: ingest 与知识库解耦后不再是流水线的一环，pipeline 概念不再适用。

### ADR-009: 多源聚合架构（v1.2）

**决策**: 所有数据源（AIHOT、SearXNG、RSS）采集后聚合到一个池子，再统一调用 LLM 解读。
- **原因**: 按维度分别解读会丢失跨源关联。聚合后一次 LLM 调用能识别重复、综合判断价值。
- **影响**: interpret_dimension 接收全部 Entity 而非单维度 Entity。

### ADR-010: 包配置内联到 .linglong.yaml（v1.2）

**决策**: 采集包定义从独立 YAML 文件合并到 `.linglong.yaml` 的 `ingest.packages` 字段。
- **原因**: 单一配置文件管理所有设置，减少维护成本。clone 即可用。
- **影响**: `package_paths` 字段移除，CLI 从 `config.ingest.packages` 直接加载。

### ADR-011: LLM 动态标签替代硬编码维度（v1.3）

**决策**: 维度归属由 LLM 根据内容自动判断，不再由搜索关键词分组决定。`dimensions` 配置替换为扁平的 `search_queries`。
- **原因**: 搜索关键词预分组导致同一条新闻只能归一个维度，无法跨维度。LLM 打标更准确，且配置更简洁。
- **影响**: 移除 `DimensionConfig`、`SearchConfig`、`FilterConfig`，新增 `SearchQueryConfig` 和 `auto_tag()`。

### ADR-012: 信源选择 — ArXiv + GitHub + RSS（v1.3）

**决策**: v1.3 新增 ArXiv、GitHub Search、OpenAI Blog RSS 三个信源。X/Twitter、Reddit、Hacker News 暂不纳入。
- **原因**: ArXiv（研究前沿）、GitHub（开源趋势）、OpenAI Blog（官方一手）均为免费直连高信噪比渠道。X/Twitter 成本过高（$100+/月），Reddit 需代理不稳定，HN AI 相关内容偏观点非新闻。
- **影响**: 新增 `ArXivAdapter`、`GitHubAdapter`，RSS 复用现有 `RSSAdapter`。

### ADR-013: IngestAgent 替代代码流水线（v2.0）

**决策**: 将 ingest 早报从"代码编排流水线（适配器→JSON→LLM打标→模板拼接）"重构为"LLM Agent 单次 prompt"。
- **原因**: v1.3 流水线把 LLM 切成碎片化 JSON 调用，auto_tag/interpret 超过 50 条时 JSON 解析频繁失败。OpenClaw 仅用一个 skill prompt 就产出高质量日报。LLM 在一个连贯思考流里做搜索+过滤+组织+写作，效果远优于工程化拆解。
- **影响**: 新增 `agent.py`（IngestAgent）、`brief_history.py`（BriefHistory）、`prompts/morning_brief.md`。旧代码保留为 legacy。

### ADR-014: GitHub Trending 三级 fallback + 日/周/月分层（v2.0）

**决策**: 开源趋势数据从 OpenGithubs（主）→ wangchujiang.com（备）→ GitHub Search API（兜底），按日/周/月分层展示。
- **原因**: GitHub 官方 trending 页面国内不可达。OpenGithubs 通过 GitHub Contents API（api.github.com 国内可达）提供结构化日/周/月排行数据。wangchujiang.com 有缓存延迟风险。Search API 只能查新建仓库，非"今日趋势"。
- **影响**: `_github_trending()` 返回 `(repos, source)` 元组，prompt 标注数据来源。
