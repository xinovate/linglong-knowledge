# D-01 流水线设计

> 状态：✅ 已实现 | 最后更新：2026-05-26

---

## 概述

`Composer.run()` 是一条完整的内容生产流水线，从知识库提取实体到输出可发布文章。

---

## 流程

```
1. 提取实体     _extract_fragments(since)
   KnowledgeStore.search(status=AUTO_CONFIRMED, limit=100)
   → IngestAdapter.adapt_many(entities)
   → MemoryFragment 列表

2. 去重          ComposerState.filter_new()
   MD5(source:content) 哈希对比
   → 排除已处理的片段

3. 分组策略
   distiller_use_llm=false → DailyAggregator.aggregate() → 按天分组
   distiller_use_llm=true  → LLMDistiller.group_by_theme() → 按主题分组

4. 逐组处理      _process_day(date_key, fragments)
   4a. 提炼素材
       LLM 模式 → LLMDistiller.distill() → ArticleMaterial
       规则模式 → DailyAggregator + TextAssetGenerator → ArticleMaterial
   4b. 应用模板
       BlogTemplate.apply(content, metadata) → formatted markdown
   4c. 质量校验（v1.1 新增）
       QualityLint.check(formatted, metadata) → LintResult
   4d. 保存草稿 / 标记发布
       draft=true → DraftManager.save_draft()
       auto_publish → DispatchManager.publish()

5. 溯源记录（v1.1 新增）
   OutputLog.append(article_id, entity_ids, publisher)
```

---

## 分组策略对比

| | 按天聚合 | 按主题分组 |
|---|---|---|
| 配置 | `distiller_use_llm: false` | `distiller_use_llm: true` |
| 实现 | `DailyAggregator` | `LLMDistiller` |
| 成本 | 零 | LLM 调用 |
| 效果 | 每天一篇 | 跨天合并同主题 |
| 适用 | 碎片化记录 | 有明确主题线索的内容 |

---

## MemoryFragment 模型

```python
@dataclass
class MemoryFragment:
    source: str           # 来源标识（entity 的 source name）
    content: str          # 内容正文
    timestamp: datetime   # 实体创建时间
    metadata: dict        # entity_id, confidence, status, created_by
    raw_path: str = ""
```

---

## ArticleMaterial 模型

```python
class ArticleMaterial:
    date: str                         # 日期或主题 key
    fragments: list[MemoryFragment]   # 原始片段
    title: str                        # 文章标题
    excerpt: str                      # 摘要
    tags: list[str]                   # 标签
    categories: list[str]             # 分类
    raw_content: str                  # 编译后的正文
```

---

## 关键文件

| 文件 | 说明 |
|------|------|
| `src/linglong/composer/composer.py` | 编排器，`Composer.run()` 和 `_process_day()` |
| `src/linglong/composer/ingest_adapter.py` | `IngestAdapter` Entity → MemoryFragment |
| `src/linglong/composer/state.py` | `ComposerState` 哈希去重 |
| `src/linglong/composer/distiller/aggregator.py` | `DailyAggregator` + `ArticleMaterial` |
| `src/linglong/composer/distiller/llm_distiller.py` | `LLMDistiller` 智能提炼 + 主题分组 |
| `src/linglong/composer/assets/prompts/blog/` | LLM prompt 模板（system.md, user_template.md） |
