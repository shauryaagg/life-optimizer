"""Repository classes for database operations."""

from __future__ import annotations

import json
import logging

from life_optimizer.collectors.base import CollectorResult
from life_optimizer.storage.database import Database
from life_optimizer.storage.models import ActivityEvent

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
