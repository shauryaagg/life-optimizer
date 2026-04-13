"""Tests for the LLM pipeline orchestrator."""

import json
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from life_optimizer.collectors.base import CollectorResult
from life_optimizer.constants import POLL
from life_optimizer.llm.pipeline import LLMPipeline
from life_optimizer.storage.database import Database
from life_optimizer.storage.repositories import EventRepository


@pytest.fixture
async def db(tmp_path):
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test_pipeline.db")
    database = Database(db_path)
    await database.initialize()
    yield database
    await database.close()


def _make_result(
    app_name: str = "TestApp",
    window_title: str = "Test Window",
    context: dict | None = None,
    timestamp: datetime | None = None,
) -> CollectorResult:
    return CollectorResult(
        app_name=app_name,
        event_type=POLL,
        window_title=window_title,
        context=context or {},
        timestamp=timestamp or datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
    )


async def test_pipeline_creation_with_none_client(db):
    """Test pipeline can be created with None client (rule-based only)."""
    pipeline = LLMPipeline(None, db)
    assert pipeline._client is None
    assert pipeline._categorizer is not None
    assert pipeline._summarizer is not None
    assert pipeline._insights is not None


async def test_pipeline_categorization_rule_based(db):
    """Test categorization pipeline end-to-end with rule-based (no LLM)."""
    repo = EventRepository(db)

    # Insert some uncategorized events
    await repo.insert_event(_make_result(app_name="Code", window_title="main.py"))
    await repo.insert_event(_make_result(app_name="Slack", window_title="General"))
    await repo.insert_event(
        _make_result(
            app_name="Google Chrome",
            window_title="Twitter",
            context={"url": "https://twitter.com"},
        )
    )

    pipeline = LLMPipeline(None, db)
    count = await pipeline.run_categorization()
    assert count == 3

    # All events should now be categorized
    remaining = await repo.get_uncategorized_events()
    assert len(remaining) == 0


async def test_pipeline_categorization_with_mock_llm(db):
    """Test categorization pipeline end-to-end with mock LLM."""
    repo = EventRepository(db)

    await repo.insert_event(_make_result(app_name="Code", window_title="main.py"))
    await repo.insert_event(_make_result(app_name="Slack", window_title="DM"))

    events = await repo.get_uncategorized_events()

    mock_client = AsyncMock()
    mock_client.generate = AsyncMock(
        return_value=json.dumps([
            {"id": events[0].id, "category": "Deep Work", "subcategory": "coding"},
            {"id": events[1].id, "category": "Communication", "subcategory": "slack-dm"},
        ])
    )

    pipeline = LLMPipeline(mock_client, db)
    count = await pipeline.run_categorization()
    assert count == 2

    remaining = await repo.get_uncategorized_events()
    assert len(remaining) == 0


async def test_pipeline_hourly_summary_no_events(db):
    """Test hourly summary returns False when no events."""
    pipeline = LLMPipeline(None, db)
    result = await pipeline.run_hourly_summary()
    assert result is False


async def test_pipeline_daily_insights_no_events(db):
    """Test daily insights returns False when no events."""
    pipeline = LLMPipeline(None, db)
    result = await pipeline.run_daily_insights(date="2025-01-15")
    assert result is False


async def test_pipeline_handles_categorization_error(db):
    """Test pipeline handles errors gracefully during categorization."""
    repo = EventRepository(db)
    await repo.insert_event(_make_result(app_name="Code"))

    mock_client = AsyncMock()
    mock_client.generate = AsyncMock(side_effect=Exception("Network error"))

    pipeline = LLMPipeline(mock_client, db)
    # Should not raise, should fall back to rules
    count = await pipeline.run_categorization()
    assert count == 1
