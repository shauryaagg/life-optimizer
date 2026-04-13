"""LLM integration for activity categorization, summaries, and insights."""

from .base import BaseLLMClient
from .claude_client import ClaudeClient
from .ollama_client import OllamaClient


def create_llm_client(config) -> BaseLLMClient | None:
    """Create the appropriate LLM client based on config.

    Args:
        config: Application Config object with an llm attribute.

    Returns:
        An LLM client instance, or None if provider is "none".

    Raises:
        ValueError: If the provider is unknown.
    """
    provider = config.llm.provider
    if provider == "claude":
        return ClaudeClient(
            model=config.llm.claude_model,
            api_key=config.llm.claude_api_key,
        )
    elif provider == "ollama":
        return OllamaClient(
            model=config.llm.ollama_model,
            base_url=config.llm.ollama_base_url,
        )
    elif provider == "none":
        return None
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


__all__ = [
    "BaseLLMClient",
    "ClaudeClient",
    "OllamaClient",
    "create_llm_client",
]
