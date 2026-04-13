"""Query classification router."""

from __future__ import annotations

import logging
import re

from life_optimizer.llm.base import BaseLLMClient
from life_optimizer.query.prompts import ROUTER_SYSTEM

logger = logging.getLogger(__name__)

# Keyword patterns for fallback classification
STRUCTURED_PATTERNS = [
    r"\bhow much\b", r"\bhow many\b", r"\bhow long\b",
    r"\bcompare\b", r"\btotal\b", r"\bcount\b",
    r"\baverage\b", r"\bmost used\b", r"\btop \d+\b",
    r"\bpercentage\b", r"\bratio\b", r"\brank\b",
]

TEMPORAL_PATTERNS = [
    r"\bat \d{1,2}\s*(am|pm)\b", r"\byesterday\b",
    r"\blast week\b", r"\bthis morning\b", r"\bthis afternoon\b",
    r"\bthis evening\b", r"\blast night\b",
    r"\bbetween \d{1,2}\s*(am|pm)?\s*and\s*\d{1,2}\s*(am|pm)\b",
    r"\bthis week\b", r"\blast month\b",
    r"\bon monday\b", r"\bon tuesday\b", r"\bon wednesday\b",
    r"\bon thursday\b", r"\bon friday\b", r"\bon saturday\b", r"\bon sunday\b",
]

SEMANTIC_PATTERNS = [
    r"\bwhat was i\b", r"\bfind\b", r"\bsimilar\b",
    r"\bsearch\b", r"\blook for\b", r"\bwhat documents\b",
    r"\bwhat files\b", r"\bwhat projects\b",
]

VALID_TYPES = {"structured", "semantic", "temporal", "insight"}


class QueryRouter:
    """Classifies questions into query types."""

    def __init__(self, llm_client: BaseLLMClient | None = None):
        self._llm = llm_client

    async def classify(self, question: str) -> str:
        """Classify a question as structured, semantic, temporal, or insight.

        Uses LLM if available, otherwise falls back to keyword-based rules.
        """
        if self._llm is not None:
            try:
                result = await self._llm.generate(question, system=ROUTER_SYSTEM)
                classification = result.strip().lower()
                if classification in VALID_TYPES:
                    return classification
                logger.warning("LLM returned invalid classification: %s", classification)
            except Exception as e:
                logger.warning("LLM classification failed, using fallback: %s", e)

        return self._classify_by_keywords(question)

    def _classify_by_keywords(self, question: str) -> str:
        """Classify a question using keyword patterns."""
        q = question.lower()

        for pattern in STRUCTURED_PATTERNS:
            if re.search(pattern, q):
                return "structured"

        for pattern in TEMPORAL_PATTERNS:
            if re.search(pattern, q):
                return "temporal"

        for pattern in SEMANTIC_PATTERNS:
            if re.search(pattern, q):
                return "semantic"

        return "insight"
