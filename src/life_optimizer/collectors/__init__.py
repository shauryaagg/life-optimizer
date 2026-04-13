"""Activity collectors for various macOS applications."""

from life_optimizer.collectors.base import BaseCollector, CollectorResult
from life_optimizer.collectors.calendar_app import CalendarCollector
from life_optimizer.collectors.chrome import ChromeCollector
from life_optimizer.collectors.finder import FinderCollector
from life_optimizer.collectors.generic import GenericCollector
from life_optimizer.collectors.jxa_bridge import JXABridge
from life_optimizer.collectors.registry import CollectorRegistry
from life_optimizer.collectors.safari import SafariCollector
from life_optimizer.collectors.slack import SlackCollector
from life_optimizer.collectors.terminal import TerminalCollector
from life_optimizer.collectors.vscode import VSCodeCollector

__all__ = [
    "BaseCollector",
    "CollectorResult",
    "CalendarCollector",
    "ChromeCollector",
    "FinderCollector",
    "GenericCollector",
    "JXABridge",
    "CollectorRegistry",
    "SafariCollector",
    "SlackCollector",
    "TerminalCollector",
    "VSCodeCollector",
]
