"""Tests for the query engine."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from life_optimizer.query.engine import ChatMessage, ChatResponse, QueryEngine
from life_optimizer.storage.database import Database


@pytest.fixture
async def db(tmp_path):
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test_engine.db")
    database = Database(db_path)
    await database.initialize()
    yield database
    await database.close()


async def test_structured_question_with_mock_llm(db):
    """Test full flow: structured question with mock LLM -> SQL result -> answer."""
    mock_llm = AsyncMock()
    # Router call returns "structured"
    # Text-to-SQL call returns a SELECT query
    # Formatter call returns formatted text
    mock_llm.generate = AsyncMock(
        side_effect=[
            "structured",  # router
            "SELECT COUNT(*) as total FROM events",  # text-to-sql
            "You have 0 events tracked.",  # formatter
        ]
    )

    engine = QueryEngine(db=db, llm_client=mock_llm)
    response = await engine.answer("how many events do I have?")

    assert isinstance(response, ChatResponse)
    assert response.query_type == "structured"
    assert response.answer is not None
    assert len(response.answer) > 0
    assert response.session_id is not None


async def test_temporal_question_with_time_range(db):
    """Test full flow: temporal question -> time range + SQL."""
    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(
        side_effect=[
            "temporal",  # router
            "SELECT * FROM events WHERE timestamp >= '2025-01-15T00:00:00' LIMIT 10",
            "No events found for today.",  # formatter
        ]
    )

    engine = QueryEngine(db=db, llm_client=mock_llm)
    response = await engine.answer("what did I do today?")

    assert isinstance(response, ChatResponse)
    assert response.query_type == "temporal"
    assert response.answer is not None


async def test_engine_with_no_llm_fallback(db):
    """Test engine works without LLM (fallback mode)."""
    engine = QueryEngine(db=db, llm_client=None, semantic_search=None)
    response = await engine.answer("how many events?")

    assert isinstance(response, ChatResponse)
    # Should fall back to keyword classification -> structured
    assert response.query_type == "structured"
    # Should return some answer (basic count)
    assert response.answer is not None
    assert len(response.answer) > 0


async def test_engine_insight_query(db):
    """Test insight query returns response."""
    engine = QueryEngine(db=db, llm_client=None, semantic_search=None)
    response = await engine.answer("give me a productivity report")

    assert isinstance(response, ChatResponse)
    assert response.query_type == "insight"
    assert response.answer is not None


async def test_engine_with_history(db):
    """Test engine accepts conversation history."""
    engine = QueryEngine(db=db, llm_client=None, semantic_search=None)
    history = [
        ChatMessage(role="user", content="what did I do today?"),
        ChatMessage(role="assistant", content="You had 5 events."),
    ]
    response = await engine.answer("tell me more", history=history)

    assert isinstance(response, ChatResponse)
    assert response.answer is not None


async def test_response_has_follow_up_suggestions(db):
    """Test that responses include follow-up suggestions."""
    engine = QueryEngine(db=db, llm_client=None, semantic_search=None)
    response = await engine.answer("how many events?")

    assert isinstance(response.follow_up_suggestions, list)
    assert len(response.follow_up_suggestions) > 0


async def test_engine_error_handling(db):
    """Test that engine handles errors gracefully."""
    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(
        side_effect=[
            "structured",  # router
            Exception("LLM crashed"),  # text-to-sql fails
        ]
    )

    engine = QueryEngine(db=db, llm_client=mock_llm)
    response = await engine.answer("how many events?")

    assert isinstance(response, ChatResponse)
    # Should still return a response (not crash)
    assert response.answer is not None
