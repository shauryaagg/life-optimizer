"""Response formatting for query results."""

from __future__ import annotations

import logging

from life_optimizer.llm.base import BaseLLMClient
from life_optimizer.query.prompts import FORMATTER_SYSTEM

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """Formats raw query results into human-readable answers."""

    async def format(
        self,
        question: str,
        query_type: str,
        raw_result: dict,
        llm_client: BaseLLMClient | None = None,
    ) -> str:
        """Format raw results into a readable answer.

        Args:
            question: The original user question.
            query_type: The query classification type.
            raw_result: Raw result data.
            llm_client: Optional LLM client for better formatting.

        Returns:
            Formatted answer string.
        """
        if llm_client is not None:
            try:
                return await self._format_with_llm(
                    question, query_type, raw_result, llm_client
                )
            except Exception as e:
                logger.warning("LLM formatting failed, using simple format: %s", e)

        return self._format_simple(question, query_type, raw_result)

    async def _format_with_llm(
        self,
        question: str,
        query_type: str,
        raw_result: dict,
        llm_client: BaseLLMClient,
    ) -> str:
        """Format results using an LLM."""
        prompt = (
            f"User question: {question}\n"
            f"Query type: {query_type}\n"
            f"Raw results:\n{self._result_to_text(raw_result)}\n\n"
            "Please format this into a clear, conversational answer."
        )
        return await llm_client.generate(prompt, system=FORMATTER_SYSTEM)

    def _format_simple(self, question: str, query_type: str, raw_result: dict) -> str:
        """Format results without an LLM."""
        if "error" in raw_result and raw_result["error"]:
            return f"Error: {raw_result['error']}"

        if "sql" in raw_result:
            return self._format_sql_result(raw_result)

        if "search_results" in raw_result:
            return self._format_search_results(raw_result)

        if "summaries" in raw_result:
            return self._format_summaries(raw_result)

        if "events" in raw_result:
            return self._format_events(raw_result)

        # Generic text result
        if "text" in raw_result:
            return raw_result["text"]

        return "No results found."

    @staticmethod
    def _format_sql_result(raw_result: dict) -> str:
        """Format SQL query results as a simple table."""
        columns = raw_result.get("columns", [])
        rows = raw_result.get("rows", [])
        row_count = raw_result.get("row_count", 0)

        if not rows:
            return "No results found."

        lines = []

        # Header
        if columns:
            header = " | ".join(str(c) for c in columns)
            lines.append(header)
            lines.append("-" * len(header))

        # Rows
        for row in rows[:50]:  # Limit display to 50 rows
            lines.append(" | ".join(str(v) for v in row))

        if row_count > 50:
            lines.append(f"... and {row_count - 50} more rows")

        return "\n".join(lines)

    @staticmethod
    def _format_search_results(raw_result: dict) -> str:
        """Format semantic search results as bullet points."""
        results = raw_result.get("search_results", [])
        if not results:
            return "No matching results found."

        lines = []
        for r in results:
            text = r.get("text", "")
            distance = r.get("distance")
            line = f"- {text}"
            if distance is not None:
                line += f" (relevance: {1 - distance:.2f})"
            lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def _format_summaries(raw_result: dict) -> str:
        """Format summary results."""
        summaries = raw_result.get("summaries", [])
        if not summaries:
            return "No summaries available."

        lines = []
        for s in summaries:
            if isinstance(s, dict):
                period = s.get("period_start", "")
                text = s.get("summary_text", "")
                lines.append(f"[{period}] {text}")
            else:
                lines.append(str(s))

        return "\n".join(lines)

    @staticmethod
    def _format_events(raw_result: dict) -> str:
        """Format event results."""
        events = raw_result.get("events", [])
        if not events:
            return "No events found."

        lines = []
        for e in events:
            if isinstance(e, dict):
                ts = e.get("timestamp", "")
                app = e.get("app_name", "")
                title = e.get("window_title", "")
                lines.append(f"[{ts}] {app}: {title}")
            else:
                lines.append(str(e))

        return "\n".join(lines)

    @staticmethod
    def _result_to_text(raw_result: dict) -> str:
        """Convert a raw result dict to plain text for the LLM."""
        parts = []
        if "sql" in raw_result:
            parts.append(f"SQL: {raw_result['sql']}")
        if "columns" in raw_result and "rows" in raw_result:
            cols = raw_result["columns"]
            rows = raw_result["rows"]
            if cols and rows:
                parts.append(f"Columns: {', '.join(str(c) for c in cols)}")
                for row in rows[:20]:
                    parts.append(" | ".join(str(v) for v in row))
                if len(rows) > 20:
                    parts.append(f"... ({len(rows)} total rows)")
        if "search_results" in raw_result:
            for r in raw_result["search_results"][:10]:
                parts.append(f"- {r.get('text', '')}")
        if "summaries" in raw_result:
            for s in raw_result["summaries"][:5]:
                if isinstance(s, dict):
                    parts.append(s.get("summary_text", ""))
        if "text" in raw_result:
            parts.append(raw_result["text"])

        return "\n".join(parts) if parts else "No data available."
