# Ingest 设计总览

> 版本：v1.0 | 更新：2026-05-22 | 状态：设计中

---

## 定位

**ingest 是用户的信息采集助手。**

采集结果交给用户阅读和思考，有价值的内容在讨论中沉淀进知识库。ingest 不是知识库的数据入口——知识库的入口是"人的思考"。

```
数据源 → ingest（采集+验证）→ 定制化信息 → 用户阅读思考 → 与 Agent 讨论 → 沉淀 → 知识库
```

这个流程中 ingest 只负责第一段（采集+验证），后面全是人的判断。

---

## 信息维度

ingest 采集的信息覆盖 6 个维度，服务于 AI 领域的技术决策和战略判断：

| # | 维度 | 采集内容 | 数据源方式 | 精选标准 |
|---|------|---------|-----------|---------|
| 1 | 研究员观点 | 技术前沿方向、新范式 | 搜索（必应CN/DuckDuckGo） | 提出新概念 → 关注；重复观点 → 跳过 |
| 2 | 公司决策 | 战略调整、产品发布、人事变动 | web_fetch + 搜索 | 战略级决策 → 关注；小版本 → 跳过 |
| 3 | 资本决策 | 大额融资、投资机构动向 | 搜索 + web_fetch | >$100M → 关注；小轮次 → 跳过 |
| 4 | 国家政策 | AI 监管、产业政策 | 搜索 + web_fetch | 国家级 → 关注；地方小政策 → 跳过 |
| 5 | 开源趋势 | AI 新项目、Stars 爆发增长 | GitHub API | 近3天新增+Stars爆发 → 关注；老项目更新 → 跳过 |
| 6 | 应用落地 | 模型/Agent/机器人产品更新 | 搜索 + web_fetch | 新产品/重大更新 → 关注；patch → 跳过 |

### 关注列表

**研究员**：Karpathy、LeCun、Ilya、Hinton、何恺明、李飞飞、姚顺雨、Andrew Ng、Harrison Chase、Lilian Weng、Jim Fan、Dario Amodei、Sergey Levine

**公司（国外）**：OpenAI、Anthropic、Google DeepMind、Meta FAIR、xAI、Mistral、Figure AI、Tesla

**公司（国内）**：字节、阿里、腾讯、百度、小米、DeepSeek、智谱、月之暗面、MiniMax、宇树、智元

**投资机构**：红杉、a16z、软银、Founders Fund、高瓴、IDG

**政策来源**：工信部、科技部、NIST、EU AI Act

---

## 数据源架构

### 现有适配器

| 适配器 | 状态 | 说明 |
|--------|------|------|
| `RSSAdapter` | ✅ 可用 | RSS feed 采集 |
| `WebFetchAdapter` | ✅ 可用 | HTTP 页面抓取 |
| `APIAdapter` | ✅ 可用 | REST API 调用（GitHub API 等） |
| `WebSearchAdapter` | 🔴 空壳 | 搜索引擎采集，未实现 |

### 缺失能力

| 能力 | 优先级 | 说明 |
|------|--------|------|
| **搜索引擎采集** | **高** | 6 个维度中 4 个依赖搜索，这是最大缺口 |
| **代理管理** | 中 | 有代理用 DuckDuckGo，无代理用必应 CN |
| **GitHub API 采集** | 中 | 开源趋势维度专用，当前靠 APIAdapter 手动配置 |
| **精选过滤** | 中 | 采集后按精选标准过滤，当前只有真实验证 |
| **个人化驱动** | 低 | 从知识库读取用户偏好，驱动采集策略 |

### 搜索策略

```
检测代理状态
  ├── 有代理 → DuckDuckGo（web_search）
  └── 无代理 → 必应 CN（web_fetch + cn.bing.com）
```

---

## YAML 包设计

### 当前结构

```yaml
name: ai-morning-brief
topic: AI
enabled: true
verification:
  enabled: true
  pass_threshold: 0.6
sources:
  - id: techcrunch
    type: rss
    config:
      url: https://techcrunch.com/feed/
```

问题：只有数据源定义和验证开关，缺少**维度分类、精选标准、搜索关键词模板**。

### 目标结构（设计）

```yaml
name: ai-morning-brief
topic: AI
schedule: "0 7 * * *"       # 调度（由调用方解释，ingest 不执行）
dimensions:                   # 按维度组织
  - name: 研究员观点
    search:
      keywords:
        - "Karpathy AI 最新"
        - "LeCun 世界模型"
      engine: bing_cn         # bing_cn | duckduckgo
    sources: []               # 该维度的固定数据源
    filter:
      max_age_days: 3
      min_confidence: 0.7

  - name: 开源趋势
    sources:
      - id: github-trending
        type: api
        config:
          url: "https://api.github.com/search/repositories"
          params:
            q: "created:>{{date -7d}} ai OR agent"
            sort: stars
            order: desc
            per_page: 10
    filter:
      min_stars: 100
      max_age_days: 3

verification:
  enabled: true
  pass_threshold: 0.6
```

### 差距

| 字段 | 当前 | 目标 | 差距 |
|------|------|------|------|
| `dimensions` | 无 | 按维度组织 | 需新增 |
| `search` | 无 | 搜索关键词+引擎 | 需新增 |
| `filter` | 无 | 精选标准 | 需新增 |
| `schedule` | 无 | 调度信息 | 仅元数据，ingest 不执行 |

---

## 个人化（v2.0）

用户的信息偏好（关注谁、关注什么公司、什么维度）存储在知识库 `personal` facet。

Agent 接入 ingest 时：
1. 读取知识库中用户的偏好设置
2. 按偏好生成或选择 YAML 包
3. 执行采集，返回定制化信息

当前阶段：偏好写在 YAML 包里手动维护，不做动态个人化。

---

## 调用方集成

ingest 不做调度，由调用方触发：

| 调用方 | 触发方式 | 场景 |
|--------|---------|------|
| OpenClaw | cron 定时 → MCP `execute_package` | 每天早上7点采集，推钉钉 |
| Claude Code | 用户对话 → MCP `fetch_rss` / `execute_package` | 用户需要时按需采集 |
| CLI | `lingest ingest` | 手动测试/调试 |

---

## 实现路线

| 阶段 | 内容 | 状态 |
|------|------|------|
| **Phase 1：架构清理** | 解耦 KnowledgeStore、MCP 工具、CLI 扁平化 | ✅ 已完成 |
| **Phase 2：搜索能力** | WebSearchAdapter 实现（必应 CN + DuckDuckGo）、代理管理 | 🔴 未开始 |
| **Phase 3：YAML 包增强** | dimensions 结构、搜索配置、filter 精选 | 🔴 未开始 |
| **Phase 4：GitHub 适配器** | 专用 GitHubAdapter（trending/search API） | 🟡 可用 APIAdapter 临时替代 |
| **Phase 5：个人化** | 偏好从知识库读取，动态生成采集策略 | 🔴 未开始（v2.0） |

---

## 参考

- [早报技能定义](~/.agents/skills/ai-morning-brief/SKILL.md) — 当前 OpenClaw 版本的 6 维度配置
- [Ingest README](../README.md) — 模块使用说明
- [API 文档](../../api.md) — 接口定义
