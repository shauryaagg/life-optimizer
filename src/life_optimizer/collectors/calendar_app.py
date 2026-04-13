"""Calendar app collector using JXA to get today's events."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from life_optimizer.collectors.base import BaseCollector, CollectorResult
from life_optimizer.collectors.jxa_bridge import JXABridge
from life_optimizer.constants import POLL

logger = logging.getLogger(__name__)

CALENDAR_JXA_SCRIPT = """(function() {
    var cal = Application('Calendar');
    if (!cal.running()) return JSON.stringify(null);
    var now = new Date();
    var start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    var end = new Date(start.getTime() + 86400000);
    var events = [];
    cal.calendars().forEach(function(c) {
        try {
            c.events.whose({startDate: {'>=': start}, startDate: {'<': end}})().forEach(function(e) {
                events.push({title: e.summary(), start: e.startDate().toISOString(), end: e.endDate().toISOString(), calendar: c.name()});
            });
        } catch(err) {}
    });
    return JSON.stringify({events: events, eventCount: events.length});
})()"""


class CalendarCollector(BaseCollector):
    """Collects today's events from Calendar.app when it is frontmost."""

    app_names: list[str] = ["Calendar"]
    bundle_ids: list[str] = ["com.apple.iCal"]

    def __init__(self, jxa_bridge: JXABridge):
        self._jxa = jxa_bridge

    async def collect(self, app_name: str, bundle_id: str | None = None) -> CollectorResult | None:
        """Collect today's calendar events via JXA.

        Args:
            app_name: Name of the application.
            bundle_id: Bundle identifier.

        Returns:
            CollectorResult with event list context, or None if unavailable.
        """
        data = await self._jxa.run_jxa_json(CALENDAR_JXA_SCRIPT)
        if data is None:
            logger.debug("Calendar collector returned no data")
            return None

        event_count = data.get("eventCount", 0)
        return CollectorResult(
            app_name=app_name,
            app_bundle_id=bundle_id or "com.apple.iCal",
            event_type=POLL,
            window_title=f"{event_count} events today",
            context={
                "events": data.get("events", []),
                "eventCount": event_count,
            },
            timestamp=datetime.now(timezone.utc),
        )

    def is_changed(self, prev: CollectorResult | None, curr: CollectorResult) -> bool:
        """Check if event count has changed.

        Args:
            prev: Previous collection result.
            curr: Current collection result.

        Returns:
            True if event count changed.
        """
        if prev is None:
            return True
        return prev.context.get("eventCount", 0) != curr.context.get("eventCount", 0)
