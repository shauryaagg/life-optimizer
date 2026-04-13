"""Data models for storage layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

# Re-export CollectorResult for convenience
from life_optimizer.collectors.base import CollectorResult

__all__ = [
    "CollectorResult",
    "ActivityEvent",
    "Screenshot",
    "Session",
    "Summary",
    "Entity",
    "EntityMention",
]


@dataclass
class ActivityEvent:
    """Represents a stored activity event from the events table."""

    id: int
    timestamp: str
    app_name: str
    event_type: str
    app_bundle_id: str | None = None
    window_title: str | None = None
    context_json: str | None = None
    duration_seconds: float | None = None
    category: str | None = None
    subcategory: str | None = None
    is_idle: int = 0
    created_at: str = ""


@dataclass
class Screenshot:
    """Represents a stored screenshot from the screenshots table."""

    id: int
    timestamp: str
    file_path: str
    app_name: str
    window_title: str | None = None
    file_size_bytes: int | None = None
    width: int | None = None
    height: int | None = None
    trigger_reason: str | None = None
    llm_description: str | None = None
    event_id: int | None = None
    created_at: str = ""


@dataclass
class Session:
    """Represents an app usage session from the sessions table."""

    id: int
    start_time: str
    app_name: str
    end_time: str | None = None
    app_bundle_id: str | None = None
    title_summary: str | None = None
    context_summary: str | None = None
    duration_seconds: float | None = None
    category: str | None = None
    subcategory: str | None = None
    event_count: int = 0
    created_at: str = ""


@dataclass
class Summary:
    """Represents a periodic summary from the summaries table."""

    id: int
    period_type: str
    period_start: str
    period_end: str
    summary_text: str
    category_breakdown: str | None = None
    top_activities: str | None = None
    insights: str | None = None
    model_used: str | None = None
    created_at: str = ""


@dataclass
class Entity:
    """Represents a tracked entity (person, project, etc.) from the entities table."""

    id: int
    entity_type: str
    name: str
    first_seen: str
    last_seen: str
    interaction_count: int = 0
    metadata_json: str | None = None
    created_at: str = ""


@dataclass
class EntityMention:
    """Represents an entity mention from the entity_mentions table."""

    id: int
    entity_id: int
    event_id: int | None = None
    mention_type: str | None = None
    timestamp: str = ""
    context: str | None = None
    created_at: str = ""
