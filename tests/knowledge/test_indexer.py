"""IndexGenerator 索引生成器测试。"""

import tempfile
from pathlib import Path

import pytest

from linglong.core.config import LinglongConfig, set_config
from linglong.core.models import Entity, EntityFacet
from linglong.knowledge.indexer import IndexGenerator
from linglong.knowledge.store import KnowledgeStore


@pytest.fixture
def index_setup():
    """创建临时知识库并写入测试数据。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        wiki_path = Path(tmpdir) / "wiki"
        config = LinglongConfig(
            data_dir=Path(tmpdir) / "data",
            knowledge=LinglongConfig().knowledge.model_copy(update={
                "wiki_path": wiki_path,
                "db_path": Path(tmpdir) / "knowledge.db",
                "generate_embeddings": False,
            }),
        )
        set_config(config)

        store = KnowledgeStore()
        store.create(Entity(
            content="# 概念A\n\n概念内容",
            facet=EntityFacet.CONCEPT,
            created_by="agent:claude",
        ))
        store.create(Entity(
            content="# 概念B\n\n另一个概念",
            facet=EntityFacet.CONCEPT,
            created_by="agent:claude",
        ))
        store.create(Entity(
            content="# 踩坑记录\n\n经验内容",
            facet=EntityFacet.EXPERIENCE,
            created_by="agent:claude",
        ))

        yield wiki_path, store


def test_generate_all_creates_index_files(index_setup):
    """generate_all 生成 index.md 和 7 个分面索引。"""
    wiki_path, _ = index_setup
    gen = IndexGenerator(wiki_path)
    stats = gen.generate_all()

    assert "index.md" in stats
    assert stats["index.md"] == 3  # 2 concept + 1 experience
    assert (wiki_path / "index.md").exists()
    assert (wiki_path / "index-concept.md").exists()
    assert (wiki_path / "index-experience.md").exists()


def test_main_index_content(index_setup):
    """主索引包含所有分类的条目。"""
    wiki_path, _ = index_setup
    gen = IndexGenerator(wiki_path)
    gen.generate_all()

    content = (wiki_path / "index.md").read_text()
    assert "概念A" in content
    assert "概念B" in content
    assert "踩坑记录" in content


def test_facet_index_content(index_setup):
    """分面索引只包含对应分类的条目。"""
    wiki_path, _ = index_setup
    gen = IndexGenerator(wiki_path)
    gen.generate_all()

    concept_content = (wiki_path / "index-concept.md").read_text()
    assert "概念A" in concept_content
    assert "概念B" in concept_content
    assert "踩坑记录" not in concept_content

    experience_content = (wiki_path / "index-experience.md").read_text()
    assert "踩坑记录" in experience_content
    assert "概念A" not in experience_content


def test_generate_single_facet(index_setup):
    """generate_facet 只生成指定分面的索引。"""
    wiki_path, _ = index_setup
    gen = IndexGenerator(wiki_path)
    count = gen.generate_facet(EntityFacet.CONCEPT)

    assert count == 2
    assert (wiki_path / "index-concept.md").exists()
    assert not (wiki_path / "index.md").exists()  # 主索引未生成
