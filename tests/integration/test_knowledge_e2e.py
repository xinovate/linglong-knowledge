"""End-to-end test: init -> write -> search -> update -> lint -> archive."""

import tempfile
from pathlib import Path

from linglong.core.config import KnowledgeConfig, LinglongConfig, set_config
from linglong.core.models import Entity, EntityFacet, EntityStatus
from linglong.knowledge.init import init_bare
from linglong.knowledge.indexer import IndexGenerator
from linglong.knowledge.lint import LintEngine
from linglong.knowledge.store import KnowledgeStore


def test_full_knowledge_lifecycle():
    """Complete knowledge base lifecycle test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        base = Path(tmpdir) / "linglong"

        # 1. init
        wiki_path = init_bare(target_dir=base)
        assert wiki_path.exists()
        assert (wiki_path / "archive").exists()
        assert (wiki_path / "concept").exists()
        assert (wiki_path / "project").exists()

        # Set up config for KnowledgeStore
        knowledge_cfg = KnowledgeConfig(
            wiki_path=wiki_path,
            db_path=base / "db" / "knowledge.db",
            generate_embeddings=False,
        )
        config = LinglongConfig(
            data_dir=base / "data",
            knowledge=knowledge_cfg,
        )
        config.ensure_directories()
        set_config(config)

        store = KnowledgeStore()

        # 2. write -- create 3 entities
        e1 = store.create(Entity(
            content="# 微服务架构\n\n参考 [[OpenClaw]] 的设计",
            facet=EntityFacet.CONCEPT,
            created_by="agent:claude",
            confidence=0.9,
        ))
        assert e1.id is not None
        assert e1.current_version == 1

        e2 = store.create(Entity(
            content="# OpenClaw\n\n跨 Agent 知识同步工具",
            facet=EntityFacet.CONCEPT,
            created_by="agent:claude",
            confidence=0.95,
        ))
        assert e2.id is not None

        e3 = store.create(Entity(
            content="# sqlite-vec 踩坑\n\n维度不匹配问题",
            facet=EntityFacet.EXPERIENCE,
            created_by="agent:openclaw",
        ))
        assert e3.id is not None

        # 3. search -- FTS5 full-text search
        # Note: FTS5 default tokenizer treats CJK sequences as single tokens,
        # so "微服务架构" (the full whitespace-delimited token) is searchable,
        # but partial substrings like "微服务" are not.
        results = store.search(query="微服务架构")
        assert len(results) == 1
        assert results[0].facet == EntityFacet.CONCEPT

        # search -- filter by facet
        results_facet = store.search(facet=EntityFacet.EXPERIENCE)
        assert len(results_facet) == 1
        assert results_facet[0].id == e3.id

        # search -- no match
        results_empty = store.search(query="不存在的关键词xyz")
        assert len(results_empty) == 0

        # 4. read
        retrieved = store.get(e1.id)
        assert retrieved is not None
        assert "微服务" in retrieved.content
        assert retrieved.facet == EntityFacet.CONCEPT

        # read non-existent
        assert store.get("nonexistent-id") is None

        # 5. update (append -- no new version)
        e3.metadata["update_mode"] = "append"
        e3.content = e3.content + "\n\n## 解决方案\n\n校验维度。"
        updated = store.update(e3)
        assert updated.current_version == 1  # append does not bump version
        assert "解决方案" in updated.content

        # 6. update (replace -- new version)
        e1.content = "# 微服务架构 v2\n\n更新后的内容"
        e1_updated = store.update(e1)
        assert e1_updated.current_version == 2
        assert len(e1_updated.versions) == 1
        assert e1_updated.versions[0]["version"] == 1

        # 7. index -- generate index files
        gen = IndexGenerator(wiki_path)
        stats = gen.generate_all()
        assert "index.md" in stats
        assert stats["index.md"] > 0
        index_content = (wiki_path / "index.md").read_text()
        assert "微服务" in index_content or "Concept" in index_content

        # 8. lint -- health checks
        lint_engine = LintEngine(store)
        lint_results = lint_engine.run_all(stale_days=90)

        # OpenClaw entity exists, so [[OpenClaw]] wikilink in e1 should resolve
        wikilink_errors = [r for r in lint_results if r.rule == "wikilinks"]
        assert len(wikilink_errors) == 0, (
            f"Unexpected wikilink errors: {[r.message for r in wikilink_errors]}"
        )

        # 9. archive
        archived = store.archive(e3.id)
        assert archived.archived_at is not None

        # Archived entity excluded from default search
        results_after = store.search(query="sqlite-vec")
        assert len(results_after) == 0

        # include_archived=True includes it
        results_with_archived = store.search(query="sqlite-vec", include_archived=True)
        assert len(results_with_archived) == 1

        # Archived entity still readable via get
        archived_get = store.get(e3.id)
        assert archived_get is not None
        assert archived_get.archived_at is not None

        # 10. final count -- only non-archived entities remain
        remaining = store.search(limit=1000)
        assert len(remaining) == 2  # e1 + e2
