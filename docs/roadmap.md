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
| **v2.0** | **产品化（多模板 + 发布队列 + Codex 接入）** | **🔴 未开始** |

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

### v1.3 已完成（ingest 信源增强 + 动态标签 + 反馈闭环）

| # | 任务 | 模块 | 优先级 | 状态 |
|---|------|------|--------|------|
| 1 | ArXiv 适配器（cs.AI/CL/RO 论文采集） | ingest | **高** | ✅ |
| 2 | GitHub Search 适配器（topic + stars 筛选） | ingest | **高** | ✅ |
| 3 | OpenAI Blog RSS 接入 | ingest | **高** | ✅ |
| 4 | LLM 动态标签（auto_tag） | ingest | **高** | ✅ |
| 5 | search_queries 替换 dimensions | ingest | **高** | ✅ |
| 6 | 晨报模板统一两列表格 | ingest | 中 | ✅ |
| 7 | FeedbackStore + ingest_feedback 表 | ingest | 中 | ✅ |
| 8 | Top 5 偏好注入 | ingest | 中 | ✅ |
| 9 | MCP record_feedback 工具 | ingest | 低 | 待实现 |

### v2.0 收尾项

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

### ingest 已知问题（非阻塞）

- Top5 偶发 JSON 解析失败（LLM 返回格式不标准）
- 晨报模板列名硬编码（投资方/金额），实际数据无这些字段
- AIHOT + SearXNG 重复新闻较多（去重已处理但消耗 token）
- LLM 无分批机制，超过 50 条可能超 token 限制

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
