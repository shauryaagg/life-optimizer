"""Tests for the Safari collector."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from life_optimizer.collectors.base import CollectorResult
from life_optimizer.collectors.safari import SafariCollector
from life_optimizer.collectors.jxa_bridge import JXABridge
from life_optimizer.constants import POLL


@pytest.fixture
def mock_jxa():
    """Create a mock JXA bridge."""
    bridge = MagicMock(spec=JXABridge)
    bridge.run_jxa_json = AsyncMock()
    return bridge


@pytest.fixture
def collector(mock_jxa):
    return SafariCollector(mock_jxa)


def _make_result(url: str, title: str) -> CollectorResult:
    """Helper to create a Safari-like CollectorResult."""
    return CollectorResult(
        app_name="Safari",
        app_bundle_id="com.apple.Safari",
        event_type=POLL,
        window_title=title,
        context={"url": url, "title": title, "windowCount": 1, "tabCount": 3},
    )


async def test_safari_collect_returns_result(collector: SafariCollector, mock_jxa):
    """Test that collect returns a proper result when Safari has data."""
    mock_jxa.run_jxa_json.return_value = {
        "url": "https://apple.com",
        "title": "Apple",
        "windowCount": 1,
        "tabCount": 5,
    }

    result = await collector.collect("Safari", "com.apple.Safari")

    assert result is not None
    assert result.app_name == "Safari"
    assert result.context["url"] == "https://apple.com"
    assert result.context["title"] == "Apple"
    assert result.event_type == POLL


async def test_safari_collect_returns_none_when_not_running(
    collector: SafariCollector, mock_jxa
):
    """Test that collect returns None when Safari is not running."""
    mock_jxa.run_jxa_json.return_value = None

    result = await collector.collect("Safari", "com.apple.Safari")
    assert result is None


def test_is_changed_with_none_previous(collector: SafariCollector):
    """Test that is_changed returns True when there's no previous result."""
    curr = _make_result("https://apple.com", "Apple")
    assert collector.is_changed(None, curr) is True


def test_is_changed_same_url_and_title(collector: SafariCollector):
    """Test that is_changed returns False when URL and title are the same."""
    prev = _make_result("https://apple.com", "Apple")
    curr = _make_result("https://apple.com", "Apple")
    assert collector.is_changed(prev, curr) is False


def test_is_changed_different_url(collector: SafariCollector):
    """Test that is_changed returns True when URL changes."""
    prev = _make_result("https://apple.com", "Apple")
    curr = _make_result("https://google.com", "Google")
    assert collector.is_changed(prev, curr) is True


def test_is_changed_different_title_same_url(collector: SafariCollector):
    """Test that is_changed returns True when title changes but URL is same."""
    prev = _make_result("https://apple.com", "Page 1")
    curr = _make_result("https://apple.com", "Page 2")
    assert collector.is_changed(prev, curr) is True
