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
    """HTMX partial: screenshot grid for a given date."""
    if date is None:
        from datetime import date as date_cls
        date = date_cls.today().isoformat()

    db = request.app.state.db
    repo = ScreenshotRepository(db)
    screenshots = await repo.get_screenshots(date=date, limit=100)

    # Build URL-safe paths for each screenshot
    screenshots_dir = Path(request.app.state.config.storage.db_path).parent / "screenshots"
    screenshot_data = []
    for s in screenshots:
        file_path = Path(s.file_path)
        # Try to make the path relative to the screenshots directory
        try:
            rel_path = file_path.relative_to(screenshots_dir)
            url = f"/screenshots-static/{rel_path}"
        except ValueError:
            # If not relative, use the filename
            url = f"/screenshots-static/{file_path.name}"

        exists = file_path.exists()
        screenshot_data.append(
            {
                "id": s.id,
                "timestamp": s.timestamp,
                "app_name": s.app_name,
                "window_title": s.window_title,
                "url": url,
                "exists": exists,
            }
        )

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "partials/screenshot_grid.html",
        {"screenshots": screenshot_data},
    )
