"""quobuz-api — FastAPI server for Qobuz playlist downloader."""

from .app import create_app
from .config import Settings

__all__ = ["create_app", "Settings"]
