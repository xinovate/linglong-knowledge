"""Tests for core configuration module."""

import tempfile
from pathlib import Path

import pytest

from linglong.core.config import (
    KnowledgeConfig,
    LinglongConfig,
    get_config,
    set_config,
)


@pytest.fixture(autouse=True)
def reset_config():
    """Reset global config before each test."""
    set_config(None)
    yield
    set_config(None)


class TestLinglongConfig:
    """Tests for LinglongConfig."""

    def test_default_creation(self):
        """Test LinglongConfig can be created with defaults."""
        config = LinglongConfig()
        assert config.debug is False
        assert config.log_level == "INFO"
        assert isinstance(config.knowledge, KnowledgeConfig)

    def test_ensure_directories(self):
        """Test ensure_directories creates required paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LinglongConfig(data_dir=Path(tmpdir) / "data")
            config.ensure_directories()

            assert config.data_dir.exists()
            assert config.knowledge.wiki_path.exists()

    def test_knowledge_defaults(self):
        """Test KnowledgeConfig defaults."""
        config = KnowledgeConfig()
        assert config.wiki_path == Path.home() / "knowledge" / "wiki"
        assert config.db_path == Path.home() / "knowledge" / "db" / "knowledge.db"
        assert config.vector_enabled is True
        assert config.vector_dimensions == 768


class TestGlobalConfig:
    """Tests for global config singleton."""

    def test_get_config_creates_singleton(self):
        """Test get_config returns the same instance."""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2
