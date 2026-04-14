"""JSON API routes for the dashboard."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Request

from life_optimizer.storage.repositories import (
    EntityRepository,
    EventRepository,
    ScreenshotRepository,
    SessionRepository,
    SummaryRepository,
)

router = APIRouter(prefix="/api")


@router.post("/chrome-extension/page-context")
async def chrome_extension_page_context(request: Request):
    """Receive page metadata from Chrome extension."""
    data = await request.json()
    db = request.app.state.db
    repo = EventRepository(db)

    await repo.insert_event_raw(
        timestamp=datetime.now().isoformat(),
        app_name="Google Chrome",
        app_bundle_id="com.google.Chrome",
        event_type="chrome_extension",
        window_title=data.get("title", ""),
        context_json=json.dumps(data),
    )
    return {"status": "ok"}


@router.post("/chrome-extension/tab-switch")
async def chrome_extension_tab_switch(request: Request):
    """Receive tab switch notification from Chrome extension."""
    data = await request.json()
    db = request.app.state.db
    repo = EventRepository(db)

    await repo.insert_event_raw(
        timestamp=data.get("timestamp", datetime.now().isoformat()),
        app_name="Google Chrome",
        app_bundle_id="com.google.Chrome",
        event_type="chrome_extension_tab_switch",
        window_title=data.get("title", ""),
        context_json=json.dumps(data),
    )
    return {"status": "ok"}


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


@router.get("/stats/weekly")
async def api_stats_weekly(request: Request, week_offset: int = 0):
    """Return category totals per day for the specified week.

    Args:
        week_offset: 0 = this week, 1 = last week, etc.
    """
    db = request.app.state.db
    repo = SessionRepository(db)

    today = date.today()
    # Monday of the current week
    monday = today - timedelta(days=today.weekday())
    # Apply offset
    week_start = monday - timedelta(weeks=week_offset)

    days = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        day_str = day.isoformat()
        sessions = await repo.get_sessions(date=day_str)

        categories: dict[str, float] = defaultdict(float)
        total_minutes = 0.0
        for s in sessions:
            cat = s.category or "other"
            dur = (s.duration_seconds or 0) / 60
            categories[cat] += dur
            total_minutes += dur

        # Round values
        categories_rounded = {k: round(v, 1) for k, v in categories.items()}

        days.append({
            "date": day_str,
            "categories": categories_rounded,
            "total_minutes": round(total_minutes, 1),
        })

    return {
        "week_start": week_start.isoformat(),
        "days": days,
    }


@router.get("/stats/monthly")
async def api_stats_monthly(request: Request, month: str | None = None):
    """Return daily totals for a given month.

    Args:
        month: Month in YYYY-MM format. Defaults to current month.
    """
    db = request.app.state.db
    repo = SessionRepository(db)

    if month is None:
        month = date.today().strftime("%Y-%m")

    # Parse the month
    try:
        year, mon = month.split("-")
        year_int, mon_int = int(year), int(mon)
    except (ValueError, AttributeError):
        return {"month": month, "days": []}

    # Determine the number of days in the month
    if mon_int == 12:
        next_month_start = date(year_int + 1, 1, 1)
    else:
        next_month_start = date(year_int, mon_int + 1, 1)
    month_start = date(year_int, mon_int, 1)
    num_days = (next_month_start - month_start).days

    days = []
    for i in range(num_days):
        day = month_start + timedelta(days=i)
        # Only include days up to today
        if day > date.today():
            break
        day_str = day.isoformat()
        sessions = await repo.get_sessions(date=day_str)

        total_minutes = 0.0
        deep_work_minutes = 0.0
        app_counts: dict[str, float] = defaultdict(float)

        for s in sessions:
            dur = (s.duration_seconds or 0) / 60
            total_minutes += dur
            if s.category == "deep_work":
                deep_work_minutes += dur
            app_counts[s.app_name] += dur

        top_app = max(app_counts, key=app_counts.get) if app_counts else None

        days.append({
            "date": day_str,
            "total_minutes": round(total_minutes, 1),
            "deep_work_minutes": round(deep_work_minutes, 1),
            "top_app": top_app,
        })

    return {
        "month": month,
        "days": days,
    }


@router.get("/sessions/timeline")
async def api_sessions_timeline(request: Request, days: int = 7):
    """Return sessions for the last N days with start/end times and categories."""
    db = request.app.state.db
    repo = SessionRepository(db)

    from datetime import timezone

    today = date.today()
    result_sessions = []

    def to_local_hhmm(iso_str: str | None) -> str:
        if not iso_str:
            return ""
        try:
            s = iso_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone().strftime("%H:%M")
        except Exception:
            return ""

    for i in range(days):
        day = today - timedelta(days=i)
        day_str = day.isoformat()
        sessions = await repo.get_sessions(date=day_str)

        for s in sessions:
            result_sessions.append({
                "date": day_str,
                "start_time": to_local_hhmm(s.start_time),
                "end_time": to_local_hhmm(s.end_time),
                "app_name": s.app_name,
                "category": s.category or "Other",
                "duration_minutes": round((s.duration_seconds or 0) / 60, 1),
            })

    return {"sessions": result_sessions}


@router.get("/entities/graph")
async def api_entities_graph(request: Request, days: int = 30):
    """Return nodes and edges for entity interaction graph.

    Nodes are entities with interaction_count.
    Edges represent co-occurrence of entities in the same hour window.
    """
    db = request.app.state.db
    entity_repo = EntityRepository(db)

    entities = await entity_repo.get_entities(limit=200)

    nodes = [
        {
            "id": e.id,
            "name": e.name,
            "type": e.entity_type,
            "interactions": e.interaction_count,
        }
        for e in entities
    ]

    # Build edges based on co-occurrence in the same hour
    # Get mentions for each entity and find hourly overlaps
    entity_hours: dict[int, set[str]] = {}
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()

    for e in entities:
        mentions = await entity_repo.get_mentions(e.id, limit=500)
        hours = set()
        for m in mentions:
            if m.timestamp and m.timestamp >= cutoff:
                # Truncate to hour
                try:
                    dt = datetime.fromisoformat(m.timestamp)
                    hours.add(dt.strftime("%Y-%m-%d %H"))
                except (ValueError, TypeError):
                    pass
        entity_hours[e.id] = hours

    # Find co-occurrences
    edges = []
    entity_ids = [e.id for e in entities]
    for i in range(len(entity_ids)):
        for j in range(i + 1, len(entity_ids)):
            id_a = entity_ids[i]
            id_b = entity_ids[j]
            overlap = entity_hours.get(id_a, set()) & entity_hours.get(id_b, set())
            if overlap:
                edges.append({
                    "source": id_a,
                    "target": id_b,
                    "weight": len(overlap),
                })

    return {"nodes": nodes, "edges": edges}
