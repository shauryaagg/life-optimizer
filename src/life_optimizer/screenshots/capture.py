"""Screenshot capture using macOS screencapture and Pillow for compression."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ScreenshotResult:
    """Result of a screenshot capture."""

    file_path: str
    timestamp: datetime
    file_size_bytes: int
    width: int
    height: int
    app_name: str
    trigger_reason: str


class ScreenshotCapture:
    """Captures screenshots using macOS screencapture, then compresses with Pillow."""

    def __init__(
        self,
        base_dir: str = "data/screenshots",
        quality: int = 60,
        scale: float = 0.5,
    ):
        self._base_dir = Path(base_dir)
        self._quality = quality
        self._scale = scale

    def _build_path(self, app_name: str, ts: datetime) -> Path:
        """Build the output file path: base/YYYY-MM-DD/HHMMSS_appname.jpg."""
        date_str = ts.strftime("%Y-%m-%d")
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", app_name).lower()
        filename = f"{ts.strftime('%H%M%S')}_{safe_name}.jpg"
        return self._base_dir / date_str / filename

    async def capture(self, app_name: str, trigger: str) -> ScreenshotResult | None:
        """Capture a screenshot, resize and compress it.

        Args:
            app_name: Name of the current frontmost application.
            trigger: Reason the screenshot was taken (e.g. "app_switch", "interval").

        Returns:
            ScreenshotResult with file details, or None on failure.
        """
        try:
            ts = datetime.now(timezone.utc)
            out_path = self._build_path(app_name, ts)
            out_path.parent.mkdir(parents=True, exist_ok=True)

            # Capture raw screenshot to a temp path
            raw_path = out_path.with_suffix(".raw.png")
            proc = await asyncio.create_subprocess_exec(
                "screencapture", "-x", "-t", "png", str(raw_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=10.0)

            if proc.returncode != 0 or not raw_path.exists():
                logger.warning("screencapture failed (rc=%s)", proc.returncode)
                return None

            # Resize and compress with Pillow
            from PIL import Image

            with Image.open(raw_path) as img:
                new_w = int(img.width * self._scale)
                new_h = int(img.height * self._scale)
                resized = img.resize((new_w, new_h), Image.LANCZOS)
                resized.save(str(out_path), "JPEG", quality=self._quality)

            # Clean up raw file
            raw_path.unlink(missing_ok=True)

            file_size = out_path.stat().st_size

            # Get dimensions of final file
            with Image.open(out_path) as final_img:
                width, height = final_img.size

            return ScreenshotResult(
                file_path=str(out_path),
                timestamp=ts,
                file_size_bytes=file_size,
                width=width,
                height=height,
                app_name=app_name,
                trigger_reason=trigger,
            )

        except asyncio.TimeoutError:
            logger.warning("screencapture timed out")
            return None
        except Exception as e:
            logger.warning("Screenshot capture failed: %s", e)
            return None
