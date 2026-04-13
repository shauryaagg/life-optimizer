"""Batch processing pipeline for LLM operations."""

from __future__ import annotations

import logging

from life_optimizer.llm.base import BaseLLMClient
from life_optimizer.llm.categorizer import Categorizer
from life_optimizer.llm.insights import InsightGenerator
from life_optimizer.llm.summarizer import Summarizer
from life_optimizer.storage.database import Database

logger = logging.getLogger(__name__)


class LLMPipeline:
    """Orchestrates batch LLM processing: categorization, summaries, insights."""

    def __init__(self, client: BaseLLMClient | None, db: Database):
        self._client = client
        self._db = db
        self._categorizer = Categorizer(client, db)
        self._summarizer = Summarizer(client, db)
        self._insights = InsightGenerator(client, db)
        self._semantic_search = None
        self._entity_extractor = None
        self._compressor = None

    def set_semantic_search(self, semantic_search) -> None:
        """Set the semantic search instance for indexing summaries."""
        self._semantic_search = semantic_search

    def set_entity_extractor(self, entity_extractor) -> None:
        """Set the entity extractor for processing events."""
        self._entity_extractor = entity_extractor

    def set_compressor(self, compressor) -> None:
        """Set the memory compressor."""
        self._compressor = compressor

    async def run_categorization(self) -> int:
        """Categorize uncategorized events. Called hourly.

        Returns:
            Number of events categorized.
        """
        try:
            count = await self._categorizer.categorize_uncategorized()
            if count > 0:
                logger.info("Categorized %d events", count)
            return count
        except Exception as e:
            logger.error("Categorization pipeline failed: %s", e, exc_info=True)
            return 0

    async def run_hourly_summary(self) -> bool:
        """Generate summary for the past hour.

        Returns:
            True if a summary was generated.
        """
        try:
            summary = await self._summarizer.generate_hourly_summary()
            if summary is not None:
                logger.info("Generated hourly summary: %s", summary.summary_text[:80])
                # Index in semantic search if available
                if self._semantic_search is not None:
                    try:
                        await self._semantic_search.index_summary(
                            summary.id,
                            summary.summary_text,
                            {
                                "period_type": summary.period_type,
                                "period_start": summary.period_start,
                                "period_end": summary.period_end,
                            },
                        )
                    except Exception as e:
                        logger.warning("Failed to index summary: %s", e)
                return True
            return False
        except Exception as e:
            logger.error("Hourly summary pipeline failed: %s", e, exc_info=True)
            return False

    async def run_daily_insights(self, date: str | None = None) -> bool:
        """Generate end-of-day insights. Called at configured time.

        Args:
            date: Date in YYYY-MM-DD format. Defaults to today.

        Returns:
            True if insights were generated.
        """
        try:
            summary = await self._insights.generate_daily_insights(date=date)
            if summary is not None:
                logger.info("Generated daily insights for %s", date or "today")
                # Index in semantic search if available
                if self._semantic_search is not None:
                    try:
                        await self._semantic_search.index_summary(
                            summary.id,
                            summary.summary_text,
                            {
                                "period_type": summary.period_type,
                                "period_start": summary.period_start,
                                "period_end": summary.period_end,
                            },
                        )
                    except Exception as e:
                        logger.warning("Failed to index daily insight: %s", e)
                return True
            return False
        except Exception as e:
            logger.error("Daily insights pipeline failed: %s", e, exc_info=True)
            return False

    async def run_entity_extraction(self) -> int:
        """Extract entities from recent uncategorized events.

        Returns:
            Number of mentions created.
        """
        if self._entity_extractor is None:
            return 0
        try:
            from life_optimizer.storage.repositories import EventRepository

            repo = EventRepository(self._db)
            events = await repo.get_uncategorized_events(limit=500)
            if not events:
                # Also process recently categorized events
                events = await repo.get_events(limit=100)
            if events:
                count = await self._entity_extractor.extract_and_store(events, self._db)
                if count > 0:
                    logger.info("Extracted %d entity mentions", count)
                return count
            return 0
        except Exception as e:
            logger.error("Entity extraction failed: %s", e, exc_info=True)
            return 0

    async def run_compression(self) -> dict:
        """Run memory compression.

        Returns:
            Dict with archived and deleted counts.
        """
        if self._compressor is None:
            return {"archived": 0, "deleted": 0}
        try:
            result = await self._compressor.compress(self._db)
            return result
        except Exception as e:
            logger.error("Compression failed: %s", e, exc_info=True)
            return {"archived": 0, "deleted": 0}
