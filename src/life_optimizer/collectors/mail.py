"""Mail.app activity collector using AppleScript."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from life_optimizer.collectors.base import BaseCollector, CollectorResult
from life_optimizer.collectors.jxa_bridge import JXABridge
from life_optimizer.constants import POLL

logger = logging.getLogger(__name__)

# AppleScript to get the frontmost Mail window title
MAIL_TITLE_SCRIPT = """tell application "System Events"
    tell process "Mail"
        try
            set winTitle to name of front window
        on error
            set winTitle to ""
        end try
        return winTitle
    end tell
end tell"""

# AppleScript to get selected message info
MAIL_SELECTION_SCRIPT = """tell application "Mail"
    try
        set sel to selection
        if (count of sel) > 0 then
            set msg to item 1 of sel
            set subj to subject of msg
            set sndr to sender of msg
            return subj & "|" & sndr
        else
            return ""
        end if
    on error
        return ""
    end try
end tell"""


def parse_mail_selection(raw: str) -> dict:
    """Parse the Mail selection AppleScript output.

    Args:
        raw: Raw output from the selection AppleScript ("subject|sender").

    Returns:
        Dict with subject and sender keys.
    """
    if not raw or not raw.strip():
        return {"subject": "", "sender": ""}

    parts = raw.strip().split("|", 1)
    if len(parts) == 2:
        return {"subject": parts[0].strip(), "sender": parts[1].strip()}
    elif len(parts) == 1:
        return {"subject": parts[0].strip(), "sender": ""}
    return {"subject": "", "sender": ""}


class MailCollector(BaseCollector):
    """Collects activity data from Mail.app via AppleScript."""

    app_names: list[str] = ["Mail"]
    bundle_ids: list[str] = ["com.apple.mail"]

    def __init__(self, jxa_bridge: JXABridge):
        self._jxa = jxa_bridge

    async def collect(self, app_name: str, bundle_id: str | None = None) -> CollectorResult | None:
        """Collect Mail.app window title and selected message metadata.

        Args:
            app_name: Name of the application (should be "Mail").
            bundle_id: Bundle identifier.

        Returns:
            CollectorResult with Mail context, or None if unavailable.
        """
        # Get window title
        raw_title = await self._jxa.run_applescript(MAIL_TITLE_SCRIPT)
        if raw_title is None:
            logger.debug("Mail collector returned no data (Mail may not be running)")
            return None

        raw_title = raw_title.strip()

        # Get selected message info
        raw_selection = await self._jxa.run_applescript(MAIL_SELECTION_SCRIPT)
        selection = parse_mail_selection(raw_selection or "")

        context = {
            "subject": selection["subject"],
            "sender": selection["sender"],
            "raw_title": raw_title,
        }

        return CollectorResult(
            app_name=app_name,
            app_bundle_id=bundle_id or "com.apple.mail",
            event_type=POLL,
            window_title=raw_title,
            context=context,
            timestamp=datetime.now(timezone.utc),
        )

    def is_changed(self, prev: CollectorResult | None, curr: CollectorResult) -> bool:
        """Check if the selected message has changed (compares subject + sender).

        Args:
            prev: Previous collection result.
            curr: Current collection result.

        Returns:
            True if subject or sender changed.
        """
        if prev is None:
            return True
        prev_subject = prev.context.get("subject", "")
        curr_subject = curr.context.get("subject", "")
        prev_sender = prev.context.get("sender", "")
        curr_sender = curr.context.get("sender", "")
        return prev_subject != curr_subject or prev_sender != curr_sender
