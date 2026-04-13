"""Tests for the Messages collector."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from life_optimizer.collectors.base import CollectorResult
from life_optimizer.collectors.messages import (
    MessagesCollector,
    parse_conversations,
)
from life_optimizer.collectors.jxa_bridge import JXABridge
from life_optimizer.constants import POLL


@pytest.fixture
def mock_jxa():
    """Create a mock JXA bridge."""
    bridge = MagicMock(spec=JXABridge)
    bridge.run_applescript = AsyncMock()
    return bridge


@pytest.fixture
def collector(mock_jxa):
    return MessagesCollector(mock_jxa)


class TestParseConversations:
    """Test conversation output parsing."""

    def test_parse_valid_output(self):
        """Parse valid conversation output."""
        raw = "Alice|iMessage;-;abc123|1\\nBob|iMessage;-;def456|2"
        result = parse_conversations(raw)
        assert len(result) == 2
        assert result[0]["name"] == "Alice"
        assert result[0]["id"] == "iMessage;-;abc123"
        assert result[0]["participant_count"] == 1
        assert result[1]["name"] == "Bob"
        assert result[1]["participant_count"] == 2

    def test_parse_empty_string(self):
        """Parse empty string returns empty list."""
        assert parse_conversations("") == []

    def test_parse_none(self):
        """Parse None returns empty list."""
        assert parse_conversations(None) == []

    def test_parse_error_output(self):
        """Parse error output returns empty list."""
        assert parse_conversations("ERROR:Some error message") == []

    def test_parse_single_conversation(self):
        """Parse single conversation line."""
        raw = "Work Chat|iMessage;-;group1|5"
        result = parse_conversations(raw)
        assert len(result) == 1
        assert result[0]["name"] == "Work Chat"
        assert result[0]["participant_count"] == 5

    def test_parse_with_trailing_newline(self):
        """Parse output with trailing newline."""
        raw = "Alice|conv1|1\\n"
        result = parse_conversations(raw)
        assert len(result) == 1
        assert result[0]["name"] == "Alice"


def _make_messages_result(
    window_title: str, conversations: list | None = None
) -> CollectorResult:
    """Helper to create a CollectorResult with Messages-like context."""
    return CollectorResult(
        app_name="Messages",
        app_bundle_id="com.apple.MobileSMS",
        event_type=POLL,
        window_title=window_title,
        context={
            "conversations": conversations or [],
            "active_conversation": window_title if window_title else None,
        },
    )


async def test_messages_collect_returns_result(collector: MessagesCollector, mock_jxa):
    """Test that collect returns a proper result."""
    mock_jxa.run_applescript.side_effect = [
        "Alice",  # window title
        "Alice|conv1|1\\nBob|conv2|2",  # conversations
    ]

    result = await collector.collect("Messages", "com.apple.MobileSMS")

    assert result is not None
    assert result.app_name == "Messages"
    assert result.window_title == "Alice"
    assert result.context["active_conversation"] == "Alice"


async def test_messages_collect_returns_none_when_not_running(
    collector: MessagesCollector, mock_jxa
):
    """Test that collect returns None when Messages is not running."""
    mock_jxa.run_applescript.return_value = None

    result = await collector.collect("Messages", "com.apple.MobileSMS")
    assert result is None


async def test_messages_collect_handles_empty_title(
    collector: MessagesCollector, mock_jxa
):
    """Test that collect works with empty window title."""
    mock_jxa.run_applescript.side_effect = [
        "",  # empty window title
        "",  # no conversations
    ]

    result = await collector.collect("Messages", "com.apple.MobileSMS")

    assert result is not None
    assert result.window_title == ""


def test_is_changed_with_none_previous(collector: MessagesCollector):
    """Test that is_changed returns True when there's no previous result."""
    curr = _make_messages_result("Alice")
    assert collector.is_changed(None, curr) is True


def test_is_changed_same_title(collector: MessagesCollector):
    """Test that is_changed returns False when window title is the same."""
    prev = _make_messages_result("Alice")
    curr = _make_messages_result("Alice")
    assert collector.is_changed(prev, curr) is False


def test_is_changed_different_title(collector: MessagesCollector):
    """Test that is_changed returns True when window title changes."""
    prev = _make_messages_result("Alice")
    curr = _make_messages_result("Bob")
    assert collector.is_changed(prev, curr) is True
