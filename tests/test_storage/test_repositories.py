"""Tests for the event repository."""

import pytest
from datetime import datetime, timezone

from life_optimizer.collectors.base import CollectorResult
from life_optimizer.constants import POLL, APP_ACTIVATE
from life_optimizer.storage.database import Database
from life_optimizer.storage.repositories import EventRepository


@pytest.fixture
async def db(tmp_path):
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test_repo.db")
    database = Database(db_path)
    await database.initialize()
    yield database
    await database.close()


@pytest.fixture
def repo(db: Database):
    return EventRepository(db)


def _make_result(
    app_name: str = "TestApp",
    event_type: str = POLL,
    window_title: str = "Test Window",
    context: dict | None = None,
    timestamp: datetime | None = None,
) -> CollectorResult:
    return CollectorResult(
        app_name=app_name,
        event_type=event_type,
        window_title=window_title,
        context=context or {},
        timestamp=timestamp or datetime.now(timezone.utc),
    )


async def test_insert_and_get_events(repo: EventRepository):
    """Test that inserted events can be retrieved."""
    result = _make_result(app_name="Chrome", window_title="Google")
    event_id = await repo.insert_event(result)

    assert event_id is not None
    assert event_id > 0

    events = await repo.get_events()
    assert len(events) == 1
    assert events[0].app_name == "Chrome"
    assert events[0].window_title == "Google"
    assert events[0].id == event_id


async def test_insert_multiple_events(repo: EventRepository):
    """Test inserting and retrieving multiple events."""
    for i in range(5):
        await repo.insert_event(_make_result(window_title=f"Window {i}"))

    events = await repo.get_events()
    assert len(events) == 5


async def test_get_event_count(repo: EventRepository):
    """Test event counting."""
    assert await repo.get_event_count() == 0

    await repo.insert_event(_make_result())
    assert await repo.get_event_count() == 1

    await repo.insert_event(_make_result())
    assert await repo.get_event_count() == 2


async def test_get_events_with_app_filter(repo: EventRepository):
    """Test filtering events by app name."""
    await repo.insert_event(_make_result(app_name="Chrome"))
    await repo.insert_event(_make_result(app_name="Slack"))
    await repo.insert_event(_make_result(app_name="Chrome"))

    chrome_events = await repo.get_events(app="Chrome")
    assert len(chrome_events) == 2
    assert all(e.app_name == "Chrome" for e in chrome_events)

    slack_events = await repo.get_events(app="Slack")
    assert len(slack_events) == 1


async def test_get_events_with_date_filter(repo: EventRepository):
    """Test filtering events by date."""
    ts1 = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2025, 1, 16, 10, 0, 0, tzinfo=timezone.utc)

    await repo.insert_event(_make_result(timestamp=ts1, window_title="Day 1"))
    await repo.insert_event(_make_result(timestamp=ts2, window_title="Day 2"))

    day1_events = await repo.get_events(date="2025-01-15")
    assert len(day1_events) == 1
    assert day1_events[0].window_title == "Day 1"

    day2_events = await repo.get_events(date="2025-01-16")
    assert len(day2_events) == 1
    assert day2_events[0].window_title == "Day 2"


async def test_get_events_with_limit(repo: EventRepository):
    """Test that limit parameter works."""
    for i in range(10):
        await repo.insert_event(_make_result(window_title=f"Win {i}"))

    events = await repo.get_events(limit=3)
    assert len(events) == 3


async def test_insert_event_with_context(repo: EventRepository):
    """Test that context JSON is properly stored and retrievable."""
    context = {"url": "https://example.com", "title": "Example"}
    result = _make_result(context=context)
    await repo.insert_event(result)

    events = await repo.get_events()
    assert len(events) == 1
    assert '"url"' in events[0].context_json
    assert "https://example.com" in events[0].context_json


async def test_get_events_ordered_by_timestamp_desc(repo: EventRepository):
    """Test that events are returned in descending timestamp order."""
    ts1 = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2025, 1, 1, 11, 0, 0, tzinfo=timezone.utc)
    ts3 = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    await repo.insert_event(_make_result(timestamp=ts1, window_title="First"))
    await repo.insert_event(_make_result(timestamp=ts3, window_title="Third"))
    await repo.insert_event(_make_result(timestamp=ts2, window_title="Second"))

    events = await repo.get_events()
    assert len(events) == 3
    assert events[0].window_title == "Third"
    assert events[1].window_title == "Second"
    assert events[2].window_title == "First"
