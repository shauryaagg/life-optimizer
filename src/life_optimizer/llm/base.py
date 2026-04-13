"""Abstract base class for LLM clients."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system: str | None = None) -> str:
        """Generate text from a prompt."""
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the LLM service is reachable."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging."""
        ...
