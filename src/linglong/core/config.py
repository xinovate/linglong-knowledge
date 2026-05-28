"""Configuration management for Linglong Knowledge."""

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_YAML_SEARCH_PATHS = [
    Path(".knowledge.yml"),
    _PROJECT_ROOT / ".knowledge.yml",
    Path.home() / ".knowledge" / "config.yml",
    # Backward compat: fall back to old filenames
    Path(".knowledge.yml"),
    _PROJECT_ROOT / ".knowledge.yml",
    Path.home() / ".linglong" / "config.yaml",
]

_KNOWLEDGE_HOME = Path.home() / "knowledge"


class KnowledgeConfig(BaseSettings):
    """Knowledge module configuration."""

    model_config = SettingsConfigDict(env_prefix="KB_KNOWLEDGE_")

    wiki_path: Path = Field(
        default=_KNOWLEDGE_HOME / "wiki", description="Path to wiki directory"
    )
    db_path: Path = Field(
        default=_KNOWLEDGE_HOME / "db" / "knowledge.db",
        description="SQLite database path",
    )
    vector_enabled: bool = Field(default=True, description="Enable vector search")
    vector_dimensions: int = Field(default=768, description="Embedding dimensions")
    embedding_url: str = Field(
        default="http://localhost:7997", description="Embedding service URL"
    )
    embedding_model: str = Field(
        default="nomic-embed-text-v1.5", description="Embedding model name"
    )
    embedding_api_key: str | None = Field(
        default=None, description="Optional API key for embedding service"
    )
    generate_embeddings: bool = Field(
        default=True, description="Auto-generate embeddings on entity create/update"
    )

    write_mode: str = Field(default="confirm", description="Write mode: confirm or auto")
    search_mode: str = Field(default="on_demand", description="Search mode: on_demand or deep")
    auto_index: bool = Field(default=True, description="Auto-update index on write")
    max_versions: int = Field(default=10, description="Max version history per entity")

    lock_timeout: int = Field(default=5, description="File lock timeout in seconds")
    db_mode: str = Field(default="wal", description="SQLite journal mode")
    auto_lint: bool = Field(default=False, description="Auto-run lint after write operations")
    lint_schedule: str | None = Field(
        default=None, description="Cron expression for scheduled lint, e.g. '0 2 * * *'"
    )

    review_high_confidence_threshold: float = Field(
        default=0.9, description="High confidence threshold for auto-confirm"
    )
    review_low_confidence_threshold: float = Field(
        default=0.6, description="Low confidence threshold for flagging review"
    )
    review_min_content_length: int = Field(
        default=50, description="Minimum content length to avoid flagging"
    )
    review_trusted_sources: list[str] = Field(
        default_factory=lambda: ["openclaw", "claude-code", "codex"],
        description="Trusted source names for auto-confirm",
    )
    review_sensitive_categories: list[str] = Field(
        default_factory=lambda: ["personal", "financial", "health", "password", "secret"],
        description="Sensitive content categories to flag",
    )

    sync_confidence: float = Field(
        default=0.95, description="Default confidence for synced entities"
    )

    openclaw_wiki_path: Path | None = Field(
        default=None, description="Path to OpenClaw wiki directory"
    )
    claude_memory_path: Path | None = Field(
        default=None, description="Path to Claude Code memory directory"
    )
    codex_path: Path | None = Field(
        default=None, description="Path to Codex CLI data directory"
    )


class MCPConfig(BaseModel):
    """MCP server configuration."""

    transport: str = Field(
        default="stdio",
        description="Transport protocol: stdio | sse | streamable-http",
    )
    host: str = Field(
        default="127.0.0.1",
        description="HTTP listen host (streamable-http / sse mode)",
    )
    port: int = Field(
        default=9900,
        description="HTTP listen port (streamable-http / sse mode)",
    )
    auth_token: str | None = Field(
        default=None,
        description="Bearer token for authentication (None = no auth)",
    )
    enabled_modules: list[str] = Field(
        default_factory=lambda: ["knowledge"],
        description="Which module tool groups to expose: knowledge",
    )
    allowed_hosts: list[str] = Field(
        default_factory=list,
        description="Allowed Host header values for DNS rebinding protection (HTTP mode)",
    )
    redis_url: str = Field(
        default="",
        description="Redis URL for dynamic token auth (e.g. redis://:password@127.0.0.1:6379/0)",
    )


class LinglongConfig(BaseSettings):
    """Main configuration."""

    model_config = SettingsConfigDict(
        env_prefix="KB_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    knowledge: KnowledgeConfig = Field(default_factory=KnowledgeConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)

    log_file: Path | None = Field(
        default=Path.home() / "linglong" / "logs" / "knowledge.log",
        description="Log file path (None to disable file logging)",
    )

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.knowledge.wiki_path.mkdir(parents=True, exist_ok=True)
        self.knowledge.db_path.parent.mkdir(parents=True, exist_ok=True)
        if self.log_file:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
        (_KNOWLEDGE_HOME / "state").mkdir(parents=True, exist_ok=True)


_config: LinglongConfig | None = None


def _find_yaml_config() -> Path | None:
    """Search for config file (.knowledge.yml preferred, .knowledge.yml fallback)."""
    for p in _YAML_SEARCH_PATHS:
        if p.exists():
            return p
    return None


def _interpolate_env(data: Any) -> Any:
    """Recursively interpolate ${ENV_VAR} references in config values."""
    if isinstance(data, str):
        if data.startswith("${") and data.endswith("}"):
            env_var = data[2:-1]
            value = os.environ.get(env_var, "")
            if not value:
                logger.warning("Environment variable %s not set", env_var)
            return value
        return data
    if isinstance(data, dict):
        return {k: _interpolate_env(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_interpolate_env(v) for v in data]
    return data


def _load_yaml_to_config(yaml_path: Path) -> LinglongConfig:
    """Construct LinglongConfig from a YAML file."""
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    data = _interpolate_env(data)
    return LinglongConfig(**data)


def get_config() -> LinglongConfig:
    """Get or create global configuration."""
    global _config
    if _config is None:
        yaml_path = _find_yaml_config()
        if yaml_path:
            logger.info("Loading config from: %s", yaml_path)
            _config = _load_yaml_to_config(yaml_path)
        else:
            _config = LinglongConfig()
        _config.ensure_directories()
    return _config


def set_config(config: LinglongConfig) -> None:
    """Set global configuration (useful for testing)."""
    global _config
    _config = config
