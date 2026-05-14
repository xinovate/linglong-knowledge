# M3: 索引 + 巡检 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 IndexGenerator（自动生成 index.md + index-*.md）、LintEngine（4 项检查 + 报告）、WikiLinks 解析、操作日志。

**Architecture:** 新建 `knowledge/indexer.py`（索引生成器）、`knowledge/lint.py`（巡检引擎）、`knowledge/wikilinks.py`（链接解析器）。三个独立模块，通过 KnowledgeStore 协调。

**Tech Stack:** Python 3.11+, SQLite, pytest

**前置依赖:** M1 完成（facet + FTS5 + wiki 目录存储）、M2 完成（CLI 命令）

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `src/linglong/knowledge/indexer.py` | 新建 | 扫描 wiki/ 生成 index.md + 7 个 index-*.md |
| `src/linglong/knowledge/lint.py` | 新建 | 4 项检查 + 3 级严重度 + 报告 + --fix |
| `src/linglong/knowledge/wikilinks.py` | 新建 | 提取 [[target]] 解析 + 查找 + 替换 |
| `src/linglong/knowledge/store.py` | 小改 | 写入操作记录到 log.md |
| `src/linglong/cli.py` | 修改 | 增加 lint / index / stats 子命令 |
| `tests/knowledge/test_indexer.py` | 新建 | 索引生成测试 |
| `tests/knowledge/test_lint.py` | 新建 | 巡检测试 |
| `tests/knowledge/test_wikilinks.py` | 新建 | WikiLinks 测试 |

---

### Task 1: WikiLinks 解析器

**Files:**
- Create: `src/linglong/knowledge/wikilinks.py`
- Test: `tests/knowledge/test_wikilinks.py`

- [ ] **Step 1: 写 WikiLinks 测试**

```python
# tests/knowledge/test_wikilinks.py
from linglong.knowledge.wikilinks import extract_wikilinks, resolve_wikilink


def test_extract_basic_wikilinks():
    """提取基本 [[target]] 链接。"""
    content = "参考了 [[微服务架构]] 和 [[sqlite-vec]] 的设计。"
    links = extract_wikilinks(content)
    assert links == ["微服务架构", "sqlite-vec"]


def test_extract_wikilinks_with_display():
    """提取 [[target|display]] 格式链接。"""
    content = "参见 [[concepts/llm-wiki|LLM Wiki 模式]]。"
    links = extract_wikilinks(content)
    assert "concepts/llm-wiki" in links


def test_skip_code_block_wikilinks():
    """跳过代码块内的 [[...]]。"""
    content = "正文 [[有效链接]]\n```\n[[不应提取]]\n```\n"
    links = extract_wikilinks(content)
    assert links == ["有效链接"]


def test_resolve_wikilink():
    """将 wikilink 目标解析为文件路径。"""
    assert resolve_wikilink("openclaw") == "entity/openclaw.md"
    assert resolve_wikilink("concepts/llm-wiki") == "concept/llm-wiki.md"
```

- [ ] **Step 2: 实现 wikilinks.py**

```python
# src/linglong/knowledge/wikilinks.py
"""WikiLinks parser for [[target]] and [[target|display]] syntax."""

import re
from pathlib import Path

# 匹配 [[target]] 或 [[target|display]]
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")


def extract_wikilinks(content: str) -> list[str]:
    """Extract wikilink targets from markdown content.

    Skips links inside code blocks (```...```).
    """
    # 移除代码块
    stripped = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
    # 移除行内代码
    stripped = re.sub(r"`[^`]+`", "", stripped)
    return list(dict.fromkeys(WIKILINK_RE.findall(stripped)))  # 去重保序


def resolve_wikilink(target: str, wiki_path: Path | None = None) -> str:
    """Resolve a wikilink target to a relative file path.

    Rules:
      - If target contains '/', use as-is (e.g., "concepts/llm-wiki" → "concept/llm-wiki.md")
      - Otherwise, default to entity/ (e.g., "openclaw" → "entity/openclaw.md")
    """
    if "/" in target:
        parts = target.split("/")
        # 单数化 facet 目录名（concepts → concept）
        facet_map = {
            "sources": "source", "entities": "entity", "concepts": "concept",
            "syntheses": "synthesis", "experiences": "experience",
            "methodologies": "methodology", "personal": "personal",
        }
        parts[0] = facet_map.get(parts[0], parts[0])
        return "/".join(parts) + ".md"
    return f"entity/{target}.md"
```

- [ ] **Step 3: 运行测试**

Run: `cd /home/user/projects/linglong && source venv/bin/activate && pytest tests/knowledge/test_wikilinks.py -v`
Expected: 全部 PASS

- [ ] **Step 4: 提交**

```bash
git add src/linglong/knowledge/wikilinks.py tests/knowledge/test_wikilinks.py
git commit -m "feat: WikiLinks 解析器，支持 [[target]] 和 [[target|display]]"
```

---

### Task 2: IndexGenerator 索引生成器

**Files:**
- Create: `src/linglong/knowledge/indexer.py`
- Test: `tests/knowledge/test_indexer.py`

- [ ] **Step 1: 写索引生成测试**

```python
# tests/knowledge/test_indexer.py
import tempfile
from pathlib import Path
from linglong.core.config import LinglongConfig, set_config
from linglong.knowledge.store import KnowledgeStore
from linglong.knowledge.indexer import IndexGenerator


def _setup_store(tmpdir):
    config = LinglongConfig(
        data_dir=Path(tmpdir) / "data",
        knowledge=LinglongConfig().knowledge.model_copy(update={
            "wiki_path": Path(tmpdir) / "wiki",
            "db_path": Path(tmpdir) / "knowledge.db",
            "generate_embeddings": False,
        }),
    )
    set_config(config)
    store = KnowledgeStore()
    return store


def test_generate_index_creates_files():
    """生成索引后 index.md 和 7 个 index-*.md 文件存在。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = _setup_store(tmpdir)
        from linglong.core.models import Entity, EntityFacet
        store.create(Entity(content="概念1", facet=EntityFacet.CONCEPT, created_by="agent:claude"))
        store.create(Entity(content="经验1", facet=EntityFacet.EXPERIENCE, created_by="agent:claude"))

        indexer = IndexGenerator()
        indexer.rebuild()

        wiki = Path(tmpdir) / "wiki"
        assert (wiki / "index.md").exists()
        assert (wiki / "index-concept.md").exists()
        assert (wiki / "index-experience.md").exists()


def test_index_contains_entity_count():
    """index.md 包含各分类的条目数。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = _setup_store(tmpdir)
        from linglong.core.models import Entity, EntityFacet
        store.create(Entity(content="c1", facet=EntityFacet.CONCEPT, created_by="agent:claude"))
        store.create(Entity(content="c2", facet=EntityFacet.CONCEPT, created_by="agent:claude"))

        indexer = IndexGenerator()
        indexer.rebuild()

        content = (Path(tmpdir) / "wiki" / "index.md").read_text()
        assert "Concept" in content
        assert "2" in content  # 2 个 concept
```

- [ ] **Step 2: 实现 indexer.py**

```python
# src/linglong/knowledge/indexer.py
"""Index generator for wiki/ directory."""

from datetime import datetime
from pathlib import Path

from linglong.core.config import get_config
from linglong.core.models import EntityFacet
from linglong.knowledge.store import KnowledgeStore


FACETS = list(EntityFacet)


class IndexGenerator:
    """Generate index.md and index-{facet}.md files from knowledge store."""

    def __init__(self):
        self.config = get_config().knowledge
        self.wiki_path = self.config.wiki_path

    def rebuild(self) -> None:
        """Rebuild all index files from knowledge store."""
        store = KnowledgeStore()
        self.wiki_path.mkdir(parents=True, exist_ok=True)

        # 生成各分类索引
        facet_counts = {}
        for facet in FACETS:
            entities = store.search(facet=facet, limit=1000)
            facet_counts[facet.value] = len(entities)
            self._write_facet_index(facet, entities)

        # 生成总索引
        self._write_main_index(facet_counts)

    def _write_facet_index(self, facet: EntityFacet, entities: list) -> None:
        """Write index-{facet}.md with entity listings."""
        lines = [f"# {facet.value.capitalize()} 索引\n"]
        for e in entities:
            preview = e.content[:80].replace("\n", " ").replace("# ", "")
            lines.append(f"- [[{facet.value}/{e.id}|{preview}]]")
        path = self.wiki_path / f"index-{facet.value}.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _write_main_index(self, facet_counts: dict) -> None:
        """Write index.md with overview and counts."""
        now = datetime.utcnow().strftime("%Y-%m-%d")
        lines = [
            f"# 知识库索引\n",
            f"> 最后更新：{now}\n",
            "## 按分类\n",
        ]
        for facet in FACETS:
            count = facet_counts.get(facet.value, 0)
            name = facet.value.capitalize()
            lines.append(f"- [[index-{facet.value}|{name}]] — {count} 篇")

        lines.append(f"\n## 统计\n")
        total = sum(facet_counts.values())
        lines.append(f"- 总计：{total} 条")
        lines.append(f"- 分类：{len(FACETS)} 个")

        path = self.wiki_path / "index.md"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
```

- [ ] **Step 3: 运行测试**

Run: `cd /home/user/projects/linglong && source venv/bin/activate && pytest tests/knowledge/test_indexer.py -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add src/linglong/knowledge/indexer.py tests/knowledge/test_indexer.py
git commit -m "feat: IndexGenerator 自动生成 index.md + 分类索引"
```

---

### Task 3: LintEngine 巡检引擎

**Files:**
- Create: `src/linglong/knowledge/lint.py`
- Test: `tests/knowledge/test_lint.py`

- [ ] **Step 1: 写巡检测试**

```python
# tests/knowledge/test_lint.py
import tempfile
from pathlib import Path
from linglong.core.config import LinglongConfig, set_config
from linglong.core.models import Entity, EntityFacet
from linglong.knowledge.store import KnowledgeStore
from linglong.knowledge.lint import LintEngine


def _setup(tmpdir):
    config = LinglongConfig(
        data_dir=Path(tmpdir) / "data",
        knowledge=LinglongConfig().knowledge.model_copy(update={
            "wiki_path": Path(tmpdir) / "wiki",
            "db_path": Path(tmpdir) / "knowledge.db",
            "generate_embeddings": False,
        }),
    )
    set_config(config)
    return KnowledgeStore()


def test_lint_clean_report():
    """正常知识库巡检报告全绿灯。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = _setup(tmpdir)
        store.create(Entity(content="正常内容", facet=EntityFacet.CONCEPT, created_by="agent:claude"))

        engine = LintEngine()
        report = engine.run()
        assert report.summary["ok"] >= 1
        assert report.summary["warning"] == 0
        assert report.summary["critical"] == 0


def test_lint_detects_dead_link():
    """检测死链。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = _setup(tmpdir)
        # Entity 包含指向不存在目标的 wikilink
        store.create(Entity(
            content="参考 [[不存在的概念]]",
            facet=EntityFacet.CONCEPT,
            created_by="agent:claude",
        ))

        engine = LintEngine()
        report = engine.run()
        assert report.summary["critical"] >= 1
        assert any("死链" in item.message for item in report.items)
```

- [ ] **Step 2: 实现 lint.py**

```python
# src/linglong/knowledge/lint.py
"""Knowledge base lint engine — health checks and reports."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from linglong.core.config import get_config
from linglong.core.models import EntityFacet
from linglong.knowledge.store import KnowledgeStore
from linglong.knowledge.wikilinks import extract_wikilinks, resolve_wikilink


class Severity(str, Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class LintItem:
    severity: Severity
    check: str
    entity_id: str | None
    message: str
    suggestion: str = ""


@dataclass
class LintReport:
    items: list[LintItem] = field(default_factory=list)

    @property
    def summary(self) -> dict[str, int]:
        return {
            "ok": sum(1 for i in self.items if i.severity == Severity.OK),
            "warning": sum(1 for i in self.items if i.severity == Severity.WARNING),
            "critical": sum(1 for i in self.items if i.severity == Severity.CRITICAL),
        }

    def format_text(self) -> str:
        lines = ["# 知识库巡检报告\n"]
        lines.append(f"✅ 绿灯：{self.summary['ok']}")
        lines.append(f"⚠️ 黄灯：{self.summary['warning']}")
        lines.append(f"❌ 红灯：{self.summary['critical']}\n")

        for item in self.items:
            if item.severity == Severity.OK:
                continue
            icon = "❌" if item.severity == Severity.CRITICAL else "⚠️"
            lines.append(f"{icon} [{item.check}] {item.message}")
            if item.suggestion:
                lines.append(f"   建议：{item.suggestion}")
            lines.append("")

        return "\n".join(lines)


class LintEngine:
    """Run health checks on the knowledge base."""

    def __init__(self):
        self.config = get_config().knowledge
        self.wiki_path = self.config.wiki_path

    def run(self, facet: EntityFacet | None = None) -> LintReport:
        """Run all lint checks and return a report."""
        report = LintReport()
        store = KnowledgeStore()
        entities = store.search(facet=facet, limit=10000)

        self._check_index_consistency(report, store, entities)
        self._check_wikilinks(report, entities)
        self._check_content_conflicts(report, entities)
        self._check_stale_content(report, entities)

        return report

    def _check_index_consistency(self, report: LintReport, store: KnowledgeStore, entities: list) -> None:
        """Check 1: index files vs actual entities."""
        # 检查每个 facet 目录的文件是否都有对应 SQLite 记录
        for facet in EntityFacet:
            facet_dir = self.wiki_path / facet.value
            if not facet_dir.exists():
                continue
            for md_file in facet_dir.glob("*.md"):
                entity_id = md_file.stem
                entity = store.get(entity_id)
                if entity:
                    report.items.append(LintItem(Severity.OK, "索引一致性", entity_id, "文件与 SQLite 一致"))
                else:
                    report.items.append(LintItem(
                        Severity.WARNING, "索引一致性", entity_id,
                        f"文件 {md_file.name} 存在但 SQLite 无记录",
                        "运行 linglong index --rebuild"
                    ))

    def _check_wikilinks(self, report: LintReport, entities: list) -> None:
        """Check 2: WikiLinks integrity — dead links and orphans."""
        all_ids = {e.id for e in entities}
        referenced = set()

        for entity in entities:
            links = extract_wikilinks(entity.content)
            for link in links:
                target_path = resolve_wikilink(link, self.wiki_path)
                target_id = Path(target_path).stem
                referenced.add(target_id)

                if target_id not in all_ids:
                    # 尝试模糊匹配文件
                    target_file = self.wiki_path / target_path
                    if not target_file.exists():
                        report.items.append(LintItem(
                            Severity.CRITICAL, "死链", entity.id,
                            f"[[{link}]] 指向不存在的目标",
                            f"创建 stub: linglong write --facet entity --title '{link}' --content 'TODO' --yes"
                        ))
                    else:
                        report.items.append(LintItem(Severity.OK, "WikiLinks", entity.id, f"[[{link}]] 有效"))

        # 孤儿检测
        for entity in entities:
            if entity.id not in referenced and len(entities) > 1:
                report.items.append(LintItem(
                    Severity.WARNING, "孤儿资源", entity.id,
                    f"无任何其他条目引用",
                    "检查是否还有价值，无价值则归档"
                ))

    def _check_content_conflicts(self, report: LintReport, entities: list) -> None:
        """Check 3: Content conflicts — duplicate/highly similar entities."""
        # 简单实现：同 facet 下检查标题重复
        from collections import Counter
        for facet in EntityFacet:
            facet_entities = [e for e in entities if e.facet == facet]
            # 用内容前 50 字符做去重
            content_prefixes = [e.content[:50] for e in facet_entities]
            dupes = [k for k, v in Counter(content_prefixes).items() if v > 1]
            for dupe in dupes:
                report.items.append(LintItem(
                    Severity.WARNING, "内容重复", None,
                    f"Facet {facet.value} 存在 {dupe[:30]}... 重复条目",
                    "运行 linglong update 合并或归档重复条目"
                ))

    def _check_stale_content(self, report: LintReport, entities: list) -> None:
        """Check 4: Stale content — long un-updated entities."""
        from datetime import datetime, timedelta
        cutoff = datetime.utcnow() - timedelta(days=180)
        for entity in entities:
            if entity.updated_at < cutoff and entity.archived_at is None:
                report.items.append(LintItem(
                    Severity.WARNING, "过期内容", entity.id,
                    f"超过 180 天未更新（{entity.updated_at.strftime('%Y-%m-%d')}）",
                    "检查是否还有价值，考虑归档"
                ))
            else:
                report.items.append(LintItem(Severity.OK, "过期内容", entity.id, "更新时间正常"))
```

- [ ] **Step 3: 运行测试**

Run: `cd /home/user/projects/linglong && source venv/bin/activate && pytest tests/knowledge/test_lint.py -v`
Expected: PASS

- [ ] **Step 4: 提交**

```bash
git add src/linglong/knowledge/lint.py tests/knowledge/test_lint.py
git commit -m "feat: LintEngine 巡检引擎，4 项检查 + 3 级严重度"
```

---

### Task 4: 操作日志 + CLI 命令

**Files:**
- Modify: `src/linglong/knowledge/store.py`（写入时记录 log.md）
- Modify: `src/linglong/cli.py`（增加 lint / index / stats 命令）

- [ ] **Step 1: 在 store.py 中增加 log 记录**

在 `store.py` 顶部增加辅助函数：

```python
def _append_log(wiki_path: Path, operation: str, entity_id: str, detail: str = "") -> None:
    """Append operation to log.md."""
    log_path = wiki_path / "log.md"
    if not log_path.exists():
        log_path.write_text("# 操作日志\n\n| 时间 | 操作 | ID | 说明 |\n|------|------|-----|------|\n", encoding="utf-8")

    from datetime import datetime
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    line = f"| {timestamp} | {operation} | {entity_id[:8]}... | {detail} |\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)
```

在 `create()` 末尾、`update()` 末尾、`archive()` 末尾分别调用：
```python
_append_log(self.wiki_path, "create", entity.id, entity.facet.value)
_append_log(self.wiki_path, "update", entity.id, f"v{entity.current_version}")
_append_log(self.wiki_path, "archive", entity.id, "")
```

- [ ] **Step 2: 增加 lint / index / stats CLI 命令**

在 `cli.py` 的 `main()` 中增加：

```python
    # lint
    lint_parser = sub.add_parser("lint", help="知识库巡检")
    lint_parser.add_argument("--facet", default=None, help="只检查指定分类")
    lint_parser.add_argument("--fix", action="store_true", help="自动修复")
    lint_parser.set_defaults(func=cmd_lint)

    # index
    index_parser = sub.add_parser("index", help="索引管理")
    index_parser.add_argument("--facet", default=None, help="查看分类索引")
    index_parser.add_argument("--rebuild", action="store_true", help="重建所有索引")
    index_parser.set_defaults(func=cmd_index)

    # stats
    stats_parser = sub.add_parser("stats", help="知识库统计")
    stats_parser.set_defaults(func=cmd_stats)
```

实现三个命令函数：

```python
def cmd_lint(args: argparse.Namespace) -> int:
    from linglong.knowledge.lint import LintEngine
    engine = LintEngine()
    facet = EntityFacet(args.facet) if args.facet else None
    report = engine.run(facet=facet)
    print(report.format_text())
    return 0


def cmd_index(args: argparse.Namespace) -> int:
    from linglong.knowledge.indexer import IndexGenerator
    indexer = IndexGenerator()
    if args.rebuild:
        indexer.rebuild()
        print("✅ 索引已重建")
    elif args.facet:
        path = get_config().knowledge.wiki_path / f"index-{args.facet}.md"
        if path.exists():
            print(path.read_text())
        else:
            print(f"索引文件不存在，运行 linglong index --rebuild")
            return 1
    else:
        path = get_config().knowledge.wiki_path / "index.md"
        if path.exists():
            print(path.read_text())
        else:
            print("索引文件不存在，运行 linglong index --rebuild")
            return 1
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    store = KnowledgeStore()
    total = len(store.search(limit=100000))
    print(f"知识库统计：")
    print(f"  总条目：{total}")
    for facet in EntityFacet:
        count = len(store.search(facet=facet, limit=100000))
        if count:
            print(f"  {facet.value}: {count}")
    return 0
```

- [ ] **Step 3: 运行全量测试**

Run: `cd /home/user/projects/linglong && source venv/bin/activate && pytest -v 2>&1 | tail -30`
Expected: 全部 PASS

- [ ] **Step 4: 提交**

```bash
git add src/linglong/knowledge/store.py src/linglong/cli.py tests/
git commit -m "feat: 操作日志 + lint/index/stats CLI 命令，M3 完成"
```
