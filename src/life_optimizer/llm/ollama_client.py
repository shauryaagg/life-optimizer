"""Ollama client for local LLM operations."""

from __future__ import annotations

import logging

from .base import BaseLLMClient

logger = logging.getLogger(__name__)


class OllamaClient(BaseLLMClient):
    """LLM client that uses a local Ollama instance."""

    def __init__(
        self, model: str = "llama3.1:8b", base_url: str = "http://localhost:11434"
    ):
        self._model = model
        self._base_url = base_url

    async def generate(self, prompt: str, system: str | None = None) -> str:
        """Generate text from a prompt using Ollama.

        Handles reasoning models (like Qwen 3.5) that put output in a
        separate `thinking` field. Also disables thinking mode when
        possible for faster, direct responses.
        """
        import httpx

        async with httpx.AsyncClient(
            base_url=self._base_url, timeout=300
        ) as client:
            payload: dict = {
                "model": self._model,
                "prompt": prompt,
                "stream": False,
                # Tell reasoning models not to emit separate thinking tokens.
                # Supported by Qwen 3.x, DeepSeek-R1, etc. Ignored by others.
                "think": False,
            }
            if system:
                payload["system"] = system
            response = await client.post("/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            # Prefer `response` field, fall back to `thinking` for reasoning
            # models that ignore `think=false`.
            text = data.get("response") or ""
            if not text.strip():
                text = data.get("thinking") or ""
            return text

    async def is_available(self) -> bool:
        """Check if the Ollama service is reachable."""
        try:
            import httpx

            async with httpx.AsyncClient(
                base_url=self._base_url, timeout=5
            ) as client:
                response = await client.get("/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    @property
    def name(self) -> str:
        """Provider name for logging."""
        return f"ollama ({self._model})"
