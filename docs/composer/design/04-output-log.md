# D-04 溯源记录设计

> 状态：✅ 已实现 | 最后更新：2026-05-26

---

## 概述

记录"哪些知识实体被编排进了哪篇文章，发布到了哪个平台"。纯追加审计日志，不过滤、不排除实体。

---

## 设计决策

**为什么不在实体 metadata 上打标记？**

- 实体是知识库的核心资产，不应该因为被编排过就被修改
- 同一实体可能被多次编排（不同角度、不同文章）
- output_log 是追加型，天然支持多次消费记录

**output_log 不过滤实体。** 下次 composer 运行时，已消费的实体仍可被重新编排。去重由 `ComposerState` 的哈希机制处理。

---

## 存储格式

**位置**：`~/linglong/state/output_log.jsonl`

每行一条记录：

```json
{
  "article_id": "abc123",
  "article_title": "MCP 协议实战笔记",
  "entity_ids": ["entity-001", "entity-002", "entity-003"],
  "publisher": "hexo",
  "published_at": "2026-05-26T10:30:00+08:00",
  "status": "published"
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `article_id` | str | 草稿 ID |
| `article_title` | str | 文章标题 |
| `entity_ids` | list[str] | 被消费的知识实体 ID 列表 |
| `publisher` | str | 发布平台（hexo / local） |
| `published_at` | str | ISO 8601 时间戳 |
| `status` | str | published / draft |

---

## 接口

```python
class OutputLog:
    def append(self, article_id, title, entity_ids, publisher, status) -> None
        """追加一条记录"""

    def query_by_entity(self, entity_id) -> list[dict]
        """查询某实体被用在哪些文章"""

    def query_by_article(self, article_id) -> dict | None
        """查询某文章用了哪些实体"""
```

---

## 调用时机

1. `auto_publish=true` 时：dispatch 发布成功后追加
2. `draft=true` 时：草稿保存时追加（status=draft）
3. 草稿手动发布时：`publish_draft()` 成功后更新 status=published

---

## 与 ComposerState 的关系

| | ComposerState | OutputLog |
|---|---|---|
| 作用 | 哈希去重（防重复处理） | 溯源记录（谁用在了哪里） |
| 存储 | JSON（processed_hashes） | JSONL（追加） |
| 过滤 | 过滤已处理片段 | 不过滤 |
| 写入时机 | 每次处理完一组 | 每次发布/保存草稿时 |
