"""Configuration management for Linglong."""

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# YAML config search paths: CWD first, then project root, then home
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_YAML_SEARCH_PATHS = [
    Path(".linglong.yaml"),
    _PROJECT_ROOT / ".linglong.yaml",
    Path.home() / ".linglong" / "config.yaml",
]


class ReviewerConfig(BaseSettings):
    """Reviewer module configuration."""

    model_config = SettingsConfigDict(env_prefix="LL_REVIEWER_")

    llm_provider: str = Field(default="openai", description="LLM provider")
    llm_model: str = Field(default="gpt-4", description="LLM model name")
    llm_api_key: str | None = Field(default=None, description="LLM API key")
    llm_base_url: str | None = Field(default=None, description="LLM base URL")
    llm_temperature: float = Field(default=0.3, description="LLM temperature for review")
    llm_max_tokens: int = Field(default=4096, description="LLM max tokens")
    passing_score: float = Field(default=6.0, description="Minimum passing score (0-10)")


class KnowledgeConfig(BaseSettings):
    """Knowledge module configuration."""

    model_config = SettingsConfigDict(env_prefix="LL_KNOWLEDGE_")

    wiki_path: Path = Field(
        default=Path.home() / "linglong" / "wiki", description="Path to wiki directory"
    )
    db_path: Path = Field(
        default=Path.home() / "linglong" / "db" / "knowledge.db",
        description="SQLite database path",
    )
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

    write_mode: str = Field(default="confirm", description="Write mode: confirm or auto")
    search_mode: str = Field(default="on_demand", description="Search mode: on_demand or deep")
    auto_index: bool = Field(default=True, description="Auto-update index on write")
    max_versions: int = Field(default=10, description="Max version history per entity")

    lock_timeout: int = Field(default=5, description="File lock timeout in seconds")
    db_mode: str = Field(default="wal", description="SQLite journal mode")
    auto_lint: bool = Field(default=False, description="Auto-run lint after write operations")
    lint_schedule: str | None = Field(
        default=None, description="定时巡检的 cron 表达式，如 '0 2 * * *'"
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


class IngestConfig(BaseSettings):
    """Ingest module configuration."""

    model_config = SettingsConfigDict(env_prefix="LL_INGEST_")

    rss_sources: list[dict[str, str]] = Field(
        default_factory=list, description="RSS source configurations"
    )
    packages: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Inline package definitions",
    )
    searxng_url: str = Field(
        default="http://localhost:8088",
        description="SearXNG instance URL for JSON API search",
    )
    search_timeout: float = Field(
        default=30.0, description="Search request timeout in seconds"
    )
    searxng_api_key: str | None = Field(
        default=None, description="SearXNG API key (Bearer Token via nginx auth)"
    )
    rsshub_access_key: str | None = Field(
        default=None, description="RSSHub ACCESS_KEY for authenticated requests"
    )

    llm_max_tokens: int = Field(
        default=8000, description="LLM max output tokens for brief generation"
    )
    llm_retries: int = Field(
        default=2, description="LLM call retry count on failure"
    )
    llm_timeout: int = Field(
        default=120, description="LLM request timeout in seconds"
    )

    github_trending_limits: dict[str, int] = Field(
        default_factory=lambda: {"daily": 5, "weekly": 3, "monthly": 3},
        description="GitHub trending repo counts per period",
    )
    github_search_fallback: dict[str, int] = Field(
        default_factory=lambda: {"since_days": 30, "min_stars": 500},
        description="GitHub Search API fallback parameters",
    )

    brief_history_dir: str = Field(
        default="~/linglong/brief_history",
        description="Directory for brief history JSON files (dedup)",
    )
    company_snapshot_path: str = Field(
        default="~/linglong/company_snapshot.json",
        description="Company funding/valuation snapshot for brief generation",
    )
    dedup_windows: dict[str, int] = Field(
        default_factory=lambda: {"关键人物": 14, "公司动态": 7, "政策动态": 14, "应用落地": 7},
        description="Per-dimension lookback days for dedup",
    )

    brief_output_dir: str = Field(
        default="~/linglong/briefs",
        description="Directory for cached daily briefs",
    )
    brief_schedule_time: str = Field(
        default="07:30",
        description="Daily brief schedule time (HH:MM), used for time range markers",
    )
    brief_cache_days: int = Field(
        default=14,
        description="Days to keep cached briefs",
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
        default_factory=lambda: ["ingest", "knowledge"],
        description="Which module tool groups to expose: ingest, knowledge, reviewer",
    )
    allowed_hosts: list[str] = Field(
        default_factory=list,
        description="Allowed Host header values for DNS rebinding protection (HTTP mode)",
    )
    redis_url: str = Field(
        default="",
        description="Redis URL for dynamic token auth (e.g. redis://:password@127.0.0.1:6379/0)",
    )


class OSSConfig(BaseModel):
    """Alibaba Cloud OSS configuration for image CDN."""

    enabled: bool = Field(default=False, description="Enable OSS image upload")
    bucket_name: str = Field(default="", description="OSS bucket name")
    endpoint: str = Field(default="", description="OSS endpoint (e.g. oss-cn-hangzhou.aliyuncs.com)")
    cdn_domain: str = Field(default="", description="CDN domain for image URLs")
    access_key_id: str = Field(
        default="",
        description="OSS access key ID (prefer LL_OSS_ACCESS_KEY_ID env var)",
    )
    access_key_secret: str = Field(
        default="",
        description="OSS access key secret (prefer LL_OSS_ACCESS_KEY_SECRET env var)",
    )
    prefix: str = Field(default="images/", description="Object key prefix in OSS bucket")


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
                    "site_url": "https://www.linglong.wiki",
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

    hexo_site_url: str = Field(
        default="https://www.linglong.wiki", description="Hexo site base URL"
    )
    hexo_deploy_command: str | None = Field(
        default=None,
        description="Custom SSH deploy command (None uses default git workflow)",
    )

    oss: OSSConfig = Field(default_factory=OSSConfig, description="OSS image CDN configuration")


class LinglongConfig(BaseSettings):
    """Main Linglong configuration."""

    model_config = SettingsConfigDict(
        env_prefix="LL_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    knowledge: KnowledgeConfig = Field(default_factory=KnowledgeConfig)
    ingest: IngestConfig = Field(default_factory=IngestConfig)
    reviewer: ReviewerConfig = Field(default_factory=ReviewerConfig)
    dispatch: DispatchConfig = Field(default_factory=DispatchConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)

    data_dir: Path = Field(
        default=Path.home() / "linglong" / "data", description="Data directory"
    )

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge.wiki_path.mkdir(parents=True, exist_ok=True)
        self.knowledge.db_path.parent.mkdir(parents=True, exist_ok=True)
        (Path.home() / "linglong" / "state").mkdir(parents=True, exist_ok=True)


_config: LinglongConfig | None = None


def _find_yaml_config() -> Path | None:
    """搜索 .linglong.yaml 配置文件，返回找到的第一个路径。"""
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
    """从 YAML 文件构造 LinglongConfig。"""
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
