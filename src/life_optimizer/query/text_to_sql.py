"""Text-to-SQL generation and execution."""

from __future__ import annotations

import asyncio
import logging
import re

from life_optimizer.llm.base import BaseLLMClient
from life_optimizer.query.prompts import TEXT_TO_SQL_SYSTEM
from life_optimizer.storage.database import Database

logger = logging.getLogger(__name__)

# Patterns that indicate dangerous SQL statements
UNSAFE_PATTERNS = [
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bDELETE\b",
    r"\bDROP\b",
    r"\bALTER\b",
    r"\bCREATE\b",
    r"\bTRUNCATE\b",
    r"\bREPLACE\b",
    r"\bATTACH\b",
    r"\bDETACH\b",
    r"\bPRAGMA\b",
]

MAX_ROWS = 1000
SQL_TIMEOUT_SECONDS = 5


def validate_sql_safety(sql: str) -> str | None:
    """Check if SQL is safe to execute.

    Returns:
        Error message if unsafe, None if safe.
    """
    sql_upper = sql.upper().strip()
    for pattern in UNSAFE_PATTERNS:
        if re.search(pattern, sql_upper):
            keyword = pattern.replace(r"\b", "")
            return f"Rejected: SQL contains disallowed keyword '{keyword}'"
    return None


class TextToSQL:
    """Generates and executes SQL from natural language questions."""

    def __init__(self, llm_client: BaseLLMClient, schema: str | None = None):
        self._llm = llm_client
        self._schema = schema

    async def generate_and_execute(
        self, question: str, db: Database
    ) -> dict:
        """Generate SQL from a question and execute it.

        Args:
            question: Natural language question.
            db: Database instance to execute against.

        Returns:
            Dict with keys: sql, columns, rows, row_count, error.
        """
        result = {
            "sql": "",
            "columns": [],
            "rows": [],
            "row_count": 0,
            "error": None,
        }

        # Generate SQL via LLM
        try:
            sql = await self._generate_sql(question)
        except Exception as e:
            result["error"] = f"Failed to generate SQL: {e}"
            return result

        # Clean the SQL
        sql = self._clean_sql(sql)
        result["sql"] = sql

        # Safety check
        safety_error = validate_sql_safety(sql)
        if safety_error:
            result["error"] = safety_error
            return result

        # Execute with timeout
        try:
            columns, rows = await asyncio.wait_for(
                self._execute_sql(sql, db),
                timeout=SQL_TIMEOUT_SECONDS,
            )
            result["columns"] = columns
            result["rows"] = rows[:MAX_ROWS]
            result["row_count"] = len(rows)
        except asyncio.TimeoutError:
            result["error"] = f"Query timed out after {SQL_TIMEOUT_SECONDS} seconds"
        except Exception as e:
            # Retry once with error context
            logger.warning("SQL execution failed, retrying: %s", e)
            try:
                sql = await self._generate_sql(
                    question,
                    error_context=f"Previous SQL failed with error: {e}. Previous SQL: {sql}",
                )
                sql = self._clean_sql(sql)
                result["sql"] = sql

                safety_error = validate_sql_safety(sql)
                if safety_error:
                    result["error"] = safety_error
                    return result

                columns, rows = await asyncio.wait_for(
                    self._execute_sql(sql, db),
                    timeout=SQL_TIMEOUT_SECONDS,
                )
                result["columns"] = columns
                result["rows"] = rows[:MAX_ROWS]
                result["row_count"] = len(rows)
            except Exception as retry_err:
                result["error"] = f"SQL execution failed after retry: {retry_err}"

        return result

    async def _generate_sql(
        self, question: str, error_context: str | None = None
    ) -> str:
        """Generate SQL from a question using the LLM."""
        prompt = f"Generate a SQLite SELECT query to answer: {question}"
        if error_context:
            prompt += f"\n\n{error_context}\n\nPlease fix the query."
        return await self._llm.generate(prompt, system=TEXT_TO_SQL_SYSTEM)

    @staticmethod
    def _clean_sql(sql: str) -> str:
        """Clean SQL response from LLM (remove markdown fences, etc.)."""
        sql = sql.strip()
        # Remove markdown code fences
        if sql.startswith("```"):
            lines = sql.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            sql = "\n".join(lines).strip()
        # Remove trailing semicolons
        sql = sql.rstrip(";").strip()
        return sql

    @staticmethod
    async def _execute_sql(
        sql: str, db: Database
    ) -> tuple[list[str], list[list]]:
        """Execute SQL and return (columns, rows)."""
        conn = db.connection
        cursor = await conn.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = await cursor.fetchall()
        return columns, [list(row) for row in rows]
