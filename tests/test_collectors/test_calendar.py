"""Tests for the Calendar collector."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from life_optimizer.collectors.base import CollectorResult
from life_optimizer.collectors.calendar_app import CalendarCollector
from life_optimizer.collectors.jxa_bridge import JXABridge
from life_optimizer.constants import POLL


@pytest.fixture
def mock_jxa():
    bridge = MagicMock(spec=JXABridge)
    bridge.run_jxa_json = AsyncMock()
    return bridge


@pytest.fixture
def collector(mock_jxa):
    return CalendarCollector(mock_jxa)


async def test_calendar_collect_returns_events(collector: CalendarCollector, mock_jxa):
    """Test that collect returns events when Calendar has data."""
    mock_jxa.run_jxa_json.return_value = {
        "events": [
            {
                "title": "Team Standup",
                "start": "2025-01-15T09:00:00.000Z",
                "end": "2025-01-15T09:30:00.000Z",
                "calendar": "Work",
            },
            {
                "title": "Lunch",
                "start": "2025-01-15T12:00:00.000Z",
                "end": "2025-01-15T13:00:00.000Z",
                "calendar": "Personal",
            },
        ],
        "eventCount": 2,
    }

    result = await collector.collect("Calendar", "com.apple.iCal")

    assert result is not None
    assert result.app_name == "Calendar"
    assert result.context["eventCount"] == 2
    assert len(result.context["events"]) == 2
    assert result.window_title == "2 events today"


async def test_calendar_collect_returns_none_when_not_running(
    collector: CalendarCollector, mock_jxa
):
    """Test that collect returns None when Calendar returns no data."""
    mock_jxa.run_jxa_json.return_value = None

    result = await collector.collect("Calendar")
    assert result is None


def _make_calendar_result(event_count: int) -> CollectorResult:
    return CollectorResult(
        app_name="Calendar",
        app_bundle_id="com.apple.iCal",
        event_type=POLL,
        window_title=f"{event_count} events today",
        context={"events": [], "eventCount": event_count},
    )


def test_is_changed_with_none_previous(collector: CalendarCollector):
    curr = _make_calendar_result(3)
    assert collector.is_changed(None, curr) is True


def test_is_changed_same_event_count(collector: CalendarCollector):
    prev = _make_calendar_result(3)
    curr = _make_calendar_result(3)
    assert collector.is_changed(prev, curr) is False


def test_is_changed_different_event_count(collector: CalendarCollector):
    prev = _make_calendar_result(3)
    curr = _make_calendar_result(5)
    assert collector.is_changed(prev, curr) is True
