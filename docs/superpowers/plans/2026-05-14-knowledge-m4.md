# M4: 初始化 + 并发 + 集成 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `linglong init` 四种模式、文件锁机制、SQLite WAL 配置、`linglong migrate` 命令、端到端集成测试。

**Architecture:** 新建 `knowledge/init.py`（初始化逻辑）和 `knowledge/lock.py`（文件锁）。init 负责目录创建和配置生成；lock 使用 fcntl.flock 实现跨进程互斥。

**Tech Stack:** Python fcntl, SQLite WAL, subprocess (git), pytest

**前置依赖:** M1-M3 全部完成

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `src/linglong/knowledge/init.py` | 新建 | 四种初始化模式 + 交互式配置 |
| `src/linglong/knowledge/lock.py` | 新建 | fcntl.flock 全局写锁 |
| `src/linglong/knowledge/store.py` | 小改 | 集成文件锁 + WAL 配置 |
| `src/linglong/cli.py` | 修改 | 增加 init / migrate 子命令 |
| `tests/knowledge/test_init.py` | 新建 | 初始化测试 |
| `tests/knowledge/test_lock.py` | 新建 | 并发锁测试 |
| `tests/integration/test_knowledge_e2e.py` | 新建 | 端到端集成测试 |

---

### Task 1: 文件锁机制

**Files:**
- Create: `src/linglong/knowledge/lock.py`
- Test: `tests/knowledge/test_lock.py`

- [ ] **Step 1: 写锁测试**

```python
# tests/knowledge/test_lock.py
import tempfile
import threading
from pathlib import Path
from linglong.knowledge.lock import LinglongLock


def test_lock_acquires_and_releases():
    """锁能正常获取和释放。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        lock = LinglongLock(Path(tmpdir) / "test.lock")
        with lock:
            assert lock._fd is not None
        # 退出后锁已释放


def test_lock_prevents_concurrent_access():
    """锁阻止并发访问。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_path = Path(tmpdir) / "test.lock"
        results = []

        def worker():
            lock = LinglongLock(lock_path, timeout=1)
            try:
                with lock:
                    results.append("acquired")
            except TimeoutError:
                results.append("timeout")

        # 先持锁
        lock1 = LinglongLock(lock_path, timeout=1)
        lock1.__enter__()

        # 另一个线程尝试获取（应超时）
        t = threading.Thread(target=worker)
        t.start()
        t.join()

        lock1.__exit__(None, None, None)
        assert "timeout" in results
```

- [ ] **Step 2: 实现 lock.py**

```python
# src/linglong/knowledge/lock.py
"""File-based lock for cross-process mutual exclusion."""

import fcntl
import os
from pathlib import Path


class LinglongLock:
    """Global write lock using fcntl.flock.

    Usage:
        with LinglongLock():
            store.create(entity)
    """

    def __init__(self, lock_path: Path | None = None, timeout: int = 5):
        self.timeout = timeout
        if lock_path is None:
            from linglong.core.config import get_config
            lock_path = get_config().knowledge.wiki_path.parent / ".linglong.lock"
        self.lock_path = lock_path
        self._fd = None

    def __enter__(self):
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = open(self.lock_path, "w")
        try:
            fcntl.flock(self._fd, fcntl.LOCK_EX)  # 阻塞等待
        except (OSError, IOError):
            self._fd.close()
            self._fd = None
            raise TimeoutError(f"无法在 {self.timeout}s 内获取锁")
        return self

    def __exit__(self, *args):
        if self._fd:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            self._fd.close()
            self._fd = None
```

- [ ] **Step 3: 运行测试**

Run: `cd /home/user/projects/linglong && source venv/bin/activate && pytest tests/knowledge/test_lock.py -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add src/linglong/knowledge/lock.py tests/knowledge/test_lock.py
git commit -m "feat: 文件锁机制 fcntl.flock 跨进程互斥"
```

---

### Task 2: store.py 集成锁 + WAL

**Files:**
- Modify: `src/linglong/knowledge/store.py`

- [ ] **Step 1: 在 _init_database 中增加 WAL 配置**

在 `_init_database` 方法的 `with sqlite3.connect(self.db_path) as conn:` 之后增加：

```python
            # WAL 模式配置
            conn.execute(f"PRAGMA journal_mode={self.config.db_mode}")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute(f"PRAGMA busy_timeout={self.config.lock_timeout * 1000}")
```

- [ ] **Step 2: 在 write 类操作中集成文件锁**

在 `create()`、`update()`、`archive()`、`delete()` 方法的核心操作外包锁：

```python
from linglong.knowledge.lock import LinglongLock

# 在 create() 中：
def create(self, entity: Entity) -> Entity:
    with LinglongLock():
        # ... 原有逻辑 ...
```

对 `update()`、`archive()`、`delete()` 同样处理。

- [ ] **Step 3: 运行全量测试**

Run: `cd /home/user/projects/linglong && source venv/bin/activate && pytest tests/knowledge/ -v`
Expected: 全部 PASS

- [ ] **Step 4: 提交**

```bash
git add src/linglong/knowledge/store.py
git commit -m "feat(store): 文件锁 + SQLite WAL 并发安全"
```

---

### Task 3: linglong init 实现

**Files:**
- Create: `src/linglong/knowledge/init.py`
- Modify: `src/linglong/cli.py`
- Test: `tests/knowledge/test_init.py`

- [ ] **Step 1: 写 init 测试**

```python
# tests/knowledge/test_init.py
import tempfile
from pathlib import Path
from linglong.knowledge.init import init_knowledge_base


def test_bare_init_creates_structure():
    """裸初始化创建目录 + 配置 + 数据库。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "linglong"
        init_knowledge_base(base_path=base)

        # 目录存在
        assert (base / "wiki").exists()
        assert (base / "wiki" / "concept").exists()
        assert (base / "wiki" / "experience").exists()
        assert (base / "wiki" / "archive").exists()
        assert (base / "db").exists()

        # 配置文件存在
        assert (base / ".linglong.yaml").exists()

        # 数据库可连接
        import sqlite3
        conn = sqlite3.connect(base / "db" / "knowledge.db")
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [t[0] for t in tables]
        assert "entities" in table_names
        conn.close()


def test_init_index_skeleton():
    """初始化创建索引骨架文件。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "linglong"
        init_knowledge_base(base_path=base)

        wiki = base / "wiki"
        assert (wiki / "index.md").exists()
        assert (wiki / "log.md").exists()
        for facet in ["source", "entity", "concept", "synthesis", "experience", "methodology", "personal"]:
            assert (wiki / f"index-{facet}.md").exists()
```

- [ ] **Step 2: 实现 init.py**

```python
# src/linglong/knowledge/init.py
"""Knowledge base initialization."""

import sqlite3
from pathlib import Path

import yaml

from linglong.core.models import EntityFacet


def init_knowledge_base(
    base_path: Path | None = None,
    embedding_url: str = "http://localhost:7997",
    embedding_model: str = "nomic-embed-text-v1.5",
) -> Path:
    """Initialize a new knowledge base directory structure.

    Args:
        base_path: Root directory (default: ~/linglong)
        embedding_url: Embedding service URL
        embedding_model: Embedding model name

    Returns:
        Path to the initialized base directory.
    """
    if base_path is None:
        base_path = Path.home() / "linglong"

    wiki_path = base_path / "wiki"
    db_path = base_path / "db" / "knowledge.db"

    # 1. 创建目录
    for facet in EntityFacet:
        (wiki_path / facet.value).mkdir(parents=True, exist_ok=True)
    (wiki_path / "archive").mkdir(parents=True, exist_ok=True)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # 2. 生成配置文件
    config = {
        "knowledge": {
            "wiki_path": str(wiki_path),
            "db_path": str(db_path),
            "write_mode": "confirm",
            "search_mode": "on_demand",
            "auto_index": True,
            "max_versions": 10,
            "lock_timeout": 5,
            "db_mode": "wal",
            "vector_enabled": True,
            "embedding_url": embedding_url,
            "embedding_model": embedding_model,
        }
    }
    config_path = base_path / ".linglong.yaml"
    if not config_path.exists():
        config_path.write_text(yaml.dump(config, default_flow_style=False, allow_unicode=True), encoding="utf-8")

    # 3. 初始化 SQLite
    if not db_path.exists():
        from linglong.core.config import LinglongConfig, set_config
        cfg = LinglongConfig(
            knowledge=LinglongConfig().knowledge.model_copy(update={
                "wiki_path": wiki_path,
                "db_path": db_path,
                "generate_embeddings": False,
            }),
        )
        set_config(cfg)
        from linglong.knowledge.store import KnowledgeStore
        KnowledgeStore()  # __init__ 调用 _init_database

    # 4. 创建索引骨架
    _create_index_skeleton(wiki_path)

    return base_path


def _create_index_skeleton(wiki_path: Path) -> None:
    """Create empty index files."""
    # index.md
    index_md = wiki_path / "index.md"
    if not index_md.exists():
        lines = ["# 知识库索引\n", "> 最后更新：初始化\n", "## 按分类\n"]
        for facet in EntityFacet:
            name = facet.value.capitalize()
            lines.append(f"- [[index-{facet.value}|{name}]] — 0 篇")
        lines.append("\n## 统计\n- 总计：0 条\n")
        index_md.write_text("\n".join(lines), encoding="utf-8")

    # index-*.md
    for facet in EntityFacet:
        facet_index = wiki_path / f"index-{facet.value}.md"
        if not facet_index.exists():
            facet_index.write_text(f"# {facet.value.capitalize()} 索引\n\n（空）\n", encoding="utf-8")

    # log.md
    log_md = wiki_path / "log.md"
    if not log_md.exists():
        log_md.write_text("# 操作日志\n\n| 时间 | 操作 | ID | 说明 |\n|------|------|-----|------|\n", encoding="utf-8")
```

- [ ] **Step 3: 增加 CLI 命令**

在 `cli.py` 的 `main()` 中增加 init 子命令：

```python
    # init
    init_parser = sub.add_parser("init", help="初始化知识库")
    init_parser.add_argument("--from-git", default=None, metavar="REPO", help="从 Git 仓库拉取 wiki")
    init_parser.add_argument("--from-backup", default=None, metavar="DIR", help="从备份恢复")
    init_parser.add_argument("--from-openclaw", action="store_true", help="从 OpenClaw wiki 迁移")
    init_parser.add_argument("--verify", action="store_true", help="验证已有知识库状态")
    init_parser.set_defaults(func=cmd_init)
```

实现 cmd_init：

```python
def cmd_init(args: argparse.Namespace) -> int:
    """Initialize knowledge base."""
    from linglong.knowledge.init import init_knowledge_base

    base_path = get_config().knowledge.wiki_path.parent

    if args.verify:
        print("验证知识库状态...")
        wiki = get_config().knowledge.wiki_path
        db = get_config().knowledge.db_path
        checks = [
            ("wiki 目录", wiki.exists()),
            ("SQLite 数据库", db.exists()),
        ]
        for name, ok in checks:
            print(f"  {'✅' if ok else '❌'} {name}")
        return 0

    if args.from_git:
        import subprocess
        wiki_path = base_path / "wiki"
        subprocess.run(["git", "clone", args.from_git, str(wiki_path)], check=True)
        init_knowledge_base(base_path)
        print(f"✅ 从 Git 初始化完成：{base_path}")
        return 0

    if args.from_backup:
        import shutil
        wiki_path = base_path / "wiki"
        shutil.copytree(args.from_backup, wiki_path, dirs_exist_ok=True)
        init_knowledge_base(base_path)
        print(f"✅ 从备份恢复完成：{base_path}")
        return 0

    if args.from_openclaw:
        init_knowledge_base(base_path)
        from linglong.knowledge.sync.openclaw import OpenClawSyncAdapter
        from linglong.knowledge.store import KnowledgeStore
        openclaw_path = Path.home() / ".openclaw" / "workspace" / "memory" / "wiki"
        if not openclaw_path.exists():
            print(f"错误：OpenClaw wiki 不存在：{openclaw_path}")
            return 1
        store = KnowledgeStore()
        adapter = OpenClawSyncAdapter(str(openclaw_path), store)
        stats = adapter.sync_to_linglong()
        print(f"✅ 从 OpenClaw 迁移完成：{stats}")
        return 0

    # 裸初始化
    path = init_knowledge_base(base_path)
    print(f"✅ 知识库初始化完成：{path}")
    return 0
```

- [ ] **Step 4: 运行测试**

Run: `cd /home/user/projects/linglong && source venv/bin/activate && pytest tests/knowledge/test_init.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/linglong/knowledge/init.py src/linglong/cli.py tests/knowledge/test_init.py
git commit -m "feat: linglong init 四种初始化模式 + 交互式配置"
```

---

### Task 4: linglong migrate 命令

**Files:**
- Modify: `src/linglong/cli.py`

- [ ] **Step 1: 增加 migrate 子命令**

在 `cli.py` 的 `main()` 中增加：

```python
    # migrate
    migrate_parser = sub.add_parser("migrate", help="从外部 wiki 迁移")
    migrate_parser.add_argument("--from", required=True, metavar="DIR", dest="source_dir", help="源 wiki 目录")
    migrate_parser.add_argument("--dry-run", action="store_true", help="预览不执行")
    migrate_parser.add_argument("--no-index", action="store_true", help="跳过索引更新")
    migrate_parser.set_defaults(func=cmd_migrate)
```

实现 cmd_migrate：

```python
def cmd_migrate(args: argparse.Namespace) -> int:
    """Migrate from external wiki."""
    source = Path(args.source_dir)
    if not source.exists():
        print(f"错误：源目录不存在：{source}")
        return 1

    store = KnowledgeStore()
    from linglong.knowledge.sync.openclaw import OpenClawSyncAdapter
    adapter = OpenClawSyncAdapter(str(source), store)

    if args.dry_run:
        # 预览：列出待迁移文件
        md_files = list(source.rglob("*.md"))
        print(f"将迁移 {len(md_files)} 个文件：")
        for f in md_files[:20]:
            print(f"  {f.relative_to(source)}")
        if len(md_files) > 20:
            print(f"  ... 还有 {len(md_files) - 20} 个")
        return 0

    stats = adapter.sync_to_linglong()
    print(f"✅ 迁移完成：{stats}")

    if not args.no_index:
        from linglong.knowledge.indexer import IndexGenerator
        IndexGenerator().rebuild()
        print("✅ 索引已重建")

    return 0
```

- [ ] **Step 2: 提交**

```bash
git add src/linglong/cli.py
git commit -m "feat(cli): linglong migrate 从外部 wiki 迁移命令"
```

---

### Task 5: 端到端集成测试

**Files:**
- Create: `tests/integration/test_knowledge_e2e.py`

- [ ] **Step 1: 写端到端测试**

```python
# tests/integration/test_knowledge_e2e.py
"""End-to-end test: init → write → search → update → lint → archive."""

import tempfile
from datetime import datetime
from pathlib import Path

from linglong.core.config import LinglongConfig, set_config
from linglong.core.models import Entity, EntityFacet, EntityStatus
from linglong.knowledge.init import init_knowledge_base
from linglong.knowledge.store import KnowledgeStore
from linglong.knowledge.indexer import IndexGenerator
from linglong.knowledge.lint import LintEngine


def test_full_knowledge_lifecycle():
    """完整知识库生命周期测试。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "linglong"

        # 1. init
        init_knowledge_base(base_path=base)
        config = LinglongConfig(
            knowledge=LinglongConfig().knowledge.model_copy(update={
                "wiki_path": base / "wiki",
                "db_path": base / "db" / "knowledge.db",
                "generate_embeddings": False,
            }),
        )
        set_config(config)

        store = KnowledgeStore()

        # 2. write
        e1 = store.create(Entity(
            content="# 微服务架构\n\n参考 [[openclaw]] 的设计",
            facet=EntityFacet.CONCEPT,
            created_by="agent:claude",
            confidence=0.9,
        ))
        e2 = store.create(Entity(
            content="# OpenClaw\n\n跨 Agent 知识同步工具",
            facet=EntityFacet.ENTITY,
            created_by="agent:claude",
            confidence=0.95,
        ))
        e3 = store.create(Entity(
            content="# sqlite-vec 踩坑\n\n维度不匹配问题",
            facet=EntityFacet.EXPERIENCE,
            created_by="agent:openclaw",
        ))

        # 3. search
        results = store.search(query="微服务")
        assert len(results) == 1
        assert results[0].facet == EntityFacet.CONCEPT

        results_facet = store.search(facet=EntityFacet.EXPERIENCE)
        assert len(results_facet) == 1

        # 4. read
        retrieved = store.get(e1.id)
        assert retrieved is not None
        assert "微服务" in retrieved.content

        # 5. update（追加）
        e3.metadata["update_mode"] = "append"
        e3.content = e3.content + "\n\n## 解决方案\n\n校验维度。"
        updated = store.update(e3)
        assert updated.current_version == 1  # 追加不产生新版本

        # 6. update（替换）
        e1.content = "# 微服务架构 v2\n\n更新后的内容"
        e1_updated = store.update(e1)
        assert e1_updated.current_version == 2
        assert len(e1_updated.versions) == 1

        # 7. review
        from linglong.knowledge.review import ReviewEngine
        engine = ReviewEngine()
        reviewed = engine.review(e3)
        assert reviewed.status == EntityStatus.AUTO_CONFIRMED  # 高置信度 + 可信来源

        # 8. index
        indexer = IndexGenerator()
        indexer.rebuild()
        index_content = (base / "wiki" / "index.md").read_text()
        assert "Concept" in index_content

        # 9. lint
        lint_engine = LintEngine()
        report = lint_engine.run()
        assert report.summary["critical"] == 0  # openclaw entity 存在，死链已解决

        # 10. archive
        archived = store.archive(e3.id)
        assert archived.archived_at is not None
        results_after = store.search(query="sqlite-vec")
        assert len(results_after) == 0  # 归档后搜不到

        # 11. stats
        remaining = store.search(limit=1000)
        assert len(remaining) == 2  # e1 + e2
```

- [ ] **Step 2: 运行测试**

Run: `cd /home/user/projects/linglong && source venv/bin/activate && pytest tests/integration/test_knowledge_e2e.py -v`
Expected: PASS

- [ ] **Step 3: 提交**

```bash
git add tests/integration/test_knowledge_e2e.py
git commit -m "test: 知识库端到端集成测试（init→write→search→update→lint→archive）"
```

---

### Task 6: 全量测试 + 文档更新

**Files:**
- 可能修复各处兼容性问题
- 更新文档

- [ ] **Step 1: 运行全量测试**

Run: `cd /home/user/projects/linglong && source venv/bin/activate && pytest -v 2>&1 | tail -40`
Expected: 全部 PASS

- [ ] **Step 2: 修复任何失败测试并提交**

- [ ] **Step 3: 最终提交**

```bash
git add -A
git commit -m "feat: M4 完成 — init + 并发 + 集成，知识库模块实施完毕"
```
