# Ingest 设计总览

> 版本：v1.1 | 更新：2026-05-22 | 状态：设计中

---

## 定位

**ingest 是用户的信息采集助手。**

采集结果交给用户阅读和思考，有价值的内容在讨论中沉淀进知识库。ingest 不是知识库的数据入口——知识库的入口是"人的思考"。

```
数据源 → ingest（采集+验证+精选+去重+格式化）→ 定制化信息 → 用户阅读思考 → 讨论 → 沉淀 → 知识库
```

ingest 负责从采集到格式化输出的完整链路。推送和调度由调用方处理。

---

## 信息维度

ingest 采集的信息覆盖 6 个维度，服务于 AI 领域的技术决策和战略判断：

| # | 维度 | 采集内容 | 数据源方式 | 精选标准 |
|---|------|---------|-----------|---------|
| 1 | 研究员观点 | 技术前沿方向、新范式 | 搜索（Google/必应CN） | 提出新概念 → 关注；重复观点 → 跳过 |
| 2 | 公司决策 | 战略调整、产品发布、人事变动 | web_fetch + 搜索 | 战略级决策 → 关注；小版本 → 跳过 |
| 3 | 资本决策 | 大额融资、投资机构动向 | 搜索 + web_fetch | >$100M → 关注；小轮次 → 跳过 |
| 4 | 国家政策 | AI 监管、产业政策 | 搜索 + web_fetch | 国家级 → 关注；地方小政策 → 跳过 |
| 5 | 开源趋势 | AI 新项目、Stars 爆发增长 | GitHub API | 近3天新增+Stars爆发 → 关注；老项目更新 → 跳过 |
| 6 | 应用落地 | 模型/Agent/机器人产品更新 | 搜索 + web_fetch | 新产品/重大更新 → 关注；patch → 跳过 |

维度可扩展——加维度就是加 YAML 配置段，不需要改代码。

### 关注列表

**研究员**：Karpathy、LeCun、Ilya、Hinton、何恺明、李飞飞、姚顺雨、Andrew Ng、Harrison Chase、Lilian Weng、Jim Fan、Dario Amodei、Sergey Levine

**公司（国外）**：OpenAI、Anthropic、Google DeepMind、Meta FAIR、xAI、Mistral、Figure AI、Tesla

**公司（国内）**：字节、阿里、腾讯、百度、小米、DeepSeek、智谱、月之暗面、MiniMax、宇树、智元

**投资机构**：红杉、a16z、软银、Founders Fund、高瓴、IDG

**政策来源**：工信部、科技部、NIST、EU AI Act

---

## 执行链路

```
采集（WebSearch/RSS/API/WebFetch）
  ↓ 可能 30+ 条
真实验证（TruthVerificationEngine，5 层）
  ↓ 过滤虚假数据
维度精选（DimensionFilter，每维度 max_results 条）
  ↓ 30 条 → 每维度 3-5 条
消息去重（同天 + 跨天）
  ↓ 跳过旧闻，保留全新/进展
按维度分组 → 格式化模板 → 输出
```

---

## 数据源架构

### 现有适配器

| 适配器 | 状态 | 说明 |
|--------|------|------|
| `RSSAdapter` | ✅ 可用 | RSS feed 采集 |
| `WebFetchAdapter` | ✅ 可用 | HTTP 页面抓取 |
| `APIAdapter` | ✅ 可用 | REST API 调用（GitHub API 等） |
| `WebSearchAdapter` | 🔴 空壳 | 搜索引擎采集，待实现 |

### 搜索策略

搜索是 ingest 最大的功能缺口（6 维度中 4 个依赖搜索）。

```
有代理 → Playwright 无头模式 → Google 搜索 → 提取结果
无代理 → web_fetch → 必应 CN（cn.bing.com）→ 提取结果
```

- Google：用 Playwright 无头浏览器（项目已有 Playwright 依赖），不需要 API key
- 必应 CN：用 web_fetch 抓搜索结果页，国内直连
- 代理配置：`.linglong.yaml` 中 `ingest.proxy: "http://127.0.0.1:7890"`，传给 Playwright launch 参数
- 不做 ClashX 自动启停，代理由用户管理

### 代理配置

```yaml
# .linglong.yaml
ingest:
  proxy: "http://127.0.0.1:7890"   # 有值 → Playwright + Google；无值 → web_fetch + 必应 CN
```

---

## YAML 包设计

### 目标结构

```yaml
name: ai-morning-brief
topic: AI
schedule: "0 7 * * *"              # 调度（由调用方解释，ingest 不执行）

output:
  format: morning-brief             # 模板名，对应 ingest/templates/morning_brief.py
  persist: true                     # 是否持久化到 data/briefs/

dimensions:
  - name: 研究员观点
    search:
      keywords:
        - "Karpathy AI 最新"
        - "LeCun 世界模型 JEPA"
        - "Ilya Sutskever AI"
      engine: auto                  # auto | google | bing_cn
    filter:
      max_results: 3                # 每维度最多保留几条
      max_age_days: 7               # 超过几天跳过

  - name: 公司决策
    search:
      keywords:
        - "OpenAI 产品发布"
        - "Anthropic 最新动态"
    sources:
      - id: anthropic-news
        type: web_fetch
        config:
          url: https://www.anthropic.com/news
    filter:
      max_results: 5
      max_age_days: 3

  - name: 资本决策
    search:
      keywords:
        - "OpenAI 融资"
        - "具身智能 投资 2026"
    filter:
      max_results: 3
      max_age_days: 7

  - name: 国家政策
    search:
      keywords:
        - "工信部 AI 政策"
        - "EU AI Act 最新"
    filter:
      max_results: 2
      max_age_days: 7

  - name: 开源趋势
    sources:
      - id: github-ai-trending
        type: api
        config:
          url: "https://api.github.com/search/repositories"
          params:
            q: "created:>{{date -7d}} ai OR agent OR llm"
            sort: stars
            order: desc
            per_page: 10
    filter:
      max_results: 5
      min_stars: 100
      max_age_days: 3

  - name: 应用落地
    search:
      keywords:
        - "Claude Code 新版本"
        - "宇树 机器人"
    filter:
      max_results: 3
      max_age_days: 3

verification:
  enabled: true
  pass_threshold: 0.6

dedup:
  enabled: true
  lookback_days: 7                  # 往回查几天做跨天去重
```

### 与当前结构的差距

| 字段 | 当前 | 目标 | 说明 |
|------|------|------|------|
| `dimensions` | 无 | 按维度组织采集+精选 | 核心增强 |
| `search` | 无 | 搜索关键词 + 引擎选择 | 配合 WebSearchAdapter |
| `filter` | 无 | 每维度精选规则（max_results, max_age_days, min_stars） | DimensionFilter |
| `output` | 无 | 格式化模板 + 持久化开关 | 格式化输出 |
| `dedup` | 无 | 去重配置 | 跨天去重 |
| `schedule` | 无 | 调度信息 | 仅元数据，ingest 不执行 |

---

## 消息去重

### 同天去重

同一事件被多个数据源报道 → 合并为一条。

实现：标题相似度匹配（关键词重叠率 > 阈值视为同事件）。

### 跨天去重

同一事件在之前 N 天已经出现过 → 判断是否需要保留。

| 场景 | 示例 | 处理 |
|------|------|------|
| 旧闻重复 | OpenAI 融资昨天已报，今天无新信息 | 跳过 |
| 事件进展 | OpenAI 融资昨天报过，今天有新细节 | 保留，标记为"进展" |
| 全新事件 | 之前未出现过 | 保留 |

实现：
1. 每次采集结果持久化到 `ingest_history` 表
2. 新采集时查询过往 N 天记录
3. 用 content_hash 精确匹配 + 标题相似度模糊匹配
4. 匹配到 → 对比内容是否有新增信息

### ingest_history 表

```sql
CREATE TABLE ingest_history (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT,
    summary TEXT,
    entities_mentioned TEXT,    -- JSON: ["OpenAI", "Sam Altman"]
    dimension TEXT NOT NULL,    -- 研究员观点 / 公司决策 / ...
    content_hash TEXT NOT NULL, -- 精确去重
    collected_at TEXT NOT NULL  -- ISO 日期
);
```

---

## 持久化与历史

### 每日结果存储

每次执行采集包后：
1. 结构化数据写入 `ingest_history` 表（用于去重查询）
2. 格式化结果写入 `data/briefs/YYYY-MM-DD.md`（用于回顾）

### 实体时间线（v2.0）

积累数据后，按公司/人维度聚合时间线：

```
OpenAI 2026-05
├── 05-20: 发布 GPT-5
├── 05-15: 融资 $40B（红杉领投）
└── 05-03: 收购 XX 公司
```

需要：实体名提取 + 归类 + 时间线聚合查询。待数据积累后再实现。

---

## 格式化输出

ingest 负责格式化，模板按 YAML 包的 `output.format` 选择。

### execute_package 返回值

```python
{
    "entities": [...],          # 精选后的 Entity 列表
    "total": 142,               # 采集总数
    "filtered": 28,             # 精选后数量
    "output": "markdown 字符串", # 格式化结果（无 output 配置时为 None）
}
```

### 模板系统

模板是 Python 函数，接收按维度分组的 entities，返回 markdown 字符串：

```
ingest/templates/
├── __init__.py
└── morning_brief.py    # 早报模板
```

后续加模板（周报、摘要）就加新文件，不改采集逻辑。

---

## 调用方集成

ingest 不做调度和推送，由调用方触发：

| 调用方 | 触发方式 | 场景 |
|--------|---------|------|
| OpenClaw | cron 定时 → MCP `execute_package` | 每天早上 7 点采集，推钉钉 |
| Claude Code | 用户对话 → MCP `fetch_rss` / `execute_package` | 用户需要时按需采集 |
| CLI | `linglong ingest` | 手动测试/调试 |

---

## 实现路线

| 阶段 | 内容 | 依赖 | 状态 |
|------|------|------|------|
| **Phase 1** | 架构清理（解耦 KnowledgeStore、MCP 工具、CLI 扁平化） | 无 | ✅ 已完成 |
| **Phase 2a** | WebSearchAdapter（Playwright + Google / web_fetch + 必应 CN） | 无 | 🔴 未开始 |
| **Phase 2b** | ingest_history 表 + 每日结果持久化 | 无 | 🔴 未开始 |
| **Phase 2c** | 消息去重（同天 + 跨天） | Phase 2b | 🔴 未开始 |
| **Phase 3** | 维度精选 filter + 格式化模板 + YAML 包增强 | Phase 2a | 🔴 未开始 |
| **Phase 4** | 实体时间线（公司/人维度聚合） | Phase 2b 数据积累 | 🔴 未开始（v2.0） |
| **Phase 5** | 个人化驱动（偏好从知识库读取） | Phase 3 | 🔴 未开始（v2.0） |

---

## 参考

- [早报技能定义](~/.agents/skills/ai-morning-brief/SKILL.md) — 当前 OpenClaw 版本的 6 维度配置
- [Ingest README](../README.md) — 模块使用说明
- [API 文档](../../api.md) — 接口定义
