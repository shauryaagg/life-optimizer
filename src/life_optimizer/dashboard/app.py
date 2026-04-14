"""FastAPI application factory for the Life Optimizer dashboard."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from life_optimizer.config import Config
from life_optimizer.storage.database import Database

logger = logging.getLogger(__name__)

DASHBOARD_DIR = Path(__file__).parent
TEMPLATES_DIR = DASHBOARD_DIR / "templates"
STATIC_DIR = DASHBOARD_DIR / "static"


def create_app(config: Config) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        config: Application configuration.

    Returns:
        Configured FastAPI instance.
    """
    db = Database(config.storage.db_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await db.initialize()
        logger.info("Dashboard database initialized")
        yield
        await db.close()
        logger.info("Dashboard database closed")

    app = FastAPI(title="Life Optimizer Dashboard", lifespan=lifespan)

    # Store config and db on app state
    app.state.config = config
    app.state.db = db

    # Templates with custom filters for local timezone display
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

    from datetime import datetime, timezone

    def to_local_time(iso_str: str | None, fmt: str = "%H:%M:%S") -> str:
        """Parse an ISO timestamp (assumed UTC if no tz) and format in local time."""
        if not iso_str:
            return ""
        try:
            # Python's fromisoformat handles "+00:00" but not "Z"
            s = iso_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(s)
            # If no tzinfo, assume UTC (the daemon stores UTC)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            # Convert to the system's local timezone
            return dt.astimezone().strftime(fmt)
        except (ValueError, TypeError):
            return iso_str

    def to_local_datetime(iso_str: str | None) -> str:
        return to_local_time(iso_str, "%Y-%m-%d %H:%M:%S")

    # Markdown renderer — LLMs emit markdown (headers, tables, lists, bold).
    # markdown-it-py is already a transitive dep.
    _md_renderer = None
    def render_markdown(text: str | None) -> str:
        nonlocal _md_renderer
        if not text:
            return ""
        if _md_renderer is None:
            try:
                from markdown_it import MarkdownIt
                _md_renderer = MarkdownIt("commonmark", {"html": False, "linkify": True, "breaks": True}).enable("table").enable("strikethrough")
            except ImportError:
                return text.replace("\n", "<br>")
        return _md_renderer.render(text)

    templates.env.filters["local_time"] = to_local_time
    templates.env.filters["local_datetime"] = to_local_datetime
    templates.env.filters["markdown"] = render_markdown
    app.state.templates = templates

    # CORS - localhost only
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:*", "http://localhost:*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Static files
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Mount screenshot directory
    screenshots_dir = Path(config.storage.db_path).parent / "screenshots"
    if screenshots_dir.exists():
        app.mount(
            "/screenshots-static",
            StaticFiles(directory=str(screenshots_dir)),
            name="screenshots-static",
        )

    # Include route modules
    from life_optimizer.dashboard.routes.api import router as api_router
    from life_optimizer.dashboard.routes.chat import router as chat_router
    from life_optimizer.dashboard.routes.chat_page import router as chat_page_router
    from life_optimizer.dashboard.routes.focus import router as focus_router
    from life_optimizer.dashboard.routes.reports import router as reports_router
    from life_optimizer.dashboard.routes.screenshots import router as screenshots_router
    from life_optimizer.dashboard.routes.settings import router as settings_router
    from life_optimizer.dashboard.routes.timeline import router as timeline_router

    app.include_router(timeline_router)
    app.include_router(reports_router)
    app.include_router(focus_router)
    app.include_router(screenshots_router)
    app.include_router(chat_page_router)
    app.include_router(settings_router)
    app.include_router(api_router)
    app.include_router(chat_router)

    # Initialize query engine (best effort)
    try:
        from life_optimizer.llm import create_llm_client
        from life_optimizer.query.engine import QueryEngine
        from life_optimizer.query.semantic_search import SemanticSearch, CHROMADB_AVAILABLE

        llm_client = create_llm_client(config)
        semantic = None
        if CHROMADB_AVAILABLE:
            chromadb_dir = getattr(
                getattr(config, "query", None), "chromadb_dir", "data/chromadb"
            )
            semantic = SemanticSearch(persist_dir=chromadb_dir)
        app.state.query_engine = QueryEngine(
            db=db, llm_client=llm_client, semantic_search=semantic
        )
        app.state.semantic_search = semantic
    except Exception as exc:
        logger.warning("Could not initialize query engine: %s", exc)
        app.state.query_engine = None
        app.state.semantic_search = None

    return app
