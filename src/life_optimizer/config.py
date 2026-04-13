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
    enabled: list[str] = field(default_factory=lambda: ["chrome", "generic"])


@dataclass
class StorageConfig:
    db_path: str = "./data/life_optimizer.db"


@dataclass
class Config:
    daemon: DaemonConfig = field(default_factory=DaemonConfig)
    collectors: CollectorsConfig = field(default_factory=CollectorsConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)


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

    return config
