"""Knowledge base initialization.

支持三种初始化模式：
- bare: 空知识库，创建目录结构和配置模板
- from-backup: 从备份目录恢复
- from-openclaw: 从 OpenClaw wiki 导入
"""

import shutil
import logging
from pathlib import Path

from linglong.core.config import get_config

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_TEMPLATE = """# Linglong 知识库配置

knowledge:
  wiki_path: ~/linglong/wiki
  db_path: ~/linglong/db/knowledge.db
  generate_embeddings: false
  write_mode: auto
  auto_lint: false
  max_versions: 10
  db_mode: wal

reviewer:
  llm_model: gpt-4
  passing_score: 6.0

dispatch:
  enabled: true
  default_publisher: local
  publishers:
    - name: local
      type: local
      enabled: true
      config:
        output_dir: ~/Downloads/linglong-output
        overwrite: true
"""


def init_bare(target_dir: Path | None = None) -> Path:
    """Initialize an empty knowledge base.

    Creates:
    - wiki/ directory
    - wiki/archive/ directory
    - .linglong.yaml config template
    - One subdirectory per EntityFacet

    Returns the wiki path.
    """
    from linglong.core.models import EntityFacet

    base = target_dir or Path.home() / "linglong"
    wiki_path = base / "wiki"
    wiki_path.mkdir(parents=True, exist_ok=True)
    (wiki_path / "archive").mkdir(exist_ok=True)

    config_path = base / ".linglong.yaml"
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

    Copies wiki/ directory from backup. If target wiki/ already exists,
    merges non-conflicting files instead of overwriting.
    """
    backup_wiki = backup_dir / "wiki"
    if not backup_wiki.exists():
        raise FileNotFoundError(f"备份目录无 wiki/：{backup_dir}")

    target_dir = target_dir or Path.home() / "linglong"
    target_wiki = target_dir / "wiki"

    if target_wiki.exists():
        # Merge, don't overwrite existing files
        for facet_dir in backup_wiki.iterdir():
            if facet_dir.is_dir():
                target_facet = target_wiki / facet_dir.name
                target_facet.mkdir(parents=True, exist_ok=True)
                for f in facet_dir.glob("*.md"):
                    if not (target_facet / f.name).exists():
                        shutil.copy2(f, target_facet / f.name)
    else:
        shutil.copytree(backup_wiki, target_wiki)

    config_path = target_dir / ".linglong.yaml"
    if not config_path.exists():
        config_path.write_text(_DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")

    logger.info("Restoring from backup: %s", backup_dir)
    return target_wiki


def init_from_openclaw(openclaw_path: Path | None = None, target_dir: Path | None = None) -> Path:
    """Initialize from OpenClaw wiki directory.

    Imports wiki markdown files as SOURCE entities.
    """
    from linglong.core.models import Entity, EntityFacet
    from linglong.knowledge.store import KnowledgeStore

    wiki_path = init_bare(target_dir)


    if openclaw_path is None:
        openclaw_path = Path.home() / ".openclaw" / "workspace" / "memory" / "wiki"

    if not openclaw_path.exists():
        raise FileNotFoundError(f"OpenClaw wiki 不存在：{openclaw_path}")

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
    """Initialize from a Git repository containing wiki files.

    Args:
        repo_url: Git repository URL
        target_dir: Target directory (default: cwd)

    Returns:
        Path to wiki directory
    """
    import subprocess

    base = target_dir or Path.home() / "linglong"
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
    """Interactive initialization with configuration wizard.

    Prompts user for key settings and generates customized .linglong.yaml.
    """
    base = target_dir or Path.home() / "linglong"

    logger.info("=== Linglong 知识库初始化向导 ===")

    default_wiki = base / "wiki"
    wiki_input = input(f"Wiki 目录 [{default_wiki}]: ").strip()
    wiki_path = Path(wiki_input) if wiki_input else default_wiki

    default_db = base / "db" / "knowledge.db"
    db_input = input(f"数据库路径 [{default_db}]: ").strip()
    db_path = Path(db_input) if db_input else default_db

    vector_input = input("启用向量搜索？[y/N]: ").strip().lower()
    vector_enabled = vector_input in ("y", "yes")

    write_input = input("写入模式 (confirm/auto) [confirm]: ").strip()
    write_mode = write_input if write_input in ("confirm", "auto") else "confirm"

    lint_input = input("写入后自动巡检？[y/N]: ").strip().lower()
    auto_lint = lint_input in ("y", "yes")

    schedule_input = input("是否启用定时巡检？[y/N]: ").strip().lower()
    lint_schedule = None
    if schedule_input in ("y", "yes"):
        cron_input = input("定时巡检时间（cron 格式，默认 0 2 * * *）: ").strip()
        lint_schedule = cron_input if cron_input else "0 2 * * *"

    init_bare(target_dir=base)


    schedule_line = f"  lint_schedule: {lint_schedule}" if lint_schedule else "  # lint_schedule: \"0 2 * * *\""
    config_content = f"""# Linglong 知识库配置
# 由 linglong init --interactive 生成

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
    config_path = base / ".linglong.yaml"
    config_path.write_text(config_content, encoding="utf-8")

    logger.info("知识库已初始化：%s", wiki_path)
    logger.info("配置文件：%s", config_path)
    return wiki_path
