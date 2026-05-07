"""FastAPI application — main entry point."""

from __future__ import annotations

import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings
from .database import Database
from .routes import router
from .scheduler import SyncScheduler
from .service import QuobuzDownloadService

logger = logging.getLogger(__name__)

# Global instances — initialized in lifespan()
db: Database | None = None
service: QuobuzDownloadService | None = None
scheduler: SyncScheduler | None = None
settings: Settings | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle — startup and shutdown."""
    global db, service, scheduler, settings

    settings = Settings.from_env()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Database
    db_path = Path(settings.data_dir) / "quobuz.db"
    db = Database(db_path)
    logger.info("Database: %s", db_path)

    # Service
    service = QuobuzDownloadService(db, settings)

    # Scheduler
    sync_schedule = db.get_setting("sync_schedule", settings.sync_schedule)
    scheduler = SyncScheduler(db, lambda pid: asyncio.create_task(service.start_download(pid)))
    scheduler.start(sync_schedule)

    logger.info("Quobuz API server starting on port %d", settings.port)

    yield

    scheduler.stop()
    logger.info("Quobuz API server stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Quobuz",
        description="Qobuz playlist downloader with WebUI",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(router)

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve React SPA — fallback to index.html for client-side routing."""
        if full_path.startswith("api/") or full_path.startswith(".well-known"):
            return _serve_index()

        webui_dir = os.environ.get("WEBUI_DIR", "/app/webui_build")
        data_dir = os.environ.get("DATA_DIR", "/app/quobuz_data")
        # Try dedicated WebUI dir first, then fallback to DATA_DIR/webui_build
        file_path = Path(webui_dir) / full_path
        if not file_path.exists() or not file_path.is_file():
            file_path = Path(data_dir) / "webui_build" / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))

        return _serve_index()

    def _serve_index():
        webui_dir = os.environ.get("WEBUI_DIR", "/app/webui_build")
        data_dir = os.environ.get("DATA_DIR", "/app/quobuz_data")
        # Try dedicated WebUI dir first, then fallback to DATA_DIR/webui_build
        index_file = Path(webui_dir) / "index.html"
        if not index_file.exists():
            index_file = Path(data_dir) / "webui_build" / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return FileResponse(index_file)

    return app


# Import needed for lifespan
import asyncio
