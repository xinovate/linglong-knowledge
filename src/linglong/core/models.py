"""Shared data models for Linglong."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic_core import core_schema


class AgentID(str):
    """Agent identifier, e.g., 'agent:violet', 'agent:claude'."""

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def _validate(cls, value):
        if not isinstance(value, str):
            raise ValueError("AgentID must be a string")
        return cls(value)


class HumanID(str):
    """Human identifier, e.g., 'human:alice'."""

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        return core_schema.no_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
            serialization=core_schema.to_string_ser_schema(),
        )

    @classmethod
    def _validate(cls, value):
        if not isinstance(value, str):
            raise ValueError("HumanID must be a string")
        return cls(value)


class SourceType(StrEnum):
    """Source types for knowledge entries."""

    RSS = "rss"
    MEMORY = "memory"
    API = "api"
    AI_TASK = "ai_task"
    MANUAL = "manual"


class Source(BaseModel):
    """Source information for a knowledge entry."""

    type: SourceType
    name: str  # e.g., "techcrunch", "openclaw"
    url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConfidenceScore(float):
    """Confidence score between 0.0 and 1.0."""

    def __new__(cls, value: float):
        if not 0.0 <= value <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return super().__new__(cls, value)

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema

        def validate(value):
            if isinstance(value, cls):
                return value
            if not isinstance(value, (int, float)):
                raise ValueError("ConfidenceScore must be a number")
            return cls(value)

        return core_schema.no_info_after_validator_function(
            validate,
            core_schema.float_schema(ge=0.0, le=1.0),
            serialization=core_schema.to_string_ser_schema(),
        )


class EntityStatus(StrEnum):
    """Status of a knowledge entity."""

    RAW = "raw"  # Just ingested
    PENDING_REVIEW = "pending_review"  # Needs review
    CONFIRMED = "confirmed"  # Human confirmed
    AUTO_CONFIRMED = "auto_confirmed"  # High confidence auto-approved
    REJECTED = "rejected"  # Rejected after review


class Relation(BaseModel):
    """Relation between entities."""

    target_id: str
    relation_type: str  # e.g., "related", "parent", "derived_from"
    strength: float = 1.0  # 0.0 to 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class Version(BaseModel):
    """Version history entry."""

    version: int
    content: str
    modified_by: AgentID
    modified_at: datetime
    change_summary: str | None = None


class Entity(BaseModel):
    """Core knowledge entity.

    This is the central data model shared across all Linglong modules.
    """

    id: str | None = Field(default=None, description="Unique identifier (UUID)")
    content: str = Field(description="Markdown content")
    summary: str | None = Field(default=None, description="AI-generated summary for quick browsing")

    # Authorship
    created_by: AgentID = Field(description="Agent that created this entity")
    confirmed_by: HumanID | None = Field(
        default=None, description="Human who confirmed this entity"
    )
    confirmed_at: datetime | None = None

    # Quality
    confidence: ConfidenceScore = Field(default=0.5, description="AI confidence score")
    status: EntityStatus = Field(default=EntityStatus.RAW)

    # Source tracking
    sources: list[Source] = Field(default_factory=list)

    # Relations
    relations: list[Relation] = Field(default_factory=list)

    # Version history
    versions: list[Version] = Field(default_factory=list)
    current_version: int = Field(default=1)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Vector embedding (stored separately in sqlite-vec)
    embedding_id: str | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "content": "# Python Type Hints\n\nPython 3.11 introduced...",
                "summary": "Overview of Python type hints in 3.11",
                "created_by": "agent:violet",
                "confidence": 0.92,
                "status": "auto_confirmed",
                "sources": [{"type": "rss", "name": "python-blog", "url": "https://..."}],
            }
        }
    )


class TaskStatus(StrEnum):
    """Status of a scheduled task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(BaseModel):
    """Scheduled task for cross-module orchestration."""

    id: str
    project: str  # "ingest", "knowledge", "composer", "dispatch"
    task_type: str  # "rss_fetch", "distill", "publish", etc.
    status: TaskStatus = TaskStatus.PENDING

    # Scheduling
    scheduled_at: datetime
    executed_at: datetime | None = None
    completed_at: datetime | None = None

    # Context
    entity_id: str | None = None  # Related entity (if any)
    params: dict[str, Any] = Field(default_factory=dict)

    # Result
    result: dict[str, Any] | None = None
    error: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
