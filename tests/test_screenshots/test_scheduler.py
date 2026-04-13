"""Tests for screenshot scheduler module."""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from life_optimizer.screenshots.capture import ScreenshotCapture, ScreenshotResult
from life_optimizer.screenshots.scheduler import ScreenshotScheduler


def _make_screenshot_result() -> ScreenshotResult:
    """Helper to create a mock ScreenshotResult."""
    return ScreenshotResult(
        file_path="data/screenshots/2025-01-01/120000_test.jpg",
        timestamp=datetime.now(timezone.utc),
        file_size_bytes=10000,
        width=960,
        height=540,
        app_name="TestApp",
        trigger_reason="test",
    )


@pytest.fixture
def mock_capture():
    """Create a mock ScreenshotCapture."""
    capture = MagicMock(spec=ScreenshotCapture)
    capture.capture = AsyncMock(return_value=_make_screenshot_result())
    return capture


@pytest.fixture
def scheduler(mock_capture):
    return ScreenshotScheduler(capture=mock_capture, interval=30.0)


async def test_on_app_switch_resets_timer(scheduler: ScreenshotScheduler, mock_capture):
    """Test that on_app_switch takes a screenshot and resets the timer."""
    scheduler._last_capture_time = 0.0

    result = await scheduler.on_app_switch("Chrome")

    assert result is not None
    mock_capture.capture.assert_called_once_with("Chrome", "app_switch")
    assert scheduler._last_capture_time > 0


async def test_tick_triggers_capture_when_interval_elapsed(
    scheduler: ScreenshotScheduler, mock_capture
):
    """Test that tick triggers capture when the interval has elapsed."""
    # Set last capture far in the past
    scheduler._last_capture_time = time.monotonic() - 60.0

    result = await scheduler.tick("Chrome")

    assert result is not None
    mock_capture.capture.assert_called_once_with("Chrome", "interval")


async def test_tick_does_not_capture_when_interval_not_elapsed(
    scheduler: ScreenshotScheduler, mock_capture
):
    """Test that tick does NOT capture when interval has not elapsed."""
    # Set last capture to now
    scheduler._last_capture_time = time.monotonic()

    result = await scheduler.tick("Chrome")

    assert result is None
    mock_capture.capture.assert_not_called()


async def test_on_app_switch_disabled(scheduler: ScreenshotScheduler, mock_capture):
    """Test that on_app_switch returns None when disabled."""
    scheduler.enabled = False

    result = await scheduler.on_app_switch("Chrome")

    assert result is None
    mock_capture.capture.assert_not_called()


async def test_tick_disabled(scheduler: ScreenshotScheduler, mock_capture):
    """Test that tick returns None when disabled."""
    scheduler.enabled = False
    scheduler._last_capture_time = 0.0

    result = await scheduler.tick("Chrome")

    assert result is None
    mock_capture.capture.assert_not_called()
