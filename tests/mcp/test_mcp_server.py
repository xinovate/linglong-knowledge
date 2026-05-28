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
    get_template,
    list_entities,
    list_templates,
    read_entity,
    search_and_read,
    search_similar,
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
