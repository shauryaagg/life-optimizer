"""Repository classes for database operations."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from life_optimizer.collectors.base import CollectorResult
from life_optimizer.screenshots.capture import ScreenshotResult
from life_optimizer.storage.database import Database
from life_optimizer.storage.models import ActivityEvent, Screenshot, Session

logger = logging.getLogger(__name__)


class EventRepository:
    """Repository for activity event CRUD operations."""

    def __init__(self, db: Database):
        self._db = db

    async def insert_event(self, result: CollectorResult) -> int:
        """Insert a collector result as an event and return the new row ID.

        Args:
            result: CollectorResult to persist.

        Returns:
            The auto-generated row ID of the inserted event.
        """
        conn = self._db.connection
        context_json = json.dumps(result.context) if result.context else None

        cursor = await conn.execute(
            """
            INSERT INTO events (timestamp, app_name, app_bundle_id, event_type,
                                window_title, context_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                result.timestamp.isoformat(),
                result.app_name,
                result.app_bundle_id,
                result.event_type,
                result.window_title,
                context_json,
            ),
        )
        await conn.commit()
        row_id = cursor.lastrowid
        logger.debug("Inserted event id=%d for app=%s", row_id, result.app_name)
        return row_id

    async def get_events(
        self,
        date: str | None = None,
        app: str | None = None,
        limit: int = 100,
    ) -> list[ActivityEvent]:
        """Retrieve events with optional filtering.

        Args:
            date: Filter by date (YYYY-MM-DD format). Matches events whose
                  timestamp starts with this date string.
            app: Filter by app_name (exact match).
            limit: Maximum number of events to return.

        Returns:
            List of ActivityEvent instances, ordered by timestamp descending.
        """
        conn = self._db.connection
        conditions = []
        params: list = []

        if date:
            conditions.append("timestamp LIKE ?")
            params.append(f"{date}%")
        if app:
            conditions.append("app_name = ?")
            params.append(app)

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT id, timestamp, app_name, app_bundle_id, event_type,
                   window_title, context_json, duration_seconds, category,
                   subcategory, is_idle, created_at
            FROM events
            {where}
            ORDER BY timestamp DESC
            LIMIT ?
        """
        params.append(limit)

        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()

        return [
            ActivityEvent(
                id=row[0],
                timestamp=row[1],
                app_name=row[2],
                app_bundle_id=row[3],
                event_type=row[4],
                window_title=row[5],
                context_json=row[6],
                duration_seconds=row[7],
                category=row[8],
                subcategory=row[9],
                is_idle=row[10] or 0,
                created_at=row[11] or "",
            )
            for row in rows
        ]

    async def get_event_count(self) -> int:
        """Get the total number of events in the database.

        Returns:
            Total event count.
        """
        conn = self._db.connection
        cursor = await conn.execute("SELECT COUNT(*) FROM events")
        row = await cursor.fetchone()
        return row[0] if row else 0


class ScreenshotRepository:
    """Repository for screenshot CRUD operations."""

    def __init__(self, db: Database):
        self._db = db

    async def insert_screenshot(self, result: ScreenshotResult) -> int:
        """Insert a screenshot result and return the new row ID.

        Args:
            result: ScreenshotResult to persist.

        Returns:
            The auto-generated row ID.
        """
        conn = self._db.connection
        cursor = await conn.execute(
            """
            INSERT INTO screenshots (timestamp, file_path, app_name,
                                     file_size_bytes, width, height, trigger_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.timestamp.isoformat(),
                result.file_path,
                result.app_name,
                result.file_size_bytes,
                result.width,
                result.height,
                result.trigger_reason,
            ),
        )
        await conn.commit()
        row_id = cursor.lastrowid
        logger.debug("Inserted screenshot id=%d for app=%s", row_id, result.app_name)
        return row_id

    async def get_screenshots(
        self, date: str | None = None, limit: int = 100
    ) -> list[Screenshot]:
        """Retrieve screenshots with optional date filtering.

        Args:
            date: Filter by date (YYYY-MM-DD format).
            limit: Maximum number of screenshots to return.

        Returns:
            List of Screenshot instances, ordered by timestamp descending.
        """
        conn = self._db.connection
        conditions = []
        params: list = []

        if date:
            conditions.append("timestamp LIKE ?")
            params.append(f"{date}%")

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT id, timestamp, file_path, app_name, window_title,
                   file_size_bytes, width, height, trigger_reason,
                   llm_description, event_id, created_at
            FROM screenshots
            {where}
            ORDER BY timestamp DESC
            LIMIT ?
        """
        params.append(limit)

        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()

        return [
            Screenshot(
                id=row[0],
                timestamp=row[1],
                file_path=row[2],
                app_name=row[3],
                window_title=row[4],
                file_size_bytes=row[5],
                width=row[6],
                height=row[7],
                trigger_reason=row[8],
                llm_description=row[9],
                event_id=row[10],
                created_at=row[11] or "",
            )
            for row in rows
        ]


class SessionRepository:
    """Repository for app usage session operations."""

    def __init__(self, db: Database):
        self._db = db

    async def start_session(
        self,
        app_name: str,
        bundle_id: str | None = None,
        window_title: str | None = None,
    ) -> int:
        """Start a new session and return its ID.

        Args:
            app_name: Name of the application.
            bundle_id: Bundle identifier.
            window_title: Initial window title.

        Returns:
            The auto-generated session ID.
        """
        conn = self._db.connection
        now = datetime.now(timezone.utc).isoformat()
        cursor = await conn.execute(
            """
            INSERT INTO sessions (start_time, app_name, app_bundle_id, title_summary)
            VALUES (?, ?, ?, ?)
            """,
            (now, app_name, bundle_id, window_title),
        )
        await conn.commit()
        row_id = cursor.lastrowid
        logger.debug("Started session id=%d for app=%s", row_id, app_name)
        return row_id

    async def end_session(
        self, session_id: int, end_time: str, event_count: int
    ) -> None:
        """End a session by setting its end time, duration, and event count.

        Args:
            session_id: ID of the session to end.
            end_time: ISO format end time string.
            event_count: Number of events recorded during this session.
        """
        conn = self._db.connection
        # Compute duration from start_time
        cursor = await conn.execute(
            "SELECT start_time FROM sessions WHERE id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        duration = None
        if row and row[0]:
            try:
                start_dt = datetime.fromisoformat(row[0])
                end_dt = datetime.fromisoformat(end_time)
                duration = (end_dt - start_dt).total_seconds()
            except (ValueError, TypeError):
                pass

        await conn.execute(
            """
            UPDATE sessions
            SET end_time = ?, duration_seconds = ?, event_count = ?
            WHERE id = ?
            """,
            (end_time, duration, event_count, session_id),
        )
        await conn.commit()
        logger.debug("Ended session id=%d, duration=%.1fs", session_id, duration or 0)

    async def get_sessions(self, date: str | None = None) -> list[Session]:
        """Retrieve sessions with optional date filtering.

        Args:
            date: Filter by date (YYYY-MM-DD format).

        Returns:
            List of Session instances, ordered by start_time descending.
        """
        conn = self._db.connection
        conditions = []
        params: list = []

        if date:
            conditions.append("start_time LIKE ?")
            params.append(f"{date}%")

        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)

        query = f"""
            SELECT id, start_time, end_time, app_name, app_bundle_id,
                   title_summary, context_summary, duration_seconds,
                   category, subcategory, event_count, created_at
            FROM sessions
            {where}
            ORDER BY start_time DESC
        """

        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()

        return [
            Session(
                id=row[0],
                start_time=row[1],
                end_time=row[2],
                app_name=row[3],
                app_bundle_id=row[4],
                title_summary=row[5],
                context_summary=row[6],
                duration_seconds=row[7],
                category=row[8],
                subcategory=row[9],
                event_count=row[10] or 0,
                created_at=row[11] or "",
            )
            for row in rows
        ]
