"""SQLite database management with WAL mode."""

from __future__ import annotations

import logging
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    app_name TEXT NOT NULL,
    app_bundle_id TEXT,
    event_type TEXT NOT NULL,
    window_title TEXT,
    context_json TEXT,
    duration_seconds REAL,
    category TEXT,
    subcategory TEXT,
    is_idle INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_app ON events(app_name, timestamp);

CREATE TABLE IF NOT EXISTS screenshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    file_path TEXT NOT NULL,
    app_name TEXT NOT NULL,
    window_title TEXT,
    file_size_bytes INTEGER,
    width INTEGER,
    height INTEGER,
    trigger_reason TEXT,
    llm_description TEXT,
    event_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_screenshots_timestamp ON screenshots(timestamp);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time TEXT NOT NULL,
    end_time TEXT,
    app_name TEXT NOT NULL,
    app_bundle_id TEXT,
    title_summary TEXT,
    context_summary TEXT,
    duration_seconds REAL,
    category TEXT,
    subcategory TEXT,
    event_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_sessions_time ON sessions(start_time, end_time);
"""


class Database:
    """Manages the SQLite database connection and schema."""

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None

    @property
    def connection(self) -> aiosqlite.Connection:
        """Get the active database connection.

        Raises:
            RuntimeError: If the database has not been initialized.
        """
        if self._conn is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._conn

    async def initialize(self) -> None:
        """Create the data directory, open connection, enable WAL, and run schema."""
        db_dir = Path(self._db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Opening database at %s", self._db_path)
        self._conn = await aiosqlite.connect(self._db_path)

        # Enable WAL mode for concurrent access
        await self._conn.execute("PRAGMA journal_mode=WAL")
        logger.info("WAL mode enabled")

        # Run schema
        await self._conn.executescript(SCHEMA_SQL)
        await self._conn.commit()
        logger.info("Database schema initialized")

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
            logger.info("Database connection closed")
