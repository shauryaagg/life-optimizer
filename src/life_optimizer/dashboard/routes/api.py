"""JSON API routes for the dashboard."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date

from fastapi import APIRouter, Request

from life_optimizer.storage.repositories import (
    EventRepository,
    ScreenshotRepository,
    SessionRepository,
    SummaryRepository,
)

router = APIRouter(prefix="/api")


@router.get("/events")
async def api_events(
    request: Request,
    date: str | None = None,
    app: str | None = None,
    limit: int = 100,
):
    """JSON list of events."""
    db = request.app.state.db
    repo = EventRepository(db)
    events = await repo.get_events(date=date, app=app, limit=limit)
    return [asdict(e) for e in events]


@router.get("/sessions")
async def api_sessions(request: Request, date: str | None = None):
    """JSON list of sessions."""
    db = request.app.state.db
    repo = SessionRepository(db)
    sessions = await repo.get_sessions(date=date)
    return [asdict(s) for s in sessions]


@router.get("/summaries")
async def api_summaries(
    request: Request,
    period_type: str | None = None,
    date: str | None = None,
    limit: int = 100,
):
    """JSON list of summaries."""
    db = request.app.state.db
    repo = SummaryRepository(db)
    summaries = await repo.get_summaries(period_type=period_type, date=date, limit=limit)
    return [asdict(s) for s in summaries]


@router.get("/stats")
async def api_stats(request: Request, date: str | None = None):
    """JSON stats: event count, category breakdown, top apps."""
    if date is None:
        from datetime import date as date_cls
        date = date_cls.today().isoformat()

    db = request.app.state.db
    event_repo = EventRepository(db)
    events = await event_repo.get_events(date=date, limit=500)

    category_counts: dict[str, int] = {}
    app_counts: dict[str, int] = {}
    for event in events:
        cat = event.category or "other"
        category_counts[cat] = category_counts.get(cat, 0) + 1
        app_counts[event.app_name] = app_counts.get(event.app_name, 0) + 1

    top_apps = sorted(app_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "date": date,
        "event_count": len(events),
        "category_breakdown": category_counts,
        "top_apps": [{"app": app, "count": count} for app, count in top_apps],
    }


@router.get("/screenshots")
async def api_screenshots(request: Request, date: str | None = None, limit: int = 100):
    """JSON list of screenshot metadata."""
    db = request.app.state.db
    repo = ScreenshotRepository(db)
    screenshots = await repo.get_screenshots(date=date, limit=limit)
    return [asdict(s) for s in screenshots]
