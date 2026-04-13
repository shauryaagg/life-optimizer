"""Tests for the query router."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from life_optimizer.query.router import QueryRouter


@pytest.fixture
def router():
    """Router with no LLM (uses keyword fallback)."""
    return QueryRouter(llm_client=None)


async def test_fallback_structured_how_much(router):
    """Test fallback classifies 'how much' as structured."""
    result = await router.classify("how much time did I spend on Slack?")
    assert result == "structured"


async def test_fallback_structured_how_many(router):
    """Test fallback classifies 'how many' as structured."""
    result = await router.classify("how many events today?")
    assert result == "structured"


async def test_fallback_structured_total(router):
    """Test fallback classifies 'total' as structured."""
    result = await router.classify("total hours coding this week")
    assert result == "structured"


async def test_fallback_structured_compare(router):
    """Test fallback classifies 'compare' as structured."""
    result = await router.classify("compare Chrome vs VS Code usage")
    assert result == "structured"


async def test_fallback_temporal_yesterday(router):
    """Test fallback classifies 'yesterday' as temporal."""
    result = await router.classify("what happened yesterday?")
    assert result == "temporal"


async def test_fallback_temporal_at_3pm(router):
    """Test fallback classifies 'at 3pm' as temporal."""
    result = await router.classify("what was I doing at 3pm?")
    assert result == "temporal"


async def test_fallback_temporal_this_morning(router):
    """Test fallback classifies 'this morning' as temporal."""
    result = await router.classify("show this morning's activity")
    assert result == "temporal"


async def test_fallback_temporal_last_week(router):
    """Test fallback classifies 'last week' as temporal."""
    result = await router.classify("what about last week?")
    assert result == "temporal"


async def test_fallback_semantic_what_was_i(router):
    """Test fallback classifies 'what was i' as semantic."""
    result = await router.classify("what was I working on?")
    assert result == "semantic"


async def test_fallback_semantic_find(router):
    """Test fallback classifies 'find' as semantic."""
    result = await router.classify("find meetings about the project")
    assert result == "semantic"


async def test_fallback_semantic_similar(router):
    """Test fallback classifies 'similar' as semantic."""
    result = await router.classify("find similar activities to what I did before")
    assert result == "semantic"


async def test_fallback_default_insight(router):
    """Test fallback classifies unknown questions as insight."""
    result = await router.classify("how productive was I?")
    assert result == "insight"


async def test_fallback_default_analysis(router):
    """Test fallback classifies analysis questions as insight."""
    result = await router.classify("give me a productivity report")
    assert result == "insight"


async def test_llm_classification():
    """Test LLM-based classification with mock client."""
    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(return_value="structured")

    router = QueryRouter(llm_client=mock_llm)
    result = await router.classify("how much time on Chrome?")

    assert result == "structured"
    mock_llm.generate.assert_called_once()


async def test_llm_classification_falls_back_on_invalid_response():
    """Test that invalid LLM response falls back to keyword matching."""
    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(return_value="invalid_type")

    router = QueryRouter(llm_client=mock_llm)
    result = await router.classify("how much time on Chrome?")

    # Should fall back to keyword-based: "how much" -> structured
    assert result == "structured"


async def test_llm_classification_falls_back_on_error():
    """Test that LLM error falls back to keyword matching."""
    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(side_effect=Exception("LLM error"))

    router = QueryRouter(llm_client=mock_llm)
    result = await router.classify("what happened yesterday?")

    # Should fall back to keyword-based: "yesterday" -> temporal
    assert result == "temporal"
