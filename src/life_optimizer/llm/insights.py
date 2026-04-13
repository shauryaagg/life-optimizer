"""Daily behavioral insights generation."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from life_optimizer.llm.base import BaseLLMClient
from life_optimizer.llm.categorizer import categorize_by_rules
from life_optimizer.storage.database import Database
from life_optimizer.storage.models import Summary
from life_optimizer.storage.repositories import (
    EventRepository,
    SessionRepository,
    SummaryRepository,
)

logger = logging.getLogger(__name__)

DAILY_SYSTEM = """You are a personal productivity coach analyzing a full day of computer activity. Be direct, specific, and actionable. Don't sugarcoat -- if the user wasted time, say so. Use the exact numbers from the data."""

DAILY_PROMPT = """Here is the complete activity data for {date}:

HOURLY SUMMARIES:
{hourly_summaries}

RAW CATEGORY BREAKDOWN:
{category_breakdown}

TOP APPS BY TIME:
{top_apps}

SESSIONS:
{sessions_text}

Generate a comprehensive daily report with this structure:

1. TIME BREAKDOWN by category (work, communication, social, entertainment, etc.) with exact hours:minutes
2. TOP APPS with time spent and what specifically was being done
3. CONTEXT SWITCHES: total count and average focus block duration
4. BEHAVIORAL PATTERNS: anything notable (excessive social media, long focus blocks, late-night work, etc.)
5. ACTIONABLE INSIGHTS: 2-3 specific, actionable suggestions for tomorrow

Be blunt and specific. Use actual numbers. Format for readability."""


def build_daily_prompt(
    date: str,
    hourly_summaries: list[Summary],
    events: list,
    sessions: list,
) -> str:
    """Build the daily insights prompt from collected data."""
    # Format hourly summaries
    hourly_lines = []
    for s in hourly_summaries:
        hourly_lines.append(
            f"  {s.period_start} - {s.period_end}: {s.summary_text}"
        )
    hourly_text = "\n".join(hourly_lines) if hourly_lines else "  No hourly summaries available."

    # Compute category breakdown from events
    category_counts: dict[str, int] = {}
    app_counts: dict[str, int] = {}
    for event in events:
        cat = event.category
        if not cat:
            cat, _ = categorize_by_rules(event.app_name, event.context_json)
        category_counts[cat] = category_counts.get(cat, 0) + 1
        app_counts[event.app_name] = app_counts.get(event.app_name, 0) + 1

    total_events = len(events) or 1
    cat_lines = []
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        pct = round(count / total_events * 100, 1)
        cat_lines.append(f"  {cat}: {count} events ({pct}%)")
    category_text = "\n".join(cat_lines) if cat_lines else "  No data."

    app_lines = []
    for app, count in sorted(app_counts.items(), key=lambda x: -x[1])[:10]:
        pct = round(count / total_events * 100, 1)
        app_lines.append(f"  {app}: {count} events ({pct}%)")
    apps_text = "\n".join(app_lines) if app_lines else "  No data."

    # Format sessions
    session_lines = []
    for s in sessions:
        dur = f"{s.duration_seconds:.0f}s" if s.duration_seconds else "ongoing"
        session_lines.append(f"  {s.app_name}: {s.start_time} ({dur})")
    sessions_text = "\n".join(session_lines[:20]) if session_lines else "  No sessions."

    return DAILY_PROMPT.format(
        date=date,
        hourly_summaries=hourly_text,
        category_breakdown=category_text,
        top_apps=apps_text,
        sessions_text=sessions_text,
    )


def generate_rule_based_insights(
    date: str,
    events: list,
    sessions: list,
) -> str:
    """Generate a basic daily report without an LLM."""
    if not events:
        return f"No activity data recorded for {date}."

    category_counts: dict[str, int] = {}
    app_counts: dict[str, int] = {}
    for event in events:
        cat = event.category
        if not cat:
            cat, _ = categorize_by_rules(event.app_name, event.context_json)
        category_counts[cat] = category_counts.get(cat, 0) + 1
        app_counts[event.app_name] = app_counts.get(event.app_name, 0) + 1

    total = len(events)
    lines = [f"Daily Activity Report for {date}", "=" * 40, ""]

    lines.append("CATEGORY BREAKDOWN:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        pct = round(count / total * 100, 1)
        lines.append(f"  {cat}: {count} events ({pct}%)")

    lines.append("")
    lines.append("TOP APPS:")
    for app, count in sorted(app_counts.items(), key=lambda x: -x[1])[:10]:
        pct = round(count / total * 100, 1)
        lines.append(f"  {app}: {count} events ({pct}%)")

    lines.append("")
    lines.append(f"SESSIONS: {len(sessions)} total")
    lines.append(f"TOTAL EVENTS: {total}")

    return "\n".join(lines)


class InsightGenerator:
    """Generates daily behavioral insights."""

    def __init__(self, client: BaseLLMClient | None, db: Database):
        self._client = client
        self._db = db
        self._event_repo = EventRepository(db)
        self._session_repo = SessionRepository(db)
        self._summary_repo = SummaryRepository(db)

    async def generate_daily_insights(self, date: str | None = None) -> Summary | None:
        """Generate insights for a given day.

        Args:
            date: Date in YYYY-MM-DD format. Defaults to today.

        Returns:
            The created Summary, or None if no data available.
        """
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Gather data
        start_time = f"{date}T00:00:00"
        end_time = f"{date}T23:59:59"

        events = await self._event_repo.get_events_between(start_time, end_time)
        if not events:
            logger.info("No events found for daily insights on %s", date)
            return None

        sessions = await self._session_repo.get_sessions(date=date)
        hourly_summaries = await self._summary_repo.get_summaries(
            period_type="hourly", date=date
        )

        # Try LLM, fall back to rule-based
        insights_text = None
        model_used = "rule-based"

        if self._client is not None:
            try:
                prompt = build_daily_prompt(
                    date, hourly_summaries, events, sessions
                )
                response = await self._client.generate(
                    prompt, system=DAILY_SYSTEM
                )
                insights_text = response
                model_used = self._client.name
            except Exception as e:
                logger.warning(
                    "LLM insights generation failed, using rule-based: %s", e
                )

        if not insights_text:
            insights_text = generate_rule_based_insights(date, events, sessions)

        # Compute category breakdown for storage
        category_counts: dict[str, int] = {}
        app_counts: dict[str, int] = {}
        for event in events:
            cat = event.category or "Other"
            category_counts[cat] = category_counts.get(cat, 0) + 1
            app_counts[event.app_name] = app_counts.get(event.app_name, 0) + 1

        top_apps = [
            {"app": app, "events": count}
            for app, count in sorted(app_counts.items(), key=lambda x: -x[1])[:10]
        ]

        summary_id = await self._summary_repo.insert_summary(
            period_type="daily",
            period_start=start_time,
            period_end=end_time,
            summary_text=insights_text,
            category_breakdown=json.dumps(category_counts),
            top_activities=json.dumps(top_apps),
            insights=insights_text,
            model_used=model_used,
        )

        return await self._summary_repo.get_summary_by_id(summary_id)
