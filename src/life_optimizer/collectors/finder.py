"""Finder activity collector using AppleScript."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from life_optimizer.collectors.base import BaseCollector, CollectorResult
from life_optimizer.collectors.jxa_bridge import JXABridge
from life_optimizer.constants import POLL

logger = logging.getLogger(__name__)

FINDER_APPLESCRIPT = """tell application "Finder"
    try
        set frontWin to front window
        set folderPath to POSIX path of (target of frontWin as alias)
        set winName to name of frontWin
        return winName & "|" & folderPath
    on error
        return ""
    end try
end tell"""


def parse_finder_output(raw: str) -> dict:
    """Parse Finder AppleScript output into window_name and folder_path.

    Args:
        raw: Output in "window_name|/folder/path" format.

    Returns:
        Dict with folder_path and window_name.
    """
    result: dict = {"folder_path": "", "window_name": ""}
    if not raw:
        return result

    parts = raw.split("|", 1)
    if len(parts) == 2:
        result["window_name"] = parts[0].strip()
        result["folder_path"] = parts[1].strip()
    elif len(parts) == 1:
        result["window_name"] = parts[0].strip()

    return result


class FinderCollector(BaseCollector):
    """Collects Finder's frontmost window folder path."""

    app_names: list[str] = ["Finder"]
    bundle_ids: list[str] = ["com.apple.finder"]

    def __init__(self, jxa_bridge: JXABridge):
        self._jxa = jxa_bridge

    async def collect(self, app_name: str, bundle_id: str | None = None) -> CollectorResult | None:
        """Collect Finder's front window folder path.

        Args:
            app_name: Name of the application.
            bundle_id: Bundle identifier.

        Returns:
            CollectorResult with folder context, or None if unavailable.
        """
        raw = await self._jxa.run_applescript(FINDER_APPLESCRIPT)
        if raw is None or raw.strip() == "":
            logger.debug("Finder collector returned no data")
            return None

        raw = raw.strip()
        parsed = parse_finder_output(raw)

        return CollectorResult(
            app_name=app_name,
            app_bundle_id=bundle_id or "com.apple.finder",
            event_type=POLL,
            window_title=parsed.get("window_name", ""),
            context=parsed,
            timestamp=datetime.now(timezone.utc),
        )

    def is_changed(self, prev: CollectorResult | None, curr: CollectorResult) -> bool:
        """Check if Finder folder path has changed.

        Args:
            prev: Previous collection result.
            curr: Current collection result.

        Returns:
            True if folder path changed.
        """
        if prev is None:
            return True
        return prev.context.get("folder_path", "") != curr.context.get("folder_path", "")
