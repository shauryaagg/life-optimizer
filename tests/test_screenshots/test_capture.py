"""Tests for screenshot capture module."""

import pytest
from datetime import datetime, timezone

from life_optimizer.screenshots.capture import ScreenshotCapture, ScreenshotResult


def test_screenshot_result_dataclass():
    """Test ScreenshotResult dataclass creation and fields."""
    ts = datetime(2025, 6, 15, 10, 30, 45, tzinfo=timezone.utc)
    result = ScreenshotResult(
        file_path="data/screenshots/2025-06-15/103045_chrome.jpg",
        timestamp=ts,
        file_size_bytes=54321,
        width=960,
        height=540,
        app_name="Google Chrome",
        trigger_reason="app_switch",
    )
    assert result.file_path == "data/screenshots/2025-06-15/103045_chrome.jpg"
    assert result.timestamp == ts
    assert result.file_size_bytes == 54321
    assert result.width == 960
    assert result.height == 540
    assert result.app_name == "Google Chrome"
    assert result.trigger_reason == "app_switch"


def test_build_path_creates_dated_directory():
    """Test that _build_path creates YYYY-MM-DD/HHMMSS_appname.jpg format."""
    capture = ScreenshotCapture(base_dir="/tmp/screenshots")
    ts = datetime(2025, 3, 20, 14, 5, 30, tzinfo=timezone.utc)

    path = capture._build_path("Google Chrome", ts)

    assert "2025-03-20" in str(path)
    assert str(path).endswith(".jpg")
    assert "google_chrome" in str(path)
    assert "140530" in str(path)


def test_build_path_sanitizes_app_name():
    """Test that special characters in app name are replaced with underscores."""
    capture = ScreenshotCapture(base_dir="/tmp/screenshots")
    ts = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    path = capture._build_path("My App (2.0)", ts)
    filename = path.name

    # Should not contain parentheses, spaces, or dots (except .jpg)
    name_part = filename.replace(".jpg", "")
    assert "(" not in name_part
    assert ")" not in name_part
    assert " " not in name_part


def test_build_path_format():
    """Test the exact file path format: HHMMSS_appname.jpg."""
    capture = ScreenshotCapture(base_dir="data/screenshots")
    ts = datetime(2025, 7, 4, 9, 15, 0, tzinfo=timezone.utc)

    path = capture._build_path("Safari", ts)

    assert str(path) == "data/screenshots/2025-07-04/091500_safari.jpg"
