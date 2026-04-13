"""Tests for semantic search."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from life_optimizer.storage.database import Database


# Check if chromadb is available
try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False


@pytest.fixture
async def db(tmp_path):
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test_semantic.db")
    database = Database(db_path)
    await database.initialize()
    yield database
    await database.close()


@pytest.mark.skipif(not CHROMADB_AVAILABLE, reason="chromadb not installed")
async def test_index_summary_and_search_roundtrip(tmp_path):
    """Test indexing a summary and searching for it."""
    from life_optimizer.query.semantic_search import SemanticSearch

    persist_dir = str(tmp_path / "chromadb")
    search = SemanticSearch(persist_dir=persist_dir)

    await search.index_summary(
        1, "Spent 2 hours coding in Python on the web dashboard project",
        {"period_type": "hourly", "period_start": "2025-01-15T10:00:00"},
    )
    await search.index_summary(
        2, "Mostly communication: Slack messages and email",
        {"period_type": "hourly", "period_start": "2025-01-15T11:00:00"},
    )

    results = await search.search("coding Python", collection="summaries")
    assert len(results) > 0
    # The coding summary should be the top result
    assert results[0]["id"] == "1"
    assert "coding" in results[0]["text"].lower()


@pytest.mark.skipif(not CHROMADB_AVAILABLE, reason="chromadb not installed")
async def test_search_with_no_results(tmp_path):
    """Test search returns empty list when collection is empty."""
    from life_optimizer.query.semantic_search import SemanticSearch

    persist_dir = str(tmp_path / "chromadb_empty")
    search = SemanticSearch(persist_dir=persist_dir)

    results = await search.search("anything", collection="summaries")
    assert results == []


@pytest.mark.skipif(not CHROMADB_AVAILABLE, reason="chromadb not installed")
async def test_index_event_and_search(tmp_path):
    """Test indexing events and searching."""
    from life_optimizer.query.semantic_search import SemanticSearch

    persist_dir = str(tmp_path / "chromadb_events")
    search = SemanticSearch(persist_dir=persist_dir)

    await search.index_event(
        1, "VS Code | main.py — life-optimizer | Deep Work",
        {"app_name": "Code", "timestamp": "2025-01-15T10:00:00"},
    )
    await search.index_event(
        2, "Google Chrome | GitHub Pull Request | Browsing",
        {"app_name": "Chrome", "timestamp": "2025-01-15T10:05:00"},
    )

    results = await search.search("Visual Studio Code", collection="events")
    assert len(results) > 0


@pytest.mark.skipif(not CHROMADB_AVAILABLE, reason="chromadb not installed")
async def test_reindex_all(tmp_path, db):
    """Test reindex_all with a database containing summaries and events."""
    from life_optimizer.query.semantic_search import SemanticSearch
    from life_optimizer.storage.repositories import SummaryRepository, EventRepository
    from life_optimizer.collectors.base import CollectorResult
    from datetime import datetime, timezone

    # Insert some data
    summary_repo = SummaryRepository(db)
    await summary_repo.insert_summary(
        period_type="hourly",
        period_start="2025-01-15T10:00:00",
        period_end="2025-01-15T11:00:00",
        summary_text="Coding in VS Code",
    )

    event_repo = EventRepository(db)
    await event_repo.insert_event(CollectorResult(
        app_name="Code",
        event_type="poll",
        window_title="main.py",
        timestamp=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
    ))

    persist_dir = str(tmp_path / "chromadb_reindex")
    search = SemanticSearch(persist_dir=persist_dir)
    count = await search.reindex_all(db)
    assert count == 2  # 1 summary + 1 event


def test_graceful_handling_when_chromadb_not_available():
    """Test that SemanticSearch handles missing chromadb gracefully."""
    from life_optimizer.query import semantic_search as ss_module

    original = ss_module.CHROMADB_AVAILABLE
    try:
        ss_module.CHROMADB_AVAILABLE = False
        search = ss_module.SemanticSearch()

        # These should all return gracefully without errors
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(search.index_summary(1, "test", {}))
        loop.run_until_complete(search.index_event(1, "test", {}))
        results = loop.run_until_complete(search.search("test"))
        assert results == []
    finally:
        ss_module.CHROMADB_AVAILABLE = original
