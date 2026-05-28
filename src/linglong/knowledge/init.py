"""Knowledge base initialization.

Supports five init modes:
- bare: empty knowledge base with directory structure and config template
- from-backup: restore from a backup directory
- from-openclaw: import from OpenClaw wiki
- from-git: clone and import from a git repository
- interactive: guided wizard with configuration prompts
"""

import shutil
import logging
from pathlib import Path

from linglong.core.config import get_config

logger = logging.getLogger(__name__)

_CONFIG_FILENAME = ".knowledge.yml"

_DEFAULT_CONFIG_TEMPLATE = """# Knowledge base configuration

knowledge:
  wiki_path: ~/knowledge/wiki
  db_path: ~/knowledge/db/knowledge.db
  generate_embeddings: false
  write_mode: auto
  auto_lint: false
  max_versions: 10
  db_mode: wal
"""

_KNOWLEDGE_HOME = Path.home() / "knowledge"


def init_bare(target_dir: Path | None = None) -> Path:
    """Initialize an empty knowledge base.

    Creates wiki/, archive/, config template, and one subdirectory per facet.
    """
    from linglong.core.models import EntityFacet

    base = target_dir or _KNOWLEDGE_HOME
    wiki_path = base / "wiki"
    wiki_path.mkdir(parents=True, exist_ok=True)
    (wiki_path / "archive").mkdir(exist_ok=True)

    config_path = base / _CONFIG_FILENAME
    if not config_path.exists():
        config_path.write_text(_DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")
        logger.info("Created config template: %s", config_path)
    else:
        logger.info("Config file already exists: %s", config_path)

    for facet in EntityFacet:
        (wiki_path / facet.value).mkdir(exist_ok=True)

    logger.info("Knowledge base initialized: %s", wiki_path)
    return wiki_path


def init_from_backup(backup_dir: Path, target_dir: Path | None = None) -> Path:
    """Initialize from a backup directory.

    Copies wiki/ directory from backup. Merges non-conflicting files.
    """
    backup_wiki = backup_dir / "wiki"
    if not backup_wiki.exists():
        raise FileNotFoundError(f"Backup directory has no wiki/: {backup_dir}")

    target_dir = target_dir or _KNOWLEDGE_HOME
    target_wiki = target_dir / "wiki"

    if target_wiki.exists():
        for facet_dir in backup_wiki.iterdir():
            if facet_dir.is_dir():
                target_facet = target_wiki / facet_dir.name
                target_facet.mkdir(parents=True, exist_ok=True)
                for f in facet_dir.glob("*.md"):
                    if not (target_facet / f.name).exists():
                        shutil.copy2(f, target_facet / f.name)
    else:
        shutil.copytree(backup_wiki, target_wiki)

    config_path = target_dir / _CONFIG_FILENAME
    if not config_path.exists():
        config_path.write_text(_DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")

    logger.info("Restored from backup: %s", backup_dir)
    return target_wiki


def init_from_openclaw(openclaw_path: Path | None = None, target_dir: Path | None = None) -> Path:
    """Initialize from OpenClaw wiki directory."""
    from linglong.core.models import Entity, EntityFacet
    from linglong.knowledge.store import KnowledgeStore

    wiki_path = init_bare(target_dir)

    if openclaw_path is None:
        openclaw_path = Path.home() / ".openclaw" / "workspace" / "memory" / "wiki"

    if not openclaw_path.exists():
        raise FileNotFoundError(f"OpenClaw wiki not found: {openclaw_path}")

    store = KnowledgeStore()
    count = 0

    for md_file in openclaw_path.rglob("*.md"):
        if md_file.name.startswith("index"):
            continue
        content = md_file.read_text(encoding="utf-8")
        if not content.strip():
            continue

        entity = Entity(
            content=content,
            facet=EntityFacet.REFERENCE,
            created_by="agent:openclaw-import",
            confidence=0.7,
        )
        store.create(entity)
        count += 1

    logger.info("Imported %d entities from OpenClaw", count)
    return wiki_path


def init_from_git(repo_url: str, target_dir: Path | None = None) -> Path:
    """Initialize from a Git repository containing wiki files."""
    import subprocess

    base = target_dir or _KNOWLEDGE_HOME
    wiki_path = base / "wiki"

    tmp_dir = base / ".tmp_clone"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)

    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(tmp_dir)],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error("Git clone failed: %s", e.stderr)
        raise RuntimeError(f"Failed to clone {repo_url}: {e.stderr}")
    except FileNotFoundError:
        raise RuntimeError("git command not found. Please install git.")

    init_bare(target_dir=base)

    source_dir = wiki_path / "reference"
    source_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for md_file in tmp_dir.rglob("*.md"):
        dest = source_dir / md_file.name
        if not dest.exists():
            shutil.copy2(md_file, dest)
            count += 1

    shutil.rmtree(tmp_dir, ignore_errors=True)

    logger.info("Initialized knowledge base from git: %s → %s (%d files)", repo_url, wiki_path, count)
    return wiki_path


def init_interactive(target_dir: Path | None = None) -> Path:
    """Interactive initialization with configuration wizard."""
    base = target_dir or _KNOWLEDGE_HOME

    logger.info("=== Knowledge base init wizard ===")

    default_wiki = base / "wiki"
    wiki_input = input(f"Wiki directory [{default_wiki}]: ").strip()
    wiki_path = Path(wiki_input) if wiki_input else default_wiki

    default_db = base / "db" / "knowledge.db"
    db_input = input(f"Database path [{default_db}]: ").strip()
    db_path = Path(db_input) if db_input else default_db

    vector_input = input("Enable vector search? [y/N]: ").strip().lower()
    vector_enabled = vector_input in ("y", "yes")

    write_input = input("Write mode (confirm/auto) [confirm]: ").strip()
    write_mode = write_input if write_input in ("confirm", "auto") else "confirm"

    lint_input = input("Auto-lint after write? [y/N]: ").strip().lower()
    auto_lint = lint_input in ("y", "yes")

    schedule_input = input("Enable scheduled lint? [y/N]: ").strip().lower()
    lint_schedule = None
    if schedule_input in ("y", "yes"):
        cron_input = input("Cron expression (default 0 2 * * *): ").strip()
        lint_schedule = cron_input if cron_input else "0 2 * * *"

    init_bare(target_dir=base)

    schedule_line = f"  lint_schedule: {lint_schedule}" if lint_schedule else "  # lint_schedule: \"0 2 * * *\""
    config_content = f"""# Knowledge base configuration
# Generated by init --interactive

knowledge:
  wiki_path: {wiki_path}
  db_path: {db_path}
  generate_embeddings: {str(vector_enabled).lower()}
  write_mode: {write_mode}
  auto_lint: {str(auto_lint).lower()}
{schedule_line}
  max_versions: 10
  db_mode: wal
"""
    config_path = base / _CONFIG_FILENAME
    config_path.write_text(config_content, encoding="utf-8")

    logger.info("Knowledge base initialized: %s", wiki_path)
    logger.info("Config file: %s", config_path)
    return wiki_path
