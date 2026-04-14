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
    """HTMX partial: session timeline data for the focus page.

    Converts UTC timestamps to local timezone HH:MM strings for positioning
    bars on the Gantt chart.
    """
    from datetime import datetime, timezone

    db = request.app.state.db
    repo = SessionRepository(db)

    def to_local_hhmm(iso_str: str | None) -> str | None:
        if not iso_str:
            return None
        try:
            s = iso_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone().strftime("%H:%M")
        except Exception:
            return iso_str

    today = date.today()
    sessions_by_day = []

    for i in range(days):
        day = today - timedelta(days=i)
        day_str = day.isoformat()
        sessions = await repo.get_sessions(date=day_str)
        # Build plain dicts with localized times so the template can do HH:MM math
        session_dicts = []
        for s in sessions:
            session_dicts.append({
                "app_name": s.app_name,
                "start_time": to_local_hhmm(s.start_time),
                "end_time": to_local_hhmm(s.end_time),
                "duration_seconds": s.duration_seconds,
                "category": s.category,
            })
        sessions_by_day.append({
            "date": day_str,
            "sessions": session_dicts,
        })

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "partials/focus_timeline.html",
        {"days_data": sessions_by_day},
    )
