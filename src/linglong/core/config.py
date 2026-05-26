"""Configuration management for Linglong."""

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# YAML 配置文件搜索路径（CWD 优先，项目根目录兜底，home 目录兜底）
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_YAML_SEARCH_PATHS = [
    Path(".linglong.yaml"),
    _PROJECT_ROOT / ".linglong.yaml",
    Path.home() / ".linglong" / "config.yaml",
]


class ImageAssetSpecConfig(BaseModel):
    """Image asset specification (size, quality, output)."""

    min_width: int = Field(default=800, description="Minimum image width in pixels")
    min_height: int = Field(default=600, description="Minimum image height in pixels")
    quality: int = Field(default=85, description="JPEG compression quality (1-100)")
    output_dir: str = Field(
        default="~/linglong/images", description="Output directory for processed images"
    )
    variants: dict[str, int] = Field(
        default_factory=lambda: {
            "thumb": 400,
            "medium": 800,
            "large": 1200,
        },
        description="Image size variants: name → max width in pixels",
    )


class ImageAssetSourceConfig(BaseModel):
    """Image source configuration (URL list file)."""

    name: str = Field(description="Source name (e.g. tuchong, unsplash)")
    url_file: str = Field(description="Path to URL list file")
    headers: dict[str, str] = Field(
        default_factory=lambda: {"User-Agent": "Mozilla/5.0", "Referer": "https://tuchong.com/"},
        description="HTTP headers for downloading",
    )
    default_usage: str = Field(
        default="both",
        description="Default usage when not marked in URL file: background, article_image, or both",
    )
    resolve_via: str = Field(
        default="direct",
        description="URL resolution method: direct (image URLs) or playwright (page URLs needing browser)",
    )
    headless: bool = Field(default=True, description="Playwright headless mode")
    delay_range: list[int] = Field(
        default=[3, 8], description="Random delay range in seconds between page visits"
    )
    max_count: int = Field(default=50, description="Max URLs to resolve per run")


class ImageAssetSelectionConfig(BaseModel):
    """Image selection strategy configuration."""

    strategy: str = Field(default="random", description="Selection strategy: random")
    dedup_days: int = Field(default=30, description="Days to remember used URLs for dedup")


class ImageAssetConfig(BaseModel):
    """Top-level image asset configuration for Composer."""

    enabled: bool = Field(default=False, description="Enable image asset fetching")
    specs: dict[str, ImageAssetSpecConfig] = Field(
        default_factory=lambda: {
            "background": ImageAssetSpecConfig(
                min_width=1920, min_height=1080, quality=90,
                output_dir="~/linglong/images/backgrounds",
            ),
            "article_image": ImageAssetSpecConfig(
                min_width=800, min_height=600, quality=85,
                output_dir="~/linglong/images/articles",
            ),
        },
        description="Image specifications keyed by usage (background, article_image)",
    )
    sources: list[ImageAssetSourceConfig] = Field(
        default_factory=list, description="Image source configurations"
    )
    selection: ImageAssetSelectionConfig = Field(
        default_factory=ImageAssetSelectionConfig, description="Selection strategy"
    )


class ComposerConfig(BaseSettings):
    """Composer module configuration."""

    model_config = SettingsConfigDict(env_prefix="LL_COMPOSER_")

    # LLM 设置
    llm_provider: str = Field(default="openai", description="LLM provider")
    llm_model: str = Field(default="gpt-4", description="LLM model name")
    llm_api_key: str | None = Field(default=None, description="LLM API key")
    llm_base_url: str | None = Field(default=None, description="LLM base URL")
    llm_temperature: float = Field(default=0.7, description="LLM temperature")
    llm_max_tokens: int = Field(default=4096, description="LLM max tokens")

    # 提炼器设置
    distiller_use_llm: bool = Field(default=False, description="Use LLM distiller")
    distiller_theme_threshold: float = Field(
        default=0.7, description="Theme grouping similarity threshold"
    )
    distiller_max_themes: int = Field(default=5, description="Max themes per aggregation")

    # 资产设置
    assets_excerpt_length: int = Field(default=200, description="Excerpt length")
    assets_cover_enabled: bool = Field(default=False, description="Enable cover generation")
    image_assets: ImageAssetConfig = Field(
        default_factory=ImageAssetConfig, description="Image asset fetching configuration"
    )

    # 模板设置
    template_name: str = Field(default="blog", description="Default template")

    # 草稿设置
    drafts_dir: Path = Field(
        default=Path.home() / "linglong" / "data" / "drafts", description="Drafts directory"
    )

    # 分发设置
    auto_publish: bool = Field(
        default=False, description="Auto-publish dispatch-ready articles via DispatchManager"
    )
    default_publisher: str = Field(
        default="local", description="Default publisher name for auto-publish"
    )


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

    # 写入设置
    write_mode: str = Field(
        default="confirm", description="Write mode: confirm or auto"
    )
    search_mode: str = Field(
        default="on_demand", description="Search mode: on_demand or deep"
    )
    auto_index: bool = Field(
        default=True, description="Auto-update index on write"
    )
    max_versions: int = Field(
        default=10, description="Max version history per entity"
    )

    # 并发设置
    lock_timeout: int = Field(
        default=5, description="File lock timeout in seconds"
    )
    db_mode: str = Field(
        default="wal", description="SQLite journal mode"
    )
    auto_lint: bool = Field(
        default=False, description="Auto-run lint after write operations"
    )
    lint_schedule: str | None = Field(
        default=None, description="定时巡检的 cron 表达式，如 '0 2 * * *'"
    )

    # 审核引擎设置
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

    # 同步适配器置信度
    sync_confidence: float = Field(
        default=0.95, description="Default confidence for synced entities"
    )

    # 同步源路径
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

    # LLM 早报生成
    llm_max_tokens: int = Field(
        default=8000, description="LLM max output tokens for brief generation"
    )
    llm_retries: int = Field(
        default=2, description="LLM call retry count on failure"
    )
    llm_timeout: int = Field(
        default=120, description="LLM request timeout in seconds"
    )

    # GitHub 开源趋势
    github_trending_limits: dict[str, int] = Field(
        default_factory=lambda: {"daily": 5, "weekly": 3, "monthly": 3},
        description="GitHub trending repo counts per period",
    )
    github_search_fallback: dict[str, int] = Field(
        default_factory=lambda: {"since_days": 30, "min_stars": 500},
        description="GitHub Search API fallback parameters",
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

    # Hexo 发布器默认值
    hexo_site_url: str = Field(
        default="https://www.linglong.wiki", description="Hexo site base URL"
    )
    hexo_deploy_command: str | None = Field(
        default=None,
        description="Custom SSH deploy command (None uses default git workflow)",
    )

    # OSS image CDN
    oss: OSSConfig = Field(default_factory=OSSConfig, description="OSS image CDN configuration")


class LinglongConfig(BaseSettings):
    """Main Linglong configuration."""

    model_config = SettingsConfigDict(
        env_prefix="LL_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # 通用
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")

    # 模块配置
    knowledge: KnowledgeConfig = Field(default_factory=KnowledgeConfig)
    ingest: IngestConfig = Field(default_factory=IngestConfig)
    composer: ComposerConfig = Field(default_factory=ComposerConfig)
    dispatch: DispatchConfig = Field(default_factory=DispatchConfig)

    # 路径
    data_dir: Path = Field(
        default=Path.home() / "linglong" / "data", description="Data directory"
    )

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge.wiki_path.mkdir(parents=True, exist_ok=True)
        self.knowledge.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.composer.drafts_dir.mkdir(parents=True, exist_ok=True)
        (Path.home() / "linglong" / "state").mkdir(parents=True, exist_ok=True)
        # 图片资产输出目录
        if self.composer.image_assets.enabled:
            for spec in self.composer.image_assets.specs.values():
                Path(spec.output_dir).expanduser().mkdir(parents=True, exist_ok=True)


# 全局配置实例
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
    """从 YAML 文件构造 LinglongConfig。

    YAML 值作为 init 参数传入（Pydantic 优先级最高），
    未在 YAML 中指定的字段回退到环境变量/默认值。
    支持 ${ENV_VAR} 语法引用环境变量。
    """
    data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    data = _interpolate_env(data)
    return LinglongConfig(**data)


def get_config() -> LinglongConfig:
    """Get or create global configuration.

    搜索顺序：.linglong.yaml (CWD) → ~/.linglong/config.yaml → 纯 env/默认值
    """
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
