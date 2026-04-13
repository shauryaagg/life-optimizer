"""Safari browser activity collector using JXA."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from life_optimizer.collectors.base import BaseCollector, CollectorResult
from life_optimizer.collectors.jxa_bridge import JXABridge
from life_optimizer.constants import POLL

logger = logging.getLogger(__name__)

SAFARI_JXA_SCRIPT = """(function() {
    var safari = Application('Safari');
    if (!safari.running()) return JSON.stringify(null);
    var wins = safari.windows();
    if (wins.length === 0) return JSON.stringify(null);
    var tab = wins[0].currentTab();
    return JSON.stringify({
        url: tab.url(),
        title: tab.name(),
        windowCount: wins.length,
        tabCount: wins[0].tabs().length
    });
})()"""


class SafariCollector(BaseCollector):
    """Collects activity data from Safari via JXA."""

    app_names: list[str] = ["Safari"]
    bundle_ids: list[str] = ["com.apple.Safari"]

    def __init__(self, jxa_bridge: JXABridge):
        self._jxa = jxa_bridge

    async def collect(self, app_name: str, bundle_id: str | None = None) -> CollectorResult | None:
        """Collect Safari's active tab URL and title.

        Args:
            app_name: Name of the application.
            bundle_id: Bundle identifier.

        Returns:
            CollectorResult with Safari tab context, or None if unavailable.
        """
        data = await self._jxa.run_jxa_json(SAFARI_JXA_SCRIPT)
        if data is None:
            logger.debug("Safari collector returned no data")
            return None

        return CollectorResult(
            app_name=app_name,
            app_bundle_id=bundle_id or "com.apple.Safari",
            event_type=POLL,
            window_title=data.get("title"),
            context={
                "url": data.get("url", ""),
                "title": data.get("title", ""),
                "windowCount": data.get("windowCount", 0),
                "tabCount": data.get("tabCount", 0),
            },
            timestamp=datetime.now(timezone.utc),
        )

    def is_changed(self, prev: CollectorResult | None, curr: CollectorResult) -> bool:
        """Check if Safari tab has changed (compares URL and title).

        Args:
            prev: Previous collection result.
            curr: Current collection result.

        Returns:
            True if URL or title changed.
        """
        if prev is None:
            return True
        prev_url = prev.context.get("url", "")
        curr_url = curr.context.get("url", "")
        prev_title = prev.context.get("title", "")
        curr_title = curr.context.get("title", "")
        return prev_url != curr_url or prev_title != curr_title
