"""Linglong CLI — entry point for the full pipeline."""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from linglong.core.config import get_config
from linglong.core.models import Entity, EntityFacet, EntityStatus
from linglong.dispatch.manager import DispatchManager
from linglong.ingest.package import SourcePackage
from linglong.knowledge.store import ConcurrentModificationError, KnowledgeStore
from linglong.knowledge.lint import LintEngine
from linglong.knowledge.indexer import IndexGenerator
from linglong.knowledge.sync.claude_code import ClaudeCodeSyncAdapter
from linglong.knowledge.sync.codex import CodexSyncAdapter
from linglong.knowledge.sync.openclaw import OpenClawSyncAdapter
from linglong.knowledge.init import init_bare, init_from_backup, init_from_git, init_from_openclaw
from linglong.knowledge.lint_schedule import run_daemon, run_lint_and_log

logger = logging.getLogger(__name__)


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def cmd_ingest(args: argparse.Namespace) -> int:
    """Run ingest packages via IngestAgent."""
    _setup_logging(args.verbose)
    config = get_config()

    packages = [SourcePackage(**p) for p in config.ingest.packages]
    if not packages:
        logger.warning("No packages defined in ingest.packages")
        return 1

    for package in packages:
        if not package.enabled:
            continue

        logger.info("Executing package: %s", package.name)
        from linglong.ingest.agent import IngestAgent
        from linglong.ingest.brief_history import BriefHistory
        from linglong.ingest.feedback import FeedbackStore

        feedback_store = FeedbackStore()
        history_dir = os.path.expanduser("~/linglong/brief_history")
        brief_history = BriefHistory(Path(history_dir))
        agent = IngestAgent(feedback_store=feedback_store, brief_history=brief_history)
        output = asyncio.run(agent.run(package))

        if output:
            output_dir = os.path.expanduser("~/Downloads")
            os.makedirs(output_dir, exist_ok=True)
            today = date.today().isoformat()
            out_path = os.path.join(output_dir, f"ai-morning-brief-{today}.md")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"Morning brief written to {out_path}")
        else:
            print("No output generated")

    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    """Publish a markdown file via dispatch."""
    _setup_logging(args.verbose)

    file_path = Path(args.file)
    if not file_path.exists():
        logger.error("File not found: %s", file_path)
        return 1

    content = file_path.read_text(encoding="utf-8")
    dispatch = DispatchManager()
    result = dispatch.publish(content, {"title": file_path.stem}, publisher_name=args.publisher)
    if not result.success:
        logger.error("Publish failed: %s", result.error)
        return 1
    logger.info("Published to: %s", result.url)
    return 0


def cmd_kb_sync(args: argparse.Namespace) -> int:
    """Check and fix DB↔filesystem consistency."""
    _setup_logging(args.verbose)
    store = KnowledgeStore()
    issues = store.sync(fix=args.fix)

    if not issues:
        print("✅ DB 与文件系统一致，无问题")
        return 0

    print(f"发现 {len(issues)} 个问题：")
    for issue in issues:
        t = issue["type"]
        if t == "missing_file":
            print(f"  ❌ 缺失文件：{issue['entity_id'][:12]}... → {issue['expected_path']}")
        elif t == "wrong_path":
            print(f"  ⚠️ 路径不对：{issue['entity_id'][:12]}... {issue['actual_path']} → {issue['expected_path']}")
        elif t == "orphan_file":
            print(f"  🔍 孤儿文件：{issue['path']}")
        elif t == "duplicate_file":
            print(f"  📄 重复文件：{issue['path']}（保留 {issue['keep_path']}）")

    if args.fix:
        print(f"\n✅ 已修复 {len(issues)} 个问题")
    else:
        print(f"\n使用 --fix 执行修复")

    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    """Sync external agent knowledge into Linglong."""
    _setup_logging(args.verbose)
    store = KnowledgeStore()
    config = get_config()

    adapters = {
        "openclaw": (OpenClawSyncAdapter, config.knowledge.openclaw_wiki_path),
        "claude": (ClaudeCodeSyncAdapter, config.knowledge.claude_memory_path),
        "codex": (CodexSyncAdapter, config.knowledge.codex_path),
    }

    cls, path = adapters.get(args.source, (None, None))
    if cls is None:
        logger.error("Unknown source: %s", args.source)
        return 1

    # CLI argument overrides configured path
    if args.path:
        path = Path(args.path)
    elif path is not None:
        path = Path(path)

    if not path or not path.exists():
        logger.error("Path does not exist: %s", path)
        return 1

    adapter = cls(str(path), store)
    stats = adapter.sync_to_linglong()
    logger.info("Sync result: %s", stats)
    return 0


# ---------------------------------------------------------------------------
# Knowledge base subcommands
# ---------------------------------------------------------------------------


def cmd_write(args: argparse.Namespace) -> int:
    """Write a new knowledge entity."""
    content = args.content
    if args.from_file:
        content = Path(args.from_file).read_text(encoding="utf-8")
    if not content:
        print("错误：必须提供 --content 或 --from-file")
        return 1

    facet = EntityFacet(args.facet)
    config = get_config()
    auto_mode = config.knowledge.write_mode == "auto"

    store = KnowledgeStore()
    existing = store.search(query=args.title, facet=facet, limit=5)
    if existing and not args.force:
        for e in existing:
            if args.title.lower() in e.content.lower():
                print(f"⚠️ 已存在相似条目：{e.id} ({e.facet.value})")
                print(f"  建议：linglong update {e.id} --append \"补充内容\"")
                if not args.yes and not auto_mode:
                    return 1

    if not args.yes and not auto_mode:
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
        group=getattr(args, "group", None),
        created_by="agent:cli",
        confidence=0.5,
    )

    created = store.create(entity)
    print(f"✅ 已创建：{created.id} ({facet.value}/{args.title})")

    # Warn about facet crowding
    if not getattr(args, "group", None):
        crowding = store.check_facet_crowding(facet)
        if crowding:
            groups = list(crowding["existing_groups"].keys())
            print(f"⚠️ {facet.value} 根目录已有 {crowding['root_count']} 条未分组条目")
            if groups:
                print(f"  建议指定 --group，已有分组：{', '.join(groups)}")

    return 0


def cmd_read(args: argparse.Namespace) -> int:
    """Read a knowledge entity."""
    store = KnowledgeStore()
    entity = store.get(args.entity_id)
    if not entity:
        print(f"错误：未找到 {args.entity_id}")
        return 1

    if args.format == "json":
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


def cmd_search(args: argparse.Namespace) -> int:
    """Search knowledge entities."""
    store = KnowledgeStore()

    facet = EntityFacet(args.facet) if args.facet else None
    status = EntityStatus(args.status) if args.status else None

    if args.mode in ("vector", "hybrid") and args.query:
        results = store.search_similar(query=args.query, limit=args.limit, status=status, facet=facet)
    else:
        results = store.search(
            query=args.query,
            facet=facet,
            status=status,
            created_by=args.created_by,
            limit=args.limit,
            since=args.since,
        )

    if not results:
        print("无搜索结果")
        return 0

    if args.format == "json":
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

    for e in results:
        preview = e.content[:60].replace("\n", " ")
        updated = e.updated_at.strftime("%Y-%m-%d") if e.updated_at else "?"
        print(f"  {e.id[:8]}...  [{e.facet.value}]  {e.status.value}  "
              f"conf={e.confidence:.1f}  v{e.current_version}  {updated}  {preview}")

    if args.deep and results:
        print(f"\n--- Top {min(3, len(results))} 完整内容 ---\n")
        for e in results[:3]:
            print(f"## {e.id}")
            print(e.content[:500])
            print()
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    """Update a knowledge entity."""
    store = KnowledgeStore()
    entity = store.get(args.entity_id)
    if not entity:
        print(f"错误：未找到 {args.entity_id}")
        return 1

    if args.history:
        print(f"版本历史 (current: v{entity.current_version}):")
        for v in entity.versions:
            print(f"  v{v.version} | {v.modified_at or '?'} | {v.modified_by or '?'} | {(v.content or '')[:50]}")
        print(f"  v{entity.current_version} | {entity.updated_at} | current")
        return 0

    if args.show_version:
        ver_num = args.show_version
        if ver_num == entity.current_version:
            print(entity.content)
        else:
            for v in entity.versions:
                if v.version == ver_num:
                    print(v.content)
                    break
            else:
                print(f"版本 v{ver_num} 不存在")
                return 1
        return 0

    if args.content:
        entity.content = args.content
    elif args.from_file:
        entity.content = Path(args.from_file).read_text(encoding="utf-8")
    elif args.append:
        entity.content = f"{entity.content}\n\n{args.append}"
    elif args.metadata:
        for kv in args.metadata:
            key, _, value = kv.partition("=")
            if value:
                entity.metadata[key] = value
    else:
        print("错误：必须指定 --content / --from-file / --append / --metadata 之一")
        return 1

    try:
        updated = store.update(entity)
    except ConcurrentModificationError as e:
        print(f"冲突：{e}")
        return 1
    mode = "替换" if args.content or args.from_file else "追加" if args.append else "元数据更新"
    print(f"✅ 已更新 ({mode})：{updated.id} v{updated.current_version}")
    return 0


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


def cmd_archive(args: argparse.Namespace) -> int:
    """Archive knowledge entities."""
    store = KnowledgeStore()

    if args.entity_id:
        try:
            archived = store.archive(args.entity_id)
        except ValueError:
            print(f"错误：未找到 {args.entity_id}")
            return 1
        print(f"📦 已归档：{archived.id} ({archived.facet.value})")
        return 0

    if args.older_than:
        days = int(args.older_than.rstrip("d"))
        cutoff = datetime.now(UTC) - timedelta(days=days)
        results = store.search(limit=1000, include_archived=False)
        count = 0
        for e in results:
            if e.updated_at and e.updated_at < cutoff:
                store.archive(e.id)
                count += 1
        print(f"📦 已归档 {count} 条超过 {days} 天的条目")
        return 0

    print("错误：请指定 entity_id 或 --older-than")
    return 1


def cmd_lint(args: argparse.Namespace) -> int:
    """Run lint checks on knowledge base."""
    if args.daemon:
        _setup_logging(args.verbose)
        run_daemon(stale_days=args.stale_days)
        return 0

    if args.run_scheduled:
        _setup_logging(args.verbose)
        return run_lint_and_log(stale_days=args.stale_days)

    store = KnowledgeStore()
    engine = LintEngine(store)

    check = args.check or args.rule
    if check:
        if check in ("index", "index_consistency"):
            results = engine.check_index_consistency()
        elif check in ("links", "wikilinks"):
            results = engine.check_wikilinks()
        elif check in ("conflicts", "content_conflict"):
            results = engine.check_content_conflicts()
        elif check in ("stale", "stale_content"):
            results = engine.check_stale_content(args.stale_days)
        elif check == "orphans":
            results = engine.check_orphans()
        else:
            results = engine.run_all(args.stale_days)
    else:
        results = engine.run_all(args.stale_days)

    if args.fix:
        results = engine.fix_all(results, stale_days=args.stale_days)
        fixed_count = sum(1 for r in results if r.fixed)
        if fixed_count:
            print(f"\n🔧 已自动修复 {fixed_count} 个问题")

    if not results:
        print("✅ 知识库健康，无问题")
        return 0

    by_severity: dict[str, list] = {"error": [], "warning": [], "info": []}
    for r in results:
        by_severity[r.severity.value].append(r)

    print(f"巡检结果：{len(results)} 个问题\n")

    for severity in ["error", "warning", "info"]:
        items = by_severity[severity]
        if not items:
            continue
        icon = {"error": "❌", "warning": "⚠️", "info": "ℹ️"}[severity]
        print(f"{icon} {severity.upper()} ({len(items)})")
        for r in items:
            eid = r.entity_id[:8] if r.entity_id else "N/A"
            print(f"  [{r.rule}] {eid}... {r.message}")
            if r.rule == "orphan" and r.details.get("suggested_references"):
                for suggestion in r.details["suggested_references"]:
                    print(f"          → 建议在 {suggestion} 中添加 [[链接]]")
        print()

    return 1 if by_severity["error"] else 0


def cmd_index(args: argparse.Namespace) -> int:
    """Generate knowledge base index."""
    store = KnowledgeStore()
    gen = IndexGenerator(store.wiki_path)

    if args.facet:
        facet = EntityFacet(args.facet)
        count = gen.generate_facet(facet)
        print(f"✅ 已生成 index-{facet.value}.md ({count} 条)")
    elif args.rebuild:
        stats = gen.generate_all()
        for name, count in stats.items():
            print(f"  {name}: {count} 条")
        print(f"✅ 已重建全部索引 ({len(stats)} 个文件)")
        # Rebuild embeddings for changed entities
        emb_stats = store.rebuild_embeddings()
        if emb_stats["total"] > 0:
            print(f"  向量化: {emb_stats['regenerated']} 条重建, "
                  f"{emb_stats['unchanged']} 条未变, "
                  f"{emb_stats['failed']} 条失败")
    else:
        stats = gen.generate_all()
        for name, count in stats.items():
            print(f"  {name}: {count} 条")
        print("✅ 已生成索引")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize knowledge base."""
    try:
        if getattr(args, 'interactive', False):
            from linglong.knowledge.init import init_interactive
            init_interactive()
            return 0
        elif args.from_git:
            init_from_git(args.from_git)
            return 0
        elif args.from_backup:
            wiki_path = init_from_backup(Path(args.from_backup))
        elif args.from_openclaw:
            wiki_path = init_from_openclaw()
        else:
            wiki_path = init_bare()
        print(f"知识库已初始化：{wiki_path}")
        return 0
    except (FileNotFoundError, RuntimeError) as e:
        print(f"错误：{e}")
        return 1


def cmd_migrate(args: argparse.Namespace) -> int:
    """Migrate from external wiki directory."""
    source = Path(args.source_dir)
    if not source.exists():
        print(f"错误：源目录不存在：{source}")
        return 1

    store = KnowledgeStore()

    if args.dry_run:
        md_files = list(source.rglob("*.md"))
        print(f"将迁移 {len(md_files)} 个文件：")
        for f in md_files[:20]:
            print(f"  {f.relative_to(source)}")
        if len(md_files) > 20:
            print(f"  ... 还有 {len(md_files) - 20} 个")
        return 0

    md_files = list(source.rglob("*.md"))
    count = 0
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        entity = Entity(
            content=content,
            facet=EntityFacet.REFERENCE,
            created_by="migrate:cli",
            confidence=0.5,
        )
        store.create(entity)
        count += 1

    print(f"迁移完成：{count} 个文件")

    gen = IndexGenerator(store.wiki_path)
    gen.generate_all()
    print("索引已重建")

    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Show knowledge base statistics."""
    store = KnowledgeStore()

    all_entities = store.search(limit=10000)
    total = len(all_entities)

    facet_counts: dict[str, int] = {}
    for facet in EntityFacet:
        results = store.search(facet=facet, limit=10000)
        facet_counts[facet.value] = len(results)

    recent = store.search(limit=5)

    print("知识库统计")
    print("==========")
    print(f"总条目：{total}")
    print()
    print("按分类：")
    for facet, count in facet_counts.items():
        bar = "█" * min(count, 20)
        print(f"  {facet:12s} {count:4d} {bar}")
    print()
    if recent:
        print("最近更新：")
        for e in recent:
            preview = e.content[:40].replace("\n", " ")
            print(f"  {e.id[:8]}... [{e.facet.value}] {preview}")
    return 0


def cmd_template(args: argparse.Namespace) -> int:
    """Manage knowledge entry templates."""
    from linglong.core.templates import get_template_manager

    manager = get_template_manager()

    if args.action == "list":
        templates = manager.list_templates()
        if not templates:
            print("暂无模板")
            return 0
        print("可用模板")
        print("========")
        for facet, info in templates.items():
            desc = info.get("description", "")
            print(f"  {facet:15s} {desc}")
        return 0

    if args.action == "get":
        content = manager.get_template(args.facet)
        if content is None:
            available = list(manager.list_templates().keys())
            print(f"模板 '{args.facet}' 不存在")
            print(f"可用模板：{', '.join(available)}")
            return 1
        print(content)
        return 0

    return 0


# ---------------------------------------------------------------------------
# Deprecated wrapper
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Parser registration helpers
# ---------------------------------------------------------------------------


def _reg_write(sub):
    p = sub.add_parser("write", help="写入知识条目")
    p.add_argument("--facet", required=True,
        choices=["concept", "experience", "methodology", "project", "reference", "personal"],
        help="知识分类")
    p.add_argument("--group", default=None, help="子目录分组（如 linglong、openclaw）")
    p.add_argument("--title", required=True, help="标题（用作文件名）")
    p.add_argument("--content", default=None, help="内容文本")
    p.add_argument("--from-file", default=None, help="从文件读取内容")
    p.add_argument("--yes", action="store_true", help="跳过确认直接写入")
    p.add_argument("--force", action="store_true", help="强制创建，即使存在相似条目")
    p.add_argument("--no-index", action="store_true", help="跳过索引更新")
    return p


def _reg_read(sub):
    p = sub.add_parser("read", help="读取知识条目")
    p.add_argument("entity_id", help="Entity ID")
    p.add_argument("--path", default=None, help="按文件路径读取")
    p.add_argument("--format", choices=["json", "markdown"], default="markdown", help="输出格式")
    return p


def _reg_search(sub):
    p = sub.add_parser("search", help="搜索知识条目")
    p.add_argument("query", nargs="?", default=None, help="搜索关键词")
    p.add_argument("--facet", default=None, help="按分类过滤")
    p.add_argument("--mode", choices=["keyword", "vector", "hybrid", "auto"], default="auto", help="搜索模式")
    p.add_argument("--deep", action="store_true", help="加载完整内容")
    p.add_argument("--limit", type=int, default=10, help="结果数量")
    p.add_argument("--status", default=None, help="按状态过滤")
    p.add_argument("--created-by", default=None, help="按创建者过滤")
    p.add_argument("--since", default=None, help="起始日期 (YYYY-MM-DD)")
    p.add_argument("--format", choices=["table", "json"], default="table", help="输出格式")
    return p


def _reg_update(sub):
    p = sub.add_parser("update", help="更新知识条目")
    p.add_argument("entity_id", help="Entity ID")
    p.add_argument("--content", default=None, help="替换内容")
    p.add_argument("--from-file", default=None, help="从文件读取替换内容")
    p.add_argument("--append", default=None, help="追加内容")
    p.add_argument("--metadata", nargs="*", default=None, help="更新元数据 key=value")
    p.add_argument("--history", action="store_true", help="查看版本历史")
    p.add_argument("--show-version", type=int, default=None, help="查看指定版本")
    p.add_argument("--yes", action="store_true", help="跳过确认")
    p.add_argument("--no-index", action="store_true", help="跳过索引更新")
    return p


def _reg_archive(sub):
    p = sub.add_parser("archive", help="归档知识条目")
    p.add_argument("entity_id", nargs="?", default=None, help="Entity ID")
    p.add_argument("--older-than", default=None, help="归档超过 N 天的条目 (如 90d)")
    return p


def _reg_review(sub):
    p = sub.add_parser("review", help="审核管理")
    p.add_argument("--list-pending", action="store_true", help="列出待审核条目")
    p.add_argument("--approve", default=None, metavar="ID", help="批准条目")
    p.add_argument("--reject", default=None, metavar="ID", help="拒绝条目")
    return p


def _reg_lint(sub):
    p = sub.add_parser("lint", help="巡检知识库")
    p.add_argument("--stale-days", type=int, default=90, help="过期天数阈值")
    p.add_argument("--check", default=None,
        choices=["index", "links", "conflicts", "stale", "orphans"],
        help="指定检查项：index（索引一致性）、links（死链）、conflicts（内容冲突）、stale（过期内容）、orphans（孤儿资源）")
    p.add_argument("--rule", default=None,
        choices=["index_consistency", "wikilinks", "content_conflict", "stale_content"],
        help="已废弃，请使用 --check")
    p.add_argument("--fix", action="store_true", help="自动修复可修复的问题")
    p.add_argument("--daemon", action="store_true", help="后台守护进程模式，按 lint_schedule 定时巡检")
    p.add_argument("--run-scheduled", action="store_true", help="立即执行一次巡检并退出（用于系统 cron 调用）")
    return p


def _reg_index(sub):
    p = sub.add_parser("index", help="生成知识库索引")
    p.add_argument("--rebuild", action="store_true", help="重建所有索引")
    p.add_argument("--facet", default=None, help="只生成指定分面的索引")
    return p


def _reg_stats(sub):
    return sub.add_parser("stats", help="知识库统计")


def _reg_kb_sync(sub):
    p = sub.add_parser("sync", help="DB↔文件一致性校验")
    p.add_argument("--fix", action="store_true", help="执行修复（默认仅预览）")
    return p


def _reg_template(sub):
    p = sub.add_parser("template", help="管理知识条目模板")
    p.add_argument("action", choices=["list", "get"], help="操作：list 列出模板，get 获取模板内容")
    p.add_argument("facet", nargs="?", default=None, help="模板分类（get 时使用）")
    return p


def _reg_init(sub):
    p = sub.add_parser("init", help="初始化知识库")
    p.add_argument("--from-backup", default=None, help="从备份目录恢复")
    p.add_argument("--from-openclaw", action="store_true", help="从 OpenClaw wiki 导入")
    p.add_argument("--from-git", default=None, metavar="URL", dest="from_git", help="从 Git 仓库初始化")
    p.add_argument("--interactive", "-i", action="store_true", help="交互式配置向导")
    return p


def _reg_migrate(sub):
    p = sub.add_parser("migrate", help="从外部 wiki 迁移")
    p.add_argument("--from", required=True, metavar="DIR", dest="source_dir", help="源 wiki 目录")
    p.add_argument("--dry-run", action="store_true", help="预览不执行")
    return p


def _reg_sync(sub):
    p = sub.add_parser("sync", help="同步 Agent 知识")
    p.add_argument("source", choices=["openclaw", "claude", "codex"], help="Source to sync")
    p.add_argument("--path", default=None, help="Override source path")
    return p


def _reg_ingest(sub):
    p = sub.add_parser("ingest", help="Run ingest packages")
    p.add_argument("--write", action="store_true", help="Write collected entities to knowledge store")
    return p


def _reg_publish(sub):
    p = sub.add_parser("publish", help="Publish a markdown file")
    p.add_argument("file", help="Markdown file to publish")
    p.add_argument("--publisher", default=None, help="Publisher name")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="linglong", description="Linglong cross-agent knowledge hub")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    # ========== kb group ==========
    kb_parser = sub.add_parser("kb", help="知识库管理")
    kb_sp = kb_parser.add_subparsers(dest="kb_sub", required=True)

    _reg_write(kb_sp).set_defaults(func=cmd_write)
    _reg_read(kb_sp).set_defaults(func=cmd_read)
    _reg_search(kb_sp).set_defaults(func=cmd_search)
    _reg_update(kb_sp).set_defaults(func=cmd_update)
    _reg_archive(kb_sp).set_defaults(func=cmd_archive)
    _reg_review(kb_sp).set_defaults(func=cmd_review)
    _reg_lint(kb_sp).set_defaults(func=cmd_lint)
    _reg_index(kb_sp).set_defaults(func=cmd_index)
    _reg_stats(kb_sp).set_defaults(func=cmd_stats)
    _reg_template(kb_sp).set_defaults(func=cmd_template)
    _reg_init(kb_sp).set_defaults(func=cmd_init)
    _reg_migrate(kb_sp).set_defaults(func=cmd_migrate)
    _reg_kb_sync(kb_sp).set_defaults(func=cmd_kb_sync)

    # ========== ingest (standalone collection tool) ==========
    _reg_ingest(sub).set_defaults(func=cmd_ingest)

    # ========== publish ==========
    _reg_publish(sub).set_defaults(func=cmd_publish)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
