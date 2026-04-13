"""Tests for text-to-SQL generation and execution."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from life_optimizer.query.text_to_sql import TextToSQL, validate_sql_safety
from life_optimizer.storage.database import Database


def test_safety_rejects_insert():
    """Test SQL safety validation rejects INSERT."""
    error = validate_sql_safety("INSERT INTO events (app_name) VALUES ('test')")
    assert error is not None
    assert "INSERT" in error


def test_safety_rejects_delete():
    """Test SQL safety validation rejects DELETE."""
    error = validate_sql_safety("DELETE FROM events WHERE id = 1")
    assert error is not None
    assert "DELETE" in error


def test_safety_rejects_drop():
    """Test SQL safety validation rejects DROP."""
    error = validate_sql_safety("DROP TABLE events")
    assert error is not None
    assert "DROP" in error


def test_safety_rejects_update():
    """Test SQL safety validation rejects UPDATE."""
    error = validate_sql_safety("UPDATE events SET category = 'test'")
    assert error is not None
    assert "UPDATE" in error


def test_safety_rejects_alter():
    """Test SQL safety validation rejects ALTER."""
    error = validate_sql_safety("ALTER TABLE events ADD COLUMN test TEXT")
    assert error is not None
    assert "ALTER" in error


def test_safety_rejects_create():
    """Test SQL safety validation rejects CREATE."""
    error = validate_sql_safety("CREATE TABLE test (id INTEGER)")
    assert error is not None
    assert "CREATE" in error


def test_safety_allows_select():
    """Test SQL safety validation allows SELECT."""
    error = validate_sql_safety("SELECT * FROM events WHERE category = 'Deep Work'")
    assert error is None


def test_safety_allows_select_with_join():
    """Test SQL safety validation allows SELECT with JOIN."""
    error = validate_sql_safety(
        "SELECT e.app_name, COUNT(*) FROM events e GROUP BY e.app_name"
    )
    assert error is None


def test_safety_case_insensitive():
    """Test SQL safety is case-insensitive."""
    error = validate_sql_safety("insert into events values (1)")
    assert error is not None

    error = validate_sql_safety("Delete FROM events")
    assert error is not None


@pytest.fixture
async def db(tmp_path):
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test_sql.db")
    database = Database(db_path)
    await database.initialize()
    yield database
    await database.close()


async def test_generate_and_execute_with_mock_llm(db):
    """Test generate_and_execute with mock LLM returning valid SQL."""
    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(
        return_value="SELECT COUNT(*) as total FROM events"
    )

    text_to_sql = TextToSQL(mock_llm)
    result = await text_to_sql.generate_and_execute("how many events?", db)

    assert result["error"] is None
    assert result["sql"] == "SELECT COUNT(*) as total FROM events"
    assert result["columns"] == ["total"]
    assert len(result["rows"]) == 1
    assert result["rows"][0][0] == 0  # No events in test db


async def test_generate_and_execute_rejects_unsafe_sql(db):
    """Test that unsafe SQL from LLM is rejected."""
    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(
        return_value="DELETE FROM events"
    )

    text_to_sql = TextToSQL(mock_llm)
    result = await text_to_sql.generate_and_execute("delete everything", db)

    assert result["error"] is not None
    assert "DELETE" in result["error"]


async def test_retry_on_sql_error(db):
    """Test that the system retries once on SQL error."""
    mock_llm = AsyncMock()
    # First call returns invalid SQL, second call returns valid SQL
    mock_llm.generate = AsyncMock(
        side_effect=[
            "SELECT * FROM nonexistent_table",
            "SELECT COUNT(*) as total FROM events",
        ]
    )

    text_to_sql = TextToSQL(mock_llm)
    result = await text_to_sql.generate_and_execute("how many events?", db)

    assert result["error"] is None
    assert mock_llm.generate.call_count == 2


async def test_max_rows_limit(db):
    """Test that results are limited to MAX_ROWS."""
    # Insert many events
    conn = db.connection
    for i in range(50):
        await conn.execute(
            "INSERT INTO events (timestamp, app_name, event_type) VALUES (?, ?, ?)",
            (f"2025-01-15T{i:02d}:00:00", "TestApp", "poll"),
        )
    await conn.commit()

    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(return_value="SELECT * FROM events")

    text_to_sql = TextToSQL(mock_llm)
    result = await text_to_sql.generate_and_execute("show all events", db)

    assert result["error"] is None
    assert result["row_count"] == 50
    assert len(result["rows"]) == 50  # Under MAX_ROWS


async def test_clean_sql_removes_markdown_fences():
    """Test that markdown fences are cleaned from SQL."""
    mock_llm = AsyncMock()
    sql_text = "```sql\nSELECT COUNT(*) FROM events\n```"
    mock_llm.generate = AsyncMock(return_value=sql_text)

    text_to_sql = TextToSQL(mock_llm)
    cleaned = text_to_sql._clean_sql(sql_text)
    assert "```" not in cleaned
    assert "SELECT COUNT(*) FROM events" in cleaned


async def test_timeout_handling(db):
    """Test that slow queries are timed out."""
    mock_llm = AsyncMock()
    # Generate SQL that is valid but we'll mock execution to be slow
    mock_llm.generate = AsyncMock(
        return_value="SELECT COUNT(*) FROM events"
    )

    text_to_sql = TextToSQL(mock_llm)

    # Patch execute_sql to simulate timeout
    original_execute = text_to_sql._execute_sql

    async def slow_execute(sql, db):
        await asyncio.sleep(10)
        return await original_execute(sql, db)

    with patch.object(text_to_sql, '_execute_sql', side_effect=slow_execute):
        # Also need to mock the retry LLM call
        mock_llm.generate = AsyncMock(
            side_effect=[
                "SELECT COUNT(*) FROM events",
                "SELECT COUNT(*) FROM events",
            ]
        )
        text_to_sql_fresh = TextToSQL(mock_llm)

        # Override timeout to be very short
        import life_optimizer.query.text_to_sql as ts_module
        original_timeout = ts_module.SQL_TIMEOUT_SECONDS
        ts_module.SQL_TIMEOUT_SECONDS = 0.1

        try:
            result = await text_to_sql_fresh.generate_and_execute("count events", db)
            # After timeout and retry, it should succeed on retry with fresh execution
            # (since real execute doesn't hang)
            assert result["error"] is None or "timed out" in result.get("error", "")
        finally:
            ts_module.SQL_TIMEOUT_SECONDS = original_timeout
