# 版本路线图

## 愿景

Linglong 作为所有 AI Agent 的统一知识底座，串联 **信息采集 → 讨论沉淀 → 文章评审 → 多平台分发** 的完整闭环。

## 版本演进

| 版本 | 主题 | 状态 |
|------|------|------|
| v0.1 | 项目骨架 | ✅ |
| v0.2 | core + ingest + knowledge + reviewer 骨架 | ✅ |
| v0.3 | 人工审核层（Draft Mode + Git Workflow Publisher） | ✅ |
| v0.4 | 知识库统一（向量搜索、OpenClaw wiki 同步、跨 Agent Schema） | ✅ |
| v0.5 | ingest 通用化（RSS/API/WebFetch、验证引擎） | ✅ |
| v0.6 | 多 Agent 接入（Claude Code memory、Codex 同步） | ✅ |
| v0.7 | reviewer 产品化（LLM 评审、Prompt 外部化） | ✅ |
| v0.8 | dispatch 正式化（DispatchManager、HexoPublisher、LocalPublisher） | ✅ |
| v0.9 | 稳定化（CLI、集成测试、auto-publish、配置外部化） | ✅ |
| v1.0 | 模块边界对齐 + 知识库封版 | ✅ |
| **v1.2** | **ingest 早报能力（SearXNG + AIHOT + LLM 解读 + 晨报）** | **✅** |
| **v1.3** | **ingest 信源增强 + 动态标签 + 反馈闭环** | **✅** |
| **v2.0** | **IngestAgent LLM 早报重构 + GitHub Trending + BriefHistory 去重** | **✅** |
| **v2.1** | **早报数据源 RSS 化（6 源接入 + 交叉去重 + 时效过滤）** | **✅** |
| **v2.2** | **ingest 增强（融资快照 + 关键人物扩展 + 8 RSS + 健康监控 + LLM 容错 + 去重量化）** | **✅** |
| **v2.3** | **安全加固 + MCP 增强（3 服务 API Key + generate_brief/search_web MCP）** | **✅** |
| **v2.4** | **Agent 接入（Claude Code MCP 连通 + RSSHub/asyncio/GitHub 修复 + 10 RSS + 331 测试）** | **✅** |
| **v2.5** | **ingest 质量优化（信息源精度 + 政策覆盖 + LLM 可信度 + 分析去模板化）** | 🔵 |
| **v2.6** | **MCP 远程部署（Cloudflare Tunnel + Redis Token + DNS 迁移 + 全链路验证）** | ✅ |

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

### v2.1 已完成（早报数据源 RSS 化）

| # | 任务 | 模块 | 状态 |
|---|------|------|------|
| 1 | RSS 订阅源配置（.linglong.yaml rss_sources） | config | ✅ |
| 2 | _fetch_rss_feeds() + _format_rss() 实现 | ingest | ✅ |
| 3 | RSS 数据注入 IngestAgent prompt（{rss_data} 占位符） | ingest | ✅ |
| 4 | 6 个 RSS 源接入（AIHOT/36氪/36氪快讯/量子位/The Rundown AI/财联社） | ingest | ✅ |
| 5 | SearXNG ↔ RSS 交叉 URL 去重 | ingest | ✅ |
| 6 | User-Agent header（解决量子位 403） | ingest | ✅ |
| 7 | 应用落地维度新增日期列 | ingest | ✅ |
| 8 | 时效性过滤（≤7 天）+ 日期倒序排序 | ingest | ✅ |
| 9 | 394 测试全通过 | ingest | ✅ |

### v2.2 已完成（ingest 增强）

| # | 任务 | 模块 | 状态 |
|---|------|------|------|
| 1 | 公司融资快照（JSON 数据文件 + prompt 注入） | ingest | ✅ |
| 2 | 关键人物扩展（20+ 人 + 10 条新搜索关键词） | ingest | ✅ |
| 3 | 更多 RSS 源（TechCrunch AI + The Verge AI，共 8 源） | ingest | ✅ |
| 4 | 信源健康监控（SourceHealth + 连续失败告警） | ingest | ✅ |
| 5 | LLM 调用容错（2 次重试 + fallback 到历史输出） | ingest | ✅ |
| 6 | BriefHistory 去重效果量化（token overlap 检测） | ingest | ✅ |
| 7 | 407 测试全通过 | ingest | ✅ |

### v2.4 已完成（Agent 接入 + Bug 修复）

| # | 任务 | 模块 | 状态 |
|---|------|------|------|
| 1 | RSSHub key 仅追加到 RSSHub URL（`:1200` 端口检测），修复非 RSSHub 源 404 | ingest + mcp | ✅ |
| 2 | MCP `_run_async()` 替代 `asyncio.run()`，修复 MCP 事件循环冲突 | mcp | ✅ |
| 3 | GitHub API 用 `gh auth token` 认证（5000 req/hr vs 60 未认证） | ingest | ✅ |
| 4 | Claude Code `settings.json` 配置 linglong MCP（env 注入 API Key） | mcp | ✅ |
| 5 | 新增 2 个 gov RSS 路由（工信部文件公示 + 发改委新闻动态） | config | ✅ |
| 6 | 新增 2 个 RSS 源（财联社深度 + TechCrunch AI），共 10 源 | config | ✅ |
| 7 | 政策搜索关键词扩展（+3 条国内政策关键词，max_results 2→5） | config | ✅ |
| 8 | 331 测试全通过 | — | ✅ |

### v2.5 待做（ingest 质量优化）

核心瓶颈：**信息源质量 + LLM 合成策略**，不是代码问题。

| # | 优化项 | 说明 | 优先级 |
|---|--------|------|--------|
| 1 | SearXNG 中文 AI 新闻覆盖 | 中文关键词搜出的结果相关性低，需更精准的信源或换搜索引擎 | 🟡 |
| 2 | 政策数据源精度 | gov RSS 路由是通用公告，AI 相关条目密度低，需更精准的政策源 | 🟡 |
| 3 | 关键人物覆盖 | 配了 ~20 个人物关键词，实际合成覆盖率低，部分人物常缺席 | 🟡 |
| 4 | LLM 来源可信度判断 | 英文小博客 rumor 和权威媒体被同等对待，需加事实标注（"据 XX 媒体报道"） | 🔴 |
| 5 | Top 5 分析去模板化 | 四段式（公司/战略/技术/启示）机械重复，应因条目而异 | 低 |

### v2.3 收尾项

| # | 任务 | 模块 | 优先级 | 说明 |
|---|------|------|--------|------|
| 1 | OpenClaw 观察期收尾 | agent | 🟡 | 确认 MCP 写入质量，禁用 wiki-maintainer |
| 2 | Codex CLI 接入 | agent | 🔴 | 当前仅预留，未实际接入 |
| 3 | 拥挤 facet 根目录清理 | knowledge | 🟡 | concept/methodology/project 根目录未分组条目 |
| 4 | output_log 输出追踪 | knowledge | 中 | 发布后记录 entity_id + publisher |
| 5 | 发布队列 + 失败重试 | dispatch | 中 | DispatchManager 当前直连发布 |
| 6 | 跨 Agent 写入冲突解决 | knowledge | 低 | 多 Agent 同时修改同一 wiki |
| 7 | API 冻结 + mypy strict | core | 低 | 稳定公开接口 |

> **注意**：composer 模块已在 v2.5 中移除，替换为 reviewer（文章评审引擎）。原 composer 收尾项（IngestAdapter 重命名、多模板、AI 封面图）已归档。

### ingest 已知问题（v2.4）

- BriefHistory 去重基于历史输出段落注入 prompt，LLM 理解"不重复"指令，但无法 100% 保证不重复 → v2.2 新增 check_overlap() token overlap 检测辅助量化
- 公司融资快照数据需要手动更新 JSON 文件（当前更新于 2026-05-25）
- SearXNG 对中文 AI 新闻覆盖不够精准，关键词搜出的结果相关性低 → v2.5 优化
- 关键人物搜索覆盖率偏低（~20 个关键词仅出 ~4 条），部分中国 AI 人物常缺席 → v2.5 优化
- LLM 不区分信源可信度，小博客 rumor 和权威媒体被同等对待 → v2.5 加事实标注
- gov RSS 路由是通用公告，AI 相关条目密度低（工信部/发改委可用，中国政府网 503）→ v2.5 优化

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

**决策**: reviewer + dispatch 发布后记录 entity_id + publisher + published_at，避免重复消费。

### ADR-008: 移除 pipeline 子命令分组（v1.0）

**决策**: 移除 `linglong pipeline` 子命令分组。`ingest`、`review`、`publish` 改为顶层命令。
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

### ADR-015: RSS 订阅源作为 IngestAgent 一等数据源（v2.1）

**决策**: 在 IngestAgent 中新增 RSS 预采集步骤，RSS 数据和 SearXNG/GitHub 数据一起注入 LLM prompt。
- **原因**: SearXNG 通用搜索对公司动态、政策动态、应用落地覆盖不足（噪音多、相关结果少）。RSS 源经编辑筛选，信噪比更高。AIHOT RSS feed 质量尤为突出（精选评分 + 编辑推荐理由）。
- **影响**: 新增 `_fetch_rss_feeds()` + `_format_rss()`，配置在 `.linglong.yaml` 的 `ingest.rss_sources`，prompt 新增 `{rss_data}` 占位符。

### ADR-016: 时效性过滤由 prompt 规则驱动，非 SearXNG time_range（v2.1）

**决策**: 时效性过滤（≤7 天）完全由 prompt 规则约束，不在 SearXNG API 层加 `time_range` 参数。
- **原因**: 测试发现 SearXNG 实例对 `time_range` 参数支持不稳定（加参数后全部返回 0 结果）。LLM 级过滤更灵活，能理解"同一事件有新进展可保留"等语义。
- **影响**: prompt 模板新增时效性规则，代码无需对接 SearXNG time_range。

### ADR-017: 公司融资快照静态 JSON + prompt 注入（v2.2）

**决策**: 公司融资/估值数据存储在静态 JSON 文件中，每次生成早报时加载注入 prompt，不做实时 API 查询。
- **原因**: 公司融资信息更新频率低（月级别），不值得对接实时 API。静态 JSON 维护成本低，LLM 直接引用即可填充公司动态表格。
- **影响**: 新增 `company_snapshot.json`，agent.py 新增 `_load_company_snapshot()` + `_format_company_snapshot()`，prompt 新增 `{company_snapshot}` 占位符。

### ADR-018: 信源健康模块级监控而非请求级（v2.2）

**决策**: SourceHealth 在 `run()` 粒度追踪三大源（SearXNG/GitHub/RSS）的成功/失败，而非在每个 HTTP 请求粒度。
- **原因**: 单次 run 涉及数十次 SearXNG 请求，请求级追踪过于细碎。用户关心的是"今天 SearXNG 整体是否正常"，而非某个关键词搜索是否失败。
- **影响**: `_source_health` 全局实例，每次 run 记录 3 条，连续 3 次失败时 WARN 日志。

### ADR-020: RSSHub key 仅追加到 RSSHub URL（v2.4）

**决策**: RSSHub ACCESS_KEY 通过 `?key=xxx` 追加时，先检测 URL 是否指向 RSSHub 实例（`:1200` 端口），非 RSSHub URL 不追加。
- **原因**: v2.3 实现对所有 RSS URL 统一追加 key，导致 The Verge、TechCrunch 等直接 RSS 源返回 404。
- **影响**: `_is_rsshub_url()` 检测函数，`agent.py` 和 `mcp/tools.py` 两处调用。

### ADR-021: MCP 内部异步调用用 _run_async()（v2.4）

**决策**: MCP Server 工具函数内的异步调用统一使用 `_run_async()` 替代 `asyncio.run()`。
- **原因**: MCP Server 运行在自己的事件循环中，`asyncio.run()` 会抛出 "cannot be called from a running event loop" 错误。`_run_async()` 检测运行中的循环，通过 `ThreadPoolExecutor` 在新线程中执行。
- **影响**: `fetch_rss`、`execute_package`、`generate_brief`、`search_web` 四处替换。

### ADR-022: GitHub API 用 gh auth token 认证（v2.4）

**决策**: IngestAgent 的 GitHub API 调用优先使用 `gh auth token` 获取认证 token。
- **原因**: 未认证 GitHub API 限制 60 req/hr，40 次 SearXNG + 3 次 GitHub 请求后触发 rate limit 403。认证后提升至 5000 req/hr。
- **影响**: `_github_headers()` 函数在 `_fetch_opengithubs()` 和 `_github_search_fallback()` 中使用。

**决策**: `_call_llm` 增加 2 次重试，全部失败时 fallback 到 BriefHistory 最近一次成功输出。
- **原因**: LLM API 偶发 400/500 错误（如 prompt 过长、服务抖动），不应让整个早报生成失败。上次成功的早报作为 fallback，虽不完美但好于无输出。
- **影响**: `_call_llm` 新增 `retries` 参数，`BriefHistory.get_last_output()` 返回最近一次 JSON 内容。
