"""Screenshots routes for the dashboard."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from life_optimizer.storage.repositories import ScreenshotRepository

router = APIRouter()


@router.get("/screenshots", response_class=HTMLResponse)
async def screenshots_page(request: Request):
    """Render the screenshot gallery page."""
    templates = request.app.state.templates
    today = date.today().isoformat()
    return templates.TemplateResponse(
        request,
        "screenshots.html",
        {"active_page": "screenshots", "today": today},
    )


@router.get("/screenshots/gallery", response_class=HTMLResponse)
async def screenshots_gallery(request: Request, date: str | None = None):
    """HTMX partial: screenshot grid for a given date.

    Screenshots are captured by the Swift menubar app (which uses its own
    Screen Recording permission) and written directly to disk. We list files
    in the dated directory, falling back to database records for metadata.
    """
    from datetime import date as date_cls
    if date is None:
        date = date_cls.today().isoformat()

    screenshots_dir = Path(request.app.state.config.storage.db_path).parent / "screenshots"
    day_dir = screenshots_dir / date

    screenshot_data = []
    if day_dir.is_dir():
        # List JPEG files sorted by newest first
        files = sorted(
            (p for p in day_dir.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for fp in files[:100]:
            # Parse filename: HHMMSS_appname.jpg
            name = fp.stem
            parts = name.split("_", 1)
            time_str = parts[0] if len(parts) == 2 else ""
            app_name = parts[1].replace("_", " ").title() if len(parts) == 2 else name

            # Build ISO timestamp with local timezone offset so the
            # template's local_time filter converts correctly.
            if len(time_str) == 6 and time_str.isdigit():
                from datetime import datetime as dt_cls
                try:
                    y, m, d = [int(p) for p in date.split("-")]
                    hh = int(time_str[0:2]); mm = int(time_str[2:4]); ss = int(time_str[4:6])
                    local_tz = dt_cls.now().astimezone().tzinfo
                    naive = dt_cls(y, m, d, hh, mm, ss, tzinfo=local_tz)
                    ts = naive.isoformat()
                except Exception:
                    ts = f"{date}T{time_str[0:2]}:{time_str[2:4]}:{time_str[4:6]}"
            else:
                ts = ""

            try:
                rel_path = fp.relative_to(screenshots_dir)
                url = f"/screenshots-static/{rel_path}"
            except ValueError:
                url = f"/screenshots-static/{fp.name}"

            screenshot_data.append({
                "id": 0,
                "timestamp": ts,
                "app_name": app_name,
                "window_title": "",
                "url": url,
                "exists": True,
            })

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "partials/screenshot_grid.html",
        {"screenshots": screenshot_data},
    )
