"""Claude API client for LLM operations."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

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


class ClaudeCodeClient(BaseLLMClient):
    """LLM client that attempts to use Claude Code session credentials.

    This is a best-effort client that looks for OAuth tokens or credential
    files in ~/.claude/ and uses them to authenticate with the Claude API.
    Falls back gracefully if no usable token is found.
    """

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self._model = model
        self._api_key: str | None = None
        self._client = None
        self._tried_loading = False

    def _load_credentials(self) -> str | None:
        """Attempt to load credentials from ~/.claude/ directory."""
        if self._tried_loading:
            return self._api_key
        self._tried_loading = True

        claude_dir = Path.home() / ".claude"
        if not claude_dir.exists():
            logger.debug("~/.claude/ directory not found")
            return None

        # Look for OAuth token files
        for candidate in [
            claude_dir / "credentials.json",
            claude_dir / "auth.json",
            claude_dir / ".credentials.json",
        ]:
            if candidate.exists():
                try:
                    data = json.loads(candidate.read_text())
                    token = (
                        data.get("api_key")
                        or data.get("token")
                        or data.get("access_token")
                        or data.get("anthropic_api_key")
                    )
                    if token:
                        self._api_key = token
                        logger.info("Loaded Claude credentials from %s", candidate)
                        return token
                except (json.JSONDecodeError, OSError) as e:
                    logger.debug("Could not read %s: %s", candidate, e)

        # Look for any JSON files that might contain tokens
        try:
            for json_file in claude_dir.glob("*.json"):
                try:
                    data = json.loads(json_file.read_text())
                    if isinstance(data, dict):
                        for key in ("api_key", "token", "access_token", "anthropic_api_key"):
                            if key in data and isinstance(data[key], str):
                                self._api_key = data[key]
                                logger.info("Loaded Claude credentials from %s", json_file)
                                return data[key]
                except (json.JSONDecodeError, OSError):
                    continue
        except OSError:
            pass

        logger.debug("No Claude credentials found in ~/.claude/")
        return None

    async def _get_client(self):
        if self._client is None:
            api_key = self._load_credentials()
            if not api_key:
                raise RuntimeError(
                    "No Claude Code credentials found in ~/.claude/"
                )
            try:
                import anthropic

                self._client = anthropic.AsyncAnthropic(api_key=api_key)
            except ImportError:
                raise RuntimeError(
                    "anthropic package not installed. Run: pip install anthropic"
                )
        return self._client

    async def generate(self, prompt: str, system: str | None = None) -> str:
        """Generate text from a prompt using Claude Code credentials."""
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
        """Check if Claude Code credentials are available."""
        api_key = self._load_credentials()
        if not api_key:
            return False
        try:
            await self._get_client()
            return True
        except Exception:
            return False

    @property
    def name(self) -> str:
        """Provider name for logging."""
        return f"claude-code ({self._model})"
