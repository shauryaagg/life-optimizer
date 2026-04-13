"""Tests for memory compression."""

import pytest
from datetime import datetime, timedelta, timezone

from life_optimizer.storage.compression import MemoryCompressor
from life_optimizer.storage.database import Database


@pytest.fixture
async def db(tmp_path):
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test_compression.db")
    database = Database(db_path)
    await database.initialize()
    yield database
    await database.close()


async def _insert_event(db, timestamp: str, app_name: str = "TestApp"):
    """Helper to insert a test event."""
    conn = db.connection
    cursor = await conn.execute(
        """
        INSERT INTO events (timestamp, app_name, event_type, created_at)
        VALUES (?, ?, 'poll', datetime('now'))
        """,
        (timestamp, app_name),
    )
    await conn.commit()
    return cursor.lastrowid


async def _count_events(db) -> int:
    """Helper to count events."""
    conn = db.connection
    cursor = await conn.execute("SELECT COUNT(*) FROM events")
    row = await cursor.fetchone()
    return row[0]


async def _count_archived(db) -> int:
    """Helper to count archived events."""
    conn = db.connection
    cursor = await conn.execute("SELECT COUNT(*) FROM archived_events")
    row = await cursor.fetchone()
    return row[0]


async def test_archive_old_events(db):
    """Test archiving events older than threshold."""
    now = datetime.now(timezone.utc)

    # Insert an old event (20 days ago)
    old_ts = (now - timedelta(days=20)).isoformat()
    await _insert_event(db, old_ts, "OldApp")

    # Insert a recent event (1 day ago)
    recent_ts = (now - timedelta(days=1)).isoformat()
    await _insert_event(db, recent_ts, "NewApp")

    compressor = MemoryCompressor(archive_after_days=14, delete_after_days=90)
    result = await compressor.compress(db)

    assert result["archived"] == 1
    assert result["deleted"] == 0

    # Old event should be archived and removed from events
    assert await _count_events(db) == 1
    assert await _count_archived(db) == 1


async def test_delete_old_archived_events(db):
    """Test deletion of old archived events."""
    now = datetime.now(timezone.utc)

    # Insert directly into archived_events with very old timestamp
    very_old_ts = (now - timedelta(days=100)).isoformat()
    conn = db.connection
    await conn.execute(
        """
        INSERT INTO archived_events (id, timestamp, app_name, created_at)
        VALUES (999, ?, 'VeryOldApp', datetime('now'))
        """,
        (very_old_ts,),
    )
    await conn.commit()

    compressor = MemoryCompressor(archive_after_days=14, delete_after_days=90)
    result = await compressor.compress(db)

    assert result["deleted"] == 1
    assert await _count_archived(db) == 0


async def test_compression_no_old_events(db):
    """Test compression with no old events (no-op)."""
    now = datetime.now(timezone.utc)

    # Insert only recent events
    recent_ts = (now - timedelta(hours=1)).isoformat()
    await _insert_event(db, recent_ts, "RecentApp")

    compressor = MemoryCompressor(archive_after_days=14, delete_after_days=90)
    result = await compressor.compress(db)

    assert result["archived"] == 0
    assert result["deleted"] == 0
    assert await _count_events(db) == 1


async def test_compression_empty_database(db):
    """Test compression on an empty database."""
    compressor = MemoryCompressor()
    result = await compressor.compress(db)

    assert result["archived"] == 0
    assert result["deleted"] == 0


async def test_compression_custom_thresholds(db):
    """Test compression with custom thresholds."""
    now = datetime.now(timezone.utc)

    # Insert an event 5 days ago
    ts = (now - timedelta(days=5)).isoformat()
    await _insert_event(db, ts)

    # With 3-day threshold, this should be archived
    compressor = MemoryCompressor(archive_after_days=3, delete_after_days=10)
    result = await compressor.compress(db)

    assert result["archived"] == 1
    assert await _count_events(db) == 0
    assert await _count_archived(db) == 1
