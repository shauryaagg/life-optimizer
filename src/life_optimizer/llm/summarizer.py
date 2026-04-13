"""Hourly and periodic activity summarization."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from life_optimizer.llm.base import BaseLLMClient
from life_optimizer.llm.categorizer import categorize_by_rules
from life_optimizer.storage.database import Database
from life_optimizer.storage.models import ActivityEvent, Summary
from life_optimizer.storage.repositories import EventRepository, SummaryRepository

logger = logging.getLogger(__name__)

HOURLY_SYSTEM = """You are a productivity analyst. Given a list of activity events from the past hour, generate a brief structured summary."""

HOURLY_PROMPT = """Summarize these activities from {start_time} to {end_time}:

Events:
{events_text}

Generate a JSON response with this structure:
{{
    "total_active_minutes": <number>,
    "top_apps": [{{"app": "<name>", "minutes": <n>}}],
    "category_breakdown": {{"<category>": <minutes>}},
    "summary": "<1-2 sentence summary of what the user was doing>"
}}

Respond with ONLY the JSON. No markdown."""


def build_events_text(events: list[ActivityEvent]) -> str:
    """Build a text representation of events for the LLM prompt."""
    lines = []
    for event in events:
        url = ""
        if event.context_json:
            try:
                ctx = json.loads(event.context_json)
                url = ctx.get("url", "")
            except (json.JSONDecodeError, TypeError):
                pass

        parts = [
            f"[{event.timestamp}]",
            event.app_name,
        ]
        if event.window_title:
            parts.append(f'"{event.window_title}"')
        if url:
            parts.append(f"({url})")
        if event.category:
            parts.append(f"[{event.category}]")

        lines.append(" | ".join(parts))

    return "\n".join(lines)


def build_hourly_prompt(
    events: list[ActivityEvent], start_time: str, end_time: str
) -> str:
    """Build the hourly summary prompt from events."""
    events_text = build_events_text(events)
    return HOURLY_PROMPT.format(
        start_time=start_time,
        end_time=end_time,
        events_text=events_text,
    )


def parse_summary_response(response_text: str) -> dict:
    """Parse a summary JSON response from the LLM."""
    text = response_text.strip()

    # Strip markdown fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Try to find a JSON object in the text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            result = json.loads(text[start : end + 1])
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    logger.warning("Failed to parse summary response")
    return {}


def generate_rule_based_summary(
    events: list[ActivityEvent], start_time: str, end_time: str
) -> dict:
    """Generate a summary using rule-based analysis (no LLM needed)."""
    if not events:
        return {
            "total_active_minutes": 0,
            "top_apps": [],
            "category_breakdown": {},
            "summary": "No activity recorded.",
        }

    # Count time per app (rough estimate based on event count)
    app_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}

    for event in events:
        app_counts[event.app_name] = app_counts.get(event.app_name, 0) + 1
        cat = event.category
        if not cat:
            cat, _ = categorize_by_rules(event.app_name, event.context_json)
        category_counts[cat] = category_counts.get(cat, 0) + 1

    total_events = len(events)
    # Rough estimate: assume 60 minutes, distribute by event proportion
    total_minutes = 60

    top_apps = []
    for app, count in sorted(app_counts.items(), key=lambda x: -x[1]):
        minutes = round(count / total_events * total_minutes, 1)
        top_apps.append({"app": app, "minutes": minutes})

    category_breakdown = {}
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        minutes = round(count / total_events * total_minutes, 1)
        category_breakdown[cat] = minutes

    top_app = top_apps[0]["app"] if top_apps else "unknown"
    summary = f"Primarily used {top_app} with {total_events} events recorded."

    return {
        "total_active_minutes": total_minutes,
        "top_apps": top_apps[:5],
        "category_breakdown": category_breakdown,
        "summary": summary,
    }


class Summarizer:
    """Generates hourly and periodic activity summaries."""

    def __init__(self, client: BaseLLMClient | None, db: Database):
        self._client = client
        self._db = db
        self._event_repo = EventRepository(db)
        self._summary_repo = SummaryRepository(db)

    async def generate_hourly_summary(
        self, start_time: str | None = None, end_time: str | None = None
    ) -> Summary | None:
        """Generate a summary for the past hour.

        Args:
            start_time: ISO format start time. Defaults to 1 hour ago.
            end_time: ISO format end time. Defaults to now.

        Returns:
            The created Summary, or None if no events found.
        """
        now = datetime.now(timezone.utc)
        if end_time is None:
            end_time = now.isoformat()
        if start_time is None:
            start_time = (now - timedelta(hours=1)).isoformat()

        events = await self._event_repo.get_events_between(start_time, end_time)
        if not events:
            logger.info("No events found for hourly summary (%s to %s)", start_time, end_time)
            return None

        # Try LLM, fall back to rule-based
        summary_data = None
        model_used = "rule-based"

        if self._client is not None:
            try:
                prompt = build_hourly_prompt(events, start_time, end_time)
                response = await self._client.generate(
                    prompt, system=HOURLY_SYSTEM
                )
                summary_data = parse_summary_response(response)
                if summary_data:
                    model_used = self._client.name
            except Exception as e:
                logger.warning(
                    "LLM summary generation failed, using rule-based: %s", e
                )

        if not summary_data:
            summary_data = generate_rule_based_summary(
                events, start_time, end_time
            )

        # Store the summary
        summary_id = await self._summary_repo.insert_summary(
            period_type="hourly",
            period_start=start_time,
            period_end=end_time,
            summary_text=summary_data.get("summary", ""),
            category_breakdown=json.dumps(
                summary_data.get("category_breakdown", {})
            ),
            top_activities=json.dumps(summary_data.get("top_apps", [])),
            insights=None,
            model_used=model_used,
        )

        return await self._summary_repo.get_summary_by_id(summary_id)
