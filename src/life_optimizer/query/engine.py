"""Query engine that orchestrates question answering."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from life_optimizer.llm.base import BaseLLMClient
from life_optimizer.query.formatter import ResponseFormatter
from life_optimizer.query.router import QueryRouter
from life_optimizer.query.semantic_search import SemanticSearch
from life_optimizer.query.temporal import TemporalParser
from life_optimizer.query.text_to_sql import TextToSQL
from life_optimizer.storage.database import Database
from life_optimizer.storage.repositories import EventRepository, SummaryRepository

logger = logging.getLogger(__name__)


@dataclass
class ChatMessage:
    """A single chat message."""

    role: str  # "user" or "assistant"
    content: str


@dataclass
class ChatResponse:
    """Response from the query engine."""

    answer: str
    query_type: str
    sql_query: str | None = None
    follow_up_suggestions: list[str] = field(default_factory=list)
    session_id: str = ""


class QueryEngine:
    """Orchestrates natural language question answering."""

    def __init__(
        self,
        db: Database,
        llm_client: BaseLLMClient | None = None,
        semantic_search: SemanticSearch | None = None,
    ):
        self._db = db
        self._llm = llm_client
        self._semantic = semantic_search
        self._router = QueryRouter(llm_client)
        self._temporal = TemporalParser()
        self._formatter = ResponseFormatter()
        self._text_to_sql = TextToSQL(llm_client) if llm_client else None

    async def answer(
        self,
        question: str,
        history: list[ChatMessage] | None = None,
    ) -> ChatResponse:
        """Answer a natural language question about activity data.

        Args:
            question: The user's question.
            history: Optional conversation history.

        Returns:
            ChatResponse with the answer and metadata.
        """
        now = datetime.now()
        context_prefix = f"Current date/time: {now.isoformat()}\n"

        # Classify the question
        query_type = await self._router.classify(question)
        logger.info("Question classified as: %s", query_type)

        # Dispatch to appropriate handler
        try:
            if query_type == "structured":
                raw_result, sql = await self._handle_structured(question)
            elif query_type == "temporal":
                raw_result, sql = await self._handle_temporal(question, now)
            elif query_type == "semantic":
                raw_result, sql = await self._handle_semantic(question)
            else:  # insight
                raw_result, sql = await self._handle_insight(question)
        except Exception as e:
            logger.error("Query handling failed: %s", e, exc_info=True)
            return ChatResponse(
                answer=f"I encountered an error processing your question: {e}",
                query_type=query_type,
                session_id=str(uuid.uuid4()),
            )

        # Format the response
        answer = await self._formatter.format(
            question, query_type, raw_result, self._llm
        )

        # Generate follow-up suggestions
        follow_ups = self._generate_follow_ups(query_type, question)

        return ChatResponse(
            answer=answer,
            query_type=query_type,
            sql_query=sql,
            follow_up_suggestions=follow_ups,
            session_id=str(uuid.uuid4()),
        )

    async def _handle_structured(
        self, question: str
    ) -> tuple[dict, str | None]:
        """Handle structured (text-to-SQL) questions."""
        if self._text_to_sql is None:
            # Fallback: return a basic count
            event_repo = EventRepository(self._db)
            count = await event_repo.get_event_count()
            return {"text": f"Total events tracked: {count}"}, None

        result = await self._text_to_sql.generate_and_execute(question, self._db)
        return result, result.get("sql")

    async def _handle_temporal(
        self, question: str, now: datetime
    ) -> tuple[dict, str | None]:
        """Handle temporal questions with time range resolution."""
        time_range = self._temporal.resolve_time_range(question, now)

        if time_range:
            start, end = time_range
            # If we have an LLM, use text-to-SQL with the time range hint
            if self._text_to_sql:
                enhanced_question = (
                    f"{question}\n(Time range: {start} to {end})"
                )
                result = await self._text_to_sql.generate_and_execute(
                    enhanced_question, self._db
                )
                return result, result.get("sql")

            # Fallback: direct SQL with time range
            event_repo = EventRepository(self._db)
            events = await event_repo.get_events_between(start, end)
            event_dicts = [
                {
                    "timestamp": e.timestamp,
                    "app_name": e.app_name,
                    "window_title": e.window_title,
                    "category": e.category,
                }
                for e in events
            ]
            return {"events": event_dicts}, None

        # No time range found, fall back to structured
        return await self._handle_structured(question)

    async def _handle_semantic(
        self, question: str
    ) -> tuple[dict, str | None]:
        """Handle semantic search questions."""
        if self._semantic:
            results = await self._semantic.search(question, collection="summaries")
            if results:
                return {"search_results": results}, None

            # Try events collection
            results = await self._semantic.search(question, collection="events")
            if results:
                return {"search_results": results}, None

        # Fallback: use text-to-SQL if available
        if self._text_to_sql:
            result = await self._text_to_sql.generate_and_execute(question, self._db)
            return result, result.get("sql")

        # No LLM either: return recent events
        event_repo = EventRepository(self._db)
        events = await event_repo.get_events(limit=20)
        event_dicts = [
            {
                "timestamp": e.timestamp,
                "app_name": e.app_name,
                "window_title": e.window_title,
                "category": e.category,
            }
            for e in events
        ]
        return {"events": event_dicts}, None

    async def _handle_insight(
        self, question: str
    ) -> tuple[dict, str | None]:
        """Handle insight/analysis questions."""
        summary_repo = SummaryRepository(self._db)
        summaries = await summary_repo.get_summaries(limit=10)

        if summaries:
            summary_dicts = [
                {
                    "period_type": s.period_type,
                    "period_start": s.period_start,
                    "summary_text": s.summary_text,
                    "insights": s.insights,
                }
                for s in summaries
            ]
            return {"summaries": summary_dicts}, None

        # No summaries available, try to get events
        event_repo = EventRepository(self._db)
        count = await event_repo.get_event_count()
        return {"text": f"No summaries available yet. Total events tracked: {count}"}, None

    @staticmethod
    def _generate_follow_ups(query_type: str, question: str) -> list[str]:
        """Generate follow-up question suggestions."""
        suggestions = {
            "structured": [
                "How does this compare to yesterday?",
                "What about last week?",
                "Break this down by category",
            ],
            "temporal": [
                "What about the rest of the day?",
                "Compare this to the same time yesterday",
                "Show me a breakdown by app",
            ],
            "semantic": [
                "Tell me more about this",
                "When did this happen most recently?",
                "How much time was spent on this?",
            ],
            "insight": [
                "How can I improve?",
                "What are my most productive hours?",
                "Compare today to my weekly average",
            ],
        }
        return suggestions.get(query_type, [])
