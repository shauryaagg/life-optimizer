"""Generic collector for any macOS application using AppleScript."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from life_optimizer.collectors.base import BaseCollector, CollectorResult
from life_optimizer.collectors.jxa_bridge import JXABridge
from life_optimizer.constants import POLL

logger = logging.getLogger(__name__)

# AppleScript to get frontmost app's window title
WINDOW_TITLE_SCRIPT = """tell application "System Events"
    set frontApp to first application process whose frontmost is true
    try
        set winTitle to name of front window of frontApp
    on error
        set winTitle to ""
    end try
    return winTitle
end tell"""


class GenericCollector(BaseCollector):
    """Collects window title for any macOS application via AppleScript."""

    app_names: list[str] = []
    bundle_ids: list[str] = []

    def __init__(self, jxa_bridge: JXABridge):
        self._jxa = jxa_bridge

    async def collect(self, app_name: str, bundle_id: str | None = None) -> CollectorResult | None:
        """Collect the frontmost window title for any app.

        Args:
            app_name: Name of the frontmost application.
            bundle_id: Bundle identifier.

        Returns:
            CollectorResult with window title, or None if collection failed.
        """
        title = await self._jxa.run_applescript(WINDOW_TITLE_SCRIPT)

        return CollectorResult(
            app_name=app_name,
            app_bundle_id=bundle_id,
            event_type=POLL,
            window_title=title or "",
            context={},
            timestamp=datetime.now(timezone.utc),
        )

    def is_changed(self, prev: CollectorResult | None, curr: CollectorResult) -> bool:
        """Check if window title has changed.

        Args:
            prev: Previous collection result.
            curr: Current collection result.

        Returns:
            True if window title changed.
        """
        if prev is None:
            return True
        return prev.window_title != curr.window_title
