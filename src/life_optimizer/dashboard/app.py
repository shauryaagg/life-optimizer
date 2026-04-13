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

    # Templates
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
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
    from life_optimizer.dashboard.routes.reports import router as reports_router
    from life_optimizer.dashboard.routes.screenshots import router as screenshots_router
    from life_optimizer.dashboard.routes.settings import router as settings_router
    from life_optimizer.dashboard.routes.timeline import router as timeline_router

    app.include_router(timeline_router)
    app.include_router(reports_router)
    app.include_router(screenshots_router)
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
