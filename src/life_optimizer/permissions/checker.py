"""macOS permission checking for Life Optimizer."""

from __future__ import annotations

import logging
import os
import subprocess

logger = logging.getLogger(__name__)


class PermissionChecker:
    """Check required macOS permissions."""

    async def check_all(self) -> dict[str, bool]:
        """Check all required permissions, return {name: granted} dict."""
        results = {}
        results["accessibility"] = await self._check_accessibility()
        results["screen_recording"] = await self._check_screen_recording()
        results["automation"] = await self._check_automation()
        return results

    async def _check_accessibility(self) -> bool:
        """Check if Accessibility permission is granted."""
        try:
            result = subprocess.run(
                [
                    "osascript",
                    "-e",
                    'tell application "System Events" to get name of '
                    "first application process whose frontmost is true",
                ],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False

    async def _check_screen_recording(self) -> bool:
        """Check if Screen Recording permission is granted."""
        try:
            test_path = "/tmp/.life_optimizer_test_screenshot.jpg"
            result = subprocess.run(
                ["screencapture", "-x", "-t", "jpg", test_path],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                try:
                    os.remove(test_path)
                except OSError:
                    pass
                return True
            return False
        except Exception:
            return False

    async def _check_automation(self) -> bool:
        """Check if Automation permission is granted (for Chrome at minimum)."""
        try:
            result = subprocess.run(
                [
                    "osascript",
                    "-l",
                    "JavaScript",
                    "-e",
                    'Application("Google Chrome").running()',
                ],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False
