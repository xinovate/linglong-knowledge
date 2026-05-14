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

_DEFAULT_CONFIG_TEMPLATE = """# Linglong 配置文件
# 详细说明：https://github.com/your-org/linglong

knowledge:
  wiki_path: ./wiki
  db_path: ./knowledge.db
  generate_embeddings: false
  write_mode: confirm
  search_mode: on_demand
  auto_index: true
  max_versions: 10
  lock_timeout: 5
  db_mode: wal
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

    wiki_path = (target_dir or Path.cwd()) / "wiki"
    wiki_path.mkdir(parents=True, exist_ok=True)
    (wiki_path / "archive").mkdir(exist_ok=True)

    # 写配置模板
    config_path = (target_dir or Path.cwd()) / ".linglong.yaml"
    if not config_path.exists():
        config_path.write_text(_DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")
        logger.info("已创建配置模板：%s", config_path)
    else:
        logger.info("配置文件已存在：%s", config_path)

    # 为每个 facet 创建目录
    for facet in EntityFacet:
        (wiki_path / facet.value).mkdir(exist_ok=True)

    logger.info("知识库已初始化：%s", wiki_path)
    return wiki_path


def init_from_backup(backup_dir: Path, target_dir: Path | None = None) -> Path:
    """Initialize from a backup directory.

    Copies wiki/ directory from backup. If target wiki/ already exists,
    merges non-conflicting files instead of overwriting.
    """
    backup_wiki = backup_dir / "wiki"
    if not backup_wiki.exists():
        raise FileNotFoundError(f"备份目录无 wiki/：{backup_dir}")

    target_dir = target_dir or Path.cwd()
    target_wiki = target_dir / "wiki"

    if target_wiki.exists():
        # 合并而非覆盖
        for facet_dir in backup_wiki.iterdir():
            if facet_dir.is_dir():
                target_facet = target_wiki / facet_dir.name
                target_facet.mkdir(parents=True, exist_ok=True)
                for f in facet_dir.glob("*.md"):
                    if not (target_facet / f.name).exists():
                        shutil.copy2(f, target_facet / f.name)
    else:
        shutil.copytree(backup_wiki, target_wiki)

    # 确保配置文件存在
    config_path = target_dir / ".linglong.yaml"
    if not config_path.exists():
        config_path.write_text(_DEFAULT_CONFIG_TEMPLATE, encoding="utf-8")

    logger.info("从备份恢复：%s", backup_dir)
    return target_wiki


def init_from_openclaw(openclaw_path: Path | None = None, target_dir: Path | None = None) -> Path:
    """Initialize from OpenClaw wiki directory.

    Imports wiki markdown files as SOURCE entities.
    """
    from linglong.core.models import Entity, EntityFacet
    from linglong.knowledge.store import KnowledgeStore

    # 先初始化空知识库
    wiki_path = init_bare(target_dir)

    # 定位 OpenClaw wiki
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
            facet=EntityFacet.SOURCE,
            created_by="agent:openclaw-import",
            confidence=0.7,
        )
        store.create(entity)
        count += 1

    logger.info("从 OpenClaw 导入 %d 条知识", count)
    return wiki_path
