"""Screenshot scheduler — triggers captures on app switch and periodic intervals."""

from __future__ import annotations

import logging
import time

from life_optimizer.screenshots.capture import ScreenshotCapture, ScreenshotResult

logger = logging.getLogger(__name__)


class ScreenshotScheduler:
    """Manages screenshot timing: immediate on app switch, periodic otherwise."""

    def __init__(self, capture: ScreenshotCapture, interval: float = 30.0):
        self._capture = capture
        self._interval = interval
        self._last_capture_time: float = 0.0
        self.enabled: bool = True

    async def on_app_switch(self, app_name: str) -> ScreenshotResult | None:
        """Take an immediate screenshot on application switch.

        Args:
            app_name: Name of the newly focused application.

        Returns:
            ScreenshotResult or None.
        """
        if not self.enabled:
            return None
        result = await self._capture.capture(app_name, "app_switch")
        self._last_capture_time = time.monotonic()
        return result

    async def tick(self, app_name: str) -> ScreenshotResult | None:
        """Check if interval has elapsed and capture if so.

        Args:
            app_name: Name of the current frontmost application.

        Returns:
            ScreenshotResult or None.
        """
        if not self.enabled:
            return None
        now = time.monotonic()
        if now - self._last_capture_time >= self._interval:
            result = await self._capture.capture(app_name, "interval")
            self._last_capture_time = now
            return result
        return None
