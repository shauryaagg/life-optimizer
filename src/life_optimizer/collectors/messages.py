"""iMessage/Messages.app activity collector using AppleScript."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from life_optimizer.collectors.base import BaseCollector, CollectorResult
from life_optimizer.collectors.jxa_bridge import JXABridge
from life_optimizer.constants import POLL

logger = logging.getLogger(__name__)

# AppleScript to get the frontmost Messages window title
MESSAGES_TITLE_SCRIPT = """tell application "System Events"
    tell process "Messages"
        try
            set winTitle to name of front window
        on error
            set winTitle to ""
        end try
        return winTitle
    end tell
end tell"""

# AppleScript to get recent conversation metadata (NOT message content)
MESSAGES_CONVERSATIONS_SCRIPT = """tell application "Messages"
    try
        set convos to conversations 1 thru 5
        set output to ""
        repeat with conv in convos
            set convName to name of conv
            set convID to id of conv
            set pCount to count of participants of conv
            set output to output & convName & "|" & convID & "|" & pCount & "\\n"
        end repeat
        return output
    on error errMsg
        return "ERROR:" & errMsg
    end try
end tell"""


def parse_conversations(raw: str) -> list[dict]:
    """Parse the AppleScript conversations output into a list of dicts.

    Args:
        raw: Raw output from the conversations AppleScript.

    Returns:
        List of dicts with name, id, and participant_count keys.
    """
    conversations = []
    if not raw or raw.startswith("ERROR:"):
        return conversations

    for line in raw.strip().split("\\n"):
        line = line.strip()
        if not line:
            continue
        parts = line.split("|", 2)
        if len(parts) == 3:
            conversations.append({
                "name": parts[0].strip(),
                "id": parts[1].strip(),
                "participant_count": int(parts[2].strip()) if parts[2].strip().isdigit() else 0,
            })
    return conversations


class MessagesCollector(BaseCollector):
    """Collects activity data from Messages.app via AppleScript."""

    app_names: list[str] = ["Messages"]
    bundle_ids: list[str] = ["com.apple.MobileSMS"]

    def __init__(self, jxa_bridge: JXABridge):
        self._jxa = jxa_bridge

    async def collect(self, app_name: str, bundle_id: str | None = None) -> CollectorResult | None:
        """Collect Messages.app window title and conversation metadata.

        Args:
            app_name: Name of the application (should be "Messages").
            bundle_id: Bundle identifier.

        Returns:
            CollectorResult with Messages context, or None if unavailable.
        """
        # Get window title (shows active conversation)
        raw_title = await self._jxa.run_applescript(MESSAGES_TITLE_SCRIPT)
        if raw_title is None:
            logger.debug("Messages collector returned no data (Messages may not be running)")
            return None

        raw_title = raw_title.strip()

        # Get conversation metadata
        raw_convos = await self._jxa.run_applescript(MESSAGES_CONVERSATIONS_SCRIPT)
        conversations = parse_conversations(raw_convos or "")

        context = {
            "conversations": conversations,
            "active_conversation": raw_title if raw_title else None,
        }

        return CollectorResult(
            app_name=app_name,
            app_bundle_id=bundle_id or "com.apple.MobileSMS",
            event_type=POLL,
            window_title=raw_title,
            context=context,
            timestamp=datetime.now(timezone.utc),
        )

    def is_changed(self, prev: CollectorResult | None, curr: CollectorResult) -> bool:
        """Check if the active conversation has changed (compares window title).

        Args:
            prev: Previous collection result.
            curr: Current collection result.

        Returns:
            True if window title changed.
        """
        if prev is None:
            return True
        return prev.window_title != curr.window_title
