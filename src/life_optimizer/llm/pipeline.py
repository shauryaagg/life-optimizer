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
                return True
            return False
        except Exception as e:
            logger.error("Daily insights pipeline failed: %s", e, exc_info=True)
            return False
