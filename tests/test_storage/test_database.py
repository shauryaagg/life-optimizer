"""Tests for the database module."""

import pytest
from pathlib import Path

from life_optimizer.storage.database import Database


@pytest.fixture
async def db(tmp_path):
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test.db")
    database = Database(db_path)
    await database.initialize()
    yield database
    await database.close()


async def test_database_creates_tables(db: Database):
    """Test that initialization creates the events table."""
    conn = db.connection
    cursor = await conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='events'"
    )
    row = await cursor.fetchone()
    assert row is not None
    assert row[0] == "events"


async def test_database_creates_indexes(db: Database):
    """Test that initialization creates the expected indexes."""
    conn = db.connection
    cursor = await conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_events_%'"
    )
    rows = await cursor.fetchall()
    index_names = {row[0] for row in rows}
    assert "idx_events_timestamp" in index_names
    assert "idx_events_app" in index_names


async def test_wal_mode_enabled(db: Database):
    """Test that WAL journal mode is enabled."""
    conn = db.connection
    cursor = await conn.execute("PRAGMA journal_mode")
    row = await cursor.fetchone()
    assert row is not None
    assert row[0].lower() == "wal"


async def test_database_creates_directory(tmp_path):
    """Test that initialize creates the parent directory if needed."""
    db_path = str(tmp_path / "subdir" / "nested" / "test.db")
    database = Database(db_path)
    await database.initialize()

    assert Path(db_path).exists()
    await database.close()


async def test_database_not_initialized_raises():
    """Test that accessing connection before init raises RuntimeError."""
    database = Database("/tmp/nonexistent.db")
    with pytest.raises(RuntimeError, match="not initialized"):
        _ = database.connection
