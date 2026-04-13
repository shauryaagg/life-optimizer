"""Reports routes for the dashboard."""

from __future__ import annotations

import json
from datetime import date

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from life_optimizer.storage.repositories import EventRepository, SummaryRepository

router = APIRouter()


@router.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request):
    """Render the reports page."""
    templates = request.app.state.templates
    today = date.today().isoformat()
    return templates.TemplateResponse(
        request,
        "reports.html",
        {"active_page": "reports", "today": today},
    )


@router.get("/reports/daily", response_class=HTMLResponse)
async def reports_daily(request: Request, date: str | None = None):
    """HTMX partial: daily summary for a given date."""
    if date is None:
        from datetime import date as date_cls
        date = date_cls.today().isoformat()

    db = request.app.state.db
    summary_repo = SummaryRepository(db)
    event_repo = EventRepository(db)

    summaries = await summary_repo.get_summaries(period_type="daily", date=date, limit=1)
    summary = summaries[0] if summaries else None

    # Get events for category breakdown and top apps
    events = await event_repo.get_events(date=date, limit=500)

    # Compute category breakdown
    category_counts: dict[str, int] = {}
    app_counts: dict[str, int] = {}
    for event in events:
        cat = event.category or "other"
        category_counts[cat] = category_counts.get(cat, 0) + 1
        app_counts[event.app_name] = app_counts.get(event.app_name, 0) + 1

    # Sort top apps by count
    top_apps = sorted(app_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "partials/summary_card.html",
        {
            "summary": summary,
            "category_counts": json.dumps(category_counts),
            "top_apps": json.dumps(top_apps),
            "event_count": len(events),
        },
    )
