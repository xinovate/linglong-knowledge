# M2: CLI 命令（核心 CRUD）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `linglong write/read/search/update/review/archive` 六个 CLI 命令，Agent 可通过命令行完成知识库全部 CRUD 操作。

**Architecture:** 在现有 CLI 框架（argparse 子命令）基础上扩展，增加知识库操作子命令。每个命令调用 M1 已实现的 KnowledgeStore 方法。保持 ingest/compose/publish/sync 四个现有命令不变。

**Tech Stack:** Python argparse, KnowledgeStore API, pytest

**前置依赖:** M1 完成（Entity 有 facet，store 有 FTS5 + facet 过滤 + 版本管理 + 归档）

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `src/linglong/cli.py` | 重构 | 增加 write/read/search/update/review/archive 子命令 |
| `src/linglong/knowledge/store.py` | 小改 | search 增加 `--deep` 模式（加载完整内容） |
| `tests/test_cli.py` | 扩展 | 每个新命令的集成测试 |

---

### Task 1: CLI 框架扩展 — 知识库子命令

**Files:**
- Modify: `src/linglong/cli.py`

- [ ] **Step 1: 在 main() 中增加知识库子命令注册**

在 `cli.py` 的 `main()` 函数中，`sync_parser` 之后、`args = parser.parse_args(argv)` 之前，增加：

```python
    # --- 知识库命令 ---

    # write
    write_parser = sub.add_parser("write", help="写入知识条目")
    write_parser.add_argument("--facet", required=True,
        choices=["source", "entity", "concept", "synthesis", "experience", "methodology", "personal"],
        help="知识分类")
    write_parser.add_argument("--title", required=True, help="标题（用作文件名）")
    write_parser.add_argument("--content", default=None, help="内容文本")
    write_parser.add_argument("--from-file", default=None, help="从文件读取内容")
    write_parser.add_argument("--yes", action="store_true", help="跳过确认直接写入")
    write_parser.add_argument("--no-index", action="store_true", help="跳过索引更新")
    write_parser.set_defaults(func=cmd_write)

    # read
    read_parser = sub.add_parser("read", help="读取知识条目")
    read_parser.add_argument("entity_id", help="Entity ID")
    read_parser.add_argument("--path", default=None, help="按文件路径读取")
    read_parser.add_argument("--format", choices=["json", "markdown"], default="markdown", help="输出格式")
    read_parser.set_defaults(func=cmd_read)

    # search
    search_parser = sub.add_parser("search", help="搜索知识条目")
    search_parser.add_argument("query", nargs="?", default=None, help="搜索关键词")
    search_parser.add_argument("--facet", default=None, help="按分类过滤")
    search_parser.add_argument("--mode", choices=["keyword", "vector", "hybrid", "auto"], default="auto", help="搜索模式")
    search_parser.add_argument("--deep", action="store_true", help="加载完整内容")
    search_parser.add_argument("--limit", type=int, default=10, help="结果数量")
    search_parser.add_argument("--status", default=None, help="按状态过滤")
    search_parser.add_argument("--created-by", default=None, help="按创建者过滤")
    search_parser.add_argument("--since", default=None, help="起始日期 (YYYY-MM-DD)")
    search_parser.set_defaults(func=cmd_search)

    # update
    update_parser = sub.add_parser("update", help="更新知识条目")
    update_parser.add_argument("entity_id", help="Entity ID")
    update_parser.add_argument("--content", default=None, help="替换内容")
    update_parser.add_argument("--append", default=None, help="追加内容")
    update_parser.add_argument("--metadata", nargs="*", default=None, help="更新元数据 key=value")
    update_parser.add_argument("--history", action="store_true", help="查看版本历史")
    update_parser.add_argument("--show-version", type=int, default=None, help="查看指定版本")
    update_parser.add_argument("--yes", action="store_true", help="跳过确认")
    update_parser.add_argument("--no-index", action="store_true", help="跳过索引更新")
    update_parser.set_defaults(func=cmd_update)

    # review
    review_parser = sub.add_parser("review", help="审核管理")
    review_parser.add_argument("--list-pending", action="store_true", help="列出待审核条目")
    review_parser.add_argument("--approve", default=None, metavar="ID", help="批准条目")
    review_parser.add_argument("--reject", default=None, metavar="ID", help="拒绝条目")
    review_parser.set_defaults(func=cmd_review)

    # archive
    archive_parser = sub.add_parser("archive", help="归档知识条目")
    archive_parser.add_argument("entity_id", nargs="?", default=None, help="Entity ID")
    archive_parser.add_argument("--older-than", default=None, help="归档超过 N 天的条目 (如 90d)")
    archive_parser.set_defaults(func=cmd_archive)
```

- [ ] **Step 2: 添加 import 语句**

在 `cli.py` 顶部 import 中增加：

```python
from linglong.core.models import Entity, EntityFacet, EntityStatus
```

- [ ] **Step 3: 提交框架变更**

```bash
git add src/linglong/cli.py
git commit -m "feat(cli): 知识库子命令框架（write/read/search/update/review/archive）"
```

---

### Task 2: cmd_write 实现

**Files:**
- Modify: `src/linglong/cli.py`

- [ ] **Step 1: 写 cmd_write 测试**

在 `tests/test_cli.py` 末尾追加：

```python
def test_write_creates_entity():
    """linglong write 创建知识条目并输出 ID。"""
    import tempfile
    from pathlib import Path
    from linglong.core.config import LinglongConfig, set_config

    with tempfile.TemporaryDirectory() as tmpdir:
        config = LinglongConfig(
            data_dir=Path(tmpdir) / "data",
            knowledge=LinglongConfig().knowledge.model_copy(update={
                "wiki_path": Path(tmpdir) / "wiki",
                "db_path": Path(tmpdir) / "knowledge.db",
                "generate_embeddings": False,
            }),
        )
        set_config(config)

        result = main([
            "write",
            "--facet", "concept",
            "--title", "测试知识",
            "--content", "这是测试内容",
            "--yes",
        ])
        assert result == 0
```

- [ ] **Step 2: 实现 cmd_write 函数**

在 `cli.py` 中（`cmd_sync` 之后）添加：

```python
def cmd_write(args: argparse.Namespace) -> int:
    """Write a new knowledge entity."""
    content = args.content
    if args.from_file:
        content = Path(args.from_file).read_text(encoding="utf-8")
    if not content:
        print("错误：必须提供 --content 或 --from-file")
        return 1

    facet = EntityFacet(args.facet)

    # 去重检查
    store = KnowledgeStore()
    existing = store.search(query=args.title, facet=facet, limit=5)
    if existing:
        for e in existing:
            if args.title.lower() in e.content.lower():
                print(f"⚠️ 已存在相似条目：{e.id} ({e.facet.value})")
                print(f"  建议：linglong update {e.id} --append \"补充内容\"")
                if not args.yes:
                    return 1

    # 确认
    if not args.yes:
        print(f"分类：{facet.value}")
        print(f"标题：{args.title}")
        print(f"内容：{content[:100]}{'...' if len(content) > 100 else ''}")
        answer = input("\n确认写入？[y/N] ")
        if answer.lower() != "y":
            print("已取消")
            return 0

    entity = Entity(
        content=f"# {args.title}\n\n{content}",
        facet=facet,
        created_by="agent:cli",
        confidence=0.5,
    )

    created = store.create(entity)
    print(f"✅ 已创建：{created.id} ({facet.value}/{args.title})")
    return 0
```

- [ ] **Step 3: 运行测试**

Run: `cd /home/user/projects/linglong && source venv/bin/activate && pytest tests/test_cli.py::test_write_creates_entity -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add src/linglong/cli.py tests/test_cli.py
git commit -m "feat(cli): linglong write 命令实现"
```

---

### Task 3: cmd_read + cmd_search 实现

**Files:**
- Modify: `src/linglong/cli.py`

- [ ] **Step 1: 实现 cmd_read**

```python
def cmd_read(args: argparse.Namespace) -> int:
    """Read a knowledge entity."""
    store = KnowledgeStore()
    entity = store.get(args.entity_id)
    if not entity:
        print(f"错误：未找到 {args.entity_id}")
        return 1

    if args.format == "json":
        import json
        print(json.dumps(entity.model_dump(mode="json"), indent=2, ensure_ascii=False, default=str))
    else:
        print(entity.content)
        print(f"\n---")
        print(f"ID: {entity.id}")
        print(f"Facet: {entity.facet.value}")
        print(f"Status: {entity.status.value}")
        print(f"Confidence: {entity.confidence}")
        print(f"Created: {entity.created_at}")
        print(f"Updated: {entity.updated_at}")
    return 0
```

- [ ] **Step 2: 实现 cmd_search**

```python
def cmd_search(args: argparse.Namespace) -> int:
    """Search knowledge entities."""
    store = KnowledgeStore()

    facet = EntityFacet(args.facet) if args.facet else None
    status = EntityStatus(args.status) if args.status else None

    if args.mode in ("vector", "hybrid") and args.query:
        results = store.search_similar(query=args.query, limit=args.limit, status=status)
    else:
        results = store.search(
            query=args.query,
            facet=facet,
            status=status,
            created_by=args.created_by,
            limit=args.limit,
        )

    if not results:
        print("无搜索结果")
        return 0

    for e in results:
        # 摘要行：ID | facet | status | updated | content preview
        preview = e.content[:60].replace("\n", " ")
        print(f"  {e.id[:8]}...  [{e.facet.value}]  {e.status.value}  {e.updated_at.strftime('%Y-%m-%d')}  {preview}")

    if args.deep and results:
        print(f"\n--- Top {min(3, len(results))} 完整内容 ---\n")
        for e in results[:3]:
            print(f"## {e.id}")
            print(e.content[:500])
            print()
    return 0
```

- [ ] **Step 3: 写测试并运行**

```python
def test_read_after_write():
    """write 后 read 能获取内容。"""
    # (复用 test_write 的 fixture 设置)
    main(["write", "--facet", "concept", "--title", "读测试", "--content", "内容", "--yes"])
    # 用 search 获取 id
    store = KnowledgeStore()
    results = store.search(query="读测试")
    assert len(results) == 1
    result = main(["read", results[0].id])
    assert result == 0
```

- [ ] **Step 4: 提交**

```bash
git add src/linglong/cli.py tests/test_cli.py
git commit -m "feat(cli): linglong read + search 命令实现"
```

---

### Task 4: cmd_update + cmd_review + cmd_archive 实现

**Files:**
- Modify: `src/linglong/cli.py`

- [ ] **Step 1: 实现 cmd_update**

```python
def cmd_update(args: argparse.Namespace) -> int:
    """Update a knowledge entity."""
    store = KnowledgeStore()
    entity = store.get(args.entity_id)
    if not entity:
        print(f"错误：未找到 {args.entity_id}")
        return 1

    # 查看版本历史
    if args.history:
        print(f"版本历史 (current: v{entity.current_version}):")
        for v in entity.versions:
            print(f"  v{v['version']} | {v.get('modified_at', '?')} | {v.get('modified_by', '?')} | {v.get('content', '')[:50]}")
        print(f"  v{entity.current_version} | {entity.updated_at} | current")
        return 0

    # 查看指定版本
    if args.show_version:
        ver_num = args.show_version
        if ver_num == entity.current_version:
            print(entity.content)
        else:
            for v in entity.versions:
                if v["version"] == ver_num:
                    print(v["content"])
                    break
            else:
                print(f"版本 v{ver_num} 不存在")
                return 1
        return 0

    # 更新操作
    if args.content:
        entity.content = args.content
    elif args.append:
        entity.metadata["update_mode"] = "append"
        entity.content = entity.content + "\n\n" + args.append
    elif args.metadata:
        for kv in args.metadata:
            key, _, value = kv.partition("=")
            if value:
                entity.metadata[key] = value
        # metadata 更新不走版本管理
    else:
        print("错误：必须指定 --content / --append / --metadata 之一")
        return 1

    updated = store.update(entity)
    mode = "替换" if args.content else "追加" if args.append else "元数据更新"
    print(f"✅ 已更新 ({mode})：{updated.id} v{updated.current_version}")
    return 0
```

- [ ] **Step 2: 实现 cmd_review**

```python
def cmd_review(args: argparse.Namespace) -> int:
    """Review pending entities."""
    store = KnowledgeStore()

    if args.list_pending:
        results = store.search(status=EntityStatus.PENDING_REVIEW, limit=50)
        if not results:
            print("无待审核条目")
            return 0
        for e in results:
            preview = e.content[:60].replace("\n", " ")
            print(f"  {e.id[:8]}...  [{e.facet.value}]  {preview}")
        return 0

    if args.approve:
        entity = store.get(args.approve)
        if not entity:
            print(f"错误：未找到 {args.approve}")
            return 1
        entity.status = EntityStatus.CONFIRMED
        store.update(entity)
        print(f"✅ 已批准：{entity.id}")
        return 0

    if args.reject:
        entity = store.get(args.reject)
        if not entity:
            print(f"错误：未找到 {args.reject}")
            return 1
        entity.status = EntityStatus.REJECTED
        store.update(entity)
        print(f"❌ 已拒绝：{entity.id}")
        return 0

    print("错误：请指定 --list-pending / --approve / --reject")
    return 1
```

- [ ] **Step 3: 实现 cmd_archive**

```python
def cmd_archive(args: argparse.Namespace) -> int:
    """Archive knowledge entities."""
    store = KnowledgeStore()

    if args.entity_id:
        archived = store.archive(args.entity_id)
        print(f"📦 已归档：{archived.id} ({archived.facet.value})")
        return 0

    if args.older_than:
        # 解析如 "90d" → 90 天
        days = int(args.older_than.rstrip("d"))
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        results = store.search(limit=1000)
        count = 0
        for e in results:
            if e.updated_at < cutoff and e.archived_at is None:
                store.archive(e.id)
                count += 1
        print(f"📦 已归档 {count} 条超过 {days} 天的条目")
        return 0

    print("错误：请指定 entity_id 或 --older-than")
    return 1
```

- [ ] **Step 4: 运行全量测试**

Run: `cd /home/user/projects/linglong && source venv/bin/activate && pytest -v 2>&1 | tail -30`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add src/linglong/cli.py tests/test_cli.py
git commit -m "feat(cli): update/review/archive 命令实现，M2 完成"
```
