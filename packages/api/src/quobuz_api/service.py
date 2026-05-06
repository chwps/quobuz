"""Download service — manages Qobuz downloads with progress tracking."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Callable

from quobuz_core import (
    DownloadConfig,
    DownloadService,
    DownloadStats,
    QobuzAPI,
    QobuzQuality,
)

from .database import Database

logger = logging.getLogger(__name__)

# SSE event callbacks
EventCallback = Callable[[str, dict], None]


class QuobuzDownloadService:
    """Service layer — coordinates API client, downloads, and DB updates."""

    def __init__(self, db: Database, settings):
        self.db = db
        self.settings = settings
        self._api: QobuzAPI | None = None
        self._sse_callbacks: list[EventCallback] = []
        self._active_download: asyncio.Task | None = None

    def add_sse_callback(self, callback: EventCallback):
        self._sse_callbacks.append(callback)

    def _emit(self, event: str, data: dict):
        """Emit SSE event to all connected clients."""
        for cb in self._sse_callbacks:
            try:
                cb(event, data)
            except Exception:
                pass

    def _log_sse(self, message: str, job_id: int | None = None):
        """Log message and emit SSE event."""
        logger.info(message)
        self.db.add_log(message, job_id=job_id)
        self._emit("log", {"message": message, "job_id": job_id})

    def _get_api(self) -> QobuzAPI:
        """Get or create authenticated API client."""
        if self._api is None:
            self._api = QobuzAPI(
                app_id=self.db.get_setting("qobuz_app_id", self.settings.qobuz_app_id),
                app_secret=self.db.get_setting("qobuz_app_secret", self.settings.qobuz_app_secret),
                email=self.db.get_setting("qobuz_email", self.settings.qobuz_email),
                password=self.db.get_setting("qobuz_password", self.settings.qobuz_password),
            )
        return self._api

    def invalidate_api(self):
        """Force API client recreation (after settings change)."""
        self._api = None

    async def authenticate(self) -> dict:
        """Authenticate with Qobuz."""
        api = self._get_api()
        await api.authenticate()
        self.invalidate_api()  # Refresh with new tokens
        return {"status": "authenticated"}

    async def get_user_info(self) -> dict:
        api = self._get_api()
        profile = await api.get_user_info()
        return {
            "email": profile.email,
            "firstname": profile.firstname,
            "lastname": profile.lastname,
            "display_name": profile.display_name,
            "country_name": profile.country_name,
            "avatar": profile.avatar,
        }

    async def get_playlists(self) -> list[dict]:
        api = self._get_api()
        playlists = await api.get_playlists()
        return [
            {
                "id": pl.id,
                "title": pl.title,
                "description": pl.description,
                "image": pl.image,
                "image_large": pl.image_large,
                "track_count": pl.track_count,
                "duration": pl.duration,
                "duration_formatted": pl.duration_formatted,
                "is_public": pl.is_public,
                "follower_count": pl.follower_count,
                "creator": pl.creator.name if pl.creator else "",
            }
            for pl in playlists
        ]

    async def get_playlist_tracks(self, playlist_id: str) -> dict:
        api = self._get_api()
        items = await api.get_playlist_tracks(playlist_id)
        return {
            "total": len(items),
            "tracks": [
                {
                    "id": item.track.id,
                    "title": item.track.title,
                    "duration": item.track.duration,
                    "duration_formatted": item.track.duration_formatted,
                    "track_number": item.track.track_number,
                    "disc_number": item.track.disc_number,
                    "artist": item.track.artist.name if item.track.artist else "",
                    "album": item.track.album.title if item.track.album else "",
                    "album_image": item.track.album.image_medium if item.track.album else "",
                }
                for item in items
            ],
        }

    async def start_download(self, playlist_qobuz_id: str) -> int:
        """Start a download job for a playlist. Returns job ID."""
        job_id = self.db.create_job(playlist_qobuz_id)

        async def _run():
            try:
                await self._execute_download(playlist_qobuz_id, job_id)
            except Exception as e:
                logger.error("Download failed: %s", e)
                self.db.update_job(job_id, status="failed", error=str(e), completed_at=f"datetime('now')")
                self._log_sse(f"Download failed: {e}", job_id)
                self._emit("job_complete", {"job_id": job_id, "status": "failed"})
            finally:
                self._active_download = None

        self._active_download = asyncio.create_task(_run())
        return job_id

    async def _execute_download(self, playlist_qobuz_id: str, job_id: int):
        """Execute a download job with progress tracking."""
        quality_id = int(self.db.get_setting("qobuz_quality", "6"))
        quality = QobuzQuality(quality_id)

        output_dir = self.db.get_setting("output_dir", str(self.settings.output_dir))
        skip_existing = self.db.get_setting("download_skip_existing", "true").lower() == "true"
        download_covers = self.db.get_setting("download_covers", "true").lower() == "true"
        create_m3u = self.db.get_setting("download_m3u", "true").lower() == "true"
        folder_format = self.db.get_setting("folder_format", self.settings.folder_format)
        filename_format = self.db.get_setting("filename_format", self.settings.filename_format)

        config = DownloadConfig(
            output_dir=output_dir,
            quality=quality,
            skip_existing=skip_existing,
            download_covers=download_covers,
            create_m3u=create_m3u,
            folder_format=folder_format,
            filename_format=filename_format,
        )

        def on_progress(stats: DownloadStats):
            self.db.update_job(
                job_id,
                total_tracks=stats.total_tracks,
                downloaded=stats.downloaded,
                skipped=stats.skipped,
                failed=stats.failed,
                progress=stats.percentage,
                current_track=stats.current_track.title if stats.current_track else "",
            )
            self._emit("progress", {
                "job_id": job_id,
                "progress": stats.percentage,
                "downloaded": stats.downloaded,
                "skipped": stats.skipped,
                "failed": stats.failed,
                "total": stats.total_tracks,
                "current_track": stats.current_track.title if stats.current_track else "",
            })

        def on_log(message: str):
            self._log_sse(message, job_id)

        api = self._get_api()
        service = DownloadService(api, config, on_progress=on_progress, on_log=on_log)

        self._log_sse(f"Starting download for playlist {playlist_qobuz_id}", job_id)
        stats = await service.download_playlist(playlist_qobuz_id)

        self.db.update_job(
            job_id,
            status="completed" if stats.failed == 0 else "partially_completed",
            completed_at=f"datetime('now')",
        )

        # Update subscription
        self.db.update_subscription(
            playlist_qobuz_id,
            last_downloaded=f"datetime('now')",
            download_count=self.db.get_subscription(playlist_qobuz_id).get("download_count", 0) + 1,
        )

        self._emit("job_complete", {"job_id": job_id, "status": self.db.get_job(job_id)["status"]})
        self._log_sse(f"Download complete: {stats.downloaded} downloaded, {stats.skipped} skipped, {stats.failed} failed", job_id)

    def cancel_download(self) -> bool:
        """Cancel the active download."""
        if self._active_download and not self._active_download.done():
            self._active_download.cancel()
            return True
        return False

    async def extract_bundle_config(self) -> dict:
        """Extract Qobuz app credentials from bundle."""
        api = QobuzAPI()
        config = await api.extract_bundle_config()
        return {
            "app_id": config.app_id,
            "app_secret": config.app_secret,
        }
