"""Timeline routes for the dashboard."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from life_optimizer.storage.repositories import EventRepository

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
@router.get("/timeline", response_class=HTMLResponse)
async def timeline_page(request: Request):
    """Render the timeline page."""
    templates = request.app.state.templates
    today = date.today().isoformat()
    return templates.TemplateResponse(
        request,
        "timeline.html",
        {"active_page": "timeline", "today": today},
    )


@router.get("/timeline/events", response_class=HTMLResponse)
async def timeline_events(
    request: Request,
    date: str | None = None,
    app: str | None = None,
):
    """HTMX partial: return rendered event cards for a given date."""
    if date is None:
        from datetime import date as date_cls
        date = date_cls.today().isoformat()

    db = request.app.state.db
    repo = EventRepository(db)
    events = await repo.get_events(date=date, app=app, limit=200)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "partials/event_card.html",
        {"events": events},
    )
