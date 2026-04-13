"""NSWorkspace event-driven app switch detection via pyobjc."""

from __future__ import annotations

import asyncio
import logging
import threading

logger = logging.getLogger(__name__)


class WorkspaceListener:
    """Listens for NSWorkspace app activation notifications in a background thread."""

    def __init__(self, event_queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self._queue = event_queue
        self._loop = loop
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="workspace-listener"
        )
        self._running = False

    def start(self):
        self._running = True
        self._thread.start()
        logger.info("NSWorkspace listener started")

    def stop(self):
        self._running = False
        # NSRunLoop will exit when thread is daemon and main thread exits

    def _run(self):
        try:
            from AppKit import NSWorkspace, NSRunLoop
            from Foundation import NSObject
            import objc

            class Observer(NSObject):
                def initWithQueue_loop_(self, queue, loop):
                    self = objc.super(Observer, self).init()
                    if self is None:
                        return None
                    self._queue = queue
                    self._loop = loop
                    return self

                def appActivated_(self, notification):
                    try:
                        user_info = notification.userInfo()
                        app_name = user_info.get("NSApplicationName", "")
                        bundle_id = user_info.get(
                            "NSApplicationBundleIdentifier", ""
                        )
                        self._loop.call_soon_threadsafe(
                            self._queue.put_nowait,
                            {"app_name": app_name, "bundle_id": bundle_id},
                        )
                    except Exception as e:
                        logger.error(f"Error in appActivated: {e}")

            observer = Observer.alloc().initWithQueue_loop_(
                self._queue, self._loop
            )
            ws = NSWorkspace.sharedWorkspace()
            nc = ws.notificationCenter()
            nc.addObserver_selector_name_object_(
                observer,
                objc.selector(observer.appActivated_, signature=b"v@:@"),
                "NSWorkspaceDidActivateApplicationNotification",
                None,
            )

            logger.info("NSWorkspace observer registered, starting run loop")
            run_loop = NSRunLoop.currentRunLoop()
            while self._running:
                run_loop.runMode_beforeDate_(
                    "NSDefaultRunLoopMode",
                    NSRunLoop.currentRunLoop().limitDateForMode_(
                        "NSDefaultRunLoopMode"
                    ),
                )

        except ImportError:
            logger.warning(
                "pyobjc not available, NSWorkspace listener disabled"
            )
        except Exception as e:
            logger.error(f"NSWorkspace listener error: {e}")
