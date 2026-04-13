"""Tests for the Finder collector."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from life_optimizer.collectors.base import CollectorResult
from life_optimizer.collectors.finder import FinderCollector, parse_finder_output
from life_optimizer.collectors.jxa_bridge import JXABridge
from life_optimizer.constants import POLL


@pytest.fixture
def mock_jxa():
    bridge = MagicMock(spec=JXABridge)
    bridge.run_applescript = AsyncMock()
    return bridge


@pytest.fixture
def collector(mock_jxa):
    return FinderCollector(mock_jxa)


class TestParseFinderOutput:
    """Test Finder output parsing."""

    def test_normal_output(self):
        """Parse 'Documents|/Users/me/Documents/'."""
        result = parse_finder_output("Documents|/Users/me/Documents/")
        assert result["window_name"] == "Documents"
        assert result["folder_path"] == "/Users/me/Documents/"

    def test_output_with_spaces(self):
        """Parse 'My Folder|/Users/me/My Folder/'."""
        result = parse_finder_output("My Folder|/Users/me/My Folder/")
        assert result["window_name"] == "My Folder"
        assert result["folder_path"] == "/Users/me/My Folder/"

    def test_empty_output(self):
        """Handle empty output."""
        result = parse_finder_output("")
        assert result["window_name"] == ""
        assert result["folder_path"] == ""

    def test_no_pipe_separator(self):
        """Handle output without pipe separator."""
        result = parse_finder_output("JustAName")
        assert result["window_name"] == "JustAName"
        assert result["folder_path"] == ""


async def test_finder_collect_returns_result(collector: FinderCollector, mock_jxa):
    """Test that collect returns a proper result."""
    mock_jxa.run_applescript.return_value = "Downloads|/Users/me/Downloads/"

    result = await collector.collect("Finder", "com.apple.finder")

    assert result is not None
    assert result.app_name == "Finder"
    assert result.context["folder_path"] == "/Users/me/Downloads/"
    assert result.context["window_name"] == "Downloads"


async def test_finder_collect_returns_none_when_empty(collector: FinderCollector, mock_jxa):
    """Test that collect returns None when Finder has no windows."""
    mock_jxa.run_applescript.return_value = ""

    result = await collector.collect("Finder")
    assert result is None


async def test_finder_collect_returns_none_on_failure(collector: FinderCollector, mock_jxa):
    """Test that collect returns None on failure."""
    mock_jxa.run_applescript.return_value = None

    result = await collector.collect("Finder")
    assert result is None


def _make_finder_result(folder_path: str) -> CollectorResult:
    return CollectorResult(
        app_name="Finder",
        app_bundle_id="com.apple.finder",
        event_type=POLL,
        window_title="test",
        context={"folder_path": folder_path, "window_name": "test"},
    )


def test_is_changed_with_none_previous(collector: FinderCollector):
    curr = _make_finder_result("/Users/me/Downloads/")
    assert collector.is_changed(None, curr) is True


def test_is_changed_same_folder(collector: FinderCollector):
    prev = _make_finder_result("/Users/me/Downloads/")
    curr = _make_finder_result("/Users/me/Downloads/")
    assert collector.is_changed(prev, curr) is False


def test_is_changed_different_folder(collector: FinderCollector):
    prev = _make_finder_result("/Users/me/Downloads/")
    curr = _make_finder_result("/Users/me/Documents/")
    assert collector.is_changed(prev, curr) is True
