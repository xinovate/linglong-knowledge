"""Tests for core configuration module."""

import tempfile
from pathlib import Path

import pytest

from linglong.core.config import (
    ComposerConfig,
    DispatchConfig,
    IngestConfig,
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
        assert isinstance(config.ingest, IngestConfig)
        assert isinstance(config.composer, ComposerConfig)
        assert isinstance(config.dispatch, DispatchConfig)

    def test_ensure_directories(self):
        """Test ensure_directories creates required paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LinglongConfig(data_dir=Path(tmpdir) / "data")
            config.ensure_directories()

            assert config.data_dir.exists()
            assert config.knowledge.wiki_path.exists()
            assert config.composer.drafts_dir.exists()

    def test_composer_defaults(self):
        """Test ComposerConfig defaults."""
        config = ComposerConfig()
        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4"
        assert config.llm_temperature == 0.7
        assert config.distiller_use_llm is False
        assert config.template_name == "blog"

    def test_knowledge_defaults(self):
        """Test KnowledgeConfig defaults."""
        config = KnowledgeConfig()
        assert config.wiki_path == Path("./wiki")
        assert config.db_path == Path("./knowledge.db")
        assert config.vector_enabled is True
        assert config.vector_dimensions == 768

    def test_ingest_defaults(self):
        """Test IngestConfig defaults."""
        config = IngestConfig()
        assert config.rss_sources == []
        assert config.fetch_interval_minutes == 30
        assert config.max_items_per_source == 50
        assert config.package_paths == ["./data/packages"]
        assert config.verification_enabled is True
        assert config.default_verification["cross_reference_min"] == 1
        assert config.default_verification["max_age_days"] == 7

    def test_dispatch_defaults(self):
        """Test DispatchConfig defaults."""
        config = DispatchConfig()
        assert config.enabled is True
        assert config.default_publisher == "hexo"
        assert len(config.publishers) == 2
        assert config.publishers[0]["name"] == "hexo"


class TestGlobalConfig:
    """Tests for global config singleton."""

    def test_get_config_creates_singleton(self):
        """Test get_config returns the same instance."""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2

    def test_set_config_overrides(self):
        """Test set_config replaces global config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom = LinglongConfig(data_dir=Path(tmpdir) / "custom")
            set_config(custom)

            assert get_config() is custom
            assert get_config().data_dir == Path(tmpdir) / "custom"

    def test_set_config_none_resets(self):
        """Test setting config to None allows fresh creation."""
        config1 = get_config()
        set_config(None)
        config2 = get_config()
        assert config1 is not config2
