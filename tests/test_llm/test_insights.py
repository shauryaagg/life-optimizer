"""Tests for the daily insights generator."""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from life_optimizer.collectors.base import CollectorResult
from life_optimizer.constants import POLL
from life_optimizer.llm.insights import (
    build_daily_prompt,
    generate_rule_based_insights,
    InsightGenerator,
)
from life_optimizer.storage.database import Database
from life_optimizer.storage.models import ActivityEvent, Summary
from life_optimizer.storage.repositories import EventRepository


def _make_activity_event(
    id: int = 1,
    app_name: str = "TestApp",
    timestamp: str = "2025-01-15T10:00:00",
    window_title: str = "Test Window",
    context_json: str | None = None,
    category: str | None = None,
) -> ActivityEvent:
    return ActivityEvent(
        id=id,
        timestamp=timestamp,
        app_name=app_name,
        event_type=POLL,
        window_title=window_title,
        context_json=context_json,
        category=category,
    )


def _make_summary(
    id: int = 1,
    period_type: str = "hourly",
    period_start: str = "2025-01-15T10:00:00",
    period_end: str = "2025-01-15T11:00:00",
    summary_text: str = "Test summary.",
) -> Summary:
    return Summary(
        id=id,
        period_type=period_type,
        period_start=period_start,
        period_end=period_end,
        summary_text=summary_text,
    )


def test_build_daily_prompt():
    """Test building the daily insights prompt."""
    events = [
        _make_activity_event(id=1, app_name="Code", category="Deep Work"),
        _make_activity_event(id=2, app_name="Slack", category="Communication"),
    ]
    summaries = [
        _make_summary(summary_text="Coded for most of the hour."),
    ]
    prompt = build_daily_prompt("2025-01-15", summaries, events, [])
    assert "2025-01-15" in prompt
    assert "Deep Work" in prompt
    assert "Communication" in prompt
    assert "Code" in prompt
    assert "Slack" in prompt
    assert "Coded for most of the hour" in prompt


def test_build_daily_prompt_no_summaries():
    """Test building the daily prompt when there are no hourly summaries."""
    events = [
        _make_activity_event(id=1, app_name="Code", category="Deep Work"),
    ]
    prompt = build_daily_prompt("2025-01-15", [], events, [])
    assert "No hourly summaries" in prompt


def test_generate_rule_based_insights():
    """Test rule-based insight generation."""
    events = [
        _make_activity_event(id=1, app_name="Code", category="Deep Work"),
        _make_activity_event(id=2, app_name="Code", category="Deep Work"),
        _make_activity_event(id=3, app_name="Slack", category="Communication"),
        _make_activity_event(id=4, app_name="Google Chrome", category="Browsing"),
    ]
    result = generate_rule_based_insights("2025-01-15", events, [])
    assert "2025-01-15" in result
    assert "Deep Work" in result
    assert "Communication" in result
    assert "Code" in result
    assert "TOTAL EVENTS: 4" in result


def test_generate_rule_based_insights_no_events():
    """Test rule-based insights with no events."""
    result = generate_rule_based_insights("2025-01-15", [], [])
    assert "No activity data" in result


# --- Integration tests with mock LLM ---


@pytest.fixture
async def db(tmp_path):
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test_insights.db")
    database = Database(db_path)
    await database.initialize()
    yield database
    await database.close()


def _make_result(
    app_name: str = "TestApp",
    window_title: str = "Test Window",
    context: dict | None = None,
) -> CollectorResult:
    return CollectorResult(
        app_name=app_name,
        event_type=POLL,
        window_title=window_title,
        context=context or {},
        timestamp=datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
    )


async def test_insight_generator_with_mock_llm(db):
    """Test daily insights with a mock LLM client."""
    repo = EventRepository(db)
    await repo.insert_event(_make_result(app_name="Code", window_title="main.py"))
    await repo.insert_event(_make_result(app_name="Slack", window_title="General"))

    mock_client = AsyncMock()
    mock_client.name = "mock-llm"
    mock_client.generate = AsyncMock(
        return_value="## Daily Report\nYou spent most of your time coding. Good focus today."
    )

    generator = InsightGenerator(mock_client, db)
    summary = await generator.generate_daily_insights(date="2025-01-15")

    assert summary is not None
    assert "coding" in summary.summary_text
    assert summary.model_used == "mock-llm"


async def test_insight_generator_rule_based_fallback(db):
    """Test insights falls back to rule-based when no LLM."""
    repo = EventRepository(db)
    await repo.insert_event(_make_result(app_name="Code", window_title="test.py"))

    generator = InsightGenerator(None, db)
    summary = await generator.generate_daily_insights(date="2025-01-15")

    assert summary is not None
    assert summary.model_used == "rule-based"
    assert "Code" in summary.summary_text


async def test_insight_generator_no_events(db):
    """Test insights returns None when there are no events."""
    generator = InsightGenerator(None, db)
    summary = await generator.generate_daily_insights(date="2025-01-15")
    assert summary is None
