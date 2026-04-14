"""Screenshot scheduler — triggers captures on app switch and periodic intervals."""

from __future__ import annotations

import logging
import time

from life_optimizer.screenshots.capture import ScreenshotCapture, ScreenshotResult

logger = logging.getLogger(__name__)


class ScreenshotScheduler:
    """Manages screenshot timing: immediate on app switch, periodic otherwise.

    If captures fail repeatedly (e.g. missing Screen Recording permission),
    the scheduler backs off to avoid spamming the system with failed calls.
    """

    # Back off to 5 minutes after this many consecutive failures
    FAILURE_THRESHOLD = 3
    BACKOFF_SECONDS = 300.0

    def __init__(self, capture: ScreenshotCapture, interval: float = 30.0):
        self._capture = capture
        self._interval = interval
        self._last_capture_time: float = 0.0
        self.enabled: bool = True
        self._consecutive_failures: int = 0
        self._backoff_until: float = 0.0

    def _in_backoff(self) -> bool:
        return time.monotonic() < self._backoff_until

    def _record_result(self, result: ScreenshotResult | None) -> None:
        if result is None:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self.FAILURE_THRESHOLD:
                self._backoff_until = time.monotonic() + self.BACKOFF_SECONDS
                logger.warning(
                    "Screenshot capture failed %d times in a row, backing off for %.0fs",
                    self._consecutive_failures,
                    self.BACKOFF_SECONDS,
                )
        else:
            self._consecutive_failures = 0

    async def on_app_switch(self, app_name: str) -> ScreenshotResult | None:
        if not self.enabled or self._in_backoff():
            return None
        result = await self._capture.capture(app_name, "app_switch")
        self._last_capture_time = time.monotonic()
        self._record_result(result)
        return result

    async def tick(self, app_name: str) -> ScreenshotResult | None:
        if not self.enabled or self._in_backoff():
            return None
        now = time.monotonic()
        if now - self._last_capture_time >= self._interval:
            result = await self._capture.capture(app_name, "interval")
            self._last_capture_time = now
            self._record_result(result)
            return result
        return None
