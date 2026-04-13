"""Tests for the temporal parser."""

import pytest
from datetime import datetime

from life_optimizer.query.temporal import TemporalParser


@pytest.fixture
def parser():
    return TemporalParser()


@pytest.fixture
def now():
    """Fixed reference time: Wednesday 2025-01-15 14:30:00"""
    return datetime(2025, 1, 15, 14, 30, 0)


def test_today_returns_correct_range(parser, now):
    """Test 'today' returns start and end of current day."""
    result = parser.resolve_time_range("what did I do today", now)
    assert result is not None
    start, end = result
    assert start == "2025-01-15T00:00:00"
    assert end == "2025-01-15T23:59:59"


def test_yesterday_returns_correct_range(parser, now):
    """Test 'yesterday' returns start and end of previous day."""
    result = parser.resolve_time_range("show me yesterday's activity", now)
    assert result is not None
    start, end = result
    assert start == "2025-01-14T00:00:00"
    assert end == "2025-01-14T23:59:59"


def test_this_morning_returns_06_to_12(parser, now):
    """Test 'this morning' returns 06:00 to 12:00."""
    result = parser.resolve_time_range("what happened this morning", now)
    assert result is not None
    start, end = result
    assert start == "2025-01-15T06:00:00"
    assert end == "2025-01-15T12:00:00"


def test_this_afternoon_returns_12_to_18(parser, now):
    """Test 'this afternoon' returns 12:00 to 18:00."""
    result = parser.resolve_time_range("show this afternoon", now)
    assert result is not None
    start, end = result
    assert start == "2025-01-15T12:00:00"
    assert end == "2025-01-15T18:00:00"


def test_this_evening_returns_18_to_2359(parser, now):
    """Test 'this evening' returns 18:00 to 23:59."""
    result = parser.resolve_time_range("show this evening", now)
    assert result is not None
    start, end = result
    assert start == "2025-01-15T18:00:00"
    assert end == "2025-01-15T23:59:00"


def test_last_week_returns_prev_monday_to_sunday(parser, now):
    """Test 'last week' returns previous Mon-Sun.

    now is Wednesday 2025-01-15.
    This Monday = 2025-01-13.
    Last Monday = 2025-01-06.
    Last Sunday = 2025-01-12.
    """
    result = parser.resolve_time_range("last week's activity", now)
    assert result is not None
    start, end = result
    assert start == "2025-01-06T00:00:00"
    assert end == "2025-01-12T23:59:59"


def test_this_week_returns_monday_to_now(parser, now):
    """Test 'this week' returns current Monday to now.

    now is Wednesday 2025-01-15.
    This Monday = 2025-01-13.
    """
    result = parser.resolve_time_range("this week", now)
    assert result is not None
    start, end = result
    assert start == "2025-01-13T00:00:00"
    assert end == "2025-01-15T23:59:59"


def test_at_3pm_returns_30_min_window(parser, now):
    """Test 'at 3pm' returns a 30-minute window around 3pm."""
    result = parser.resolve_time_range("what was I doing at 3pm", now)
    assert result is not None
    start, end = result
    # 3pm = 15:00, start = 14:45, end = 15:15
    assert start == "2025-01-15T14:45:00"
    assert end == "2025-01-15T15:15:00"


def test_at_9am_returns_30_min_window(parser, now):
    """Test 'at 9am' returns a 30-minute window around 9am."""
    result = parser.resolve_time_range("what happened at 9am", now)
    assert result is not None
    start, end = result
    assert start == "2025-01-15T08:45:00"
    assert end == "2025-01-15T09:15:00"


def test_between_2pm_and_4pm(parser, now):
    """Test 'between 2pm and 4pm' returns correct range."""
    result = parser.resolve_time_range("show activity between 2pm and 4pm", now)
    assert result is not None
    start, end = result
    assert start == "2025-01-15T14:00:00"
    assert end == "2025-01-15T16:00:00"


def test_no_time_reference_returns_none(parser, now):
    """Test that a question with no time reference returns None."""
    result = parser.resolve_time_range("how much time on Slack", now)
    assert result is None


def test_no_time_reference_generic_question(parser, now):
    """Test another question with no time reference."""
    result = parser.resolve_time_range("what apps do I use most", now)
    assert result is None


def test_uses_current_time_when_now_is_none(parser):
    """Test that resolve_time_range uses current time when now is not provided."""
    result = parser.resolve_time_range("today")
    assert result is not None
    start, end = result
    # Should be valid ISO format strings
    assert "T00:00:00" in start
    assert "T23:59:59" in end


def test_at_12pm_noon(parser, now):
    """Test 'at 12pm' correctly handles noon."""
    result = parser.resolve_time_range("at 12pm", now)
    assert result is not None
    start, end = result
    # 12pm = 12:00, start = 11:45, end = 12:15
    assert start == "2025-01-15T11:45:00"
    assert end == "2025-01-15T12:15:00"


def test_between_9am_and_12pm(parser, now):
    """Test 'between 9am and 12pm' returns correct range."""
    result = parser.resolve_time_range("between 9am and 12pm", now)
    assert result is not None
    start, end = result
    assert start == "2025-01-15T09:00:00"
    assert end == "2025-01-15T12:00:00"
