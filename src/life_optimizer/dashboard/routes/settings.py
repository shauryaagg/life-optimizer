"""Settings routes for the dashboard."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from life_optimizer.storage.repositories import EventRepository, ScreenshotRepository

router = APIRouter()


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Render the settings page."""
    config = request.app.state.config
    db = request.app.state.db
    templates = request.app.state.templates

    # Storage stats
    db_path = Path(config.storage.db_path)
    db_size = db_path.stat().st_size if db_path.exists() else 0
    db_size_mb = round(db_size / (1024 * 1024), 2)

    screenshots_dir = db_path.parent / "screenshots"
    screenshot_size = 0
    screenshot_count = 0
    if screenshots_dir.exists():
        for f in screenshots_dir.iterdir():
            if f.is_file():
                screenshot_size += f.stat().st_size
                screenshot_count += 1
    screenshot_size_mb = round(screenshot_size / (1024 * 1024), 2)

    # Event count
    event_repo = EventRepository(db)
    event_count = await event_repo.get_event_count()

    # Permission status
    permissions = {}
    try:
        from life_optimizer.permissions.checker import PermissionChecker
        checker = PermissionChecker()
        permissions = await checker.check_all()
    except Exception:
        permissions = {"accessibility": False, "screen_recording": False, "automation": False}

    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "active_page": "settings",
            "config": config,
            "db_size_mb": db_size_mb,
            "screenshot_size_mb": screenshot_size_mb,
            "screenshot_count": screenshot_count,
            "event_count": event_count,
            "permissions": permissions,
        },
    )
