"""Tests for the collector registry."""

import pytest

from life_optimizer.collectors.chrome import ChromeCollector
from life_optimizer.collectors.generic import GenericCollector
from life_optimizer.collectors.registry import CollectorRegistry


def test_registry_returns_chrome_for_google_chrome():
    """Test that the registry returns ChromeCollector for 'Google Chrome'."""
    registry = CollectorRegistry.setup(enabled=["chrome", "generic"])
    collector = registry.get_collector("Google Chrome")
    assert isinstance(collector, ChromeCollector)


def test_registry_returns_generic_for_unknown_app():
    """Test that the registry returns GenericCollector for unknown apps."""
    registry = CollectorRegistry.setup(enabled=["chrome", "generic"])
    collector = registry.get_collector("SomeRandomApp")
    assert isinstance(collector, GenericCollector)


def test_registry_returns_generic_for_finder():
    """Test that Finder (no specific collector) gets the generic collector."""
    registry = CollectorRegistry.setup(enabled=["chrome", "generic"])
    collector = registry.get_collector("Finder")
    assert isinstance(collector, GenericCollector)


def test_registry_setup_without_chrome():
    """Test registry setup with Chrome disabled."""
    registry = CollectorRegistry.setup(enabled=["generic"])
    collector = registry.get_collector("Google Chrome")
    # Without Chrome enabled, it should fall back to generic
    assert isinstance(collector, GenericCollector)


def test_registry_register_custom_collector():
    """Test manual registration of a collector."""
    registry = CollectorRegistry.setup(enabled=[])
    from life_optimizer.collectors.jxa_bridge import JXABridge

    bridge = JXABridge()
    chrome = ChromeCollector(bridge)
    registry.register(chrome)

    collector = registry.get_collector("Google Chrome")
    assert isinstance(collector, ChromeCollector)
