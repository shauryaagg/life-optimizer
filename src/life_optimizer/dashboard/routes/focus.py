"""Focus timeline routes for the dashboard."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from life_optimizer.storage.repositories import SessionRepository

router = APIRouter()


@router.get("/focus", response_class=HTMLResponse)
async def focus_page(request: Request):
    """Render the focus timeline page."""
    templates = request.app.state.templates
    today = date.today().isoformat()
    return templates.TemplateResponse(
        request,
        "focus.html",
        {"active_page": "focus", "today": today},
    )


@router.get("/focus/timeline", response_class=HTMLResponse)
async def focus_timeline(request: Request, days: int = 7):
    """HTMX partial: session timeline data for the focus page."""
    db = request.app.state.db
    repo = SessionRepository(db)

    today = date.today()
    sessions_by_day = []

    for i in range(days):
        day = today - timedelta(days=i)
        day_str = day.isoformat()
        sessions = await repo.get_sessions(date=day_str)
        sessions_by_day.append({
            "date": day_str,
            "sessions": sessions,
        })

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "partials/focus_timeline.html",
        {"days_data": sessions_by_day},
    )
