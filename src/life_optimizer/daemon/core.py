"""Core daemon loop for polling and storing activity events."""

from __future__ import annotations

import asyncio
import logging
import signal
from datetime import datetime, timezone

from life_optimizer.collectors.base import CollectorResult
from life_optimizer.collectors.jxa_bridge import JXABridge
from life_optimizer.collectors.registry import CollectorRegistry
from life_optimizer.config import Config
from life_optimizer.constants import APP_ACTIVATE
from life_optimizer.storage.database import Database
from life_optimizer.storage.repositories import EventRepository

logger = logging.getLogger(__name__)

# AppleScript to detect the frontmost application
FRONTMOST_APP_SCRIPT = """tell application "System Events"
    set frontApp to first application process whose frontmost is true
    set appName to name of frontApp
    set bundleID to bundle identifier of frontApp
    return appName & "|" & bundleID
end tell"""


class Daemon:
    """Main daemon that polls for activity and stores events."""

    def __init__(self, config: Config):
        self._config = config
        self._running = False
        self._previous_result: CollectorResult | None = None
        self._previous_app: str | None = None
        self._jxa_bridge = JXABridge()
        self._db: Database | None = None
        self._repo: EventRepository | None = None
        self._registry: CollectorRegistry | None = None

    async def start(self) -> None:
        """Initialize all components and start the main polling loop."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )

        logger.info("Starting Life Optimizer daemon...")
        logger.info("Poll interval: %.1fs", self._config.daemon.poll_interval)

        # Initialize database
        self._db = Database(self._config.storage.db_path)
        await self._db.initialize()
        self._repo = EventRepository(self._db)

        # Initialize collector registry
        self._registry = CollectorRegistry.setup(
            enabled=self._config.collectors.enabled
        )

        self._running = True

        # Register signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        logger.info("Daemon started. Press Ctrl+C to stop.")
        print("=" * 60)
        print("Life Optimizer — Activity Monitor")
        print(f"Database: {self._config.storage.db_path}")
        print(f"Poll interval: {self._config.daemon.poll_interval}s")
        print("=" * 60)

        try:
            await self._main_loop()
        except asyncio.CancelledError:
            pass
        finally:
            await self._cleanup()

    async def stop(self) -> None:
        """Signal the daemon to stop."""
        logger.info("Stop requested")
        self._running = False

    async def _cleanup(self) -> None:
        """Clean up resources on shutdown."""
        if self._repo is not None and self._db is not None:
            try:
                count = await self._repo.get_event_count()
                logger.info("Total events stored: %d", count)
            except Exception:
                pass
        if self._db is not None:
            await self._db.close()
        logger.info("Daemon stopped.")

    async def _main_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                await self._poll_once()
            except Exception as e:
                logger.error("Error during poll: %s", e, exc_info=True)

            await asyncio.sleep(self._config.daemon.poll_interval)

    async def _poll_once(self) -> None:
        """Execute a single poll cycle."""
        # Detect frontmost app
        app_info = await self._detect_frontmost_app()
        if app_info is None:
            return

        app_name, bundle_id = app_info

        # Check if app changed
        app_changed = app_name != self._previous_app
        if app_changed:
            self._previous_result = None  # Reset dedup on app change

        # Get the appropriate collector
        collector = self._registry.get_collector(app_name)

        # Collect data
        result = await collector.collect(app_name, bundle_id)
        if result is None:
            return

        # Override event type if app just changed
        if app_changed:
            result.event_type = APP_ACTIVATE

        # Check if result has changed (deduplication)
        if not collector.is_changed(self._previous_result, result):
            return  # Skip, nothing changed

        # Store the event
        event_id = await self._repo.insert_event(result)

        # Print for debugging
        context_str = ""
        if result.context:
            url = result.context.get("url", "")
            if url:
                context_str = f" | {url}"

        timestamp = result.timestamp.strftime("%H:%M:%S")
        print(
            f"[{timestamp}] {result.event_type:15s} | {result.app_name:20s} "
            f"| {result.window_title or '(no title)':40s}{context_str}"
        )

        # Update state
        self._previous_result = result
        self._previous_app = app_name

    async def _detect_frontmost_app(self) -> tuple[str, str | None] | None:
        """Detect the frontmost macOS application.

        Returns:
            Tuple of (app_name, bundle_id) or None if detection failed.
        """
        result = await self._jxa_bridge.run_applescript(FRONTMOST_APP_SCRIPT)
        if result is None:
            logger.debug("Failed to detect frontmost app")
            return None

        parts = result.split("|", 1)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
        elif len(parts) == 1:
            return parts[0].strip(), None
        return None
