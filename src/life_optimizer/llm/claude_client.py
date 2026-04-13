"""Claude API client for LLM operations."""

from __future__ import annotations

import logging
import os

from .base import BaseLLMClient

logger = logging.getLogger(__name__)


class ClaudeClient(BaseLLMClient):
    """LLM client that uses the Anthropic Claude API."""

    def __init__(
        self, model: str = "claude-sonnet-4-20250514", api_key: str | None = None
    ):
        self._model = model
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._client = None

    async def _get_client(self):
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
            except ImportError:
                raise RuntimeError(
                    "anthropic package not installed. Run: pip install anthropic"
                )
        return self._client

    async def generate(self, prompt: str, system: str | None = None) -> str:
        """Generate text from a prompt using the Claude API."""
        client = await self._get_client()
        kwargs = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        response = await client.messages.create(**kwargs)
        return response.content[0].text

    async def is_available(self) -> bool:
        """Check if the Claude API is reachable."""
        if not self._api_key:
            return False
        try:
            await self._get_client()
            return True
        except Exception:
            return False

    @property
    def name(self) -> str:
        """Provider name for logging."""
        return f"claude ({self._model})"
