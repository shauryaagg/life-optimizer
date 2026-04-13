"""Tests for the VS Code collector."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from life_optimizer.collectors.base import CollectorResult
from life_optimizer.collectors.vscode import VSCodeCollector, parse_vscode_title
from life_optimizer.collectors.jxa_bridge import JXABridge
from life_optimizer.constants import POLL


@pytest.fixture
def mock_jxa():
    bridge = MagicMock(spec=JXABridge)
    bridge.run_applescript = AsyncMock()
    return bridge


@pytest.fixture
def collector(mock_jxa):
    return VSCodeCollector(mock_jxa)


class TestParseVSCodeTitle:
    """Test VS Code title parsing."""

    def test_full_title_vscode(self):
        """Parse 'file.py \u2014 project \u2014 Visual Studio Code'."""
        result = parse_vscode_title("main.py \u2014 my-project \u2014 Visual Studio Code")
        assert result["filename"] == "main.py"
        assert result["project"] == "my-project"

    def test_full_title_cursor(self):
        """Parse 'file.py \u2014 project \u2014 Cursor'."""
        result = parse_vscode_title("app.tsx \u2014 web-app \u2014 Cursor")
        assert result["filename"] == "app.tsx"
        assert result["project"] == "web-app"

    def test_welcome_tab(self):
        """Parse 'Welcome \u2014 Visual Studio Code'."""
        result = parse_vscode_title("Welcome \u2014 Visual Studio Code")
        assert result["filename"] == "Welcome"
        assert result["project"] is None

    def test_project_only_cursor(self):
        """Parse 'project \u2014 Cursor'."""
        result = parse_vscode_title("my-project \u2014 Cursor")
        assert result["filename"] == "my-project"
        assert result["project"] is None

    def test_empty_title(self):
        """Handle empty title."""
        result = parse_vscode_title("")
        assert result["filename"] is None
        assert result["project"] is None

    def test_plain_title_no_separator(self):
        """Handle title without em-dash separator."""
        result = parse_vscode_title("Untitled")
        assert result["filename"] is None
        assert result["project"] is None


def _make_vscode_result(raw_title: str) -> CollectorResult:
    parsed = parse_vscode_title(raw_title)
    return CollectorResult(
        app_name="Code",
        app_bundle_id="com.microsoft.VSCode",
        event_type=POLL,
        window_title=raw_title,
        context=parsed,
    )


async def test_vscode_collect_returns_result(collector: VSCodeCollector, mock_jxa):
    """Test that collect returns a proper result."""
    mock_jxa.run_applescript.return_value = "test.py \u2014 project \u2014 Visual Studio Code"

    result = await collector.collect("Code", "com.microsoft.VSCode")

    assert result is not None
    assert result.app_name == "Code"
    assert result.context["filename"] == "test.py"
    assert result.context["project"] == "project"


async def test_vscode_collect_returns_none(collector: VSCodeCollector, mock_jxa):
    """Test that collect returns None when no data."""
    mock_jxa.run_applescript.return_value = None
    result = await collector.collect("Code")
    assert result is None


def test_is_changed_with_none_previous(collector: VSCodeCollector):
    curr = _make_vscode_result("file.py \u2014 project \u2014 Visual Studio Code")
    assert collector.is_changed(None, curr) is True


def test_is_changed_same_title(collector: VSCodeCollector):
    prev = _make_vscode_result("file.py \u2014 project \u2014 Visual Studio Code")
    curr = _make_vscode_result("file.py \u2014 project \u2014 Visual Studio Code")
    assert collector.is_changed(prev, curr) is False


def test_is_changed_different_title(collector: VSCodeCollector):
    prev = _make_vscode_result("file.py \u2014 project \u2014 Visual Studio Code")
    curr = _make_vscode_result("other.py \u2014 project \u2014 Visual Studio Code")
    assert collector.is_changed(prev, curr) is True
