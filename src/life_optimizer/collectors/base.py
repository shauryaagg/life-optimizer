"""Base collector interface and result dataclass."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class CollectorResult:
    """Result of a single collection event."""

    app_name: str
    event_type: str
    app_bundle_id: str | None = None
    window_title: str | None = None
    context: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaseCollector(ABC):
    """Abstract base class for activity collectors."""

    app_names: list[str] = []
    bundle_ids: list[str] = []

    @abstractmethod
    async def collect(self, app_name: str, bundle_id: str | None = None) -> CollectorResult | None:
        """Collect activity data for the current frontmost app.

        Args:
            app_name: Name of the frontmost application.
            bundle_id: Bundle identifier of the frontmost application.

        Returns:
            CollectorResult with collected data, or None if collection failed.
        """
        ...

    def is_changed(self, prev: CollectorResult | None, curr: CollectorResult) -> bool:
        """Determine if the collected result differs from the previous one.

        Args:
            prev: Previous collection result (None if first collection).
            curr: Current collection result.

        Returns:
            True if the result has changed and should be stored.
        """
        if prev is None:
            return True
        return prev.window_title != curr.window_title or prev.context != curr.context
