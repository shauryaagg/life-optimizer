"""Tests for the Chrome collector."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from life_optimizer.collectors.base import CollectorResult
from life_optimizer.collectors.chrome import ChromeCollector
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
    return ChromeCollector(mock_jxa)


def _make_result(url: str, title: str, window_count: int = 1, tab_count: int = 5) -> CollectorResult:
    """Helper to create a CollectorResult with Chrome-like context."""
    return CollectorResult(
        app_name="Google Chrome",
        app_bundle_id="com.google.Chrome",
        event_type=POLL,
        window_title=title,
        context={
            "url": url,
            "title": title,
            "windowCount": window_count,
            "tabCount": tab_count,
        },
    )


async def test_chrome_collect_returns_result(collector: ChromeCollector, mock_jxa):
    """Test that collect returns a proper result when Chrome has data."""
    mock_jxa.run_jxa_json.return_value = {
        "url": "https://example.com",
        "title": "Example",
        "windowCount": 1,
        "tabCount": 3,
    }

    result = await collector.collect("Google Chrome", "com.google.Chrome")

    assert result is not None
    assert result.app_name == "Google Chrome"
    assert result.context["url"] == "https://example.com"
    assert result.context["title"] == "Example"
    assert result.event_type == POLL


async def test_chrome_collect_returns_none_when_not_running(collector: ChromeCollector, mock_jxa):
    """Test that collect returns None when Chrome is not running."""
    mock_jxa.run_jxa_json.return_value = None

    result = await collector.collect("Google Chrome", "com.google.Chrome")
    assert result is None


def test_is_changed_with_none_previous(collector: ChromeCollector):
    """Test that is_changed returns True when there's no previous result."""
    curr = _make_result("https://example.com", "Example")
    assert collector.is_changed(None, curr) is True


def test_is_changed_same_url_and_title(collector: ChromeCollector):
    """Test that is_changed returns False when URL and title are the same."""
    prev = _make_result("https://example.com", "Example", window_count=1, tab_count=3)
    curr = _make_result("https://example.com", "Example", window_count=2, tab_count=10)
    assert collector.is_changed(prev, curr) is False


def test_is_changed_different_url(collector: ChromeCollector):
    """Test that is_changed returns True when URL changes."""
    prev = _make_result("https://example.com", "Example")
    curr = _make_result("https://other.com", "Other")
    assert collector.is_changed(prev, curr) is True


def test_is_changed_different_title_same_url(collector: ChromeCollector):
    """Test that is_changed returns True when title changes but URL is same."""
    prev = _make_result("https://example.com", "Page 1")
    curr = _make_result("https://example.com", "Page 2")
    assert collector.is_changed(prev, curr) is True


def test_is_changed_different_tab_count_only(collector: ChromeCollector):
    """Test that is_changed returns False when only tab count changes."""
    prev = _make_result("https://example.com", "Example", tab_count=5)
    curr = _make_result("https://example.com", "Example", tab_count=10)
    assert collector.is_changed(prev, curr) is False
