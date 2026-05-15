# P1+P2 功能补全实施计划（开源准备）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补全设计文档 00-08 中所有 P1+P2 功能缺口，使知识库模块可独立开源。

**Architecture:** 在现有 M1-M4 实现基础上增量修改。Store 层增强搜索和并发安全，Lint/Review 增加 fix 和 facet 规则，CLI 增强输出和交互体验。

**Tech Stack:** Python 3.12, SQLite (FTS5 + sqlite-vec), Pydantic v2, pytest

---

## 文件结构

| 文件 | 操作 | Task |
|------|------|------|
| `src/linglong/knowledge/store.py` | 修改 | 1, 2, 3, 7 |
| `src/linglong/cli.py` | 修改 | 1, 4, 5, 6, 10, 11, 12 |
| `src/linglong/knowledge/lint.py` | 修改 | 6 |
| `src/linglong/knowledge/review.py` | 修改 | 8 |
| `src/linglong/knowledge/sync/openclaw.py` | 修改 | 9 |
| `src/linglong/knowledge/init.py` | 修改 | 10, 12 |
| `src/linglong/core/config.py` | 修改 | 7 |
| `tests/knowledge/test_store.py` | 扩展 | 1, 2, 3, 4 |
| `tests/knowledge/test_lint.py` | 扩展 | 6 |
| `tests/knowledge/test_review.py` | 扩展 | 8 |
| `tests/test_cli.py` | 扩展 | 5, 10, 11 |

---

### Task 1: --since 日期过滤

**Files:**
- Modify: `src/linglong/knowledge/store.py`（search 方法）
- Modify: `src/linglong/cli.py`（cmd_search）
- Test: `tests/knowledge/test_store.py`

- [ ] **Step 1: store.py search() 增加 since 参数**

search() 签名增加 `since: str | None = None`，在非 FTS 路径的 conditions 中增加：

```python
if since:
    conditions.append("updated_at >= ?")
    params.append(since)
```

FTS 路径同理，在 JOIN 后加 `AND e.updated_at >= ?`。

- [ ] **Step 2: cli.py cmd_search 传递 since**

在 cmd_search 的 `store.search()` 调用中增加 `since=args.since`。

- [ ] **Step 3: 写测试并运行**

```python
def test_search_since_filter(temp_store):
    """按日期过滤搜索结果。"""
    from datetime import timedelta
    e = temp_store.create(Entity(
        content="旧条目",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))
    # 修改 updated_at 为 10 天前
    e.updated_at = datetime.utcnow() - timedelta(days=10)
    temp_store.update(e)

    recent = temp_store.create(Entity(
        content="新条目",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    cutoff = (datetime.utcnow() - timedelta(days=5)).strftime("%Y-%m-%d")
    results = temp_store.search(since=cutoff)
    assert len(results) == 1
    assert results[0].content == "新条目"
```

- [ ] **Step 4: 提交**

```bash
git add src/linglong/knowledge/store.py src/linglong/cli.py tests/knowledge/test_store.py
git commit -m "feat(store): search 增加 since 日期过滤"
```

---

### Task 2: 乐观锁

**Files:**
- Modify: `src/linglong/knowledge/store.py`（update 方法 + 新异常类）
- Modify: `src/linglong/cli.py`（cmd_update 捕获异常）

- [ ] **Step 1: store.py 增加 ConcurrentModificationError**

在 store.py 顶部异常类区域增加：

```python
class ConcurrentModificationError(Exception):
    """Raised when an entity was modified by another process after being read."""
    pass
```

- [ ] **Step 2: update() 增加版本检查**

在 `current = self.get(entity.id)` 之后、版本管理逻辑之前：

```python
# 乐观锁：检查 entity 是否在读取后被修改
if entity.updated_at and current.updated_at != entity.updated_at:
    raise ConcurrentModificationError(
        f"Entity {entity.id} was modified at {current.updated_at}, "
        f"but you have version from {entity.updated_at}. "
        f"Please re-read and retry."
    )
```

- [ ] **Step 3: cmd_update 捕获异常**

```python
try:
    updated = store.update(entity)
except ConcurrentModificationError as e:
    print(f"冲突：{e}")
    return 1
```

- [ ] **Step 4: 写测试并提交**

```python
def test_optimistic_lock(temp_store):
    """乐观锁检测并发修改冲突。"""
    from linglong.knowledge.store import ConcurrentModificationError

    entity = temp_store.create(Entity(
        content="v1",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    # 模拟另一个进程先修改
    current = temp_store.get(entity.id)
    current.content = "v2 by other"
    temp_store.update(current)

    # 原进程用过时对象更新 → 应抛异常
    entity.content = "v2 by me"
    with pytest.raises(ConcurrentModificationError):
        temp_store.update(entity)
```

---

### Task 3: WikiLinks → Relations 自动填充

**Files:**
- Modify: `src/linglong/knowledge/store.py`

- [ ] **Step 1: store.py 增加 _resolve_wikilinks 方法**

```python
def _resolve_wikilinks(self, entity: Entity) -> None:
    """Parse [[links]] and auto-fill entity.relations."""
    from linglong.knowledge.wikilinks import WikiLinksParser
    parser = WikiLinksParser()
    links = parser.parse(entity.content)
    if not links:
        return

    # 构建标题→ID 映射
    all_entities = self.search(limit=10000, include_archived=False)
    title_to_id: dict[str, str] = {}
    for e in all_entities:
        for line in e.content.split("\n"):
            if line.startswith("# "):
                title_to_id[line[2:].strip()] = e.id
                break
        title_to_id[e.id] = e.id  # ID 也可作为目标

    # 去重已有 relations
    existing_targets = {r.target_id for r in entity.relations}

    for link in links:
        target_id = title_to_id.get(link.target)
        if target_id and target_id not in existing_targets:
            entity.relations.append(Relation(
                target_id=target_id,
                relation_type="wikilink",
                strength=1.0,
            ))
            existing_targets.add(target_id)
```

- [ ] **Step 2: 在 create() 和 update() 中调用**

在 create() 的 `self._save_to_filesystem(entity)` 之前调用 `self._resolve_wikilinks(entity)`。
在 update() 的版本管理逻辑之后、写入之前调用。

- [ ] **Step 3: 写测试并提交**

```python
def test_wikilinks_auto_relations(temp_store):
    """创建带 [[link]] 的 Entity 时自动填充 relations。"""
    # 先创建目标
    target = temp_store.create(Entity(
        content="# 概念A\n\n描述",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    # 创建引用方
    entity = temp_store.create(Entity(
        content=f"# 引用方\n\n参考 [[概念A]]",
        facet=EntityFacet.CONCEPT,
        created_by="agent:claude",
    ))

    assert len(entity.relations) == 1
    assert entity.relations[0].target_id == target.id
    assert entity.relations[0].relation_type == "wikilink"
```

---

### Task 4: search_similar 增加 facet 过滤

**Files:**
- Modify: `src/linglong/knowledge/store.py`（search_similar）
- Modify: `src/linglong/cli.py`（cmd_search）

- [ ] **Step 1: search_similar 增加 facet 参数**

签名增加 `facet: EntityFacet | None = None`，conditions 中增加：

```python
if facet:
    conditions.append("e.facet = ?")
    params.insert(1 if not params else len(params) - 1, facet.value)
```

注意 params 的位置：embedding 在最前，limit 在最后，facet 插在中间。

- [ ] **Step 2: cmd_search vector/hybrid 传递 facet**

```python
if args.mode in ("vector", "hybrid") and args.query:
    results = store.search_similar(
        query=args.query, limit=args.limit, status=status, facet=facet
    )
```

- [ ] **Step 3: 测试并提交**

---

### Task 5: CLI search 输出增强（简化版两步索引）

**Files:**
- Modify: `src/linglong/cli.py`（cmd_search）

- [ ] **Step 1: cmd_search 增加 --format json 和结构化摘要输出**

默认输出增加 summary、confidence、version 字段：

```python
for e in results:
    preview = e.content[:60].replace("\n", " ")
    updated = e.updated_at.strftime("%Y-%m-%d") if e.updated_at else "?"
    print(f"  {e.id[:8]}...  [{e.facet.value}]  {e.status.value}  "
          f"conf={e.confidence:.1f}  v{e.current_version}  {updated}  {preview}")
```

增加 `--format json` 时输出摘要 JSON（非完整 Entity）：

```python
if args.format == "json":
    import json
    summaries = [{
        "id": e.id,
        "facet": e.facet.value,
        "status": e.status.value,
        "confidence": e.confidence,
        "version": e.current_version,
        "updated_at": e.updated_at.isoformat() if e.updated_at else None,
        "preview": e.content[:100].replace("\n", " "),
    } for e in results]
    print(json.dumps(summaries, indent=2, ensure_ascii=False))
    return 0
```

search_parser 增加 `--format` 参数（默认 table）。

- [ ] **Step 2: 测试并提交**

---

### Task 6: lint --fix 自动修复

**Files:**
- Modify: `src/linglong/knowledge/lint.py`
- Modify: `src/linglong/cli.py`

- [ ] **Step 1: LintResult 增加 fixed 字段**

```python
@dataclass
class LintResult:
    ...
    fixed: bool = False
```

- [ ] **Step 2: LintEngine 增加 fix_all 方法**

```python
def fix_all(self, results: list[LintResult] | None = None) -> list[LintResult]:
    """Auto-fix issues where possible. Returns updated results."""
    if results is None:
        results = self.run_all()

    for r in results:
        if r.rule == "index_consistency" and r.entity_id:
            # 删除孤立文件
            facet_dir = self.store.wiki_path / r.facet if r.facet else None
            if facet_dir:
                orphan = facet_dir / f"{r.entity_id}.md"
                if orphan.exists():
                    orphan.unlink()
                    r.fixed = True
        # wikilinks 和 content_conflict 不可自动修复
    return results
```

- [ ] **Step 3: CLI lint 增加 --fix**

```python
if args.fix:
    results = engine.fix_all(results)
    fixed_count = sum(1 for r in results if r.fixed)
    if fixed_count:
        print(f"已自动修复 {fixed_count} 个问题")
```

- [ ] **Step 4: 测试并提交**

---

### Task 7: lint 写入时自动触发

**Files:**
- Modify: `src/linglong/core/config.py`（KnowledgeConfig 增加 auto_lint）
- Modify: `src/linglong/knowledge/store.py`（create/update 末尾触发）

- [ ] **Step 1: KnowledgeConfig 增加 auto_lint**

```python
auto_lint: bool = Field(
    default=False, description="Auto-run lint after write operations"
)
```

- [ ] **Step 2: store.py create/update 末尾触发**

```python
if self.config.auto_lint:
    try:
        from linglong.knowledge.lint import LintEngine
        engine = LintEngine(self)
        results = engine.run_all()
        if results:
            logger.info("Auto-lint found %d issues", len(results))
    except Exception as e:
        logger.warning("Auto-lint failed: %s", e)
```

- [ ] **Step 3: 测试并提交**

---

### Task 8: ReviewEngine facet 规则

**Files:**
- Modify: `src/linglong/knowledge/review.py`

- [ ] **Step 1: 增加 facet 差异化审核规则**

在 `_setup_default_rules` 末尾增加：

```python
# 规则 5：personal 分面需人工确认
self.rules.append(
    Rule(
        name="personal_requires_review",
        condition=lambda e: hasattr(e, 'facet') and e.facet == EntityFacet.PERSONAL,
        action=Action.REQUIRE_HUMAN_CONFIRM,
        priority=80,
    )
)

# 规则 6：source 分面高置信度自动确认
self.rules.append(
    Rule(
        name="source_auto_confirm",
        condition=lambda e: (
            hasattr(e, 'facet')
            and e.facet == EntityFacet.SOURCE
            and float(e.confidence) >= 0.7
        ),
        action=Action.AUTO_CONFIRM,
        priority=85,
    )
)
```

注意：review.py 需要导入 EntityFacet。

- [ ] **Step 2: 测试并提交**

---

### Task 9: OpenClaw type→facet 映射

**Files:**
- Modify: `src/linglong/knowledge/sync/openclaw.py`

- [ ] **Step 1: 增加 TYPE_TO_FACET 映射**

```python
TYPE_TO_FACET: dict[str, EntityFacet] = {
    # 标准分面
    "concept": EntityFacet.CONCEPT,
    "entity": EntityFacet.ENTITY,
    "experience": EntityFacet.EXPERIENCE,
    "methodology": EntityFacet.METHODOLOGY,
    "personal": EntityFacet.PERSONAL,
    "source": EntityFacet.SOURCE,
    "synthesis": EntityFacet.SYNTHESIS,
    # OpenClaw 特有类型
    "article": EntityFacet.SOURCE,
    "tutorial": EntityFacet.METHODOLOGY,
    "debug-log": EntityFacet.EXPERIENCE,
    "decision": EntityFacet.SYNTHESIS,
    "tip": EntityFacet.EXPERIENCE,
    "reference": EntityFacet.SOURCE,
    "howto": EntityFacet.METHODOLOGY,
    "note": EntityFacet.EXPERIENCE,
    "project": EntityFacet.SYNTHESIS,
    "area": EntityFacet.CONCEPT,
    "moc": EntityFacet.SYNTHESIS,
    "daily": EntityFacet.PERSONAL,
    "meeting": EntityFacet.PERSONAL,
    "idea": EntityFacet.CONCEPT,
    "bookmark": EntityFacet.SOURCE,
}
```

- [ ] **Step 2: _file_to_entity 使用映射**

```python
# 从 frontmatter 获取 type
file_type = post.get("type", "source")
facet = TYPE_TO_FACET.get(file_type, EntityFacet.SOURCE)
```

替换硬编码 `facet=EntityFacet.SOURCE`。

- [ ] **Step 3: 测试并提交**

---

### Task 10: init --from-git

**Files:**
- Modify: `src/linglong/knowledge/init.py`
- Modify: `src/linglong/cli.py`

- [ ] **Step 1: init.py 增加 init_from_git**

```python
def init_from_git(repo_url: str, target_dir: Path | None = None) -> Path:
    """Initialize from a Git repository containing wiki files."""
    import subprocess

    base = target_dir or Path.cwd()
    wiki_path = base / "wiki"

    # clone 到临时目录
    tmp_dir = base / ".tmp_clone"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)

    subprocess.run(["git", "clone", "--depth", "1", repo_url, str(tmp_dir)],
                   check=True, capture_output=True)

    # 初始化目录结构
    init_bare(target_dir=base)

    # 复制 md 文件
    for md_file in tmp_dir.rglob("*.md"):
        dest = wiki_path / "source" / md_file.name
        shutil.copy2(md_file, dest)

    # 清理临时目录
    shutil.rmtree(tmp_dir)

    logger.info("已从 Git 初始化知识库：%s → %s", repo_url, wiki_path)
    return wiki_path
```

- [ ] **Step 2: CLI init 增加 --from-git**

```python
init_parser.add_argument("--from-git", default=None, metavar="URL", help="从 Git 仓库初始化")
```

cmd_init 中处理 `args.from_git`。

- [ ] **Step 3: 测试并提交**

---

### Task 11: write_mode 确认模式

**Files:**
- Modify: `src/linglong/cli.py`（cmd_write）

- [ ] **Step 1: cmd_write 读取 config.write_mode**

在 cmd_write 去重检查之前：

```python
config = get_config()
auto_mode = config.knowledge.write_mode == "auto"

# 去重检查
...
if existing and not args.yes and not auto_mode:
    return 1

# 确认
if not args.yes and not auto_mode:
    ...
```

- [ ] **Step 2: 测试并提交**

---

### Task 12: 交互式配置向导

**Files:**
- Modify: `src/linglong/knowledge/init.py`
- Modify: `src/linglong/cli.py`

- [ ] **Step 1: init.py 增加 init_interactive**

```python
def init_interactive(target_dir: Path | None = None) -> Path:
    """Interactive initialization with configuration wizard."""
    base = target_dir or Path.cwd()

    print("=== Linglong 知识库初始化向导 ===\n")

    wiki_path = base / "wiki"
    db_path = base / "db" / "knowledge.db"

    # Wiki 路径
    custom_wiki = input(f"Wiki 目录 [{wiki_path}]: ").strip()
    if custom_wiki:
        wiki_path = Path(custom_wiki)

    # 向量搜索
    vector_enabled = input("启用向量搜索？[y/N]: ").strip().lower() == "y"

    # 写入模式
    write_mode = input("写入模式 (confirm/auto) [confirm]: ").strip() or "confirm"

    # 生成配置
    init_bare(target_dir=base)

    config_content = f"""# Linglong 知识库配置
# 由 linglong init --interactive 生成

knowledge:
  wiki_path: {wiki_path}
  db_path: {db_path}
  generate_embeddings: {str(vector_enabled).lower()}
  write_mode: {write_mode}
  auto_lint: false
  max_versions: 10
  db_mode: wal
"""
    config_path = base / ".linglong.yaml"
    config_path.write_text(config_content, encoding="utf-8")

    print(f"\n✅ 知识库已初始化：{wiki_path}")
    print(f"   配置文件：{config_path}")
    return wiki_path
```

- [ ] **Step 2: CLI init 交互模式**

当 init 没有任何参数时调用 `init_interactive()`：

```python
def cmd_init(args: argparse.Namespace) -> int:
    if args.from_git:
        ...
    elif args.from_openclaw:
        ...
    elif args.interactive:
        init_interactive()
    else:
        init_bare()
```

增加 `--interactive` 参数。

- [ ] **Step 3: 测试并提交**

---

## 执行顺序

```
Batch 1 (并行): Task 1, 2, 3, 4
Batch 2 (顺序): Task 5, 6, 7, 8
Batch 3 (并行): Task 9, 10, 11, 12
```

## 验证

```bash
source venv/bin/activate && pytest -v  # 每个 Task 完成后全绿
```
