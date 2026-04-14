"""Screenshot capture has been moved to the Swift macOS app.

The Swift app is the only TCC principal with Screen Recording permission.
Calling screencapture from this Python process would trigger a macOS
permission dialog every time, because the Python process has a different
code signature / identity than the Swift app.

This module is kept as a stub so existing imports don't break. It returns
None on every capture call, disabling Python-side screenshots entirely.
The Swift app at macos-app/Sources/LifeOptimizer/Screenshots/ScreenshotCapture.swift
handles all screenshot capture using CGWindowListCreateImage with the
app's native TCC permission.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class ScreenshotResult:
    """Result of a screenshot capture."""

    file_path: str
    timestamp: datetime
    file_size_bytes: int
    width: int
    height: int
    app_name: str
    trigger_reason: str


class ScreenshotCapture:
    """Disabled — the Swift app handles screenshot capture.

    All methods return None to make the daemon explicitly inert with respect
    to screen recording. The Swift app writes JPEGs directly to
    data/screenshots/YYYY-MM-DD/ and the dashboard lists files from disk.
    """

    def __init__(self, base_dir: str = "data/screenshots", quality: int = 60, scale: float = 0.5):
        # Kept for API compatibility; arguments are ignored
        self._base_dir = base_dir
        self._quality = quality
        self._scale = scale

    async def capture(self, app_name: str, trigger: str) -> ScreenshotResult | None:
        """Disabled. Swift app handles screen recording."""
        return None
