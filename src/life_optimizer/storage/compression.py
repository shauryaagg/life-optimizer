"""Memory compression: archive old events and prune stale data."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from life_optimizer.storage.database import Database

logger = logging.getLogger(__name__)

DEFAULT_ARCHIVE_AFTER_DAYS = 14
DEFAULT_DELETE_AFTER_DAYS = 90


class MemoryCompressor:
    """Archives old events and deletes stale archived data."""

    def __init__(
        self,
        archive_after_days: int = DEFAULT_ARCHIVE_AFTER_DAYS,
        delete_after_days: int = DEFAULT_DELETE_AFTER_DAYS,
    ):
        self._archive_after_days = archive_after_days
        self._delete_after_days = delete_after_days

    async def compress(self, db: Database) -> dict:
        """Run compression: archive old events and prune stale archives.

        Args:
            db: Database instance.

        Returns:
            Dict with keys "archived" and "deleted" indicating counts.
        """
        conn = db.connection
        now = datetime.now(timezone.utc)

        # Archive events older than archive_after_days
        archive_cutoff = (now - timedelta(days=self._archive_after_days)).isoformat()
        cursor = await conn.execute(
            """
            INSERT OR IGNORE INTO archived_events (id, timestamp, app_name, category, duration_seconds, created_at)
            SELECT id, timestamp, app_name, category, duration_seconds, created_at
            FROM events
            WHERE timestamp < ?
            """,
            (archive_cutoff,),
        )
        archived_count = cursor.rowcount or 0

        # Delete the archived events from the main events table
        if archived_count > 0:
            await conn.execute(
                """
                DELETE FROM events
                WHERE timestamp < ? AND id IN (SELECT id FROM archived_events)
                """,
                (archive_cutoff,),
            )

        # Delete archived events older than delete_after_days
        delete_cutoff = (now - timedelta(days=self._delete_after_days)).isoformat()
        cursor = await conn.execute(
            "DELETE FROM archived_events WHERE timestamp < ?",
            (delete_cutoff,),
        )
        deleted_count = cursor.rowcount or 0

        await conn.commit()

        if archived_count > 0 or deleted_count > 0:
            logger.info(
                "Compression: archived=%d, deleted=%d",
                archived_count,
                deleted_count,
            )

        return {"archived": archived_count, "deleted": deleted_count}
