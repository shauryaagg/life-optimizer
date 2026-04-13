"""Tests for the event repository."""

import pytest
from datetime import datetime, timezone

from life_optimizer.collectors.base import CollectorResult
from life_optimizer.constants import POLL, APP_ACTIVATE
from life_optimizer.screenshots.capture import ScreenshotResult
from life_optimizer.storage.database import Database
from life_optimizer.storage.repositories import (
    EventRepository,
    ScreenshotRepository,
    SessionRepository,
)


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


# --- ScreenshotRepository tests ---


@pytest.fixture
def screenshot_repo(db: Database):
    return ScreenshotRepository(db)


def _make_screenshot(
    app_name: str = "Chrome",
    file_path: str = "data/screenshots/2025-01-15/100000_chrome.jpg",
    timestamp: datetime | None = None,
) -> ScreenshotResult:
    return ScreenshotResult(
        file_path=file_path,
        timestamp=timestamp or datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        file_size_bytes=50000,
        width=960,
        height=540,
        app_name=app_name,
        trigger_reason="interval",
    )


async def test_insert_and_get_screenshots(screenshot_repo: ScreenshotRepository):
    """Test that inserted screenshots can be retrieved."""
    sr = _make_screenshot()
    sid = await screenshot_repo.insert_screenshot(sr)

    assert sid is not None
    assert sid > 0

    screenshots = await screenshot_repo.get_screenshots()
    assert len(screenshots) == 1
    assert screenshots[0].app_name == "Chrome"
    assert screenshots[0].file_path == sr.file_path
    assert screenshots[0].width == 960
    assert screenshots[0].height == 540
    assert screenshots[0].trigger_reason == "interval"


async def test_get_screenshots_with_date_filter(screenshot_repo: ScreenshotRepository):
    """Test filtering screenshots by date."""
    ts1 = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2025, 1, 16, 10, 0, 0, tzinfo=timezone.utc)

    await screenshot_repo.insert_screenshot(_make_screenshot(timestamp=ts1))
    await screenshot_repo.insert_screenshot(
        _make_screenshot(timestamp=ts2, file_path="data/screenshots/2025-01-16/100000_chrome.jpg")
    )

    day1 = await screenshot_repo.get_screenshots(date="2025-01-15")
    assert len(day1) == 1

    day2 = await screenshot_repo.get_screenshots(date="2025-01-16")
    assert len(day2) == 1


async def test_get_screenshots_with_limit(screenshot_repo: ScreenshotRepository):
    """Test that limit parameter works for screenshots."""
    for i in range(5):
        await screenshot_repo.insert_screenshot(
            _make_screenshot(file_path=f"data/screenshots/2025-01-15/{i:06d}_chrome.jpg")
        )

    screenshots = await screenshot_repo.get_screenshots(limit=2)
    assert len(screenshots) == 2


# --- SessionRepository tests ---


@pytest.fixture
def session_repo(db: Database):
    return SessionRepository(db)


async def test_start_and_get_session(session_repo: SessionRepository):
    """Test starting a session and retrieving it."""
    sid = await session_repo.start_session("Chrome", "com.google.Chrome", "Google")

    assert sid is not None
    assert sid > 0

    sessions = await session_repo.get_sessions()
    assert len(sessions) == 1
    assert sessions[0].app_name == "Chrome"
    assert sessions[0].app_bundle_id == "com.google.Chrome"
    assert sessions[0].title_summary == "Google"
    assert sessions[0].end_time is None


async def test_end_session(session_repo: SessionRepository):
    """Test ending a session sets end_time, duration, and event_count."""
    sid = await session_repo.start_session("Chrome")

    # Retrieve to get start_time
    sessions = await session_repo.get_sessions()
    start_time = sessions[0].start_time

    # End the session a bit later
    end_dt = datetime.fromisoformat(start_time)
    from datetime import timedelta

    end_time = (end_dt + timedelta(seconds=120)).isoformat()
    await session_repo.end_session(sid, end_time, event_count=5)

    sessions = await session_repo.get_sessions()
    assert len(sessions) == 1
    assert sessions[0].end_time == end_time
    assert sessions[0].event_count == 5
    assert sessions[0].duration_seconds is not None
    assert abs(sessions[0].duration_seconds - 120.0) < 1.0


async def test_get_sessions_with_date_filter(session_repo: SessionRepository):
    """Test filtering sessions by date."""
    await session_repo.start_session("Chrome")
    await session_repo.start_session("Slack")

    # Both sessions started "now" so they share the same date
    sessions = await session_repo.get_sessions()
    assert len(sessions) == 2

    # Filter by a date that won't match
    sessions_none = await session_repo.get_sessions(date="2020-01-01")
    assert len(sessions_none) == 0
