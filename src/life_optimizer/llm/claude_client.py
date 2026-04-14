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
        self, model: str = "claude-sonnet-4-6", api_key: str | None = None
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
    """LLM client that uses the Claude Code CLI (`claude` command).

    This is the way to use a Claude Max subscription without an API key.
    The `claude` CLI ships with Claude Code and authenticates via OAuth
    (stored in ~/.claude/). Requests made through it are billed against
    the user's Max/Pro subscription, not API credits.

    Works by shelling out: `claude -p "<prompt>"` returns the response
    text and exits.
    """

    def __init__(self, model: str = "claude-sonnet-4-6", cli_path: str | None = None):
        self._model = model
        # Locate claude CLI. Standard locations:
        #   ~/.local/bin/claude (Claude Code install)
        #   /usr/local/bin/claude (Homebrew or manual)
        #   /opt/homebrew/bin/claude
        import shutil
        self._cli_path = (
            cli_path
            or shutil.which("claude")
            or str(Path.home() / ".local/bin/claude")
            or "/usr/local/bin/claude"
        )

    async def generate(self, prompt: str, system: str | None = None) -> str:
        """Generate text by piping prompt to `claude -p` via stdin.

        Piping stdin avoids ARG_MAX limits with long prompts and is more
        robust with special characters / newlines.
        """
        import asyncio

        full_prompt = prompt
        if system:
            full_prompt = f"{system}\n\n{prompt}"

        # Build environment with PATH that includes common tool locations.
        # Claude Code's session hooks need `node`, which is typically in
        # /opt/homebrew/bin or ~/.nvm/ but not in the daemon's inherited PATH.
        env = dict(os.environ)
        home = str(Path.home())
        extra_paths = [
            "/opt/homebrew/bin",
            "/opt/homebrew/sbin",
            "/usr/local/bin",
            "/usr/bin",
            "/bin",
            f"{home}/.nvm/versions/node/current/bin",
            f"{home}/.local/bin",
            f"{home}/.volta/bin",
        ]
        existing = env.get("PATH", "").split(":")
        merged = extra_paths + [p for p in existing if p not in extra_paths]
        env["PATH"] = ":".join(merged)

        try:
            proc = await asyncio.create_subprocess_exec(
                self._cli_path,
                "-p",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=full_prompt.encode("utf-8")),
                timeout=300.0,
            )
            out = (stdout or b"").decode("utf-8", errors="replace").strip()
            err = (stderr or b"").decode("utf-8", errors="replace")

            # Exit 1 with non-empty stdout usually means hooks failed but
            # the actual completion succeeded — log the hook error but
            # return the response. Only fail if stdout is truly empty.
            if proc.returncode != 0 and not out:
                raise RuntimeError(
                    f"claude CLI exited {proc.returncode}: {err[:500]}"
                )
            if proc.returncode != 0:
                logger.warning("claude CLI exited %d but returned output; stderr: %s",
                               proc.returncode, err[:200])
            return out
        except asyncio.TimeoutError:
            raise RuntimeError("claude CLI timed out after 300s")
        except FileNotFoundError:
            raise RuntimeError(
                f"claude CLI not found at {self._cli_path}. "
                "Install Claude Code from https://claude.ai/download"
            )

    async def is_available(self) -> bool:
        """Check if the claude CLI is installed and can be invoked."""
        import asyncio

        try:
            proc = await asyncio.create_subprocess_exec(
                self._cli_path,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=5.0)
            return proc.returncode == 0
        except (FileNotFoundError, asyncio.TimeoutError, OSError):
            return False

    @property
    def name(self) -> str:
        """Provider name for logging."""
        return f"claude-code (CLI, {self._model})"
