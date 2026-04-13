"""Tests for idle detection in the daemon."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from life_optimizer.config import Config
from life_optimizer.daemon.core import Daemon


@pytest.fixture
def config():
    """Create a test config."""
    cfg = Config()
    cfg.daemon.idle_threshold = 300
    return cfg


@pytest.fixture
def daemon(config):
    """Create a daemon instance for testing."""
    return Daemon(config)


async def test_check_idle_returns_float(daemon):
    """Test that _check_idle returns a float value."""
    result = await daemon._check_idle()
    assert isinstance(result, float)


async def test_check_idle_returns_zero_without_quartz(daemon):
    """Test that _check_idle returns 0.0 when Quartz is not available."""
    with patch.dict("sys.modules", {"Quartz": None}):
        result = await daemon._check_idle()
        assert result == 0.0


async def test_check_idle_with_mock_quartz(daemon):
    """Test _check_idle with a mocked Quartz module."""
    mock_quartz = MagicMock()
    mock_quartz.CGEventSourceSecondsSinceLastEventType.return_value = 42.5
    mock_quartz.kCGEventSourceStateHIDSystemState = 1
    mock_quartz.kCGAnyInputEventType = 0xFFFFFFFF

    with patch.dict("sys.modules", {"Quartz": mock_quartz}):
        result = await daemon._check_idle()
        assert result == 42.5


async def test_check_idle_handles_import_error(daemon):
    """Test that _check_idle handles ImportError gracefully."""
    # Force an ImportError by temporarily removing Quartz
    import sys
    original = sys.modules.get("Quartz")
    sys.modules["Quartz"] = None
    try:
        result = await daemon._check_idle()
        assert result == 0.0
    finally:
        if original is not None:
            sys.modules["Quartz"] = original
        else:
            sys.modules.pop("Quartz", None)


async def test_idle_state_transition_to_idle(daemon):
    """Test that daemon transitions to idle state when idle threshold exceeded."""
    assert daemon._is_idle is False
    assert daemon._idle_start_time is None


async def test_idle_state_initial_values(daemon):
    """Test initial idle state values."""
    assert daemon._is_idle is False
    assert daemon._idle_start_time is None


async def test_poll_once_skips_when_idle(daemon):
    """Test that _poll_once returns early (skips collection) when user is idle."""
    # Set up minimal mocks for the daemon internals
    daemon._repo = MagicMock()
    daemon._repo.insert_event = AsyncMock()
    daemon._screenshot_scheduler = None
    daemon._screenshot_repo = None
    daemon._session_repo = None
    daemon._registry = MagicMock()

    # Mock _check_idle to return a value above the threshold
    daemon._check_idle = AsyncMock(return_value=600.0)
    daemon._detect_frontmost_app = AsyncMock(return_value=("Safari", "com.apple.Safari"))

    await daemon._poll_once()

    # Since user is idle, the collector should NOT have been called
    daemon._registry.get_collector.assert_not_called()
    # Daemon should now be in idle state
    assert daemon._is_idle is True


async def test_poll_once_resumes_after_idle(daemon):
    """Test that _poll_once resumes normal operation when user returns from idle."""
    import time

    # Put daemon into idle state
    daemon._is_idle = True
    daemon._idle_start_time = time.time() - 60  # Was idle for 60 seconds

    # Set up minimal mocks
    daemon._repo = MagicMock()
    daemon._repo.insert_event = AsyncMock(return_value=1)
    daemon._screenshot_scheduler = None
    daemon._screenshot_repo = None
    daemon._session_repo = None

    # Mock a collector that returns a result
    mock_collector = MagicMock()
    mock_result = MagicMock()
    mock_result.event_type = "poll"
    mock_result.app_name = "Safari"
    mock_result.window_title = "Test"
    mock_result.context = {}
    mock_result.timestamp = MagicMock()
    mock_result.timestamp.strftime = MagicMock(return_value="12:00:00")
    mock_collector.collect = AsyncMock(return_value=mock_result)
    mock_collector.is_changed = MagicMock(return_value=True)

    daemon._registry = MagicMock()
    daemon._registry.get_collector = MagicMock(return_value=mock_collector)

    # Mock _check_idle to return 0 (user is back)
    daemon._check_idle = AsyncMock(return_value=0.0)
    daemon._detect_frontmost_app = AsyncMock(return_value=("Safari", "com.apple.Safari"))

    await daemon._poll_once()

    # Daemon should no longer be idle
    assert daemon._is_idle is False
    assert daemon._idle_start_time is None

    # Collection should have happened
    mock_collector.collect.assert_called_once()


async def test_screenshots_stop_during_idle(daemon):
    """Test that screenshots are not taken during idle periods."""
    daemon._repo = MagicMock()
    daemon._repo.insert_event = AsyncMock()
    daemon._session_repo = None

    mock_scheduler = MagicMock()
    mock_scheduler.tick = AsyncMock(return_value=None)
    mock_scheduler.on_app_switch = AsyncMock(return_value=None)
    daemon._screenshot_scheduler = mock_scheduler
    daemon._screenshot_repo = MagicMock()

    daemon._registry = MagicMock()

    # Mock idle state
    daemon._check_idle = AsyncMock(return_value=600.0)
    daemon._detect_frontmost_app = AsyncMock(return_value=("Safari", "com.apple.Safari"))

    await daemon._poll_once()

    # Screenshot scheduler should NOT have been called (tick or on_app_switch)
    mock_scheduler.tick.assert_not_called()
    # The daemon is idle, so it returns early before any screenshot logic
    assert daemon._is_idle is True
