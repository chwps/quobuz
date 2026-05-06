"""API routes for quobuz service."""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from .database import Database
from .service import QuobuzDownloadService

router = APIRouter()


def get_service() -> QuobuzDownloadService:
    """Get the global service instance."""
    from .app import service as _service
    return _service


def get_db() -> Database:
    """Get the global database instance."""
    from .app import db as _db
    return _db


# --- Auth ---


@router.post("/api/auth/login")
async def login():
    """Authenticate with Qobuz using stored credentials."""
    svc = get_service()
    try:
        result = await svc.authenticate()
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/api/auth/user")
async def get_user():
    """Get current user info."""
    svc = get_service()
    try:
        user = await svc.get_user_info()
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/api/auth/refresh-credentials")
async def refresh_credentials():
    """Extract fresh app credentials from Qobuz bundle."""
    svc = get_service()
    try:
        config = await svc.extract_bundle_config()
        db = get_db()
        if config.get("app_id"):
            db.set_setting("qobuz_app_id", config["app_id"])
        if config.get("app_secret"):
            db.set_setting("qobuz_app_secret", config["app_secret"])
        return {"success": True, **config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Playlists ---


@router.get("/api/playlists")
async def list_playlists():
    """Get authenticated user's Qobuz playlists."""
    svc = get_service()
    try:
        playlists = await svc.get_playlists()
        local = get_db().get_all_playlists()
        local_ids = {p["qobuz_id"] for p in local}

        result = []
        for pl in playlists:
            pid = str(pl["id"])
            result.append({
                **pl,
                "qobuz_id": pid,
                "is_subscribed": pid in local_ids,
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/api/playlists/{playlist_id}/tracks")
async def get_playlist_tracks(playlist_id: str):
    """Get tracks for a Qobuz playlist."""
    svc = get_service()
    try:
        tracks = await svc.get_playlist_tracks(playlist_id)
        return tracks
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/playlists/{playlist_id}/subscribe")
async def subscribe_playlist(playlist_id: str):
    """Subscribe to a playlist for auto-sync."""
    db = get_db()
    playlist = db.get_playlist(playlist_id)
    if not playlist:
        raise HTTPException(status_code=404, detail="Playlist not found")

    db.add_subscription(playlist_id)
    return {"success": True}


@router.post("/api/playlists/{playlist_id}/unsubscribe")
async def unsubscribe_playlist(playlist_id: str):
    """Unsubscribe from a playlist."""
    db = get_db()
    db.delete_subscription(playlist_id)
    db.delete_playlist(playlist_id)
    return {"success": True}


@router.post("/api/playlists/{playlist_id}/download")
async def download_playlist(playlist_id: str):
    """Start downloading a playlist."""
    db = get_db()
    if not db.get_playlist(playlist_id):
        raise HTTPException(status_code=404, detail="Playlist not found")

    svc = get_service()
    job_id = await svc.start_download(playlist_id)
    return {"job_id": job_id}


@router.post("/api/playlists/add")
async def add_playlist(qobuz_id: str = Query(...), title: str = Query(""), description: str = Query(""), image: str = Query(""), track_count: int = Query(0), duration: int = Query(0)):
    """Add a playlist to local tracking."""
    db = get_db()
    pid = db.add_playlist(qobuz_id, title, description, image, track_count, duration)
    return {"success": True, "id": pid}


# --- Subscriptions ---


@router.get("/api/subscriptions")
async def list_subscriptions():
    """Get all subscriptions."""
    db = get_db()
    return db.get_all_subscriptions()


@router.put("/api/subscriptions/{playlist_id}")
async def update_subscription(playlist_id: str, active: bool = Query(True)):
    """Update subscription settings."""
    db = get_db()
    db.update_subscription(playlist_id, active=int(active))
    return {"success": True}


# --- Jobs ---


@router.get("/api/jobs/active")
async def get_active_jobs():
    """Get currently running jobs."""
    db = get_db()
    return db.get_active_jobs()


@router.get("/api/jobs/recent")
async def get_recent_jobs(limit: int = 50):
    """Get recent completed jobs."""
    db = get_db()
    return db.get_recent_jobs(limit)


@router.get("/api/jobs/{job_id}")
async def get_job(job_id: int):
    """Get job details."""
    db = get_db()
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/api/jobs/cancel")
async def cancel_download():
    """Cancel the active download."""
    svc = get_service()
    result = svc.cancel_download()
    return {"cancelled": result}


# --- Settings ---


@router.get("/api/settings")
async def get_settings():
    """Get all settings."""
    db = get_db()
    return db.get_all_settings()


@router.put("/api/settings")
async def update_settings(settings: dict):
    """Update settings."""
    db = get_db()
    svc = get_service()

    for key, value in settings.items():
        db.set_setting(key, str(value))

    # If Qobuz credentials changed, invalidate API client
    if any(k in settings for k in ["qobuz_email", "qobuz_password", "qobuz_app_id", "qobuz_app_secret"]):
        svc.invalidate_api()

    return {"success": True}


# --- Logs ---


@router.get("/api/logs")
async def get_logs(limit: int = 200, job_id: int | None = None):
    """Get application logs."""
    db = get_db()
    return db.get_logs(limit, job_id)


@router.delete("/api/logs")
async def clear_logs(days: int = 7):
    """Clear old logs."""
    db = get_db()
    db.clear_logs(days)
    return {"success": True}


# --- SSE Stream ---


@router.get("/api/stream")
async def sse_stream():
    """Server-Sent Events stream for real-time updates."""

    async def event_stream():
        buffer = []
        flush_event = asyncio.Event()

        def on_event(event: str, data: dict):
            buffer.append(f"event: {event}\ndata: {json.dumps(data)}\n\n")
            flush_event.set()

        svc = get_service()
        svc.add_sse_callback(on_event)

        # Send initial connection event
        yield f"event: connected\ndata: {{'timestamp': {time.time()}}}\n\n"

        try:
            while True:
                flush_event.wait()
                while buffer:
                    yield buffer.pop(0)
                flush_event.clear()
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        finally:
            if on_event in svc._sse_callbacks:
                svc._sse_callbacks.remove(on_event)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
