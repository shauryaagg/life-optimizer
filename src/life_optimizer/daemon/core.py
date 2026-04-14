"""Core daemon loop for polling and storing activity events."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from datetime import datetime, timezone
from pathlib import Path

from life_optimizer.collectors.base import CollectorResult
from life_optimizer.collectors.jxa_bridge import JXABridge
from life_optimizer.collectors.registry import CollectorRegistry
from life_optimizer.config import Config
from life_optimizer.constants import APP_ACTIVATE
from life_optimizer.screenshots.capture import ScreenshotCapture
from life_optimizer.screenshots.scheduler import ScreenshotScheduler
from life_optimizer.storage.database import Database
from life_optimizer.storage.repositories import (
    EventRepository,
    ScreenshotRepository,
    SessionRepository,
)
from life_optimizer.llm import create_llm_client
from life_optimizer.llm.pipeline import LLMPipeline

logger = logging.getLogger(__name__)

# Try to import WorkspaceListener; it is optional
try:
    from life_optimizer.daemon.workspace_listener import WorkspaceListener

    _HAS_WORKSPACE_LISTENER = True
except ImportError:
    _HAS_WORKSPACE_LISTENER = False

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
        self._screenshot_repo: ScreenshotRepository | None = None
        self._session_repo: SessionRepository | None = None
        self._registry: CollectorRegistry | None = None
        self._screenshot_scheduler: ScreenshotScheduler | None = None
        self._current_session_id: int | None = None
        self._session_event_count: int = 0
        self._workspace_listener: object | None = None
        self._event_queue: asyncio.Queue | None = None
        self._llm_pipeline: LLMPipeline | None = None
        self._last_categorization: float = 0
        self._last_daily_insight: str | None = None
        self._is_idle: bool = False
        self._idle_start_time: float | None = None

    async def start(self) -> None:
        """Initialize all components and start the main polling loop."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )

        logger.info("Starting Life Optimizer daemon...")
        logger.info("Poll interval: %.1fs", self._config.daemon.poll_interval)

        # Acquire PID lock — kill any existing daemon first
        self._acquire_pid_lock()

        # Initialize database
        self._db = Database(self._config.storage.db_path)
        await self._db.initialize()
        self._repo = EventRepository(self._db)
        self._screenshot_repo = ScreenshotRepository(self._db)
        self._session_repo = SessionRepository(self._db)

        # Initialize collector registry
        self._registry = CollectorRegistry.setup(
            enabled=self._config.collectors.enabled
        )

        # Initialize screenshot scheduler
        sc_config = self._config.screenshots
        capture = ScreenshotCapture(
            quality=sc_config.quality,
            scale=sc_config.scale,
        )
        self._screenshot_scheduler = ScreenshotScheduler(
            capture=capture,
            interval=sc_config.interval,
        )
        self._screenshot_scheduler.enabled = sc_config.enabled

        # Initialize LLM pipeline (optional)
        try:
            llm_client = create_llm_client(self._config)
            self._llm_pipeline = LLMPipeline(llm_client, self._db)
            llm_status = llm_client.name if llm_client else "none (rule-based only)"
        except Exception as e:
            logger.warning("Failed to initialize LLM pipeline: %s", e)
            self._llm_pipeline = None
            llm_status = "failed"

        self._running = True

        # Register signal handlers for graceful shutdown
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))

        # Start NSWorkspace listener (optional — falls back to polling if unavailable)
        workspace_status = "unavailable"
        if _HAS_WORKSPACE_LISTENER:
            try:
                self._event_queue = asyncio.Queue()
                self._workspace_listener = WorkspaceListener(
                    self._event_queue, loop
                )
                self._workspace_listener.start()
                workspace_status = "active"
            except Exception as e:
                logger.warning(
                    "NSWorkspace listener failed to start, using polling only: %s", e
                )
                self._workspace_listener = None
                workspace_status = "failed"
        else:
            logger.info(
                "pyobjc not available, using polling only for app detection"
            )

        logger.info("Daemon started. Press Ctrl+C to stop.")
        print("=" * 60)
        print("Life Optimizer -- Activity Monitor")
        print(f"Database: {self._config.storage.db_path}")
        print(f"Poll interval: {self._config.daemon.poll_interval}s")
        print(f"Screenshots: {'enabled' if sc_config.enabled else 'disabled'}")
        print(f"NSWorkspace listener: {workspace_status}")
        print(f"LLM provider: {llm_status}")
        print("=" * 60)

        try:
            # Run both the polling loop and event queue consumer concurrently
            tasks = [asyncio.create_task(self._main_loop())]
            if self._workspace_listener is not None and self._event_queue is not None:
                tasks.append(asyncio.create_task(self._process_workspace_events()))
            if self._llm_pipeline is not None:
                tasks.append(asyncio.create_task(self._llm_periodic_loop()))
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass
        finally:
            if self._workspace_listener is not None:
                self._workspace_listener.stop()
            await self._cleanup()

    async def stop(self) -> None:
        """Signal the daemon to stop."""
        logger.info("Stop requested")
        self._running = False

    def _acquire_pid_lock(self) -> None:
        """Kill any existing daemon and write our PID to a lockfile."""
        lock_path = Path(self._config.storage.db_path).parent / "daemon.pid"
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        # If a PID file exists, check if that process is still running
        if lock_path.exists():
            try:
                old_pid = int(lock_path.read_text().strip())
                if old_pid != os.getpid():
                    try:
                        # Check if alive: kill -0 doesn't kill, just probes
                        os.kill(old_pid, 0)
                        # It's alive — terminate it
                        logger.warning("Killing existing daemon PID %d", old_pid)
                        os.kill(old_pid, signal.SIGTERM)
                        import time
                        time.sleep(1)
                        try:
                            os.kill(old_pid, 0)
                            # Still alive after SIGTERM, force kill
                            os.kill(old_pid, signal.SIGKILL)
                            time.sleep(0.5)
                        except ProcessLookupError:
                            pass  # Exited cleanly
                    except ProcessLookupError:
                        pass  # Not running — stale lockfile
            except (ValueError, OSError) as e:
                logger.debug("Could not parse existing PID file: %s", e)

        # Write our PID
        try:
            lock_path.write_text(str(os.getpid()))
            logger.info("Acquired daemon lock: %s (PID %d)", lock_path, os.getpid())
        except OSError as e:
            logger.warning("Failed to write PID lock: %s", e)

        self._pid_lock_path = lock_path

    def _release_pid_lock(self) -> None:
        """Remove the PID lockfile on clean shutdown."""
        lock_path = getattr(self, "_pid_lock_path", None)
        if lock_path is None:
            return
        try:
            if lock_path.exists():
                current = lock_path.read_text().strip()
                if current == str(os.getpid()):
                    lock_path.unlink()
        except OSError:
            pass

    async def _cleanup(self) -> None:
        """Clean up resources on shutdown."""
        # End any active session
        await self._end_current_session()
        self._release_pid_lock()

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

    async def _process_workspace_events(self) -> None:
        """Drain the NSWorkspace event queue and handle app-switch events."""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            except Exception:
                continue

            try:
                app_name = event.get("app_name", "")
                bundle_id = event.get("bundle_id", "")
                if not app_name:
                    continue

                logger.debug(
                    "NSWorkspace event: %s (%s)", app_name, bundle_id
                )

                # Trigger an immediate poll for this app switch
                await self._handle_app_switch_event(app_name, bundle_id)
            except Exception as e:
                logger.error("Error processing workspace event: %s", e)

    async def _handle_app_switch_event(
        self, app_name: str, bundle_id: str
    ) -> None:
        """Handle an app-switch event from the NSWorkspace listener."""
        if app_name == self._previous_app:
            return  # Not actually a switch

        self._previous_result = None  # Reset dedup

        # End previous session and start new one
        await self._end_current_session()
        if self._session_repo is not None:
            self._current_session_id = await self._session_repo.start_session(
                app_name, bundle_id
            )

        # Screenshot on app switch
        if (
            self._screenshot_scheduler is not None
            and self._config.screenshots.capture_on_app_switch
        ):
            ss_result = await self._screenshot_scheduler.on_app_switch(app_name)
            if ss_result is not None and self._screenshot_repo is not None:
                await self._screenshot_repo.insert_screenshot(ss_result)

        # Get the appropriate collector and collect data
        collector = self._registry.get_collector(app_name)
        result = await collector.collect(app_name, bundle_id)
        if result is not None:
            result.event_type = APP_ACTIVATE

            event_id = await self._repo.insert_event(result)
            self._session_event_count += 1

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

            self._previous_result = result

        self._previous_app = app_name

    async def _end_current_session(self) -> None:
        """End the current session if one is active."""
        if self._current_session_id is not None and self._session_repo is not None:
            try:
                end_time = datetime.now(timezone.utc).isoformat()
                await self._session_repo.end_session(
                    self._current_session_id,
                    end_time,
                    self._session_event_count,
                )
            except Exception as e:
                logger.warning("Failed to end session: %s", e)
            self._current_session_id = None
            self._session_event_count = 0

    async def _llm_periodic_loop(self) -> None:
        """Periodically run LLM categorization and daily insights."""
        import time

        batch_interval = self._config.llm.batch_interval
        daily_insight_time = self._config.llm.daily_insight_time

        while self._running:
            try:
                now = time.time()

                # Run categorization at batch_interval
                if now - self._last_categorization >= batch_interval:
                    await self._llm_pipeline.run_categorization()
                    await self._llm_pipeline.run_hourly_summary()
                    self._last_categorization = now

                # Check for daily insight time
                current_time = datetime.now().strftime("%H:%M")
                today = datetime.now().strftime("%Y-%m-%d")
                if (
                    current_time >= daily_insight_time
                    and self._last_daily_insight != today
                ):
                    await self._llm_pipeline.run_daily_insights(date=today)
                    self._last_daily_insight = today

            except Exception as e:
                logger.error("Error in LLM periodic loop: %s", e, exc_info=True)

            # Check every 60 seconds
            await asyncio.sleep(60)

    async def _poll_once(self) -> None:
        """Execute a single poll cycle."""
        import time

        # Check idle state
        idle_seconds = await self._check_idle()
        idle_threshold = self._config.daemon.idle_threshold

        if idle_seconds >= idle_threshold:
            if not self._is_idle:
                # Transition to idle
                self._is_idle = True
                self._idle_start_time = time.time()
                logger.info(
                    "User idle (%.0fs > %ds threshold)", idle_seconds, idle_threshold
                )
            # While idle, skip screenshots and collection
            return

        if self._is_idle:
            # Returning from idle
            idle_duration = time.time() - (self._idle_start_time or time.time())
            self._is_idle = False
            self._idle_start_time = None
            logger.info("User returned from idle (was idle %.0fs)", idle_duration)

            # Take immediate screenshot on return from idle
            if self._screenshot_scheduler is not None:
                app_info = await self._detect_frontmost_app()
                if app_info is not None:
                    ss_result = await self._screenshot_scheduler.on_app_switch(
                        app_info[0]
                    )
                    if ss_result is not None and self._screenshot_repo is not None:
                        await self._screenshot_repo.insert_screenshot(ss_result)

        # Detect frontmost app
        app_info = await self._detect_frontmost_app()
        if app_info is None:
            return

        app_name, bundle_id = app_info

        # Check if app changed
        app_changed = app_name != self._previous_app
        if app_changed:
            self._previous_result = None  # Reset dedup on app change

            # End previous session and start new one
            await self._end_current_session()
            if self._session_repo is not None:
                self._current_session_id = await self._session_repo.start_session(
                    app_name, bundle_id
                )

            # Screenshot on app switch
            if (
                self._screenshot_scheduler is not None
                and self._config.screenshots.capture_on_app_switch
            ):
                ss_result = await self._screenshot_scheduler.on_app_switch(app_name)
                if ss_result is not None and self._screenshot_repo is not None:
                    await self._screenshot_repo.insert_screenshot(ss_result)

        # Periodic screenshot tick
        if self._screenshot_scheduler is not None:
            ss_result = await self._screenshot_scheduler.tick(app_name)
            if ss_result is not None and self._screenshot_repo is not None:
                await self._screenshot_repo.insert_screenshot(ss_result)

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
        self._session_event_count += 1

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

    async def _check_idle(self) -> float:
        """Return seconds since last user input (keyboard/mouse).

        Uses CoreGraphics via pyobjc when available, falls back to 0.0.

        Returns:
            Seconds since last user input event, or 0.0 if unavailable.
        """
        try:
            import Quartz
            idle_time = Quartz.CGEventSourceSecondsSinceLastEventType(
                Quartz.kCGEventSourceStateHIDSystemState,
                Quartz.kCGAnyInputEventType,
            )
            return idle_time
        except (ImportError, Exception):
            return 0.0

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
