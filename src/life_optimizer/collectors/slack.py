"""Slack activity collector using AppleScript window title parsing."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from life_optimizer.collectors.base import BaseCollector, CollectorResult
from life_optimizer.collectors.jxa_bridge import JXABridge
from life_optimizer.constants import POLL

logger = logging.getLogger(__name__)

SLACK_TITLE_SCRIPT = """tell application "System Events"
    tell process "Slack"
        try
            set winTitle to name of front window
        on error
            set winTitle to ""
        end try
        return winTitle
    end tell
end tell"""


def parse_slack_title(raw_title: str) -> dict:
    """Parse a Slack window title into components.

    Expected formats:
        "#channel - Workspace - Slack"
        "Person Name - Workspace - Slack"

    Args:
        raw_title: The raw window title string.

    Returns:
        Dict with workspace, channel, type, and raw_title.
    """
    result: dict = {"raw_title": raw_title, "workspace": "", "channel": "", "type": "unknown"}

    if not raw_title:
        return result

    # Strip trailing " - Slack" if present
    title = raw_title
    if title.endswith(" - Slack"):
        title = title[: -len(" - Slack")]

    # Split on " - " to find channel/person and workspace
    parts = title.split(" - ", 1)
    if len(parts) == 2:
        channel_or_person = parts[0].strip()
        workspace = parts[1].strip()
        result["workspace"] = workspace
        result["channel"] = channel_or_person
        result["type"] = "channel" if channel_or_person.startswith("#") else "dm"
    elif len(parts) == 1:
        result["channel"] = parts[0].strip()

    return result


class SlackCollector(BaseCollector):
    """Collects activity data from Slack via AppleScript window title."""

    app_names: list[str] = ["Slack"]
    bundle_ids: list[str] = ["com.tinyspeck.slackmacgap"]

    def __init__(self, jxa_bridge: JXABridge):
        self._jxa = jxa_bridge

    async def collect(self, app_name: str, bundle_id: str | None = None) -> CollectorResult | None:
        """Collect Slack's window title and parse it.

        Args:
            app_name: Name of the application.
            bundle_id: Bundle identifier.

        Returns:
            CollectorResult with parsed Slack context, or None if unavailable.
        """
        raw_title = await self._jxa.run_applescript(SLACK_TITLE_SCRIPT)
        if raw_title is None or raw_title.strip() == "":
            logger.debug("Slack collector returned no data")
            return None

        raw_title = raw_title.strip()
        parsed = parse_slack_title(raw_title)

        return CollectorResult(
            app_name=app_name,
            app_bundle_id=bundle_id or "com.tinyspeck.slackmacgap",
            event_type=POLL,
            window_title=raw_title,
            context=parsed,
            timestamp=datetime.now(timezone.utc),
        )

    def is_changed(self, prev: CollectorResult | None, curr: CollectorResult) -> bool:
        """Check if Slack channel/workspace has changed.

        Args:
            prev: Previous collection result.
            curr: Current collection result.

        Returns:
            True if channel or workspace changed.
        """
        if prev is None:
            return True
        prev_channel = prev.context.get("channel", "")
        curr_channel = curr.context.get("channel", "")
        prev_workspace = prev.context.get("workspace", "")
        curr_workspace = curr.context.get("workspace", "")
        return prev_channel != curr_channel or prev_workspace != curr_workspace
