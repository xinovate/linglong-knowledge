# D-02 Agent 流水线

> 状态：✅ 已实现 | 最后更新：2026-05-26

---

## 概述

`IngestAgent.run()` 是 ingest 的核心——三路数据采集、聚合去重、单次 LLM prompt 直接输出 markdown 早报。

---

## 流程

```
1. 三路并发采集
   asyncio.gather(
       _search_all_keywords(package),   # SearXNG
       _github_trending(),               # GitHub
       _fetch_rss_feeds(),               # RSS
   )

2. URL 去重 + 交叉去重
   SearXNG 内部 URL 去重
   RSS 内部 URL 去重
   RSS 排除已出现在 SearXNG 中的 URL

3. Prompt 组装
   占位符替换：
   {topic}          包主题
   {date}           今天日期
   {time_range}     播报时段
   {search_results} SearXNG 搜索结果
   {github_data}    GitHub Trending 表格
   {rss_data}       RSS 条目
   {company_snapshot} 公司融资快照
   {preference_section} 用户偏好
   {history_section}   BriefHistory 近期已播报

4. LLM 调用
   _call_llm(prompt)
   - 读取 config.composer.llm_base_url + llm_model
   - Anthropic Messages API 格式
   - 最多 llm_retries=2 次重试
   - 超时 llm_timeout=120s

5. 保存 BriefHistory
   保存当天输出，供后续跨天去重
```

---

## LLM 配置

| 配置 | 值 | 说明 |
|------|---|------|
| model | glm-5.1 | 智谱旗舰模型 |
| base_url | `https://open.bigmodel.cn/api/anthropic` | Anthropic 兼容端点 |
| max_tokens | 8000 | 输出上限 |
| timeout | 120s | 单次调用超时 |
| retries | 2 | 失败重试次数 |

`_call_llm()` 从 config 读 base_url（非硬编码），支持切换模型和端点。

---

## 时段标记

```python
schedule_time = config.ingest.brief_schedule_time  # "07:30"
time_range = f"{(date.today() - timedelta(days=1)).isoformat()} {schedule_time} → {today} {schedule_time}"
```

输出：`> 播报时段：2026-05-25 07:30 → 2026-05-26 07:30`

---

## 容错

- 单个 SearXNG 查询失败：log warning，返回空列表，不阻断
- 单个 RSS 源失败：log warning，跳过该源
- GitHub Trending：三级 fallback
- LLM 调用失败：重试 llm_retries 次，仍失败则 BriefHistory fallback（返回历史输出）

---

## 关键文件

| 文件 | 说明 |
|------|------|
| `src/linglong/ingest/agent.py` | `IngestAgent.run()` + 所有采集方法 |
| `src/linglong/ingest/prompts/morning_brief.md` | 早报 prompt 模板 |
| `src/linglong/core/config.py` | `IngestConfig` 配置模型 |
