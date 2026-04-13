"""Tests for the Mail collector."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from life_optimizer.collectors.base import CollectorResult
from life_optimizer.collectors.mail import MailCollector, parse_mail_selection
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
    return MailCollector(mock_jxa)


class TestParseMailSelection:
    """Test Mail selection output parsing."""

    def test_parse_valid_selection(self):
        """Parse valid subject|sender output."""
        result = parse_mail_selection("Meeting Tomorrow|john@example.com")
        assert result["subject"] == "Meeting Tomorrow"
        assert result["sender"] == "john@example.com"

    def test_parse_empty_string(self):
        """Parse empty string returns empty fields."""
        result = parse_mail_selection("")
        assert result["subject"] == ""
        assert result["sender"] == ""

    def test_parse_none(self):
        """Parse None returns empty fields."""
        result = parse_mail_selection(None)
        assert result["subject"] == ""
        assert result["sender"] == ""

    def test_parse_subject_only(self):
        """Parse output with no pipe separator (subject only)."""
        result = parse_mail_selection("Some Subject")
        assert result["subject"] == "Some Subject"
        assert result["sender"] == ""

    def test_parse_subject_with_pipe_in_sender(self):
        """Parse output where sender may contain pipe characters."""
        result = parse_mail_selection("Subject|sender@example.com")
        assert result["subject"] == "Subject"
        assert result["sender"] == "sender@example.com"

    def test_parse_whitespace_only(self):
        """Parse whitespace-only string."""
        result = parse_mail_selection("   ")
        assert result["subject"] == ""
        assert result["sender"] == ""


def _make_mail_result(
    subject: str, sender: str, raw_title: str = "Inbox"
) -> CollectorResult:
    """Helper to create a CollectorResult with Mail-like context."""
    return CollectorResult(
        app_name="Mail",
        app_bundle_id="com.apple.mail",
        event_type=POLL,
        window_title=raw_title,
        context={
            "subject": subject,
            "sender": sender,
            "raw_title": raw_title,
        },
    )


async def test_mail_collect_returns_result(collector: MailCollector, mock_jxa):
    """Test that collect returns a proper result."""
    mock_jxa.run_applescript.side_effect = [
        "Inbox - Mail",  # window title
        "Meeting Tomorrow|john@example.com",  # selection
    ]

    result = await collector.collect("Mail", "com.apple.mail")

    assert result is not None
    assert result.app_name == "Mail"
    assert result.window_title == "Inbox - Mail"
    assert result.context["subject"] == "Meeting Tomorrow"
    assert result.context["sender"] == "john@example.com"


async def test_mail_collect_returns_none_when_not_running(
    collector: MailCollector, mock_jxa
):
    """Test that collect returns None when Mail is not running."""
    mock_jxa.run_applescript.return_value = None

    result = await collector.collect("Mail", "com.apple.mail")
    assert result is None


async def test_mail_collect_handles_no_selection(
    collector: MailCollector, mock_jxa
):
    """Test that collect works when there is no selected message."""
    mock_jxa.run_applescript.side_effect = [
        "Inbox - Mail",  # window title
        "",  # no selection
    ]

    result = await collector.collect("Mail", "com.apple.mail")

    assert result is not None
    assert result.context["subject"] == ""
    assert result.context["sender"] == ""


def test_is_changed_with_none_previous(collector: MailCollector):
    """Test that is_changed returns True when there's no previous result."""
    curr = _make_mail_result("Test Subject", "alice@test.com")
    assert collector.is_changed(None, curr) is True


def test_is_changed_same_subject_and_sender(collector: MailCollector):
    """Test that is_changed returns False when subject and sender are same."""
    prev = _make_mail_result("Test Subject", "alice@test.com")
    curr = _make_mail_result("Test Subject", "alice@test.com")
    assert collector.is_changed(prev, curr) is False


def test_is_changed_different_subject(collector: MailCollector):
    """Test that is_changed returns True when subject changes."""
    prev = _make_mail_result("Subject A", "alice@test.com")
    curr = _make_mail_result("Subject B", "alice@test.com")
    assert collector.is_changed(prev, curr) is True


def test_is_changed_different_sender(collector: MailCollector):
    """Test that is_changed returns True when sender changes."""
    prev = _make_mail_result("Same Subject", "alice@test.com")
    curr = _make_mail_result("Same Subject", "bob@test.com")
    assert collector.is_changed(prev, curr) is True


def test_is_changed_different_title_same_selection(collector: MailCollector):
    """Test that is_changed returns False when only window title changes but subject/sender stay same."""
    prev = _make_mail_result("Subject", "alice@test.com", raw_title="Inbox")
    curr = _make_mail_result("Subject", "alice@test.com", raw_title="Sent")
    assert collector.is_changed(prev, curr) is False
