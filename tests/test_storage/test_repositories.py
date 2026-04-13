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
    SummaryRepository,
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


# --- EventRepository new methods ---


async def test_update_event_category(repo: EventRepository):
    """Test updating the category and subcategory of an event."""
    result = _make_result(app_name="Code", window_title="main.py")
    event_id = await repo.insert_event(result)

    await repo.update_event_category(event_id, "Deep Work", "coding-python")

    events = await repo.get_events()
    assert len(events) == 1
    assert events[0].category == "Deep Work"
    assert events[0].subcategory == "coding-python"


async def test_get_uncategorized_events(repo: EventRepository):
    """Test retrieving uncategorized events."""
    # Insert two events, categorize one
    id1 = await repo.insert_event(_make_result(app_name="Code"))
    id2 = await repo.insert_event(_make_result(app_name="Slack"))

    await repo.update_event_category(id1, "Deep Work", "coding")

    uncategorized = await repo.get_uncategorized_events()
    assert len(uncategorized) == 1
    assert uncategorized[0].app_name == "Slack"


async def test_get_uncategorized_events_limit(repo: EventRepository):
    """Test that limit works for uncategorized events."""
    for i in range(5):
        await repo.insert_event(_make_result(window_title=f"Win {i}"))

    uncategorized = await repo.get_uncategorized_events(limit=2)
    assert len(uncategorized) == 2


async def test_get_events_between(repo: EventRepository):
    """Test retrieving events within a time range."""
    ts1 = datetime(2025, 1, 15, 9, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    ts3 = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

    await repo.insert_event(_make_result(timestamp=ts1, window_title="Morning"))
    await repo.insert_event(_make_result(timestamp=ts2, window_title="Mid"))
    await repo.insert_event(_make_result(timestamp=ts3, window_title="Afternoon"))

    events = await repo.get_events_between(
        "2025-01-15T10:00:00", "2025-01-15T11:00:00"
    )
    assert len(events) == 1
    assert events[0].window_title == "Mid"


async def test_get_events_between_inclusive(repo: EventRepository):
    """Test that get_events_between is inclusive on both ends."""
    ts = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    await repo.insert_event(_make_result(timestamp=ts, window_title="Exact"))

    events = await repo.get_events_between(
        "2025-01-15T10:00:00", "2025-01-15T10:00:00+00:00"
    )
    assert len(events) == 1


# --- SummaryRepository tests ---


@pytest.fixture
def summary_repo(db: Database):
    return SummaryRepository(db)


async def test_insert_and_get_summary(summary_repo: SummaryRepository):
    """Test inserting and retrieving a summary."""
    sid = await summary_repo.insert_summary(
        period_type="hourly",
        period_start="2025-01-15T10:00:00",
        period_end="2025-01-15T11:00:00",
        summary_text="Mostly coding in VS Code.",
        category_breakdown='{"Deep Work": 40}',
        top_activities='[{"app": "Code", "minutes": 40}]',
        model_used="test-model",
    )
    assert sid is not None
    assert sid > 0

    summaries = await summary_repo.get_summaries()
    assert len(summaries) == 1
    assert summaries[0].period_type == "hourly"
    assert summaries[0].summary_text == "Mostly coding in VS Code."
    assert summaries[0].model_used == "test-model"


async def test_get_summaries_with_type_filter(summary_repo: SummaryRepository):
    """Test filtering summaries by period type."""
    await summary_repo.insert_summary(
        period_type="hourly",
        period_start="2025-01-15T10:00:00",
        period_end="2025-01-15T11:00:00",
        summary_text="Hourly summary.",
    )
    await summary_repo.insert_summary(
        period_type="daily",
        period_start="2025-01-15T00:00:00",
        period_end="2025-01-15T23:59:59",
        summary_text="Daily summary.",
    )

    hourly = await summary_repo.get_summaries(period_type="hourly")
    assert len(hourly) == 1
    assert hourly[0].period_type == "hourly"

    daily = await summary_repo.get_summaries(period_type="daily")
    assert len(daily) == 1
    assert daily[0].period_type == "daily"


async def test_get_latest_summary(summary_repo: SummaryRepository):
    """Test getting the most recent summary of a given type."""
    await summary_repo.insert_summary(
        period_type="hourly",
        period_start="2025-01-15T09:00:00",
        period_end="2025-01-15T10:00:00",
        summary_text="First.",
    )
    await summary_repo.insert_summary(
        period_type="hourly",
        period_start="2025-01-15T10:00:00",
        period_end="2025-01-15T11:00:00",
        summary_text="Second.",
    )

    latest = await summary_repo.get_latest_summary("hourly")
    assert latest is not None
    assert latest.summary_text == "Second."


async def test_get_latest_summary_none(summary_repo: SummaryRepository):
    """Test get_latest_summary returns None when no summaries exist."""
    latest = await summary_repo.get_latest_summary("hourly")
    assert latest is None


async def test_get_summary_by_id(summary_repo: SummaryRepository):
    """Test getting a summary by its ID."""
    sid = await summary_repo.insert_summary(
        period_type="daily",
        period_start="2025-01-15T00:00:00",
        period_end="2025-01-15T23:59:59",
        summary_text="Daily report.",
        insights="Work more.",
    )

    summary = await summary_repo.get_summary_by_id(sid)
    assert summary is not None
    assert summary.summary_text == "Daily report."
    assert summary.insights == "Work more."


async def test_get_summary_by_id_not_found(summary_repo: SummaryRepository):
    """Test get_summary_by_id returns None for nonexistent ID."""
    summary = await summary_repo.get_summary_by_id(9999)
    assert summary is None


async def test_get_summaries_with_date_filter(summary_repo: SummaryRepository):
    """Test filtering summaries by date."""
    await summary_repo.insert_summary(
        period_type="hourly",
        period_start="2025-01-15T10:00:00",
        period_end="2025-01-15T11:00:00",
        summary_text="Day 1.",
    )
    await summary_repo.insert_summary(
        period_type="hourly",
        period_start="2025-01-16T10:00:00",
        period_end="2025-01-16T11:00:00",
        summary_text="Day 2.",
    )

    day1 = await summary_repo.get_summaries(date="2025-01-15")
    assert len(day1) == 1
    assert day1[0].summary_text == "Day 1."


# --- EntityRepository tests ---


from life_optimizer.storage.repositories import EntityRepository, ChatHistoryRepository


@pytest.fixture
def entity_repo(db: Database):
    return EntityRepository(db)


async def test_entity_upsert_and_get(entity_repo: EntityRepository):
    """Test upserting and retrieving entities."""
    entity_id = await entity_repo.upsert_entity(
        entity_type="person",
        name="John Smith",
        timestamp="2025-01-15T10:00:00",
    )
    assert entity_id is not None
    assert entity_id > 0

    entities = await entity_repo.get_entities(entity_type="person")
    assert len(entities) == 1
    assert entities[0].name == "John Smith"
    assert entities[0].entity_type == "person"
    assert entities[0].interaction_count == 1
    assert entities[0].first_seen == "2025-01-15T10:00:00"


async def test_entity_upsert_increments_count(entity_repo: EntityRepository):
    """Test that upserting same entity increments interaction count."""
    await entity_repo.upsert_entity("person", "Jane", "2025-01-15T10:00:00")
    await entity_repo.upsert_entity("person", "Jane", "2025-01-15T11:00:00")

    entities = await entity_repo.get_entities(entity_type="person")
    assert len(entities) == 1
    assert entities[0].interaction_count == 2
    assert entities[0].last_seen == "2025-01-15T11:00:00"


async def test_entity_add_mention_and_get(entity_repo: EntityRepository):
    """Test adding and retrieving entity mentions."""
    entity_id = await entity_repo.upsert_entity(
        "person", "Alice", "2025-01-15T10:00:00"
    )

    mention_id = await entity_repo.add_mention(
        entity_id=entity_id,
        event_id=1,
        mention_type="slack_dm",
        timestamp="2025-01-15T10:00:00",
        context="Slack DM",
    )
    assert mention_id is not None
    assert mention_id > 0

    mentions = await entity_repo.get_mentions(entity_id)
    assert len(mentions) == 1
    assert mentions[0].mention_type == "slack_dm"
    assert mentions[0].context == "Slack DM"


async def test_entity_get_all_types(entity_repo: EntityRepository):
    """Test getting entities of all types."""
    await entity_repo.upsert_entity("person", "Bob", "2025-01-15T10:00:00")
    await entity_repo.upsert_entity("project", "my-project", "2025-01-15T10:00:00")

    all_entities = await entity_repo.get_entities()
    assert len(all_entities) == 2

    people = await entity_repo.get_entities(entity_type="person")
    assert len(people) == 1
    assert people[0].name == "Bob"

    projects = await entity_repo.get_entities(entity_type="project")
    assert len(projects) == 1
    assert projects[0].name == "my-project"


# --- ChatHistoryRepository tests ---


@pytest.fixture
def chat_repo(db: Database):
    return ChatHistoryRepository(db)


async def test_chat_add_and_get_history(chat_repo: ChatHistoryRepository):
    """Test adding messages and retrieving chat history."""
    await chat_repo.add_message(
        session_id="session-1",
        role="user",
        content="hello",
    )
    await chat_repo.add_message(
        session_id="session-1",
        role="assistant",
        content="Hi there!",
        query_type="insight",
        sql_query=None,
    )

    history = await chat_repo.get_history("session-1")
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "hello"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Hi there!"
    assert history[1]["query_type"] == "insight"


async def test_chat_history_separate_sessions(chat_repo: ChatHistoryRepository):
    """Test that chat history is separated by session."""
    await chat_repo.add_message("session-a", "user", "question a")
    await chat_repo.add_message("session-b", "user", "question b")

    history_a = await chat_repo.get_history("session-a")
    assert len(history_a) == 1
    assert history_a[0]["content"] == "question a"

    history_b = await chat_repo.get_history("session-b")
    assert len(history_b) == 1
    assert history_b[0]["content"] == "question b"


async def test_chat_history_empty_session(chat_repo: ChatHistoryRepository):
    """Test getting history for nonexistent session returns empty list."""
    history = await chat_repo.get_history("nonexistent")
    assert history == []
