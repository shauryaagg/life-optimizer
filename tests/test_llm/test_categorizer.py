"""Tests for the activity categorizer."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from life_optimizer.collectors.base import CollectorResult
from life_optimizer.constants import POLL
from life_optimizer.llm.categorizer import (
    categorize_by_rules,
    parse_llm_categorization,
    Categorizer,
)
from life_optimizer.storage.database import Database
from life_optimizer.storage.repositories import EventRepository


def test_rule_based_chrome_github():
    """Chrome + github.com should categorize as Deep Work."""
    context = json.dumps({"url": "https://github.com/user/repo"})
    category, subcategory = categorize_by_rules("Google Chrome", context)
    assert category == "Deep Work"


def test_rule_based_chrome_twitter():
    """Chrome + twitter.com should categorize as Social Media."""
    context = json.dumps({"url": "https://twitter.com/home"})
    category, subcategory = categorize_by_rules("Google Chrome", context)
    assert category == "Social Media"


def test_rule_based_chrome_x():
    """Chrome + x.com should categorize as Social Media."""
    context = json.dumps({"url": "https://x.com/home"})
    category, subcategory = categorize_by_rules("Google Chrome", context)
    assert category == "Social Media"


def test_rule_based_slack():
    """Slack app should categorize as Communication."""
    category, subcategory = categorize_by_rules("Slack")
    assert category == "Communication"


def test_rule_based_vscode():
    """VS Code (named 'Code') should categorize as Deep Work."""
    category, subcategory = categorize_by_rules("Code")
    assert category == "Deep Work"


def test_rule_based_terminal():
    """Terminal should categorize as Deep Work."""
    category, subcategory = categorize_by_rules("Terminal")
    assert category == "Deep Work"


def test_rule_based_unknown_app():
    """Unknown app should categorize as Other."""
    category, subcategory = categorize_by_rules("SomeRandomApp")
    assert category == "Other"
    assert subcategory == "somerandomapp"


def test_rule_based_chrome_no_url():
    """Chrome without a URL should categorize as Browsing."""
    category, subcategory = categorize_by_rules("Google Chrome")
    assert category == "Browsing"


def test_rule_based_spotify():
    """Spotify should categorize as Entertainment."""
    category, subcategory = categorize_by_rules("Spotify")
    assert category == "Entertainment"


def test_rule_based_calendar():
    """Calendar should categorize as Planning."""
    category, subcategory = categorize_by_rules("Calendar")
    assert category == "Planning"


def test_rule_based_youtube():
    """Chrome + youtube.com should categorize as Entertainment."""
    context = json.dumps({"url": "https://www.youtube.com/watch?v=abc"})
    category, subcategory = categorize_by_rules("Google Chrome", context)
    assert category == "Entertainment"


def test_rule_based_reddit():
    """Chrome + reddit.com should categorize as Social Media."""
    context = json.dumps({"url": "https://www.reddit.com/r/python"})
    category, subcategory = categorize_by_rules("Google Chrome", context)
    assert category == "Social Media"


def test_rule_based_notion_url():
    """Chrome + notion.so should categorize as Planning."""
    context = json.dumps({"url": "https://notion.so/page"})
    category, subcategory = categorize_by_rules("Google Chrome", context)
    assert category == "Planning"


def test_rule_based_gmail():
    """Chrome + mail.google.com should categorize as Communication."""
    context = json.dumps({"url": "https://mail.google.com/mail/u/0/"})
    category, subcategory = categorize_by_rules("Google Chrome", context)
    assert category == "Communication"


def test_rule_based_invalid_context_json():
    """Invalid context JSON should not crash, should fall back gracefully."""
    category, subcategory = categorize_by_rules("Google Chrome", "not-json")
    assert category == "Browsing"


def test_parse_llm_response_valid():
    """Test parsing a well-formed LLM categorization response."""
    response = json.dumps([
        {"id": 1, "category": "Deep Work", "subcategory": "coding-python"},
        {"id": 2, "category": "Social Media", "subcategory": "twitter-timeline"},
    ])
    result = parse_llm_categorization(response)
    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[0]["category"] == "Deep Work"
    assert result[1]["subcategory"] == "twitter-timeline"


def test_parse_llm_response_with_markdown_fences():
    """Test parsing LLM response wrapped in markdown code fences."""
    response = '```json\n[{"id": 1, "category": "Deep Work", "subcategory": "coding"}]\n```'
    result = parse_llm_categorization(response)
    assert len(result) == 1
    assert result[0]["category"] == "Deep Work"


def test_parse_llm_response_with_extra_text():
    """Test parsing when LLM adds explanation text around JSON."""
    response = 'Here are the results:\n[{"id": 1, "category": "Other", "subcategory": "misc"}]\nDone!'
    result = parse_llm_categorization(response)
    assert len(result) == 1
    assert result[0]["category"] == "Other"


def test_parse_llm_response_malformed():
    """Test that malformed responses return empty list."""
    result = parse_llm_categorization("This is not JSON at all")
    assert result == []


def test_parse_llm_response_empty():
    """Test that empty string returns empty list."""
    result = parse_llm_categorization("")
    assert result == []


# --- LLM-based categorization with mock ---


@pytest.fixture
async def db(tmp_path):
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test_categorizer.db")
    database = Database(db_path)
    await database.initialize()
    yield database
    await database.close()


def _make_result(
    app_name: str = "TestApp",
    event_type: str = POLL,
    window_title: str = "Test Window",
    context: dict | None = None,
) -> CollectorResult:
    from datetime import datetime, timezone
    return CollectorResult(
        app_name=app_name,
        event_type=event_type,
        window_title=window_title,
        context=context or {},
        timestamp=datetime.now(timezone.utc),
    )


async def test_llm_categorization_with_mock(db):
    """Test LLM-based categorization with a mock client."""
    repo = EventRepository(db)

    # Insert uncategorized events
    await repo.insert_event(_make_result(app_name="Code", window_title="main.py"))
    await repo.insert_event(
        _make_result(
            app_name="Google Chrome",
            window_title="Twitter",
            context={"url": "https://twitter.com"},
        )
    )

    # Get the event IDs
    events = await repo.get_uncategorized_events()
    assert len(events) == 2

    # Create mock LLM client
    mock_client = AsyncMock()
    mock_client.generate = AsyncMock(
        return_value=json.dumps([
            {"id": events[0].id, "category": "Deep Work", "subcategory": "coding-python"},
            {"id": events[1].id, "category": "Social Media", "subcategory": "twitter-timeline"},
        ])
    )

    categorizer = Categorizer(mock_client, db)
    count = await categorizer.categorize_uncategorized()
    assert count == 2

    # Verify categories were set
    remaining = await repo.get_uncategorized_events()
    assert len(remaining) == 0


async def test_categorizer_rule_based_fallback(db):
    """Test categorization falls back to rules when no LLM client."""
    repo = EventRepository(db)

    await repo.insert_event(_make_result(app_name="Slack", window_title="General"))
    await repo.insert_event(_make_result(app_name="Code", window_title="test.py"))

    categorizer = Categorizer(None, db)
    count = await categorizer.categorize_uncategorized()
    assert count == 2

    remaining = await repo.get_uncategorized_events()
    assert len(remaining) == 0


async def test_categorizer_handles_llm_failure(db):
    """Test that categorizer falls back to rules when LLM fails."""
    repo = EventRepository(db)

    await repo.insert_event(_make_result(app_name="Slack", window_title="DM"))

    mock_client = AsyncMock()
    mock_client.generate = AsyncMock(side_effect=Exception("API Error"))

    categorizer = Categorizer(mock_client, db)
    count = await categorizer.categorize_uncategorized()
    assert count == 1

    remaining = await repo.get_uncategorized_events()
    assert len(remaining) == 0
