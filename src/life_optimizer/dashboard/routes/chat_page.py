"""Chat page routes for the dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request):
    """Render the chat page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "chat.html",
        {"active_page": "chat"},
    )
