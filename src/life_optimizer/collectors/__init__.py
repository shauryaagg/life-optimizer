"""Activity collectors for various macOS applications."""

from life_optimizer.collectors.base import BaseCollector, CollectorResult
from life_optimizer.collectors.chrome import ChromeCollector
from life_optimizer.collectors.generic import GenericCollector
from life_optimizer.collectors.jxa_bridge import JXABridge
from life_optimizer.collectors.registry import CollectorRegistry

__all__ = [
    "BaseCollector",
    "CollectorResult",
    "ChromeCollector",
    "GenericCollector",
    "JXABridge",
    "CollectorRegistry",
]
