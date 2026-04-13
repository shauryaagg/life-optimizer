"""Registry for mapping application names to their collectors."""

from __future__ import annotations

import logging

from life_optimizer.collectors.base import BaseCollector
from life_optimizer.collectors.chrome import ChromeCollector
from life_optimizer.collectors.generic import GenericCollector
from life_optimizer.collectors.jxa_bridge import JXABridge

logger = logging.getLogger(__name__)


class CollectorRegistry:
    """Maps application names to specialized collectors."""

    def __init__(self, default: BaseCollector, jxa_bridge: JXABridge):
        self._collectors: dict[str, BaseCollector] = {}
        self._default = default
        self._jxa_bridge = jxa_bridge

    def register(self, collector: BaseCollector) -> None:
        """Register a collector for its declared app names.

        Args:
            collector: Collector instance to register.
        """
        for name in collector.app_names:
            self._collectors[name] = collector
            logger.debug("Registered collector for '%s': %s", name, type(collector).__name__)

    def get_collector(self, app_name: str) -> BaseCollector:
        """Get the collector for a given app name.

        Args:
            app_name: Name of the application to look up.

        Returns:
            The specialized collector for the app, or the default generic collector.
        """
        return self._collectors.get(app_name, self._default)

    @classmethod
    def setup(cls, enabled: list[str] | None = None) -> CollectorRegistry:
        """Create a fully configured registry with all built-in collectors.

        Args:
            enabled: List of collector names to enable. If None, enables all.

        Returns:
            Configured CollectorRegistry instance.
        """
        if enabled is None:
            enabled = ["chrome", "generic"]

        jxa_bridge = JXABridge()
        generic = GenericCollector(jxa_bridge)
        registry = cls(default=generic, jxa_bridge=jxa_bridge)

        if "chrome" in enabled:
            chrome = ChromeCollector(jxa_bridge)
            registry.register(chrome)
            logger.info("Chrome collector enabled")

        logger.info(
            "Registry setup complete: %d app-specific collectors, generic fallback",
            len(registry._collectors),
        )
        return registry
