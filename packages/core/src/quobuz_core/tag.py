"""Audio file tagger — embed metadata and cover art in FLAC/MP3 files."""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from mutagen.flac import FLAC, Picture
from mutagen.id3 import ID3, APIC, COMM, TALB, TCON, TPE1, TPE2, TPOS, TRCK, TIT2, TXXX, USLT
from mutagen.mp3 import MP3

from .models import Track, QobuzQuality

logger = logging.getLogger(__name__)


class AudioTagger:
    """Tag audio files with metadata and embedded artwork."""

    FLAC_EXTENSIONS = {".flac"}
    MP3_EXTENSIONS = {".mp3"}

    @staticmethod
    async def tag_file(filepath: str | Path, track: Track, quality: QobuzQuality, cover_path: str | Path | None = None) -> None:
        """Tag an audio file with track metadata and optional cover art."""
        filepath = Path(filepath)
        ext = filepath.suffix.lower()

        try:
            if ext in AudioTagger.FLAC_EXTENSIONS:
                await asyncio.to_thread(AudioTagger._tag_flac, filepath, track, cover_path)
            elif ext in AudioTagger.MP3_EXTENSIONS:
                await asyncio.to_thread(AudioTagger._tag_mp3, filepath, track, cover_path)
            else:
                logger.warning("Unsupported file format for tagging: %s", ext)
        except Exception as e:
            logger.error("Failed to tag %s: %s", filepath.name, e)

    @staticmethod
    def _tag_flac(filepath: Path, track: Track, cover_path: Path | str | None = None) -> None:
        """Tag a FLAC file."""
        audio = FLAC(str(filepath))

        audio["TITLE"] = track.title
        audio["TRACKNUMBER"] = str(track.track_number)
        audio["TRACKTOTAL"] = str(track.track_number)  # Will be updated later
        audio["DISCNUMBER"] = str(track.disc_number)
        audio["DATE"] = str(track.album.release_date)[:4] if track.album and track.album.release_date else ""

        if track.artist and track.artist.name:
            audio["ARTIST"] = track.artist.name
        if track.album and track.album.title:
            audio["ALBUM"] = track.album.title
        if track.album and track.album.artist and track.album.artist.name:
            audio["ALBUMARTIST"] = track.album.artist.name

        if cover_path and Path(cover_path).exists():
            img_data = Path(cover_path).read_bytes()
            picture = Picture()
            picture.type = 3  # Front cover
            picture.mime = "image/jpeg" if Path(cover_path).suffix.lower() == ".jpg" else "image/png"
            picture.data = img_data
            audio.add_picture(picture)

        audio.save()
        logger.debug("Tagged FLAC: %s", filepath.name)

    @staticmethod
    def _tag_mp3(filepath: Path, track: Track, cover_path: Path | str | None = None) -> None:
        """Tag an MP3 file."""
        try:
            audio = ID3(str(filepath))
        except Exception:
            audio = ID3()
            audio.save(str(filepath))
            audio = ID3(str(filepath))

        audio.add(TIT2(encoding=3, text=track.title))
        audio.add(TRCK(encoding=3, text=str(track.track_number)))
        audio.add(TPOS(encoding=3, text=str(track.disc_number)))

        if track.artist and track.artist.name:
            audio.add(TPE1(encoding=3, text=track.artist.name))
        if track.album and track.album.title:
            audio.add(TALB(encoding=3, text=track.album.title))

        if cover_path and Path(cover_path).exists():
            img_data = Path(cover_path).read_bytes()
            mime = "image/jpeg" if Path(cover_path).suffix.lower() == ".jpg" else "image/png"
            audio.add(APIC(encoding=3, mime=mime, type=3, data=img_data))

        audio.save()
        logger.debug("Tagged MP3: %s", filepath.name)

    @staticmethod
    async def generate_m3u(album_dir: str | Path, tracks: list[Track], album_title: str) -> Path:
        """Generate an M3U playlist file for an album."""
        album_dir = Path(album_dir)
        m3u_path = album_dir / f"{album_title}.m3u"

        lines = ["#EXTM3U\n"]
        for track in sorted(tracks, key=lambda t: (t.disc_number, t.track_number)):
            safe_name = track.safe_filename()
            # Find the actual file
            files = list(album_dir.glob(f"{safe_name}*"))
            if files:
                filename = files[0].name
            else:
                filename = f"{track.track_number:02d} - {track.title}.flac"

            lines.append(f"#EXTINF:{track.duration},{track.artist.name if track.artist else ''} - {track.title}")
            lines.append(filename)

        m3u_path.write_text("\n".join(lines), encoding="utf-8")
        logger.debug("Generated M3U: %s", m3u_path.name)
        return m3u_path
