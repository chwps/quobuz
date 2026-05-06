#!/usr/bin/env python3
"""Quobuz API server entry point."""

import uvicorn

from quobuz_api import create_app, Settings

settings = Settings.from_env()
app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
