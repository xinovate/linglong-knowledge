"""知识库初始化测试。"""

import tempfile
from pathlib import Path

import pytest

from linglong.core.config import LinglongConfig, set_config
from linglong.core.models import EntityFacet
from linglong.knowledge.init import init_bare, init_from_backup


@pytest.fixture
def init_dir():
    """临时目录，用完即清理。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


def _make_init_config(tmp_path: Path) -> LinglongConfig:
    """创建测试用 LinglongConfig，禁用 embedding。"""
    config = LinglongConfig(
        data_dir=tmp_path / "data",
        knowledge=LinglongConfig().knowledge.model_copy(
            update={
                "wiki_path": tmp_path / "wiki",
                "db_path": tmp_path / "knowledge.db",
                "generate_embeddings": False,
            }
        ),
    )
    set_config(config)
    return config


def test_init_bare_creates_directories(init_dir):
    """裸初始化创建所有 facet 目录和配置文件。"""
    _make_init_config(init_dir)
    wiki_path = init_bare(init_dir)

    assert wiki_path.exists()
    assert (wiki_path / "archive").exists()
    for facet in EntityFacet:
        assert (wiki_path / facet.value).exists()
    assert (init_dir / ".knowledge.yml").exists()


def test_init_bare_idempotent(init_dir):
    """重复初始化不会报错。"""
    _make_init_config(init_dir)
    wiki1 = init_bare(init_dir)
    wiki2 = init_bare(init_dir)
    assert wiki1 == wiki2


def test_init_bare_preserves_existing_config(init_dir):
    """已有配置文件时不覆盖。"""
    _make_init_config(init_dir)
    config_path = init_dir / ".knowledge.yml"
    config_path.write_text("existing: true\n", encoding="utf-8")

    init_bare(init_dir)

    content = config_path.read_text(encoding="utf-8")
    assert content == "existing: true\n"


def test_init_from_backup(init_dir):
    """从备份恢复 wiki 文件。"""
    # 创建备份
    backup = init_dir / "backup" / "wiki" / "concept"
    backup.mkdir(parents=True)
    (backup / "test.md").write_text("# 测试\n内容", encoding="utf-8")

    _make_init_config(init_dir)
    wiki_path = init_from_backup(init_dir / "backup", target_dir=init_dir)

    assert (wiki_path / "concept" / "test.md").exists()
    assert (wiki_path / "concept" / "test.md").read_text(encoding="utf-8") == "# 测试\n内容"


def test_init_from_backup_creates_config(init_dir):
    """从备份恢复时自动创建配置文件。"""
    backup = init_dir / "backup" / "wiki" / "concept"
    backup.mkdir(parents=True)
    (backup / "test.md").write_text("# 测试", encoding="utf-8")

    _make_init_config(init_dir)
    init_from_backup(init_dir / "backup", target_dir=init_dir)

    assert (init_dir / ".knowledge.yml").exists()


def test_init_from_backup_merges(init_dir):
    """从备份恢复时合并而不覆盖已有文件。"""
    _make_init_config(init_dir)

    # 先创建已有的 wiki 文件
    wiki = init_dir / "wiki" / "concept"
    wiki.mkdir(parents=True)
    (wiki / "existing.md").write_text("已有内容", encoding="utf-8")
    (wiki / "test.md").write_text("旧内容", encoding="utf-8")

    # 备份中有新文件和同名文件
    backup = init_dir / "backup" / "wiki" / "concept"
    backup.mkdir(parents=True)
    (backup / "new.md").write_text("新文件", encoding="utf-8")
    (backup / "test.md").write_text("新内容", encoding="utf-8")

    init_from_backup(init_dir / "backup", target_dir=init_dir)

    # 新文件已复制
    assert (wiki / "new.md").exists()
    # 同名文件不覆盖
    assert (wiki / "test.md").read_text(encoding="utf-8") == "旧内容"
    # 已有文件保留
    assert (wiki / "existing.md").exists()


def test_init_from_backup_missing_wiki(init_dir):
    """备份目录无 wiki/ 时报错。"""
    _make_init_config(init_dir)
    bad_backup = init_dir / "bad_backup"
    bad_backup.mkdir()

    with pytest.raises(FileNotFoundError, match="has no wiki"):
        init_from_backup(bad_backup, target_dir=init_dir)
