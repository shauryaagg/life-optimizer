"""Chat and query API routes."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Request
from pydantic import BaseModel

from life_optimizer.query.engine import ChatMessage, QueryEngine
from life_optimizer.storage.repositories import (
    ChatHistoryRepository,
    EntityRepository,
    EventRepository,
)

router = APIRouter(prefix="/api")


class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None
    history: list[dict] | None = None


@router.post("/chat")
async def chat(request: Request, body: ChatRequest):
    """Answer a natural language question about activity data."""
    db = request.app.state.db
    query_engine: QueryEngine | None = getattr(request.app.state, "query_engine", None)

    if query_engine is None:
        # Create a minimal engine without LLM
        query_engine = QueryEngine(db=db, llm_client=None, semantic_search=None)

    # Convert history if provided
    history = None
    if body.history:
        history = [
            ChatMessage(role=msg.get("role", "user"), content=msg.get("content", ""))
            for msg in body.history
        ]

    response = await query_engine.answer(body.question, history=history)

    # Store in chat history
    chat_repo = ChatHistoryRepository(db)
    session_id = body.session_id or response.session_id
    await chat_repo.add_message(
        session_id=session_id,
        role="user",
        content=body.question,
    )
    await chat_repo.add_message(
        session_id=session_id,
        role="assistant",
        content=response.answer,
        query_type=response.query_type,
        sql_query=response.sql_query,
    )

    return {
        "answer": response.answer,
        "query_type": response.query_type,
        "sql_query": response.sql_query,
        "follow_up_suggestions": response.follow_up_suggestions,
        "session_id": session_id,
    }


@router.get("/chat/history")
async def chat_history(request: Request, session_id: str):
    """Get chat history for a session."""
    db = request.app.state.db
    repo = ChatHistoryRepository(db)
    history = await repo.get_history(session_id)
    return history


@router.get("/status")
async def status(request: Request):
    """Get system status."""
    db = request.app.state.db
    event_repo = EventRepository(db)
    count = await event_repo.get_event_count()

    # Get last event time
    events = await event_repo.get_events(limit=1)
    last_event_time = events[0].timestamp if events else None

    return {
        "daemon_running": True,
        "tracking_status": "active",
        "event_count": count,
        "last_event_time": last_event_time,
    }


@router.get("/entities")
async def entities(
    request: Request,
    type: str | None = None,
    limit: int = 100,
):
    """Get tracked entities."""
    db = request.app.state.db
    repo = EntityRepository(db)
    entity_list = await repo.get_entities(entity_type=type, limit=limit)
    return [asdict(e) for e in entity_list]
