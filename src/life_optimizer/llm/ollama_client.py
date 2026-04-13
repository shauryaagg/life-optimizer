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
        """Generate text from a prompt using Ollama."""
        import httpx

        async with httpx.AsyncClient(
            base_url=self._base_url, timeout=120
        ) as client:
            payload: dict = {
                "model": self._model,
                "prompt": prompt,
                "stream": False,
            }
            if system:
                payload["system"] = system
            response = await client.post("/api/generate", json=payload)
            response.raise_for_status()
            return response.json()["response"]

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
