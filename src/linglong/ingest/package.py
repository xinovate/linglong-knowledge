"""Source package model and YAML loader."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class SourceDefinition(BaseModel):
    """A single source within a package."""

    id: str
    type: str
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchQueryConfig(BaseModel):
    """Flat search query (no preset dimension)."""

    keywords: list[str] = Field(default_factory=list)
    max_results: int = 5
    max_age_days: int = 7


# Deprecated aliases for backward compat with tests/external code
class SearchConfig(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    engine: str = "auto"
    concurrent: bool = False


class FilterConfig(BaseModel):
    max_results: int = 5
    max_age_days: int = 7
    min_stars: int = 0


class DimensionConfig(BaseModel):
    name: str
    search: SearchConfig = Field(default_factory=SearchConfig)
    sources: list[SourceDefinition] = Field(default_factory=list)
    filter: FilterConfig = Field(default_factory=FilterConfig)


class OutputConfig(BaseModel):
    """Output configuration for a package."""

    format: str = ""  # morning-brief | weekly | empty = no formatting
    persist: bool = False


class VerificationSettings(BaseModel):
    """Truth verification configuration for a package."""

    enabled: bool = True
    cross_reference_min: int = 1
    max_age_days: int = 7
    fallback_max_age_days: int = 14
    authority_weights: dict[str, float] = Field(
        default_factory=lambda: {"high": 1.0, "medium": 0.7, "low": 0.4}
    )


class SourcePackage(BaseModel):
    """A topic-agnostic ingest package definition."""

    name: str
    topic: str
    schedule: str = "0 7 * * *"
    enabled: bool = True
    sources: list[SourceDefinition] = Field(default_factory=list)
    search_queries: list[SearchQueryConfig] = Field(default_factory=list)
    dimensions: list[DimensionConfig] = Field(default_factory=list)  # deprecated
    verification: VerificationSettings = Field(default_factory=VerificationSettings)
    output: OutputConfig = Field(default_factory=OutputConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "SourcePackage":
        """Load a SourcePackage from a YAML file."""
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data)

    @classmethod
    def load_all(cls, directories: list[str]) -> list["SourcePackage"]:
        """Load all .yaml packages from given directories."""
        packages = []
        for directory in directories:
            dir_path = Path(directory)
            if not dir_path.exists():
                continue
            for yaml_file in dir_path.glob("*.yaml"):
                try:
                    packages.append(cls.from_yaml(yaml_file))
                except Exception as e:
                    import logging

                    logging.getLogger(__name__).warning("Failed to load %s: %s", yaml_file, e)
        return packages
