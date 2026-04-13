"""Tests for the Slack collector."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from life_optimizer.collectors.base import CollectorResult
from life_optimizer.collectors.slack import SlackCollector, parse_slack_title
from life_optimizer.collectors.jxa_bridge import JXABridge
from life_optimizer.constants import POLL


@pytest.fixture
def mock_jxa():
    bridge = MagicMock(spec=JXABridge)
    bridge.run_applescript = AsyncMock()
    return bridge


@pytest.fixture
def collector(mock_jxa):
    return SlackCollector(mock_jxa)


class TestParseSlackTitle:
    """Test Slack window title parsing."""

    def test_channel_format(self):
        """Parse '#channel - Workspace - Slack' correctly."""
        result = parse_slack_title("#general - My Company - Slack")
        assert result["channel"] == "#general"
        assert result["workspace"] == "My Company"
        assert result["type"] == "channel"
        assert result["raw_title"] == "#general - My Company - Slack"

    def test_dm_format(self):
        """Parse 'Person Name - Workspace - Slack' correctly."""
        result = parse_slack_title("John Doe - My Company - Slack")
        assert result["channel"] == "John Doe"
        assert result["workspace"] == "My Company"
        assert result["type"] == "dm"

    def test_no_workspace_separator(self):
        """Handle title with no workspace separator (just app name)."""
        result = parse_slack_title("Slack")
        # "Slack" has no " - " separator, so it becomes the channel field
        assert result["channel"] == "Slack"
        assert result["workspace"] == ""
        assert result["type"] == "unknown"

    def test_empty_title(self):
        """Handle empty title string."""
        result = parse_slack_title("")
        assert result["channel"] == ""
        assert result["workspace"] == ""
        assert result["type"] == "unknown"

    def test_title_without_slack_suffix(self):
        """Handle title that doesn't end with ' - Slack'."""
        result = parse_slack_title("#general - My Company")
        assert result["channel"] == "#general"
        assert result["workspace"] == "My Company"
        assert result["type"] == "channel"

    def test_channel_with_dash_in_name(self):
        """Parse channel name that contains dashes."""
        result = parse_slack_title("#dev-team - Acme Corp - Slack")
        assert result["channel"] == "#dev-team"
        assert result["workspace"] == "Acme Corp"
        assert result["type"] == "channel"


def _make_slack_result(channel: str, workspace: str, msg_type: str = "channel") -> CollectorResult:
    return CollectorResult(
        app_name="Slack",
        app_bundle_id="com.tinyspeck.slackmacgap",
        event_type=POLL,
        window_title=f"{channel} - {workspace} - Slack",
        context={"channel": channel, "workspace": workspace, "type": msg_type, "raw_title": f"{channel} - {workspace} - Slack"},
    )


async def test_slack_collect_returns_result(collector: SlackCollector, mock_jxa):
    """Test that collect returns a proper result."""
    mock_jxa.run_applescript.return_value = "#general - My Company - Slack"

    result = await collector.collect("Slack", "com.tinyspeck.slackmacgap")

    assert result is not None
    assert result.app_name == "Slack"
    assert result.context["channel"] == "#general"
    assert result.context["workspace"] == "My Company"
    assert result.context["type"] == "channel"


async def test_slack_collect_returns_none_when_empty(collector: SlackCollector, mock_jxa):
    """Test that collect returns None when title is empty."""
    mock_jxa.run_applescript.return_value = ""

    result = await collector.collect("Slack")
    assert result is None


def test_is_changed_with_none_previous(collector: SlackCollector):
    """Test that is_changed returns True when there's no previous result."""
    curr = _make_slack_result("#general", "Company")
    assert collector.is_changed(None, curr) is True


def test_is_changed_same_channel_and_workspace(collector: SlackCollector):
    """Test that is_changed returns False when channel and workspace are same."""
    prev = _make_slack_result("#general", "Company")
    curr = _make_slack_result("#general", "Company")
    assert collector.is_changed(prev, curr) is False


def test_is_changed_different_channel(collector: SlackCollector):
    """Test that is_changed returns True when channel changes."""
    prev = _make_slack_result("#general", "Company")
    curr = _make_slack_result("#random", "Company")
    assert collector.is_changed(prev, curr) is True


def test_is_changed_different_workspace(collector: SlackCollector):
    """Test that is_changed returns True when workspace changes."""
    prev = _make_slack_result("#general", "Company A")
    curr = _make_slack_result("#general", "Company B")
    assert collector.is_changed(prev, curr) is True
