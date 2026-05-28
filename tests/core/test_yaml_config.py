"""Tests for YAML configuration loading."""

import tempfile
from pathlib import Path

import pytest
import yaml

from linglong.core.config import (
    LinglongConfig,
    _find_yaml_config,
    _load_yaml_to_config,
    get_config,
    set_config,
)


@pytest.fixture(autouse=True)
def reset_config():
    """Reset global config before each test."""
    set_config(None)
    yield
    set_config(None)


class TestFindYamlConfig:
    """Tests for _find_yaml_config()."""

    def test_finds_cwd_config(self, tmp_path, monkeypatch):
        """Finds .linglong.yaml in current directory."""
        yaml_file = tmp_path / ".linglong.yaml"
        yaml_file.write_text("debug: true\n")
        monkeypatch.chdir(tmp_path)

        result = _find_yaml_config()
        assert result is not None
        assert result.exists()

    def test_returns_none_when_missing(self, tmp_path, monkeypatch):
        """Returns None when no config file exists."""
        monkeypatch.chdir(tmp_path)
        result = _find_yaml_config()
        assert result is None


class TestLoadYamlToConfig:
    """Tests for _load_yaml_to_config()."""

    def test_loads_basic_yaml(self, tmp_path):
        """Loads simple YAML values."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml.dump({"debug": True, "log_level": "DEBUG"}))

        config = _load_yaml_to_config(yaml_file)
        assert config.debug is True
        assert config.log_level == "DEBUG"

    def test_loads_nested_config(self, tmp_path):
        """Loads nested knowledge config."""
        yaml_file = tmp_path / "config.yaml"
        data = {
            "knowledge": {"vector_enabled": False, "vector_dimensions": 384},
        }
        yaml_file.write_text(yaml.dump(data))

        config = _load_yaml_to_config(yaml_file)
        assert config.knowledge.vector_enabled is False
        assert config.knowledge.vector_dimensions == 384

    def test_missing_fields_use_defaults(self, tmp_path):
        """YAML with partial config uses defaults for missing fields."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml.dump({"debug": True}))

        config = _load_yaml_to_config(yaml_file)
        assert config.debug is True
        assert config.log_level == "INFO"
        assert config.knowledge.vector_enabled is True

    def test_empty_yaml(self, tmp_path):
        """Empty YAML file creates config with all defaults."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("")

        config = _load_yaml_to_config(yaml_file)
        assert config.debug is False
        assert config.log_level == "INFO"

    def test_ignores_unknown_sections(self, tmp_path):
        """Extra YAML sections (from old config) are silently ignored."""
        yaml_file = tmp_path / "config.yaml"
        data = {
            "debug": True,
            "ingest": {"searxng_url": "http://localhost:8088"},
            "reviewer": {"passing_score": 7.0},
        }
        yaml_file.write_text(yaml.dump(data))

        config = _load_yaml_to_config(yaml_file)
        assert config.debug is True


class TestGetYamlConfig:
    """Tests for get_config() with YAML loading."""

    def test_get_config_without_yaml(self, tmp_path, monkeypatch):
        """get_config() works when no YAML file exists."""
        monkeypatch.chdir(tmp_path)
        config = get_config()
        assert isinstance(config, LinglongConfig)

    def test_get_config_with_yaml(self, tmp_path, monkeypatch):
        """get_config() loads from YAML when present."""
        monkeypatch.chdir(tmp_path)
        yaml_file = tmp_path / ".linglong.yaml"
        yaml_file.write_text(yaml.dump({"debug": True, "log_level": "DEBUG"}))

        config = get_config()
        assert config.debug is True
        assert config.log_level == "DEBUG"

    def test_get_config_caches_instance(self, tmp_path, monkeypatch):
        """get_config() returns same instance on repeated calls."""
        monkeypatch.chdir(tmp_path)
        yaml_file = tmp_path / ".linglong.yaml"
        yaml_file.write_text("debug: true\n")

        config1 = get_config()
        config2 = get_config()
        assert config1 is config2
