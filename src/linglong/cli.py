"""Linglong CLI — entry point for the full pipeline."""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from linglong.composer.composer import Composer
from linglong.core.config import get_config
from linglong.dispatch.manager import DispatchManager
from linglong.ingest.executor import PackageExecutor
from linglong.ingest.package import SourcePackage
from linglong.knowledge.store import KnowledgeStore
from linglong.knowledge.sync.claude_code import ClaudeCodeSyncAdapter
from linglong.knowledge.sync.codex import CodexSyncAdapter
from linglong.knowledge.sync.openclaw import OpenClawSyncAdapter

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

    # Allow CLI override of path
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

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
