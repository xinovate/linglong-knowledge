"""Linglong CLI — entry point for the full pipeline."""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

from linglong.composer.composer import Composer
from linglong.core.config import get_config
from linglong.core.models import Entity, EntityFacet, EntityStatus
from linglong.dispatch.manager import DispatchManager
from linglong.ingest.executor import PackageExecutor
from linglong.ingest.package import SourcePackage
from linglong.knowledge.store import ConcurrentModificationError, KnowledgeStore
from linglong.knowledge.lint import LintEngine
from linglong.knowledge.indexer import IndexGenerator
from linglong.knowledge.sync.claude_code import ClaudeCodeSyncAdapter
from linglong.knowledge.sync.codex import CodexSyncAdapter
from linglong.knowledge.sync.openclaw import OpenClawSyncAdapter
from linglong.knowledge.init import init_bare, init_from_backup, init_from_openclaw

logger = logging.getLogger(__name__)


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def cmd_ingest(args: argparse.Namespace) -> int:
    """Run ingest packages."""
    _setup_logging(args.verbose)
    config = get_config()
    store = KnowledgeStore()

    packages = SourcePackage.load_all(config.ingest.package_paths)
    if not packages:
        logger.warning("No packages found in %s", config.ingest.package_paths)
        return 1

    executor = PackageExecutor(store=store)
    for package in packages:
        if not package.enabled:
            continue
        logger.info("Executing package: %s", package.name)
        result = asyncio.run(executor.execute(package))
        logger.info("Result: %s", result)

    return 0


def cmd_compose(args: argparse.Namespace) -> int:
    """Run composer pipeline."""
    _setup_logging(args.verbose)
    composer = Composer()
    result = composer.run(dry_run=args.dry_run, draft=args.draft)
    logger.info("Composer result: %s", result)
    if not result.success:
        return 1
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    """Publish a draft by ID."""
    _setup_logging(args.verbose)
    from linglong.composer.draft import DraftManager

    dm = DraftManager()
    entry = dm.get_draft(args.draft_id)
    if entry is None:
        logger.error("Draft not found: %s", args.draft_id)
        return 1

    payload = dm.publish_draft(entry.id)
    dispatch = DispatchManager()
    result = dispatch.publish(payload, args.publisher)
    if not result.success:
        logger.error("Publish failed: %s", result.error)
        return 1
    logger.info("Published to: %s", result.url)
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

    # CLI 参数覆盖路径
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
# 知识库子命令
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
        results = store.search_similar(query=args.query, limit=args.limit, status=status)
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

    for e in results:
        preview = e.content[:60].replace("\n", " ")
        updated = e.updated_at.strftime("%Y-%m-%d") if e.updated_at else "?"
        print(f"  {e.id[:8]}...  [{e.facet.value}]  {e.status.value}  {updated}  {preview}")

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

    # 查看版本历史
    if args.history:
        print(f"版本历史 (current: v{entity.current_version}):")
        for v in entity.versions:
            print(f"  v{v.version} | {v.modified_at or '?'} | {v.modified_by or '?'} | {(v.content or '')[:50]}")
        print(f"  v{entity.current_version} | {entity.updated_at} | current")
        return 0

    # 查看指定版本
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

    # 更新操作
    if args.content:
        entity.content = args.content
    elif args.append:
        entity.content = entity.content + "\n\n" + args.append
    elif args.metadata:
        for kv in args.metadata:
            key, _, value = kv.partition("=")
            if value:
                entity.metadata[key] = value
    else:
        print("错误：必须指定 --content / --append / --metadata 之一")
        return 1

    try:
        updated = store.update(entity)
    except ConcurrentModificationError as e:
        print(f"冲突：{e}")
        return 1
    mode = "替换" if args.content else "追加" if args.append else "元数据更新"
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
        cutoff = datetime.utcnow() - timedelta(days=days)
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
    store = KnowledgeStore()
    engine = LintEngine(store)

    if args.rule:
        if args.rule == "index_consistency":
            results = engine.check_index_consistency()
        elif args.rule == "wikilinks":
            results = engine.check_wikilinks()
        elif args.rule == "content_conflict":
            results = engine.check_content_conflicts()
        elif args.rule == "stale_content":
            results = engine.check_stale_content(args.stale_days)
        else:
            results = engine.run_all(args.stale_days)
    else:
        results = engine.run_all(args.stale_days)

    if not results:
        print("✅ 知识库健康，无问题")
        return 0

    # 按严重度分组
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
    else:
        stats = gen.generate_all()
        for name, count in stats.items():
            print(f"  {name}: {count} 条")
        print("✅ 已生成索引")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize knowledge base."""
    try:
        if args.from_backup:
            wiki_path = init_from_backup(Path(args.from_backup))
        elif args.from_openclaw:
            wiki_path = init_from_openclaw()
        else:
            wiki_path = init_bare()
        print(f"知识库已初始化：{wiki_path}")
        return 0
    except FileNotFoundError as e:
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
        # 预览：列出待迁移文件
        md_files = list(source.rglob("*.md"))
        print(f"将迁移 {len(md_files)} 个文件：")
        for f in md_files[:20]:
            print(f"  {f.relative_to(source)}")
        if len(md_files) > 20:
            print(f"  ... 还有 {len(md_files) - 20} 个")
        return 0

    # 迁移：逐个读取 md 文件并创建 Entity
    md_files = list(source.rglob("*.md"))
    count = 0
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        entity = Entity(
            content=content,
            facet=EntityFacet.SOURCE,
            created_by="migrate:cli",
            confidence=0.5,
        )
        store.create(entity)
        count += 1

    print(f"迁移完成：{count} 个文件")

    # 重建索引
    gen = IndexGenerator(store.wiki_path)
    gen.generate_all()
    print("索引已重建")

    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Show knowledge base statistics."""
    store = KnowledgeStore()

    # 总数
    all_entities = store.search(limit=10000)
    total = len(all_entities)

    # 按 facet 统计
    facet_counts: dict[str, int] = {}
    for facet in EntityFacet:
        results = store.search(facet=facet, limit=10000)
        facet_counts[facet.value] = len(results)

    # 最近更新
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="linglong", description="Linglong cross-agent knowledge hub")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    # ingest
    ingest_parser = sub.add_parser("ingest", help="Run ingest packages")
    ingest_parser.set_defaults(func=cmd_ingest)

    # compose
    compose_parser = sub.add_parser("compose", help="Run composer pipeline")
    compose_parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    compose_parser.add_argument("--draft", action="store_true", help="Draft mode")
    compose_parser.set_defaults(func=cmd_compose)

    # publish
    publish_parser = sub.add_parser("publish", help="Publish a draft")
    publish_parser.add_argument("draft_id", help="Draft ID to publish")
    publish_parser.add_argument("--publisher", default=None, help="Publisher name")
    publish_parser.set_defaults(func=cmd_publish)

    # sync
    sync_parser = sub.add_parser("sync", help="Sync agent knowledge")
    sync_parser.add_argument("source", choices=["openclaw", "claude", "codex"], help="Source to sync")
    sync_parser.add_argument("--path", default=None, help="Override source path")
    sync_parser.set_defaults(func=cmd_sync)

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

    # lint
    lint_parser = sub.add_parser("lint", help="巡检知识库")
    lint_parser.add_argument("--stale-days", type=int, default=90, help="过期天数阈值")
    lint_parser.add_argument("--rule", default=None,
        choices=["index_consistency", "wikilinks", "content_conflict", "stale_content"])
    lint_parser.set_defaults(func=cmd_lint)

    # index
    index_parser = sub.add_parser("index", help="生成知识库索引")
    index_parser.add_argument("--rebuild", action="store_true", help="重建所有索引")
    index_parser.add_argument("--facet", default=None, help="只生成指定分面的索引")
    index_parser.set_defaults(func=cmd_index)

    # stats
    stats_parser = sub.add_parser("stats", help="知识库统计")
    stats_parser.set_defaults(func=cmd_stats)

    # init
    init_parser = sub.add_parser("init", help="初始化知识库")
    init_parser.add_argument("--from-backup", default=None, help="从备份目录恢复")
    init_parser.add_argument("--from-openclaw", action="store_true", help="从 OpenClaw wiki 导入")
    init_parser.set_defaults(func=cmd_init)

    # migrate
    migrate_parser = sub.add_parser("migrate", help="从外部 wiki 迁移")
    migrate_parser.add_argument("--from", required=True, metavar="DIR", dest="source_dir",
                                help="源 wiki 目录")
    migrate_parser.add_argument("--dry-run", action="store_true", help="预览不执行")
    migrate_parser.set_defaults(func=cmd_migrate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
