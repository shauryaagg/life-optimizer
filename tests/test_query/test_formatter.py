"""Tests for response formatting."""

import pytest
from unittest.mock import AsyncMock

from life_optimizer.query.formatter import ResponseFormatter


@pytest.fixture
def formatter():
    return ResponseFormatter()


async def test_format_with_no_llm_sql_result(formatter):
    """Test formatting SQL results without LLM."""
    raw_result = {
        "sql": "SELECT app_name, COUNT(*) FROM events GROUP BY app_name",
        "columns": ["app_name", "count"],
        "rows": [["Chrome", 15], ["Slack", 10], ["Code", 25]],
        "row_count": 3,
        "error": None,
    }

    answer = await formatter.format("what apps did I use?", "structured", raw_result)

    assert "Chrome" in answer
    assert "Slack" in answer
    assert "Code" in answer
    assert "15" in answer
    assert "25" in answer


async def test_format_sql_result_empty(formatter):
    """Test formatting empty SQL results."""
    raw_result = {
        "sql": "SELECT * FROM events WHERE 1=0",
        "columns": [],
        "rows": [],
        "row_count": 0,
        "error": None,
    }

    answer = await formatter.format("anything?", "structured", raw_result)
    assert "no results" in answer.lower() or "no data" in answer.lower()


async def test_format_error_result(formatter):
    """Test formatting error results."""
    raw_result = {
        "error": "Query timed out after 5 seconds",
    }

    answer = await formatter.format("query?", "structured", raw_result)
    assert "error" in answer.lower()
    assert "timed out" in answer.lower()


async def test_format_search_results(formatter):
    """Test formatting semantic search results."""
    raw_result = {
        "search_results": [
            {"id": "1", "text": "Coding in Python", "distance": 0.2},
            {"id": "2", "text": "Writing documentation", "distance": 0.4},
        ],
    }

    answer = await formatter.format("what was I doing?", "semantic", raw_result)
    assert "Coding in Python" in answer
    assert "Writing documentation" in answer


async def test_format_summaries(formatter):
    """Test formatting summary results."""
    raw_result = {
        "summaries": [
            {
                "period_start": "2025-01-15T10:00:00",
                "summary_text": "Mostly coding in VS Code.",
            },
        ],
    }

    answer = await formatter.format("how was my day?", "insight", raw_result)
    assert "Mostly coding" in answer


async def test_format_with_llm(formatter):
    """Test formatting with LLM for better readability."""
    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(
        return_value="Based on the data, you spent most of your time coding."
    )

    raw_result = {
        "sql": "SELECT app_name FROM events",
        "columns": ["app_name"],
        "rows": [["Code"]],
        "row_count": 1,
        "error": None,
    }

    answer = await formatter.format(
        "what did I do?", "structured", raw_result, llm_client=mock_llm
    )
    assert "coding" in answer.lower()
    mock_llm.generate.assert_called_once()


async def test_format_text_result(formatter):
    """Test formatting a plain text result."""
    raw_result = {"text": "Total events tracked: 42"}
    answer = await formatter.format("how many events?", "structured", raw_result)
    assert "42" in answer


async def test_format_events_result(formatter):
    """Test formatting event results."""
    raw_result = {
        "events": [
            {
                "timestamp": "2025-01-15T10:00:00",
                "app_name": "Code",
                "window_title": "main.py",
            },
        ],
    }

    answer = await formatter.format("what happened?", "temporal", raw_result)
    assert "Code" in answer
    assert "main.py" in answer
