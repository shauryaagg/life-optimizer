"""Chrome browser activity collector using JXA."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from life_optimizer.collectors.base import BaseCollector, CollectorResult
from life_optimizer.collectors.jxa_bridge import JXABridge
from life_optimizer.constants import POLL

logger = logging.getLogger(__name__)

# JXA script to get active Chrome tab information
CHROME_JXA_SCRIPT = """(function() {
    var chrome = Application('Google Chrome');
    if (!chrome.running()) return JSON.stringify(null);
    var wins = chrome.windows();
    if (wins.length === 0) return JSON.stringify(null);
    var active = wins[0].activeTab();
    return JSON.stringify({
        url: active.url(),
        title: active.title(),
        windowCount: wins.length,
        tabCount: wins[0].tabs().length
    });
})()"""


class ChromeCollector(BaseCollector):
    """Collects activity data from Google Chrome via JXA."""

    app_names: list[str] = ["Google Chrome"]
    bundle_ids: list[str] = ["com.google.Chrome"]

    def __init__(self, jxa_bridge: JXABridge):
        self._jxa = jxa_bridge

    async def collect(self, app_name: str, bundle_id: str | None = None) -> CollectorResult | None:
        """Collect Chrome's active tab URL and title.

        Args:
            app_name: Name of the application (should be "Google Chrome").
            bundle_id: Bundle identifier.

        Returns:
            CollectorResult with Chrome tab context, or None if unavailable.
        """
        data = await self._jxa.run_jxa_json(CHROME_JXA_SCRIPT)
        if data is None:
            logger.debug("Chrome collector returned no data (Chrome may not be running)")
            return None

        return CollectorResult(
            app_name=app_name,
            app_bundle_id=bundle_id or "com.google.Chrome",
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
        """Check if Chrome tab has changed (compares URL and title only).

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
