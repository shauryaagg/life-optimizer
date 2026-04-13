"""Bridge for running JXA (JavaScript for Automation) and AppleScript via osascript."""

from __future__ import annotations

import asyncio
import json
import logging

logger = logging.getLogger(__name__)


class JXABridge:
    """Executes JXA and AppleScript scripts via osascript with concurrency control."""

    def __init__(self, max_concurrent: int = 3, timeout: float = 5.0):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._timeout = timeout

    async def run_jxa(self, script: str) -> str | None:
        """Run a JXA script and return stdout as a string.

        Args:
            script: JavaScript for Automation script source.

        Returns:
            stdout output as string, or None on failure.
        """
        return await self._run_osascript(["-l", "JavaScript", "-e", script])

    async def run_applescript(self, script: str) -> str | None:
        """Run an AppleScript and return stdout as a string.

        Args:
            script: AppleScript source.

        Returns:
            stdout output as string, or None on failure.
        """
        return await self._run_osascript(["-e", script])

    async def run_jxa_json(self, script: str) -> dict | None:
        """Run a JXA script and parse the JSON output.

        Args:
            script: JXA script that outputs JSON via JSON.stringify().

        Returns:
            Parsed dict, or None on failure / null output.
        """
        result = await self.run_jxa(script)
        if result is None:
            return None
        result = result.strip()
        if not result or result == "null":
            return None
        try:
            parsed = json.loads(result)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse JXA JSON output: %s (output: %r)", e, result[:200])
            return None

    async def _run_osascript(self, args: list[str]) -> str | None:
        """Run osascript with the given arguments, respecting semaphore and timeout.

        Args:
            args: Arguments to pass to osascript.

        Returns:
            stdout output as string, or None on failure/timeout.
        """
        async with self._semaphore:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "osascript",
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self._timeout,
                )

                if proc.returncode != 0:
                    stderr_text = stderr.decode("utf-8", errors="replace").strip()
                    if stderr_text:
                        logger.debug("osascript stderr: %s", stderr_text)
                    return None

                return stdout.decode("utf-8", errors="replace").strip()

            except asyncio.TimeoutError:
                logger.warning("osascript timed out after %.1fs", self._timeout)
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass
                return None
            except Exception as e:
                logger.warning("osascript execution failed: %s", e)
                return None
