"""Terminal/iTerm2 activity collector using AppleScript window title parsing."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from life_optimizer.collectors.base import BaseCollector, CollectorResult
from life_optimizer.collectors.jxa_bridge import JXABridge
from life_optimizer.constants import POLL

logger = logging.getLogger(__name__)

TERMINAL_TITLE_SCRIPT = """tell application "System Events"
    set frontApp to first application process whose frontmost is true
    try
        set winTitle to name of front window of frontApp
    on error
        set winTitle to ""
    end try
    return winTitle
end tell"""


def parse_terminal_title(raw_title: str) -> dict:
    """Parse a terminal window title for cwd and command hints.

    Common formats:
        "user@host: ~/path"
        "user@host: ~/path - command"
        "~/path -- command"
        "~/path"

    Args:
        raw_title: The raw window title.

    Returns:
        Dict with raw_title, parsed_cwd, and parsed_command.
    """
    result: dict = {"raw_title": raw_title, "parsed_cwd": None, "parsed_command": None}

    if not raw_title:
        return result

    title = raw_title.strip()

    # Try "user@host: path" or "user@host: path - command"
    match = re.match(r"^[^@]+@[^:]+:\s*(.+)$", title)
    if match:
        path_and_rest = match.group(1).strip()
        # Check for " - command" or " -- command" suffix
        cmd_match = re.split(r"\s+[-\u2014]{1,2}\s+", path_and_rest, maxsplit=1)
        if len(cmd_match) == 2:
            result["parsed_cwd"] = cmd_match[0].strip()
            result["parsed_command"] = cmd_match[1].strip()
        else:
            result["parsed_cwd"] = path_and_rest
        return result

    # Try "~/path -- command" or "~/path - command"
    if title.startswith("~") or title.startswith("/"):
        cmd_match = re.split(r"\s+[-\u2014]{1,2}\s+", title, maxsplit=1)
        if len(cmd_match) == 2:
            result["parsed_cwd"] = cmd_match[0].strip()
            result["parsed_command"] = cmd_match[1].strip()
        else:
            result["parsed_cwd"] = title
        return result

    return result


class TerminalCollector(BaseCollector):
    """Collects activity from Terminal.app and iTerm2 via window title."""

    app_names: list[str] = ["Terminal", "iTerm2"]
    bundle_ids: list[str] = ["com.apple.Terminal", "com.googlecode.iterm2"]

    def __init__(self, jxa_bridge: JXABridge):
        self._jxa = jxa_bridge

    async def collect(self, app_name: str, bundle_id: str | None = None) -> CollectorResult | None:
        """Collect terminal window title and parse for cwd/command.

        Args:
            app_name: Name of the application.
            bundle_id: Bundle identifier.

        Returns:
            CollectorResult with parsed terminal context, or None if unavailable.
        """
        raw_title = await self._jxa.run_applescript(TERMINAL_TITLE_SCRIPT)
        if raw_title is None:
            logger.debug("Terminal collector returned no data")
            return None

        raw_title = raw_title.strip()
        parsed = parse_terminal_title(raw_title)

        return CollectorResult(
            app_name=app_name,
            app_bundle_id=bundle_id,
            event_type=POLL,
            window_title=raw_title,
            context=parsed,
            timestamp=datetime.now(timezone.utc),
        )

    def is_changed(self, prev: CollectorResult | None, curr: CollectorResult) -> bool:
        """Check if terminal window title has changed.

        Args:
            prev: Previous collection result.
            curr: Current collection result.

        Returns:
            True if raw window title changed.
        """
        if prev is None:
            return True
        return prev.window_title != curr.window_title
