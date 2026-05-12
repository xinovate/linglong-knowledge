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
    verification: VerificationSettings = Field(default_factory=VerificationSettings)
    output: dict[str, Any] = Field(default_factory=dict)

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
