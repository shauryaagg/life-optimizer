"""Tests for the activity summarizer."""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from life_optimizer.collectors.base import CollectorResult
from life_optimizer.constants import POLL
from life_optimizer.llm.summarizer import (
    build_events_text,
    build_hourly_prompt,
    parse_summary_response,
    generate_rule_based_summary,
    Summarizer,
)
from life_optimizer.storage.database import Database
from life_optimizer.storage.models import ActivityEvent
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


def test_build_events_text():
    """Test building events text from activity events."""
    events = [
        _make_activity_event(
            id=1,
            app_name="Code",
            window_title="main.py",
            category="Deep Work",
        ),
        _make_activity_event(
            id=2,
            app_name="Google Chrome",
            window_title="GitHub",
            context_json=json.dumps({"url": "https://github.com"}),
        ),
    ]
    text = build_events_text(events)
    assert "Code" in text
    assert "main.py" in text
    assert "GitHub" in text
    assert "github.com" in text
    assert "Deep Work" in text


def test_build_hourly_prompt():
    """Test building the hourly summary prompt."""
    events = [
        _make_activity_event(id=1, app_name="Code", window_title="test.py"),
    ]
    prompt = build_hourly_prompt(events, "2025-01-15T10:00:00", "2025-01-15T11:00:00")
    assert "2025-01-15T10:00:00" in prompt
    assert "2025-01-15T11:00:00" in prompt
    assert "Code" in prompt
    assert "test.py" in prompt


def test_parse_summary_response_valid():
    """Test parsing a valid summary response."""
    response = json.dumps({
        "total_active_minutes": 45,
        "top_apps": [{"app": "Code", "minutes": 30}],
        "category_breakdown": {"Deep Work": 30, "Browsing": 15},
        "summary": "Mostly coding in VS Code.",
    })
    result = parse_summary_response(response)
    assert result["total_active_minutes"] == 45
    assert result["summary"] == "Mostly coding in VS Code."
    assert len(result["top_apps"]) == 1


def test_parse_summary_response_with_fences():
    """Test parsing summary wrapped in markdown code fences."""
    response = '```json\n{"total_active_minutes": 30, "summary": "Working."}\n```'
    result = parse_summary_response(response)
    assert result["total_active_minutes"] == 30


def test_parse_summary_response_malformed():
    """Test that malformed responses return empty dict."""
    result = parse_summary_response("not json")
    assert result == {}


def test_parse_summary_response_with_surrounding_text():
    """Test parsing when LLM adds explanation around JSON."""
    response = 'Here is the summary:\n{"total_active_minutes": 20, "summary": "Browsing."}\nEnd.'
    result = parse_summary_response(response)
    assert result["total_active_minutes"] == 20


def test_generate_rule_based_summary():
    """Test rule-based summary generation."""
    events = [
        _make_activity_event(id=1, app_name="Code", category="Deep Work"),
        _make_activity_event(id=2, app_name="Code", category="Deep Work"),
        _make_activity_event(id=3, app_name="Slack", category="Communication"),
    ]
    result = generate_rule_based_summary(
        events, "2025-01-15T10:00:00", "2025-01-15T11:00:00"
    )
    assert result["total_active_minutes"] == 60
    assert len(result["top_apps"]) == 2
    assert "Deep Work" in result["category_breakdown"]
    assert "Communication" in result["category_breakdown"]
    assert "Code" in result["summary"]


def test_generate_rule_based_summary_empty():
    """Test rule-based summary with no events."""
    result = generate_rule_based_summary([], "2025-01-15T10:00:00", "2025-01-15T11:00:00")
    assert result["total_active_minutes"] == 0
    assert result["top_apps"] == []
    assert "No activity" in result["summary"]


# --- Integration tests with mock LLM ---


@pytest.fixture
async def db(tmp_path):
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test_summarizer.db")
    database = Database(db_path)
    await database.initialize()
    yield database
    await database.close()


def _make_result(
    app_name: str = "TestApp",
    window_title: str = "Test Window",
    context: dict | None = None,
    timestamp: datetime | None = None,
) -> CollectorResult:
    return CollectorResult(
        app_name=app_name,
        event_type=POLL,
        window_title=window_title,
        context=context or {},
        timestamp=timestamp or datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
    )


async def test_summarizer_with_mock_llm(db):
    """Test summarizer with a mock LLM client."""
    repo = EventRepository(db)
    await repo.insert_event(_make_result(app_name="Code", window_title="main.py"))
    await repo.insert_event(_make_result(app_name="Slack", window_title="General"))

    mock_client = AsyncMock()
    mock_client.name = "mock-llm"
    mock_client.generate = AsyncMock(
        return_value=json.dumps({
            "total_active_minutes": 45,
            "top_apps": [{"app": "Code", "minutes": 30}],
            "category_breakdown": {"Deep Work": 30, "Communication": 15},
            "summary": "Mostly coding, some Slack.",
        })
    )

    summarizer = Summarizer(mock_client, db)
    summary = await summarizer.generate_hourly_summary(
        start_time="2025-01-15T10:00:00",
        end_time="2025-01-15T11:00:00",
    )

    assert summary is not None
    assert "Mostly coding" in summary.summary_text
    assert summary.model_used == "mock-llm"


async def test_summarizer_rule_based_fallback(db):
    """Test summarizer falls back to rule-based when no LLM."""
    repo = EventRepository(db)
    await repo.insert_event(_make_result(app_name="Code", window_title="test.py"))

    summarizer = Summarizer(None, db)
    summary = await summarizer.generate_hourly_summary(
        start_time="2025-01-15T10:00:00",
        end_time="2025-01-15T11:00:00",
    )

    assert summary is not None
    assert summary.model_used == "rule-based"


async def test_summarizer_no_events(db):
    """Test summarizer returns None when there are no events."""
    summarizer = Summarizer(None, db)
    summary = await summarizer.generate_hourly_summary(
        start_time="2025-01-15T10:00:00",
        end_time="2025-01-15T11:00:00",
    )
    assert summary is None
