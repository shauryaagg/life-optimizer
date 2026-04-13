"""Tests for the Terminal collector."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from life_optimizer.collectors.base import CollectorResult
from life_optimizer.collectors.terminal import TerminalCollector, parse_terminal_title
from life_optimizer.collectors.jxa_bridge import JXABridge
from life_optimizer.constants import POLL


@pytest.fixture
def mock_jxa():
    bridge = MagicMock(spec=JXABridge)
    bridge.run_applescript = AsyncMock()
    return bridge


@pytest.fixture
def collector(mock_jxa):
    return TerminalCollector(mock_jxa)


class TestParseTerminalTitle:
    """Test terminal title parsing for various formats."""

    def test_user_at_host_with_path(self):
        """Parse 'user@host: ~/projects/myapp'."""
        result = parse_terminal_title("user@host: ~/projects/myapp")
        assert result["parsed_cwd"] == "~/projects/myapp"
        assert result["parsed_command"] is None

    def test_user_at_host_with_path_and_command(self):
        """Parse 'user@host: ~/projects \u2014 vim main.py'."""
        result = parse_terminal_title("user@host: ~/projects \u2014 vim main.py")
        assert result["parsed_cwd"] == "~/projects"
        assert result["parsed_command"] == "vim main.py"

    def test_tilde_path_only(self):
        """Parse '~/projects'."""
        result = parse_terminal_title("~/projects")
        assert result["parsed_cwd"] == "~/projects"
        assert result["parsed_command"] is None

    def test_absolute_path_with_command(self):
        """Parse '/usr/local/bin - htop'."""
        result = parse_terminal_title("/usr/local/bin - htop")
        assert result["parsed_cwd"] == "/usr/local/bin"
        assert result["parsed_command"] == "htop"

    def test_empty_title(self):
        """Handle empty title."""
        result = parse_terminal_title("")
        assert result["parsed_cwd"] is None
        assert result["parsed_command"] is None

    def test_unparseable_title(self):
        """Handle title that doesn't match any expected format."""
        result = parse_terminal_title("bash")
        assert result["parsed_cwd"] is None
        assert result["parsed_command"] is None
        assert result["raw_title"] == "bash"

    def test_user_at_host_with_dash_command(self):
        """Parse 'user@host: ~/code - python'."""
        result = parse_terminal_title("user@host: ~/code - python")
        assert result["parsed_cwd"] == "~/code"
        assert result["parsed_command"] == "python"


async def test_terminal_collect_returns_result(collector: TerminalCollector, mock_jxa):
    """Test that collect returns a proper result."""
    mock_jxa.run_applescript.return_value = "user@host: ~/projects"

    result = await collector.collect("Terminal", "com.apple.Terminal")

    assert result is not None
    assert result.app_name == "Terminal"
    assert result.context["parsed_cwd"] == "~/projects"


async def test_terminal_collect_returns_none(collector: TerminalCollector, mock_jxa):
    """Test that collect returns None when no data."""
    mock_jxa.run_applescript.return_value = None
    result = await collector.collect("Terminal")
    assert result is None


def _make_terminal_result(raw_title: str) -> CollectorResult:
    return CollectorResult(
        app_name="Terminal",
        event_type=POLL,
        window_title=raw_title,
        context=parse_terminal_title(raw_title),
    )


def test_is_changed_with_none_previous(collector: TerminalCollector):
    curr = _make_terminal_result("user@host: ~/code")
    assert collector.is_changed(None, curr) is True


def test_is_changed_same_title(collector: TerminalCollector):
    prev = _make_terminal_result("user@host: ~/code")
    curr = _make_terminal_result("user@host: ~/code")
    assert collector.is_changed(prev, curr) is False


def test_is_changed_different_title(collector: TerminalCollector):
    prev = _make_terminal_result("user@host: ~/code")
    curr = _make_terminal_result("user@host: ~/other")
    assert collector.is_changed(prev, curr) is True
