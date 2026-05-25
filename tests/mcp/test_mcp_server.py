"""Tests for Linglong MCP Server tools."""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from linglong.core.config import LinglongConfig, get_config, set_config
from linglong.core.models import Entity, EntityFacet
from linglong.knowledge.store import KnowledgeStore
from linglong.mcp.tools import (
    execute_package,
    fetch_rss,
    generate_brief,
    get_template,
    list_entities,
    list_templates,
    read_entity,
    search_and_read,
    search_similar,
    search_web,
    search_wiki,
    update_entity,
    write_entity,
)


@pytest.fixture(autouse=True)
def reset_store():
    """Reset the global store singleton before each test."""
    from linglong.mcp import tools

    tools._store = None
    yield
    tools._store = None


@pytest.fixture
def temp_store():
    """Create a temporary knowledge store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = LinglongConfig(
            data_dir=Path(tmpdir) / "data",
            knowledge=LinglongConfig().knowledge.model_copy(
                update={
                    "wiki_path": Path(tmpdir) / "wiki",
                    "db_path": Path(tmpdir) / "knowledge.db",
                    "generate_embeddings": False,
                }
            ),
        )
        set_config(config)
        store = KnowledgeStore()
        # Inject into tools module so MCP tools use this store
        from linglong.mcp import tools

        tools._store = store
        yield store
        tools._store = None


# --- search_wiki ---


def test_search_wiki_returns_results(temp_store):
    temp_store.create(
        Entity(
            content="# Python 教程\n\n学习 Python 的最佳实践",
            facet=EntityFacet.CONCEPT,
            created_by="agent:test",
        )
    )
    temp_store.create(
        Entity(
            content="# JavaScript 指南\n\n前端开发基础",
            facet=EntityFacet.CONCEPT,
            created_by="agent:test",
        )
    )

    result = search_wiki("Python")
    data = json.loads(result)
    assert "error" not in data
    assert data["count"] == 1
    assert data["results"][0]["title"] == "Python 教程"


def test_search_wiki_with_facet_filter(temp_store):
    temp_store.create(
        Entity(
            content="# Python Concept\n\nPython concept content",
            facet=EntityFacet.CONCEPT,
            created_by="agent:test",
        )
    )
    temp_store.create(
        Entity(
            content="# JS Experience\n\nJavaScript experience content",
            facet=EntityFacet.EXPERIENCE,
            created_by="agent:test",
        )
    )

    result = search_wiki("Python", facet="concept")
    data = json.loads(result)
    assert data["count"] == 1
    assert data["results"][0]["facet"] == "concept"


# --- search_similar ---


def test_search_similar_with_mock_embedding(temp_store):
    from linglong.mcp import tools

    tools._store = None
    set_config(
        LinglongConfig(
            data_dir=get_config().data_dir,
            knowledge=LinglongConfig().knowledge.model_copy(
                update={
                    "wiki_path": temp_store.wiki_path,
                    "db_path": temp_store.db_path,
                    "generate_embeddings": True,
                }
            ),
        )
    )
    store = KnowledgeStore()
    tools._store = store

    def fake_generate(text):
        if "python" in text.lower():
            return [1.0] + [0.0] * 767
        return [0.0] * 767 + [1.0]

    with patch(
        "linglong.knowledge.embeddings.EmbeddingGenerator.generate",
        side_effect=fake_generate,
    ):
        store.create(
            Entity(
                content="# Python 教程\n\n学习 Python",
                facet=EntityFacet.CONCEPT,
                created_by="agent:test",
            )
        )
        store.create(
            Entity(
                content="# 烹饪食谱\n\n做菜方法",
                facet=EntityFacet.CONCEPT,
                created_by="agent:test",
            )
        )

    with patch(
        "linglong.knowledge.embeddings.EmbeddingGenerator.generate",
        return_value=[1.0] + [0.0] * 767,
    ):
        result = search_similar("python", limit=5)

    data = json.loads(result)
    assert "error" not in data
    assert data["count"] >= 1
    assert data["results"][0]["title"] == "Python 教程"


def test_search_similar_fallback_when_vector_unavailable(temp_store):
    result = search_similar("test", limit=5)
    data = json.loads(result)
    assert "error" not in data
    # When vector is unavailable, search_similar falls back to regular search
    # which returns empty for a fresh store - that's fine
    assert "results" in data


# --- read_entity ---


def test_read_entity_success(temp_store):
    created = temp_store.create(
        Entity(
            content="# 测试标题\n\n测试内容",
            facet=EntityFacet.CONCEPT,
            created_by="agent:test",
        )
    )

    result = read_entity(created.id)
    data = json.loads(result)
    assert "error" not in data
    assert data["id"] == created.id
    assert "测试标题" in data["content"]


def test_read_entity_not_found(temp_store):
    result = read_entity("nonexistent-id-12345")
    data = json.loads(result)
    assert "error" in data
    assert "not found" in data["error"].lower()


# --- write_entity ---


def test_write_entity_success(temp_store):
    result = write_entity(
        title="新实体标题",
        content="这是内容正文。",
        facet="concept",
    )
    data = json.loads(result)
    assert "error" not in data
    assert "id" in data
    assert data["facet"] == "concept"

    # Verify via store
    entity = temp_store.get(data["id"])
    assert entity is not None
    assert "# 新实体标题" in entity.content
    assert entity.created_by == "agent:mcp"


def test_write_entity_with_tags(temp_store):
    result = write_entity(
        title="带标签的实体",
        content="内容",
        facet="experience",
        tags=["python", "debug"],
    )
    data = json.loads(result)
    assert "error" not in data

    entity = temp_store.get(data["id"])
    assert entity.metadata.get("tags") == ["python", "debug"]


def test_write_entity_invalid_facet(temp_store):
    result = write_entity(
        title="标题",
        content="内容",
        facet="invalid_facet",
    )
    data = json.loads(result)
    assert "error" in data
    assert "Invalid facet" in data["error"]


# --- search_and_read ---


def test_search_and_read_returns_full_content(temp_store):
    temp_store.create(
        Entity(
            content="# Python 教程\n\n学习 Python 的最佳实践和高级技巧。",
            facet=EntityFacet.CONCEPT,
            created_by="agent:test",
        )
    )
    temp_store.create(
        Entity(
            content="# JavaScript 指南\n\n前端开发基础知识。",
            facet=EntityFacet.CONCEPT,
            created_by="agent:test",
        )
    )

    result = search_and_read("Python", limit=5)
    data = json.loads(result)
    assert "error" not in data
    assert data["count"] >= 1
    # Should return full content (under default 2000 limit), not just preview
    assert "学习 Python 的最佳实践" in data["results"][0]["content"]
    assert data["results"][0]["truncated"] is False


def test_search_and_read_truncates_long_content(temp_store):
    long_text = "A" * 5000
    temp_store.create(
        Entity(
            content=f"# 长文\n\n{long_text}",
            facet=EntityFacet.CONCEPT,
            created_by="agent:test",
        )
    )

    result = search_and_read("长文", limit=1, max_content_length=2000)
    data = json.loads(result)
    assert "error" not in data
    assert data["count"] == 1
    assert "... [truncated]" in data["results"][0]["content"]
    assert data["results"][0]["truncated"] is True
    # Verify it was actually truncated
    assert len(data["results"][0]["content"]) < 5000


def test_search_and_read_empty_results(temp_store):
    result = search_and_read("nonexistent-query-xyz")
    data = json.loads(result)
    assert "error" not in data
    assert data["count"] == 0


# --- update_entity ---


def test_update_entity_replace(temp_store):
    created = temp_store.create(
        Entity(
            content="# 原始标题\n\n原始内容",
            facet=EntityFacet.CONCEPT,
            created_by="agent:test",
        )
    )

    result = update_entity(created.id, "# 新标题\n\n新内容")
    data = json.loads(result)
    assert "error" not in data
    assert data["message"] == "Entity updated successfully"

    entity = temp_store.get(created.id)
    assert "新内容" in entity.content


def test_update_entity_append(temp_store):
    created = temp_store.create(
        Entity(
            content="# 原始标题\n\n原始内容",
            facet=EntityFacet.CONCEPT,
            created_by="agent:test",
        )
    )

    result = update_entity(created.id, "追加内容", append=True)
    data = json.loads(result)
    assert "error" not in data

    entity = temp_store.get(created.id)
    assert "原始内容" in entity.content
    assert "追加内容" in entity.content


def test_update_entity_not_found(temp_store):
    result = update_entity("nonexistent-id-12345", "新内容")
    data = json.loads(result)
    assert "error" in data
    assert "not found" in data["error"].lower()


# --- template ---


def test_list_templates_returns_available():
    result = list_templates()
    data = json.loads(result)
    assert "error" not in data
    assert data["count"] >= 1
    facets = [t["facet"] for t in data["templates"]]
    assert "concept" in facets


def test_get_template_concept():
    result = get_template("concept")
    data = json.loads(result)
    assert "error" not in data
    assert data["facet"] == "concept"
    assert "# [概念名称]" in data["template"]


def test_get_template_not_found():
    result = get_template("nonexistent_facet_xyz")
    data = json.loads(result)
    assert "error" in data
    assert "available_templates" in data


# --- list_entities ---


def test_list_entities_default(temp_store):
    temp_store.create(
        Entity(
            content="# 第一条",
            facet=EntityFacet.CONCEPT,
            created_by="agent:test",
        )
    )
    temp_store.create(
        Entity(
            content="# 第二条",
            facet=EntityFacet.CONCEPT,
            created_by="agent:test",
        )
    )

    result = list_entities(limit=10)
    data = json.loads(result)
    assert "error" not in data
    assert data["count"] == 2


def test_list_entities_with_facet(temp_store):
    temp_store.create(
        Entity(
            content="# 概念",
            facet=EntityFacet.CONCEPT,
            created_by="agent:test",
        )
    )
    temp_store.create(
        Entity(
            content="# 经验",
            facet=EntityFacet.EXPERIENCE,
            created_by="agent:test",
        )
    )

    result = list_entities(facet="experience", limit=10)
    data = json.loads(result)
    assert data["count"] == 1
    assert data["results"][0]["facet"] == "experience"


# --- fetch_rss ---


def test_fetch_rss_returns_previews(temp_store):
    rss_xml = """<?xml version="1.0"?>
    <rss version="2.0">
      <channel>
        <title>Test Feed</title>
        <item>
          <title>Test Article</title>
          <link>https://example.com/article1</link>
          <description>Article content here</description>
        </item>
      </channel>
    </rss>"""

    mock_response = MagicMock()
    mock_response.text = rss_xml
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = fetch_rss("https://example.com/feed.xml", name="test-feed")
        data = json.loads(result)

    assert "error" not in data
    assert data["count"] == 1
    assert data["results"][0]["title"] == "Test Article"


def test_fetch_rss_handles_error(temp_store):
    with patch("asyncio.run", side_effect=Exception("Connection failed")):
        result = fetch_rss("https://invalid.example/feed.xml")
        data = json.loads(result)

    assert "error" in data


# --- generate_brief ---


def test_generate_brief_returns_output(temp_store):
    config = get_config()
    config.ingest.packages = [{"name": "ai-morning-brief", "topic": "AI 早报"}]
    set_config(config)

    with patch("linglong.ingest.agent.IngestAgent") as mock_agent_cls, \
         patch("linglong.ingest.brief_history.BriefHistory") as mock_bh_cls, \
         patch("linglong.ingest.feedback.FeedbackStore") as mock_fs_cls, \
         patch("asyncio.run", return_value="# AI 早报\n\nContent"):
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value="# AI 早报\n\nContent")
        mock_agent_cls.return_value = mock_agent

        result = generate_brief()
        data = json.loads(result)

    assert "error" not in data
    assert data["package"] == "ai-morning-brief"
    assert "output" in data


def test_generate_brief_no_packages(temp_store):
    config = get_config()
    config.ingest.packages = []
    set_config(config)

    result = generate_brief()
    data = json.loads(result)

    assert "error" in data
    assert "No packages" in data["error"]


def test_generate_brief_handles_error(temp_store):
    config = get_config()
    config.ingest.packages = [{"name": "test", "topic": "test"}]
    set_config(config)

    with patch("linglong.ingest.agent.IngestAgent", side_effect=Exception("Agent failed")):
        result = generate_brief()
        data = json.loads(result)

    assert "error" in data


# --- search_web ---


def test_search_web_returns_results(temp_store):
    mock_data = {
        "results": [
            {"title": "AI News", "url": "https://example.com", "content": "Summary", "engine": "google"},
        ]
    }
    mock_response = MagicMock()
    mock_response.json.return_value = mock_data
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = search_web("AI news", max_results=5)
        data = json.loads(result)

    assert "error" not in data
    assert data["count"] == 1
    assert data["results"][0]["title"] == "AI News"


def test_search_web_handles_error(temp_store):
    with patch("asyncio.run", side_effect=Exception("Connection failed")):
        result = search_web("test query")
        data = json.loads(result)

    assert "error" in data


def test_execute_package_returns_results(temp_store):
    with patch("linglong.ingest.package.SourcePackage") as mock_pkg_cls, \
         patch("linglong.ingest.agent.IngestAgent") as mock_agent_cls, \
         patch("linglong.ingest.brief_history.BriefHistory") as mock_bh_cls, \
         patch("linglong.ingest.feedback.FeedbackStore") as mock_fs_cls, \
         patch("asyncio.run", return_value="# AI 早报\n\nContent"):
        mock_pkg = MagicMock()
        mock_pkg.name = "test-package"
        mock_pkg_cls.from_yaml.return_value = mock_pkg

        result = execute_package("/path/to/package.yaml")
        data = json.loads(result)

    assert "error" not in data
    assert data["package"] == "test-package"
    assert "output" in data


def test_execute_package_handles_error(temp_store):
    with patch("linglong.ingest.package.SourcePackage") as mock_cls:
        mock_cls.from_yaml.side_effect = FileNotFoundError("Package not found")

        result = execute_package("/nonexistent/package.yaml")
        data = json.loads(result)

    assert "error" in data
