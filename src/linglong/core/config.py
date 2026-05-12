"""Configuration management for Linglong."""

from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ComposerConfig(BaseSettings):
    """Composer module configuration."""

    model_config = SettingsConfigDict(env_prefix="LL_COMPOSER_")

    # LLM settings
    llm_provider: str = Field(default="openai", description="LLM provider")
    llm_model: str = Field(default="gpt-4", description="LLM model name")
    llm_api_key: str | None = Field(default=None, description="LLM API key")
    llm_base_url: str | None = Field(default=None, description="LLM base URL")
    llm_temperature: float = Field(default=0.7, description="LLM temperature")
    llm_max_tokens: int = Field(default=4096, description="LLM max tokens")

    # Distiller settings
    distiller_use_llm: bool = Field(default=False, description="Use LLM distiller")
    distiller_theme_threshold: float = Field(
        default=0.7, description="Theme grouping similarity threshold"
    )
    distiller_max_themes: int = Field(default=5, description="Max themes per aggregation")

    # Asset settings
    assets_excerpt_length: int = Field(default=200, description="Excerpt length")
    assets_cover_enabled: bool = Field(default=False, description="Enable cover generation")

    # Template settings
    template_name: str = Field(default="blog", description="Default template")

    # Draft settings
    drafts_dir: Path = Field(default=Path("./data/drafts"), description="Drafts directory")


class KnowledgeConfig(BaseSettings):
    """Knowledge module configuration."""

    model_config = SettingsConfigDict(env_prefix="LL_KNOWLEDGE_")

    wiki_path: Path = Field(default=Path("./wiki"), description="Path to wiki directory")
    db_path: Path = Field(default=Path("./knowledge.db"), description="SQLite database path")
    vector_enabled: bool = Field(default=True, description="Enable vector search")
    vector_dimensions: int = Field(default=768, description="Embedding dimensions")
    watch_enabled: bool = Field(default=True, description="Watch filesystem for changes")
    embedding_url: str = Field(
        default="http://localhost:7997", description="OpenClaw embedding service URL"
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


class IngestConfig(BaseSettings):
    """Ingest module configuration."""

    model_config = SettingsConfigDict(env_prefix="LL_INGEST_")

    rss_sources: list[dict[str, str]] = Field(
        default_factory=list, description="RSS source configurations"
    )
    fetch_interval_minutes: int = Field(default=30, description="Fetch interval in minutes")
    max_items_per_source: int = Field(default=50, description="Max items to fetch per source")
    package_paths: list[str] = Field(
        default_factory=lambda: ["./data/packages"],
        description="Directories containing source package YAML files",
    )
    verification_enabled: bool = Field(default=True, description="Enable truth verification engine")
    default_verification: dict[str, Any] = Field(
        default_factory=lambda: {
            "cross_reference_min": 1,
            "max_age_days": 7,
            "fallback_max_age_days": 14,
        },
        description="Default truth verification settings",
    )


class DispatchConfig(BaseSettings):
    """Dispatch module configuration."""

    model_config = SettingsConfigDict(env_prefix="LL_DISPATCH_")

    enabled: bool = Field(default=True, description="Enable dispatch module")
    default_publisher: str = Field(default="hexo", description="Default publisher name")
    publishers: list[dict[str, Any]] = Field(
        default_factory=lambda: [
            {
                "name": "hexo",
                "type": "hexo",
                "enabled": True,
                "config": {
                    "hexo_path": "~/blog",
                    "use_git_workflow": True,
                    "git_remote": "origin",
                    "git_branch": "master",
                },
            },
            {
                "name": "local",
                "type": "local",
                "enabled": False,
                "config": {
                    "output_dir": "~/Downloads",
                    "overwrite": False,
                },
            },
        ],
        description="Publisher configurations",
    )


class LinglongConfig(BaseSettings):
    """Main Linglong configuration."""

    model_config = SettingsConfigDict(
        env_prefix="LL_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # General
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # Module configs
    knowledge: KnowledgeConfig = Field(default_factory=KnowledgeConfig)
    ingest: IngestConfig = Field(default_factory=IngestConfig)
    composer: ComposerConfig = Field(default_factory=ComposerConfig)
    dispatch: DispatchConfig = Field(default_factory=DispatchConfig)

    # Paths
    data_dir: Path = Field(default=Path("./data"), description="Data directory")

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge.wiki_path.mkdir(parents=True, exist_ok=True)
        self.composer.drafts_dir.mkdir(parents=True, exist_ok=True)


# Global config instance
_config: LinglongConfig | None = None


def get_config() -> LinglongConfig:
    """Get or create global configuration."""
    global _config
    if _config is None:
        _config = LinglongConfig()
        _config.ensure_directories()
    return _config


def set_config(config: LinglongConfig) -> None:
    """Set global configuration (useful for testing)."""
    global _config
    _config = config
