"""Temporal expression parser for time range resolution."""

from __future__ import annotations

import re
from datetime import datetime, timedelta


class TemporalParser:
    """Resolves natural language time references to ISO datetime ranges."""

    def resolve_time_range(
        self, text: str, now: datetime | None = None
    ) -> tuple[str, str] | None:
        """Resolve a time expression to a (start_iso, end_iso) tuple.

        Args:
            text: Natural language text containing time references.
            now: Reference time. Defaults to datetime.now().

        Returns:
            Tuple of (start_iso, end_iso) or None if no time reference found.
        """
        if now is None:
            now = datetime.now()

        t = text.lower().strip()

        # "between Xpm and Ypm" / "between Xam and Yam"
        between_match = re.search(
            r"between\s+(\d{1,2})\s*(am|pm)?\s*and\s+(\d{1,2})\s*(am|pm)",
            t,
        )
        if between_match:
            h1 = int(between_match.group(1))
            ampm1 = between_match.group(2) or between_match.group(4)
            h2 = int(between_match.group(3))
            ampm2 = between_match.group(4)
            h1 = self._to_24h(h1, ampm1)
            h2 = self._to_24h(h2, ampm2)
            start = now.replace(hour=h1, minute=0, second=0, microsecond=0)
            end = now.replace(hour=h2, minute=0, second=0, microsecond=0)
            return start.isoformat(), end.isoformat()

        # "at Xpm" / "at Xam"
        at_match = re.search(r"at\s+(\d{1,2})\s*(am|pm)", t)
        if at_match:
            hour = int(at_match.group(1))
            ampm = at_match.group(2)
            hour = self._to_24h(hour, ampm)
            start = now.replace(hour=hour, minute=0, second=0, microsecond=0) - timedelta(minutes=15)
            end = start + timedelta(minutes=30)
            return start.isoformat(), end.isoformat()

        # "today"
        if re.search(r"\btoday\b", t):
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=0)
            return start.isoformat(), end.isoformat()

        # "yesterday"
        if re.search(r"\byesterday\b", t):
            yesterday = now - timedelta(days=1)
            start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end = yesterday.replace(hour=23, minute=59, second=59, microsecond=0)
            return start.isoformat(), end.isoformat()

        # "this morning"
        if re.search(r"\bthis morning\b", t):
            start = now.replace(hour=6, minute=0, second=0, microsecond=0)
            end = now.replace(hour=12, minute=0, second=0, microsecond=0)
            return start.isoformat(), end.isoformat()

        # "this afternoon"
        if re.search(r"\bthis afternoon\b", t):
            start = now.replace(hour=12, minute=0, second=0, microsecond=0)
            end = now.replace(hour=18, minute=0, second=0, microsecond=0)
            return start.isoformat(), end.isoformat()

        # "this evening"
        if re.search(r"\bthis evening\b", t):
            start = now.replace(hour=18, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=0, microsecond=0)
            return start.isoformat(), end.isoformat()

        # "this week" — Monday to now
        if re.search(r"\bthis week\b", t):
            monday = now - timedelta(days=now.weekday())
            start = monday.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=0)
            return start.isoformat(), end.isoformat()

        # "last week" — prev Monday to prev Sunday
        if re.search(r"\blast week\b", t):
            this_monday = now - timedelta(days=now.weekday())
            last_monday = this_monday - timedelta(days=7)
            last_sunday = this_monday - timedelta(days=1)
            start = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
            end = last_sunday.replace(hour=23, minute=59, second=59, microsecond=0)
            return start.isoformat(), end.isoformat()

        return None

    @staticmethod
    def _to_24h(hour: int, ampm: str) -> int:
        """Convert 12-hour time to 24-hour."""
        ampm = ampm.lower()
        if ampm == "am":
            return 0 if hour == 12 else hour
        else:  # pm
            return hour if hour == 12 else hour + 12
