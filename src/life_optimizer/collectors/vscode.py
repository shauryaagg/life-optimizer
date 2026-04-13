"""VS Code / Cursor activity collector using AppleScript window title parsing."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from life_optimizer.collectors.base import BaseCollector, CollectorResult
from life_optimizer.collectors.jxa_bridge import JXABridge
from life_optimizer.constants import POLL

logger = logging.getLogger(__name__)

VSCODE_TITLE_SCRIPT = """tell application "System Events"
    set frontApp to first application process whose frontmost is true
    try
        set winTitle to name of front window of frontApp
    on error
        set winTitle to ""
    end try
    return winTitle
end tell"""


def parse_vscode_title(raw_title: str) -> dict:
    """Parse a VS Code or Cursor window title.

    Common formats:
        "filename.py \u2014 project-name \u2014 Visual Studio Code"
        "filename.py \u2014 project-name \u2014 Cursor"
        "Welcome \u2014 Visual Studio Code"
        "project-name"

    Args:
        raw_title: The raw window title.

    Returns:
        Dict with raw_title, filename, and project.
    """
    result: dict = {"raw_title": raw_title, "filename": None, "project": None}

    if not raw_title:
        return result

    # Split on " \u2014 " (em-dash with spaces, used by VS Code/Cursor)
    parts = re.split(r"\s+\u2014\s+", raw_title)

    if len(parts) >= 3:
        # "filename \u2014 project \u2014 Visual Studio Code" or "filename \u2014 project \u2014 Cursor"
        result["filename"] = parts[0].strip()
        result["project"] = parts[1].strip()
    elif len(parts) == 2:
        # Could be "Welcome \u2014 Visual Studio Code" or "project \u2014 Cursor"
        # If the second part looks like an app name, first is filename/project
        second = parts[1].strip()
        if second in ("Visual Studio Code", "Cursor"):
            result["filename"] = parts[0].strip()
        else:
            result["filename"] = parts[0].strip()
            result["project"] = second

    return result


class VSCodeCollector(BaseCollector):
    """Collects activity from VS Code and Cursor via window title."""

    app_names: list[str] = ["Code", "Cursor"]
    bundle_ids: list[str] = ["com.microsoft.VSCode", "com.todesktop.230313mzl4w4u92"]

    def __init__(self, jxa_bridge: JXABridge):
        self._jxa = jxa_bridge

    async def collect(self, app_name: str, bundle_id: str | None = None) -> CollectorResult | None:
        """Collect VS Code/Cursor window title and parse for file/project.

        Args:
            app_name: Name of the application.
            bundle_id: Bundle identifier.

        Returns:
            CollectorResult with parsed context, or None if unavailable.
        """
        raw_title = await self._jxa.run_applescript(VSCODE_TITLE_SCRIPT)
        if raw_title is None:
            logger.debug("VSCode collector returned no data")
            return None

        raw_title = raw_title.strip()
        parsed = parse_vscode_title(raw_title)

        return CollectorResult(
            app_name=app_name,
            app_bundle_id=bundle_id,
            event_type=POLL,
            window_title=raw_title,
            context=parsed,
            timestamp=datetime.now(timezone.utc),
        )

    def is_changed(self, prev: CollectorResult | None, curr: CollectorResult) -> bool:
        """Check if VS Code window title has changed.

        Args:
            prev: Previous collection result.
            curr: Current collection result.

        Returns:
            True if raw window title changed.
        """
        if prev is None:
            return True
        return prev.window_title != curr.window_title
