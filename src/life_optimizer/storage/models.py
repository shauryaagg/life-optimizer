"""Data models for storage layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

# Re-export CollectorResult for convenience
from life_optimizer.collectors.base import CollectorResult

__all__ = ["CollectorResult", "ActivityEvent"]


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
