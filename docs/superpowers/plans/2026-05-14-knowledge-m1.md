# M1: 数据模型 + 存储层重构 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entity 增加 facet 分类，KnowledgeStore 支持 FTS5 全文搜索 + facet 过滤 + wiki 目录存储 + 版本管理 + 归档。

**Architecture:** 在现有 KnowledgeStore（SQLite + sqlite-vec）基础上扩展。新增 EntityFacet 枚举到 models.py，SQLite 表增加 facet + archived_at 列和 FTS5 虚拟表，store.py 的路径策略从 `wiki/{id[:2]}/{id}.md` 改为 `wiki/{facet}/{slug}.md`。

**Tech Stack:** Python 3.11+, SQLite (sqlean + FTS5 + sqlite-vec), Pydantic v2, pytest

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `src/linglong/core/models.py` | 修改 | 增加 EntityFacet 枚举、Entity 增加 facet + archived_at 字段 |
| `src/linglong/core/config.py` | 修改 | KnowledgeConfig 增加 max_versions、db_mode 字段 |
| `src/linglong/knowledge/store.py` | 重构 | FTS5、facet 过滤、wiki 目录存储、版本管理、归档 |
| `src/linglong/knowledge/review.py` | 小改 | review 方法接受带 facet 的 Entity |
| `src/linglong/knowledge/sync/openclaw.py` | 小改 | sync 时设置 facet 字段 |
| `src/linglong/knowledge/sync/claude_code.py` | 小改 | sync 时设置 facet 字段 |
| `src/linglong/knowledge/sync/codex.py` | 小改 | sync 时设置 facet 字段 |
| `tests/knowledge/test_store.py` | 扩展 | facet、FTS5、版本管理、归档测试 |
| `tests/core/test_models.py` | 扩展 | EntityFacet 枚举测试 |

---

### Task 1: EntityFacet 枚举 + Entity 模型扩展

**Files:**
- Modify: `src/linglong/core/models.py`
- Test: `tests/core/test_models.py`

- [ ] **Step 1: 写 EntityFacet 枚举测试**

在 `tests/core/test_models.py` 末尾追加：

```python
from linglong.core.models import EntityFacet


def test_entity_facet_values():
    """EntityFacet 包含 7 个分面值。"""
    expected = {"source", "entity", "concept", "synthesis", "experience", "methodology", "personal"}
    actual = {f.value for f in EntityFacet}
    assert actual == expected


def test_entity_has_facet_field():
    """Entity 模型包含 facet 字段。"""
    e = Entity(
        content="测试",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    )
    assert e.facet == EntityFacet.CONCEPT


def test_entity_facet_required():
    """facet 字段没有默认值，必须提供。"""
    import pytest
    with pytest.raises(Exception):
        Entity(
            content="测试",
            created_by="agent:claude",
        )


def test_entity_archived_at_default_none():
    """archived_at 默认为 None。"""
    e = Entity(
        content="测试",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    )
    assert e.archived_at is None
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /home/user/projects/linglong && source venv/bin/activate && pytest tests/core/test_models.py::test_entity_facet_values -v`
Expected: FAIL — `ImportError: cannot import name 'EntityFacet'`

- [ ] **Step 3: 在 models.py 中 EntityStatus 之后添加 EntityFacet 枚举**

在 `src/linglong/core/models.py` 的 `EntityStatus` 类（约 L95-102）之后、`Relation` 类之前，插入：

```python
class EntityFacet(StrEnum):
    """Knowledge entity classification."""

    SOURCE = "source"            # 原始资料汇编
    ENTITY = "entity"            # 专有名词
    CONCEPT = "concept"          # 抽象知识
    SYNTHESIS = "synthesis"      # 跨源综合
    EXPERIENCE = "experience"    # 实战经验
    METHODOLOGY = "methodology"  # 方法论
    PERSONAL = "personal"        # 个人数据
```

- [ ] **Step 4: 在 Entity 类中增加 facet 和 archived_at 字段**

在 `src/linglong/core/models.py` 的 Entity 类中，在 `content` 字段之后（约 L130）插入：

```python
    facet: EntityFacet = Field(description="Knowledge classification facet")
    archived_at: datetime | None = Field(default=None, description="Archive timestamp")
```

同时更新 `json_schema_extra` example，在 `"content"` 后添加：
```python
"facet": "concept",
"archived_at": None,
```

- [ ] **Step 5: 运行测试确认通过**

Run: `cd /home/user/projects/linglong && source venv/bin/activate && pytest tests/core/test_models.py -v`
Expected: 4 个新测试 PASS

- [ ] **Step 6: 运行全量测试检查破坏**

Run: `cd /home/user/projects/linglong && source venv/bin/activate && pytest --tb=short 2>&1 | tail -30`
Expected: 已有测试因 Entity 新增必填字段 facet 而失败 — 这些在后续 Task 修复

- [ ] **Step 7: 提交**

```bash
git add src/linglong/core/models.py tests/core/test_models.py
git commit -m "feat(models): 增加 EntityFacet 7 分面枚举 + Entity facet/archived_at 字段"
```

---

### Task 2: KnowledgeConfig 扩展

**Files:**
- Modify: `src/linglong/core/config.py`
- Test: `tests/core/test_config.py`

- [ ] **Step 1: 在 KnowledgeConfig 中增加新字段**

在 `src/linglong/core/config.py` 的 `KnowledgeConfig` 类中，在 `generate_embeddings` 字段之后（约 L170）添加：

```python
    # 写入设置
    write_mode: str = Field(
        default="confirm", description="Write mode: confirm or auto"
    )
    search_mode: str = Field(
        default="on_demand", description="Search mode: on_demand or deep"
    )
    auto_index: bool = Field(
        default=True, description="Auto-update index on write"
    )
    max_versions: int = Field(
        default=10, description="Max version history per entity"
    )

    # 并发设置
    lock_timeout: int = Field(
        default=5, description="File lock timeout in seconds"
    )
    db_mode: str = Field(
        default="wal", description="SQLite journal mode"
    )
```

- [ ] **Step 2: 运行配置测试确认不破坏**

Run: `cd /home/user/projects/linglong && source venv/bin/activate && pytest tests/core/test_config.py tests/core/test_yaml_config.py -v`
Expected: PASS

- [ ] **Step 3: 提交**

```bash
git add src/linglong/core/config.py
git commit -m "feat(config): KnowledgeConfig 增加写入/搜索/并发配置字段"
```

---

### Task 3: 修复现有测试的 facet 兼容性

**Files:**
- Modify: `tests/knowledge/test_store.py`
- Modify: `tests/knowledge/test_review.py`
- Modify: 其他需要 facet 的测试文件

- [ ] **Step 1: 修复 test_store.py 中所有 Entity 构造**

在 `tests/knowledge/test_store.py` 中，所有创建 Entity 的地方添加 `facet=EntityFacet.CONCEPT`，并在 import 中添加 `EntityFacet`：

```python
from linglong.core.models import Entity, EntityStatus, EntityFacet
```

所有 `Entity(content=..., created_by=...)` 调用增加 `facet=EntityFacet.CONCEPT`。

- [ ] **Step 2: 修复 test_review.py 中所有 Entity 构造**

在 `tests/knowledge/test_review.py` 中，同样添加 facet。import 行改为：

```python
from linglong.core.models import Entity, EntityStatus, Source, SourceType, EntityFacet
```

每个 Entity 构造添加 `facet=EntityFacet.CONCEPT`。

- [ ] **Step 3: 搜索并修复所有其他文件中的 Entity 构造**

Run: `cd /home/user/projects/linglong && grep -rn "Entity(" tests/ --include="*.py" | grep -v "EntityFacet"`
逐个检查并添加 `facet=EntityFacet.CONCEPT`。

- [ ] **Step 4: 搜索并修复 src/ 中的 Entity 构造**

Run: `cd /home/user/projects/linglong && grep -rn "Entity(" src/ --include="*.py" | grep -v "EntityFacet" | grep -v "class Entity" | grep -v "# Entity"`
在 sync adapter 和其他源文件中，给 Entity 构造添加适当的 facet（如 `EntityFacet.SOURCE`）。

- [ ] **Step 5: 运行全量测试**

Run: `cd /home/user/projects/linglong && source venv/bin/activate && pytest --tb=short 2>&1 | tail -30`
Expected: 全部 PASS

- [ ] **Step 6: 提交**

```bash
git add tests/ src/
git commit -m "fix: 所有 Entity 构造适配必填 facet 字段"
```

---

### Task 4: SQLite schema 增加 facet 列 + FTS5 虚拟表

**Files:**
- Modify: `src/linglong/knowledge/store.py`（`_init_database` 方法）
- Test: `tests/knowledge/test_store.py`

- [ ] **Step 1: 写 FTS5 + facet 的测试**

在 `tests/knowledge/test_store.py` 末尾追加：

```python
def test_create_entity_stores_facet(temp_store):
    """创建 Entity 时 facet 正确存入 SQLite。"""
    entity = Entity(
        content="微服务架构设计",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    )
    created = temp_store.create(entity)
    retrieved = temp_store.get(created.id)
    assert retrieved.facet == EntityFacet.CONCEPT


def test_search_by_facet(temp_store):
    """按 facet 过滤搜索。"""
    temp_store.create(Entity(
        content="概念文章", facet=EntityFacet.CONCEPT, created_by="agent:claude"
    ))
    temp_store.create(Entity(
        content="踩坑记录", facet=EntityFacet.EXPERIENCE, created_by="agent:claude"
    ))

    concepts = temp_store.search(facet=EntityFacet.CONCEPT)
    assert len(concepts) == 1
    assert concepts[0].facet == EntityFacet.CONCEPT


def test_fts5_fulltext_search(temp_store):
    """FTS5 全文搜索能匹配内容关键词。"""
    temp_store.create(Entity(
        content="SQLite 向量搜索使用 sqlite-vec 扩展",
        facet=EntityFacet.EXPERIENCE,
        created_by="agent:claude",
    ))
    temp_store.create(Entity(
        content="Python 类型提示的最佳实践",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    results = temp_store.search(query="sqlite-vec")
    assert len(results) == 1
    assert "sqlite-vec" in results[0].content

    results2 = temp_store.search(query="Python 类型")
    assert len(results2) == 1
    assert "Python" in results2[0].content
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /home/user/projects/linglong && source venv/bin/activate && pytest tests/knowledge/test_store.py::test_search_by_facet -v`
Expected: FAIL — `TypeError: search() got an unexpected keyword argument 'facet'`

- [ ] **Step 3: 修改 _init_database 增加 facet 列和 FTS5 表**

在 `src/linglong/knowledge/store.py` 的 `_init_database` 方法中：

1. `entities` 表的 `metadata TEXT` 后增加：
```sql
facet TEXT NOT NULL DEFAULT 'concept',
archived_at TIMESTAMP,
```

2. 在 `conn.commit()` 之前，增加 FTS5 虚拟表创建：
```python
# FTS5 全文搜索虚拟表
conn.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS entity_fts USING fts5(
        id,
        content,
        facet,
        status,
        content='entities',
        content_rowid='rowid'
    )
""")

# FTS5 同步触发器
conn.execute("""
    CREATE TRIGGER IF NOT EXISTS entities_ai AFTER INSERT ON entities BEGIN
        INSERT INTO entity_fts(rowid, id, content, facet, status)
        VALUES (new.rowid, new.id, new.content, new.facet, new.status);
    END
""")
conn.execute("""
    CREATE TRIGGER IF NOT EXISTS entities_ad AFTER DELETE ON entities BEGIN
        INSERT INTO entity_fts(entity_fts, rowid, id, content, facet, status)
        VALUES ('delete', old.rowid, old.id, old.content, old.facet, old.status);
    END
""")
conn.execute("""
    CREATE TRIGGER IF NOT EXISTS entities_au AFTER UPDATE ON entities BEGIN
        INSERT INTO entity_fts(entity_fts, rowid, id, content, facet, status)
        VALUES ('delete', old.rowid, old.id, old.content, old.facet, old.status);
        INSERT INTO entity_fts(rowid, id, content, facet, status)
        VALUES (new.rowid, new.id, new.content, new.facet, new.status);
    END
""")
```

- [ ] **Step 4: 修改 create() 方法的 SQL 包含 facet 和 archived_at**

在 `store.py` 的 `create` 方法中，INSERT SQL 增加 `facet` 和 `archived_at` 列：

```sql
INSERT INTO entities
(id, content, summary, facet, created_by, confirmed_by, confirmed_at,
 confidence, status, sources, relations, versions, current_version,
 created_at, updated_at, archived_at, embedding_id, metadata)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
```

params 增加 `entity.facet.value` 和 `None`（archived_at）。

- [ ] **Step 5: 修改 search() 增加 query 和 facet 参数**

替换 `search` 方法签名为：

```python
def search(
    self,
    query: str | None = None,
    facet: EntityFacet | None = None,
    status: EntityStatus | None = None,
    created_by: str | None = None,
    limit: int = 50,
) -> list[Entity]:
```

在方法体中，如果有 `query` 参数，使用 FTS5：
```python
if query:
    # FTS5 全文搜索
    conditions_fts = []
    params_fts: list = [query]

    if facet:
        conditions_fts.append("entity_fts.facet = ?")
        params_fts.append(facet.value)
    if status:
        conditions_fts.append("entity_fts.status = ?")
        params_fts.append(status.value)

    fts_where = " AND ".join(conditions_fts) if conditions_fts else "1=1"

    rows = conn.execute(
        f"""
        SELECT e.* FROM entity_fts
        JOIN entities AS e ON e.id = entity_fts.id
        WHERE entity_fts MATCH ? AND {fts_where}
        ORDER BY rank
        LIMIT ?
        """,
        (*params_fts, limit),
    ).fetchall()
    return [self._row_to_entity(row) for row in rows]
```

否则保持原有过滤逻辑，但增加 `facet` 过滤条件：
```python
if facet:
    conditions.append("facet = ?")
    params.append(facet.value)
```

- [ ] **Step 6: 修改 _row_to_entity 增加 facet 和 archived_at**

在 `_row_to_entity` 中增加：
```python
facet=EntityFacet(row["facet"]),
archived_at=(
    datetime.fromisoformat(row["archived_at"]) if row["archived_at"] else None
),
```

- [ ] **Step 7: 修改 update() 的 SQL 增加 facet 和 archived_at**

在 `update` 方法的 UPDATE SQL 中增加 `facet = ?` 和 `archived_at = ?`，params 增加 `entity.facet.value` 和 `entity.archived_at.isoformat() if entity.archived_at else None`。

- [ ] **Step 8: 运行测试**

Run: `cd /home/user/projects/linglong && source venv/bin/activate && pytest tests/knowledge/test_store.py -v`
Expected: 全部 PASS

- [ ] **Step 9: 提交**

```bash
git add src/linglong/knowledge/store.py tests/knowledge/test_store.py
git commit -m "feat(store): FTS5 全文搜索 + facet 分类过滤 + schema 扩展"
```

---

### Task 5: wiki 目录存储（按 facet 分目录）

**Files:**
- Modify: `src/linglong/knowledge/store.py`（`_save_to_filesystem` + `_get_entity_path`）
- Test: `tests/knowledge/test_store.py`

- [ ] **Step 1: 写 wiki 目录存储测试**

```python
def test_create_entity_saves_to_facet_directory(temp_store):
    """创建 Entity 时文件存入 wiki/{facet}/ 目录。"""
    entity = Entity(
        content="测试内容",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    )
    created = temp_store.create(entity)

    # 文件应在 wiki/concept/ 目录下
    wiki_path = temp_store.wiki_path
    facet_files = list((wiki_path / "concept").glob("*.md"))
    assert len(facet_files) == 1
    assert created.id in facet_files[0].name


def test_entity_file_has_frontmatter(temp_store):
    """Entity 文件包含正确的 YAML frontmatter。"""
    entity = Entity(
        content="测试内容",
        facet=EntityFacet.EXPERIENCE,
        created_by="agent:claude",
    )
    created = temp_store.create(entity)

    path = temp_store.wiki_path / "experience" / f"{created.id}.md"
    assert path.exists()
    content = path.read_text()
    assert "type: experience" in content
    assert "created_by: agent:claude" in content
```

- [ ] **Step 2: 修改 _get_entity_path 使用 facet 目录**

替换 `_get_entity_path` 方法：

```python
def _get_entity_path(self, entity_id: str, facet: str = "concept") -> Path:
    """Get filesystem path for an entity, organized by facet."""
    return self.wiki_path / facet / f"{entity_id}.md"
```

注意：调用此方法时需要传入 facet。在 `get()` 中需要先查 SQLite 获取 facet，或从文件系统搜索。

实际策略：`_get_entity_path` 需要接受 facet 参数。`create`、`update`、`delete` 中都已有 Entity 对象可直接取 `entity.facet.value`。`delete` 中需要先 get 获取 facet。

- [ ] **Step 3: 修改 _save_to_filesystem 写入正确 frontmatter**

替换 `_save_to_filesystem` 方法，使用标准 YAML frontmatter 格式：

```python
def _save_to_filesystem(self, entity: Entity) -> None:
    """Save entity as Markdown file in facet directory."""
    facet = entity.facet.value
    entity_path = self._get_entity_path(entity.id, facet)
    entity_path.parent.mkdir(parents=True, exist_ok=True)

    frontmatter = {
        "id": entity.id,
        "type": facet,
        "created_by": entity.created_by,
        "confirmed_by": entity.confirmed_by,
        "confidence": float(entity.confidence),
        "status": entity.status.value,
        "created_at": entity.created_at.isoformat(),
        "updated_at": entity.updated_at.isoformat(),
    }
    if entity.summary:
        frontmatter["summary"] = entity.summary
    if entity.archived_at:
        frontmatter["archived_at"] = entity.archived_at.isoformat()

    content = f"""---
{json.dumps(frontmatter, indent=2, ensure_ascii=False)}
---

{entity.content}
"""
    entity_path.write_text(content, encoding="utf-8")
```

- [ ] **Step 4: 修改 delete() 先获取 facet 再删文件**

在 `delete` 方法中，从已获取的 row 中读取 facet：

```python
# 获取 entity 信息（包括 facet 和 embedding_id）
with sqlite3.connect(self.db_path) as conn:
    row = conn.execute(
        "SELECT embedding_id, facet FROM entities WHERE id = ?", (entity_id,)
    ).fetchone()
    if row:
        embedding_id, facet = row[0], row[1]
    else:
        return False

# 从文件系统删除
entity_path = self._get_entity_path(entity_id, facet or "concept")
if entity_path.exists():
    entity_path.unlink()
```

- [ ] **Step 5: 运行测试**

Run: `cd /home/user/projects/linglong && source venv/bin/activate && pytest tests/knowledge/test_store.py -v`
Expected: 全部 PASS

- [ ] **Step 6: 提交**

```bash
git add src/linglong/knowledge/store.py tests/knowledge/test_store.py
git commit -m "feat(store): Entity 文件按 facet 分目录存储 + YAML frontmatter"
```

---

### Task 6: 版本管理（update 路径）

**Files:**
- Modify: `src/linglong/knowledge/store.py`
- Test: `tests/knowledge/test_store.py`

- [ ] **Step 1: 写版本管理测试**

```python
def test_update_content_creates_version(temp_store):
    """替换内容时产生新版本。"""
    entity = temp_store.create(Entity(
        content="v1 内容",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))
    assert entity.current_version == 1
    assert len(entity.versions) == 0

    # 更新内容
    entity.content = "v2 内容"
    updated = temp_store.update(entity)

    assert updated.current_version == 2
    assert len(updated.versions) == 1
    assert updated.versions[0]["version"] == 1
    assert updated.versions[0]["content"] == "v1 内容"


def test_update_appends_no_new_version(temp_store):
    """追加内容不产生新版本。"""
    entity = temp_store.create(Entity(
        content="原始内容",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    # 追加（通过 metadata 标记）
    entity.metadata["update_mode"] = "append"
    entity.content = "原始内容\n\n追加内容"
    updated = temp_store.update(entity)

    assert updated.current_version == 1
    assert len(updated.versions) == 0
    assert "追加内容" in updated.content


def test_version_compaction(temp_store):
    """版本超过上限时自动压缩。"""
    # 设置低版本上限
    temp_store.config.max_versions = 3

    entity = temp_store.create(Entity(
        content="v1",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    for i in range(2, 6):
        entity.content = f"v{i}"
        entity = temp_store.update(entity)

    # 应保留首版 + 最近 3 版 = 共 4 版（首版摘要 + 3 个完整版本）
    assert entity.current_version == 5
    # 中间版本只保留摘要
    assert len(entity.versions) <= 4
```

- [ ] **Step 2: 修改 update() 增加版本管理逻辑**

在 `store.py` 的 `update` 方法开头增加版本判断：

```python
def update(self, entity: Entity) -> Entity:
    """Update an existing entity."""
    # 获取当前版本用于乐观锁和版本管理
    current = self.get(entity.id)
    if current is None:
        raise ValueError(f"Entity {entity.id} not found")

    # 判断是否需要产生新版本
    update_mode = entity.metadata.pop("update_mode", None)
    content_changed = current.content != entity.content

    if content_changed and update_mode != "append":
        # 替换模式：产生新版本
        version_entry = {
            "version": current.current_version,
            "content": current.content,
            "modified_by": current.created_by,
            "modified_at": current.updated_at.isoformat(),
        }
        entity.versions = current.versions + [version_entry]
        entity.current_version = current.current_version + 1

        # 版本压缩
        max_versions = self.config.max_versions
        if len(entity.versions) > max_versions:
            # 保留首版摘要 + 最近 (max_versions - 1) 版
            first = entity.versions[0]
            recent = entity.versions[-(max_versions - 1):]
            # 中间版本只保留摘要
            first_compact = {
                "version": first["version"],
                "content": "(compressed)",
                "modified_by": first["modified_by"],
                "modified_at": first["modified_at"],
            }
            entity.versions = [first_compact] + recent

    entity.updated_at = datetime.utcnow()
    # ... 后续写入逻辑不变
```

- [ ] **Step 3: 运行测试**

Run: `cd /home/user/projects/linglong && source venv/bin/activate && pytest tests/knowledge/test_store.py -v`
Expected: 全部 PASS

- [ ] **Step 4: 提交**

```bash
git add src/linglong/knowledge/store.py tests/knowledge/test_store.py
git commit -m "feat(store): 更新时版本管理 + 版本压缩策略"
```

---

### Task 7: 归档机制

**Files:**
- Modify: `src/linglong/knowledge/store.py`
- Test: `tests/knowledge/test_store.py`

- [ ] **Step 1: 写归档测试**

```python
def test_archive_entity(temp_store):
    """归档 Entity 设置 archived_at 并移入 archive 目录。"""
    entity = temp_store.create(Entity(
        content="待归档内容",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    archived = temp_store.archive(entity.id)

    assert archived.archived_at is not None
    assert archived.status == EntityStatus.AUTO_CONFIRMED or archived.status == entity.status

    # 原 facet 目录文件应不存在
    original_path = temp_store._get_entity_path(entity.id, "concept")
    assert not original_path.exists()

    # archive 目录应有文件
    archive_files = list((temp_store.wiki_path / "archive").rglob("*.md"))
    assert len(archive_files) == 1


def test_archived_entity_not_in_search(temp_store):
    """归档的 Entity 不出现在默认搜索结果中。"""
    entity = temp_store.create(Entity(
        content="将被归档",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))
    temp_store.archive(entity.id)

    results = temp_store.search(query="将被归档")
    assert len(results) == 0

    # 带 include_archived 可搜到
    results = temp_store.search(query="将被归档", include_archived=True)
    assert len(results) == 1
```

- [ ] **Step 2: 增加 archive() 方法**

在 `store.py` 的 `delete` 方法之前，增加 `archive` 方法：

```python
def archive(self, entity_id: str) -> Entity:
    """Archive an entity: mark archived_at and move file to archive/."""
    entity = self.get(entity_id)
    if entity is None:
        raise ValueError(f"Entity {entity_id} not found")

    entity.archived_at = datetime.utcnow()

    # 从原 facet 目录删除
    old_path = self._get_entity_path(entity.id, entity.facet.value)
    if old_path.exists():
        old_path.unlink()

    # 写入 archive 目录
    archive_dir = self.wiki_path / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"{entity.id}.md"
    archive_path.write_text(
        f"---\nid: {entity.id}\ntype: {entity.facet.value}\narchived_at: {entity.archived_at.isoformat()}\n---\n\n{entity.content}",
        encoding="utf-8",
    )

    # 更新 SQLite
    entity.updated_at = datetime.utcnow()
    with sqlite3.connect(self.db_path) as conn:
        conn.execute(
            "UPDATE entities SET archived_at = ?, updated_at = ? WHERE id = ?",
            (entity.archived_at.isoformat(), entity.updated_at.isoformat(), entity.id),
        )
        conn.commit()

    return entity
```

- [ ] **Step 3: 修改 search() 增加 archived 过滤**

在 `search` 方法中，默认排除已归档条目：

```python
# 在非 FTS 搜索的 conditions 中增加
if not include_archived:
    conditions.append("archived_at IS NULL")
```

方法签名增加 `include_archived: bool = False`。FTS 搜索同理增加过滤。

- [ ] **Step 4: 运行测试**

Run: `cd /home/user/projects/linglong && source venv/bin/activate && pytest tests/knowledge/test_store.py -v`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add src/linglong/knowledge/store.py tests/knowledge/test_store.py
git commit -m "feat(store): 归档机制 + archived_at + archive 目录"
```

---

### Task 8: 全量测试验证 + 兼容性确认

**Files:**
- 可能修复其他测试文件中的兼容性问题

- [ ] **Step 1: 运行全量测试**

Run: `cd /home/user/projects/linglong && source venv/bin/activate && pytest -v 2>&1 | tail -40`
Expected: 全部 PASS

- [ ] **Step 2: 如有失败，逐个修复并提交**

常见问题：
- sync adapter 创建 Entity 时缺少 facet → 根据 wiki 目录类型映射 facet
- 其他模块测试 fixture 中的 Entity 缺少 facet → 添加 `facet=EntityFacet.SOURCE`

- [ ] **Step 3: 最终提交（如有修复）**

```bash
git add tests/ src/
git commit -m "fix: 全量测试通过，M1 完成"
```

---

## 自检

**Spec 覆盖度**：对照 `docs/superpowers/specs/2026-05-14-knowledge-module-implementation.md` M1 部分：
- ✅ 1.1 EntityFacet 枚举 → Task 1
- ✅ 1.2 Entity 增加 facet + archived_at → Task 1
- ✅ 1.3 KnowledgeConfig 扩展 → Task 2
- ✅ 1.4 FTS5 全文搜索 → Task 4
- ✅ 1.5 search() 重写 → Task 4
- ✅ 1.6 wiki 目录存储 → Task 5
- ✅ 1.7 update() 版本管理 → Task 6
- ✅ 1.8 archive() 方法 → Task 7
- ✅ 1.9 测试对齐 → Task 3 + 各 Task 内测试

**Placeholder 扫描**：无 TBD/TODO。

**类型一致性**：所有方法签名中 `facet` 参数类型为 `EntityFacet | None`，字段名统一为 `facet`。`archived_at` 类型为 `datetime | None`。
