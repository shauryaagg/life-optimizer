"""Configuration loading and validation."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class DaemonConfig:
    poll_interval: float = 2.0
    idle_threshold: int = 300


@dataclass
class CollectorsConfig:
    enabled: list[str] = field(
        default_factory=lambda: [
            "chrome", "safari", "slack", "terminal",
            "vscode", "calendar", "finder", "messages",
            "mail", "generic",
        ]
    )


@dataclass
class MessagesConfig:
    include_content: bool = False


@dataclass
class ChromeExtensionConfig:
    enabled: bool = True


@dataclass
class StorageConfig:
    db_path: str = "./data/life_optimizer.db"


@dataclass
class ScreenshotsConfig:
    enabled: bool = True
    interval: float = 30.0
    quality: int = 60
    scale: float = 0.5
    capture_on_app_switch: bool = True
    retention_days: int = 30


@dataclass
class LLMConfig:
    provider: str = "claude"
    claude_model: str = "claude-sonnet-4-20250514"
    claude_api_key: str = ""
    ollama_model: str = "llama3.1:8b"
    ollama_base_url: str = "http://localhost:11434"
    batch_interval: int = 3600
    daily_insight_time: str = "22:00"


@dataclass
class DashboardConfig:
    host: str = "127.0.0.1"
    port: int = 8765


@dataclass
class Config:
    daemon: DaemonConfig = field(default_factory=DaemonConfig)
    collectors: CollectorsConfig = field(default_factory=CollectorsConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    screenshots: ScreenshotsConfig = field(default_factory=ScreenshotsConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    messages: MessagesConfig = field(default_factory=MessagesConfig)
    chrome_extension: ChromeExtensionConfig = field(default_factory=ChromeExtensionConfig)


def load_config(path: str = "config.yaml") -> Config:
    """Load configuration from YAML file, merging with defaults."""
    config = Config()

    config_path = Path(path)
    if not config_path.exists():
        return config

    with open(config_path, "r") as f:
        raw = yaml.safe_load(f)

    if not raw:
        return config

    if "daemon" in raw:
        d = raw["daemon"]
        if "poll_interval" in d:
            config.daemon.poll_interval = float(d["poll_interval"])
        if "idle_threshold" in d:
            config.daemon.idle_threshold = int(d["idle_threshold"])

    if "collectors" in raw:
        c = raw["collectors"]
        if "enabled" in c:
            config.collectors.enabled = list(c["enabled"])

    if "storage" in raw:
        s = raw["storage"]
        if "db_path" in s:
            config.storage.db_path = s["db_path"]

    if "screenshots" in raw:
        sc = raw["screenshots"]
        if "enabled" in sc:
            config.screenshots.enabled = bool(sc["enabled"])
        if "interval" in sc:
            config.screenshots.interval = float(sc["interval"])
        if "quality" in sc:
            config.screenshots.quality = int(sc["quality"])
        if "scale" in sc:
            config.screenshots.scale = float(sc["scale"])
        if "capture_on_app_switch" in sc:
            config.screenshots.capture_on_app_switch = bool(sc["capture_on_app_switch"])
        if "retention_days" in sc:
            config.screenshots.retention_days = int(sc["retention_days"])

    if "llm" in raw:
        llm = raw["llm"]
        if "provider" in llm:
            config.llm.provider = str(llm["provider"])
        if "claude" in llm:
            claude = llm["claude"]
            if "model" in claude:
                config.llm.claude_model = str(claude["model"])
            if "api_key_env" in claude:
                env_var = str(claude["api_key_env"])
                config.llm.claude_api_key = os.environ.get(env_var, "")
        if "ollama" in llm:
            ollama = llm["ollama"]
            if "model" in ollama:
                config.llm.ollama_model = str(ollama["model"])
            if "base_url" in ollama:
                config.llm.ollama_base_url = str(ollama["base_url"])
        if "batch_interval" in llm:
            config.llm.batch_interval = int(llm["batch_interval"])
        if "daily_insight_time" in llm:
            config.llm.daily_insight_time = str(llm["daily_insight_time"])

    if "dashboard" in raw:
        dash = raw["dashboard"]
        if "host" in dash:
            config.dashboard.host = str(dash["host"])
        if "port" in dash:
            config.dashboard.port = int(dash["port"])

    if "collectors" in raw:
        c = raw["collectors"]
        if "messages" in c and isinstance(c["messages"], dict):
            msg = c["messages"]
            if "include_content" in msg:
                config.messages.include_content = bool(msg["include_content"])

    if "chrome_extension" in raw:
        ce = raw["chrome_extension"]
        if "enabled" in ce:
            config.chrome_extension.enabled = bool(ce["enabled"])

    return config
