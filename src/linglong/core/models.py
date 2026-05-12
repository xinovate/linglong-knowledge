"""Shared data models for Linglong."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentID(str):
    """Agent identifier, e.g., 'agent:violet', 'agent:claude'."""


class HumanID(str):
    """Human identifier, e.g., 'human:alice'."""


class SourceType(str, Enum):
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
    url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConfidenceScore(float):
    """Confidence score between 0.0 and 1.0."""

    def __new__(cls, value: float):
        if not 0.0 <= value <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return super().__new__(cls, value)


class EntityStatus(str, Enum):
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
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Version(BaseModel):
    """Version history entry."""

    version: int
    content: str
    modified_by: AgentID
    modified_at: datetime
    change_summary: Optional[str] = None


class Entity(BaseModel):
    """Core knowledge entity.

    This is the central data model shared across all Linglong modules.
    """

    id: str = Field(description="Unique identifier (UUID)")
    content: str = Field(description="Markdown content")
    summary: Optional[str] = Field(
        default=None, description="AI-generated summary for quick browsing"
    )

    # Authorship
    created_by: AgentID = Field(description="Agent that created this entity")
    confirmed_by: Optional[HumanID] = Field(
        default=None, description="Human who confirmed this entity"
    )
    confirmed_at: Optional[datetime] = None

    # Quality
    confidence: ConfidenceScore = Field(
        default=0.5, description="AI confidence score"
    )
    status: EntityStatus = Field(default=EntityStatus.RAW)

    # Source tracking
    sources: List[Source] = Field(default_factory=list)

    # Relations
    relations: List[Relation] = Field(default_factory=list)

    # Version history
    versions: List[Version] = Field(default_factory=list)
    current_version: int = Field(default=1)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Vector embedding (stored separately in sqlite-vec)
    embedding_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "content": "# Python Type Hints\n\nPython 3.11 introduced...",
                "summary": "Overview of Python type hints in 3.11",
                "created_by": "agent:violet",
                "confidence": 0.92,
                "status": "auto_confirmed",
                "sources": [
                    {"type": "rss", "name": "python-blog", "url": "https://..."}
                ],
            }
        }


class TaskStatus(str, Enum):
    """Status of a scheduled task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(BaseModel):
    """Scheduled task for cross-module orchestration."""

    id: str
    project: str  # "ingest", "knowledge", "pipeline", "dispatch"
    task_type: str  # "rss_fetch", "distill", "publish", etc.
    status: TaskStatus = TaskStatus.PENDING

    # Scheduling
    scheduled_at: datetime
    executed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Context
    entity_id: Optional[str] = None  # Related entity (if any)
    params: Dict[str, Any] = Field(default_factory=dict)

    # Result
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
