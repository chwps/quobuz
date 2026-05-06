"""Download service — HTTP download, file organization, and stats tracking."""

from __future__ import annotations

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import httpx

from .api import QobuzAPI
from .models import Album, Artist, Playlist, PlaylistItem, QobuzQuality, QualityMeta, Track
from .tag import AudioTagger

logger = logging.getLogger(__name__)


@dataclass
class DownloadStats:
    """Download progress tracking."""
    total_tracks: int = 0
    downloaded: int = 0
    skipped: int = 0
    failed: int = 0
    current_track: Track | None = None
    progress: float = 0.0
    speed: str = ""
    albums_created: int = 0

    @property
    def is_complete(self) -> bool:
        return self.downloaded + self.skipped + self.failed >= self.total_tracks > 0

    @property
    def percentage(self) -> float:
        if self.total_tracks == 0:
            return 0.0
        return (self.downloaded + self.skipped) / self.total_tracks * 100


@dataclass
class DownloadConfig:
    """Download configuration."""
    output_dir: str = "~/Music/Qobuz"
    quality: QobuzQuality = QobuzQuality.FLAC_CD
    skip_existing: bool = True
    download_covers: bool = True
    create_m3u: bool = True
    folder_format: str = "{album_artist}/{album_title}"
    filename_format: str = "{track_number:02d} - {title}"


class DownloadService:
    """Manages Qobuz track downloads with organization and tagging."""

    def __init__(
        self,
        api: QobuzAPI,
        config: DownloadConfig | None = None,
        on_progress: Callable[[DownloadStats], None] | None = None,
        on_log: Callable[[str], None] | None = None,
    ):
        self.api = api
        self.config = config or DownloadConfig()
        self.on_progress = on_progress
        self.on_log = on_log
        self.stats = DownloadStats()
        self._cancelled = False
        self._cover_cache: dict[str, Path] = {}

    def _log(self, message: str) -> None:
        logger.info(message)
        if self.on_log:
            self.on_log(message)

    def _progress(self) -> None:
        if self.on_progress:
            self.on_progress(self.stats)

    def _sanitize(self, text: str) -> str:
        """Sanitize filename/path components."""
        text = re.sub(r'[\\/*?:"<>|]', "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip().rstrip("/")

    def _get_album_path(self, artist: Artist, album: Album) -> Path:
        """Get the output path for an album based on folder format."""
        output = Path(self.config.output_dir).expanduser()

        artist_name = self._sanitize(artist.name) if artist else "Unknown Artist"
        album_title = self._sanitize(album.title) if album else "Unknown Album"

        folder = self.config.folder_format.format(
            album_artist=artist_name,
            album_title=album_title,
            album_year=str(album.release_date)[:4] if album.release_date else "",
            album_upc=album.upc,
        )

        return output / folder

    async def download_playlist(self, playlist_id: str | int) -> DownloadStats:
        """Download all tracks from a playlist, organized by album."""
        self._cancelled = False
        self.stats = DownloadStats()
        self._cover_cache = {}

        self._log(f"Fetching playlist {playlist_id}...")
        items = await self.api.get_playlist_tracks(playlist_id)
        self.stats.total_tracks = len(items)
        self._progress()

        if not items:
            self._log("No tracks found in playlist.")
            return self.stats

        # Group by album
        albums: dict[int, list[PlaylistItem]] = {}
        album_titles: dict[int, str] = {}
        album_artists: dict[int, Artist] = {}
        album_images: dict[int, str | None] = {}

        for item in items:
            album = item.track.album
            if not album:
                continue
            aid = album.id if hasattr(album, "id") else hash(album.title)
            albums.setdefault(aid, []).append(item)
            album_titles[aid] = album.title
            album_artists[aid] = album.artist or Artist(name="Unknown")
            album_images[aid] = album.image

        self._log(f"Playlist contains {len(items)} tracks across {len(albums)} albums.")

        # Download each album
        for aid, album_tracks in albums.items():
            if self._cancelled:
                self._log("Download cancelled.")
                break

            artist = album_artists.get(aid, Artist(name="Unknown"))
            title = album_titles.get(aid, "Unknown Album")
            image_url = album_images.get(aid)

            await self._download_album(artist, title, image_url, album_tracks, aid)

        self.stats.albums_created = len(albums)
        self._log(
            f"Done: {self.stats.downloaded} downloaded, "
            f"{self.stats.skipped} skipped, "
            f"{self.stats.failed} failed"
        )
        self._progress()
        return self.stats

    async def _download_album(
        self,
        artist: Artist,
        album_title: str,
        image_url: str | None,
        tracks: list[PlaylistItem],
        album_id: int,
    ) -> None:
        """Download all tracks for a single album."""
        album_path = self._get_album_path(artist, Album(title=album_title, artist=artist))
        album_path.mkdir(parents=True, exist_ok=True)

        self._log(f"Album: {artist.name} - {album_title}")

        # Download cover art
        cover_path = None
        if self.config.download_covers and image_url:
            cover_key = str(image_url)
            if cover_key not in self._cover_cache:
                cover_path = await self._download_cover(image_url, album_path, album_id)
                if cover_path:
                    self._cover_cache[cover_key] = cover_path
            else:
                cover_path = self._cover_cache[cover_key]

        # Download each track
        for item in tracks:
            if self._cancelled:
                break

            self.stats.current_track = item.track
            await self._download_track(item.track, album_path, cover_path)
            self._progress()

        # Generate M3U
        if self.config.create_m3u:
            album_track_list = [item.track for item in tracks]
            await AudioTagger.generate_m3u(album_path, album_track_list, album_title)

    async def _download_track(
        self,
        track: Track,
        album_path: Path,
        cover_path: Path | None = None,
    ) -> None:
        """Download and tag a single track."""
        quality = self.config.quality
        ext = QualityMeta.from_quality(quality).extension

        # Build output filename
        filename = self.config.filename_format.format(
            track_number=track.track_number,
            title=self._sanitize(track.title),
            artist=self._sanitize(track.artist.name) if track.artist else "",
        )
        output_file = album_path / f"{filename}.{ext}"

        # Skip existing
        if self.config.skip_existing and output_file.exists():
            self.stats.skipped += 1
            self._log(f"  SKIP: {track.title}")
            return

        # Get stream URL
        self._log(f"  Getting URL: {track.title}...")
        url = await self.api.get_stream_url(track.id, quality)

        if not url:
            self.stats.failed += 1
            self._log(f"  FAIL: {track.title} — no stream URL")
            return

        # Download
        self._log(f"  Downloading: {track.title}...")
        try:
            await self._http_download(url, output_file, ext)
            self.stats.downloaded += 1
            self._log(f"  OK: {track.title}")
        except Exception as e:
            self.stats.failed += 1
            self._log(f"  FAIL: {track.title} — {e}")
            if output_file.exists():
                output_file.unlink()
            return

        # Tag
        try:
            await AudioTagger.tag_file(output_file, track, quality, cover_path)
        except Exception as e:
            self._log(f"  WARN: Tagging failed for {track.title}: {e}")

    async def _download_cover(
        self,
        image_url: str,
        album_path: Path,
        album_id: int,
    ) -> Path | None:
        """Download album cover art."""
        # Try JPG first
        for ext in [".jpg", ".jpeg", ".png"]:
            cover_path = album_path / f"cover{ext}"
            if cover_path.exists():
                return cover_path

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(image_url)
                resp.raise_for_status()
                ext = ".jpg" if "image/jpeg" in resp.headers.get("content-type", "") else ".png"
                cover_path = album_path / f"cover{ext}"
                cover_path.write_bytes(resp.content)
                self._log(f"  Cover downloaded: {cover_path.name}")
                return cover_path
        except Exception as e:
            self._log(f"  Could not download cover: {e}")
            return None

    async def _http_download(self, url: str, filepath: Path, ext: str) -> None:
        """Download file with progress tracking."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))
                downloaded = 0

                with open(filepath, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=64 * 1024):
                        f.write(chunk)
                        downloaded += len(chunk)

    def cancel(self) -> None:
        """Signal the download to stop."""
        self._cancelled = True
        self._log("Cancelling download...")
