"""Tests for Linglong CLI."""

import pytest

from linglong.cli import main


def test_cli_help():
    """CLI should show help without error."""
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


def test_cli_ingest_no_packages(tmp_path, monkeypatch):
    """ingest with no packages should warn and exit 1."""
    from linglong.core.config import LinglongConfig, set_config

    config = LinglongConfig(
        data_dir=tmp_path / "data",
        ingest=LinglongConfig().ingest.model_copy(
            update={"package_paths": [str(tmp_path / "nonexistent")]}
        ),
    )
    set_config(config)

    code = main(["ingest"])
    assert code == 1


def test_cli_compose_dry_run(tmp_path, monkeypatch):
    """compose --dry-run should succeed with empty store."""
    from linglong.core.config import LinglongConfig, set_config

    config = LinglongConfig(
        data_dir=tmp_path / "data",
        knowledge=LinglongConfig().knowledge.model_copy(
            update={
                "wiki_path": tmp_path / "wiki",
                "db_path": tmp_path / "knowledge.db",
            }
        ),
        composer=LinglongConfig().composer.model_copy(
            update={"drafts_dir": tmp_path / "drafts"}
        ),
    )
    set_config(config)

    code = main(["compose", "--dry-run"])
    assert code == 0


# ---------------------------------------------------------------------------
# 知识库子命令测试
# ---------------------------------------------------------------------------


def _make_config(tmp_path):
    """创建测试用 LinglongConfig，禁用 embedding。"""
    from linglong.core.config import LinglongConfig, set_config

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


def test_write_creates_entity(tmp_path):
    """linglong write 创建知识条目并输出 ID。"""
    _make_config(tmp_path)

    code = main([
        "write",
        "--facet", "concept",
        "--title", "测试知识",
        "--content", "这是测试内容",
        "--yes",
    ])
    assert code == 0


def test_write_from_file(tmp_path):
    """linglong write --from-file 从文件读取内容。"""
    _make_config(tmp_path)

    content_file = tmp_path / "note.md"
    content_file.write_text("从文件读取的内容", encoding="utf-8")

    code = main([
        "write",
        "--facet", "experience",
        "--title", "文件测试",
        "--from-file", str(content_file),
        "--yes",
    ])
    assert code == 0


def test_write_no_content_fails(tmp_path):
    """linglong write 缺少内容应返回错误。"""
    _make_config(tmp_path)

    code = main([
        "write",
        "--facet", "concept",
        "--title", "空内容",
        "--yes",
    ])
    assert code == 1


def test_read_entity(tmp_path):
    """linglong read 读取已创建的条目。"""
    _make_config(tmp_path)

    # 先写入
    code = main([
        "write",
        "--facet", "concept",
        "--title", "读取测试",
        "--content", "用于测试读取",
        "--yes",
    ])
    assert code == 0

    # 搜索获取 ID
    from linglong.knowledge.store import KnowledgeStore
    store = KnowledgeStore()
    results = store.search(query="读取测试", limit=1)
    assert len(results) == 1
    entity_id = results[0].id

    # 读取
    code = main(["read", entity_id])
    assert code == 0


def test_read_json_format(tmp_path, capsys):
    """linglong read --format json 输出 JSON。"""
    _make_config(tmp_path)

    code = main([
        "write",
        "--facet", "concept",
        "--title", "JSON 测试",
        "--content", "JSON 输出",
        "--yes",
    ])
    assert code == 0

    from linglong.knowledge.store import KnowledgeStore
    store = KnowledgeStore()
    results = store.search(query="JSON 测试", limit=1)
    entity_id = results[0].id

    # 刷新 write 阶段的输出
    capsys.readouterr()

    code = main(["read", entity_id, "--format", "json"])
    assert code == 0

    import json
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["facet"] == "concept"


def test_search_no_results(tmp_path):
    """linglong search 无结果时不报错。"""
    _make_config(tmp_path)

    code = main(["search", "不存在的关键词"])
    assert code == 0


def test_search_with_entities(tmp_path, capsys):
    """linglong search 能搜到已写入的条目。"""
    _make_config(tmp_path)

    main([
        "write",
        "--facet", "methodology",
        "--title", "搜索方法论",
        "--content", "这是搜索方法论的内容",
        "--yes",
    ])

    code = main(["search", "搜索方法论"])
    assert code == 0
    captured = capsys.readouterr()
    assert "搜索方法论" in captured.out


def test_update_append(tmp_path):
    """linglong update --append 追加内容。"""
    _make_config(tmp_path)

    main([
        "write",
        "--facet", "concept",
        "--title", "更新测试",
        "--content", "原始内容",
        "--yes",
    ])

    from linglong.knowledge.store import KnowledgeStore
    store = KnowledgeStore()
    results = store.search(query="更新测试", limit=1)
    entity_id = results[0].id

    code = main(["update", entity_id, "--append", "追加的内容"])
    assert code == 0


def test_update_metadata(tmp_path):
    """linglong update --metadata 更新元数据。"""
    _make_config(tmp_path)

    main([
        "write",
        "--facet", "concept",
        "--title", "元数据测试",
        "--content", "测试元数据更新",
        "--yes",
    ])

    from linglong.knowledge.store import KnowledgeStore
    store = KnowledgeStore()
    results = store.search(query="元数据测试", limit=1)
    entity_id = results[0].id

    code = main(["update", entity_id, "--metadata", "priority=high", "tag=test"])
    assert code == 0


def test_review_list_pending(tmp_path):
    """linglong review --list-pending 列出待审核条目。"""
    _make_config(tmp_path)

    code = main(["review", "--list-pending"])
    assert code == 0


def test_archive_nonexistent(tmp_path):
    """linglong archive 不存在的 ID 应报错。"""
    _make_config(tmp_path)

    code = main(["archive", "nonexistent-id"])
    assert code == 1


def test_archive_no_args(tmp_path):
    """linglong archive 无参数应提示错误。"""
    _make_config(tmp_path)

    code = main(["archive"])
    assert code == 1


# ---------------------------------------------------------------------------
# lint / index / stats 子命令测试
# ---------------------------------------------------------------------------


def test_lint_clean_kb(tmp_path):
    """空知识库 lint 无问题。"""
    _make_config(tmp_path)
    result = main(["lint"])
    assert result == 0


def test_index_generates_files(tmp_path):
    """index 命令生成索引文件。"""
    from linglong.core.models import Entity, EntityFacet
    from linglong.knowledge.store import KnowledgeStore

    _make_config(tmp_path)
    store = KnowledgeStore()
    store.create(Entity(
        content="# 测试\n\n内容",
        facet=EntityFacet.CONCEPT,
        created_by="agent:test",
    ))
    result = main(["index"])
    assert result == 0


def test_stats_shows_count(tmp_path):
    """stats 命令输出统计。"""
    from linglong.core.models import Entity, EntityFacet
    from linglong.knowledge.store import KnowledgeStore

    _make_config(tmp_path)
    store = KnowledgeStore()
    store.create(Entity(
        content="# 测试\n\n内容",
        facet=EntityFacet.CONCEPT,
        created_by="agent:test",
    ))
    result = main(["stats"])
    assert result == 0


def test_init_bare(tmp_path):
    """init 命令创建基本目录结构。"""
    _make_config(tmp_path)
    result = main(["init"])
    assert result == 0


def test_migrate_dry_run(tmp_path):
    """migrate --dry-run 预览模式。"""
    _make_config(tmp_path)

    # 创建源目录和测试文件
    src = tmp_path / "source_wiki"
    src.mkdir()
    (src / "test.md").write_text("# 测试迁移\n\n内容")
    (src / "sub").mkdir()
    (src / "sub" / "nested.md").write_text("# 嵌套文件\n\n更多内容")

    result = main(["migrate", "--from", str(src), "--dry-run"])
    assert result == 0


def test_migrate_creates_entities(tmp_path):
    """migrate 实际迁移文件。"""
    _make_config(tmp_path)
    from linglong.core.config import get_config
    config = get_config()

    src = tmp_path / "source_wiki"
    src.mkdir()
    (src / "article.md").write_text("# 迁移文章\n\n内容")

    result = main(["migrate", "--from", str(src)])
    assert result == 0

    # 验证已创建
    from linglong.knowledge.store import KnowledgeStore
    store = KnowledgeStore()
    results = store.search(query="迁移文章")
    assert len(results) == 1


def test_migrate_nonexistent_source(tmp_path):
    """migrate 不存在的源目录报错。"""
    _make_config(tmp_path)

    result = main(["migrate", "--from", "/nonexistent/path"])
    assert result == 1
