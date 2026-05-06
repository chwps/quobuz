"""Qobuz data models — pydantic types for API responses."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class QobuzQuality(Enum):
    """Qobuz audio quality IDs — matches play.qobuz.com."""
    MP3_320 = 5
    FLAC_CD = 6
    FLAC_HIRES = 7
    FLAC_HIRES_ULTRA = 27


class QualityLabel(str):
    """Human-readable quality labels for UI display."""
    MP3_320 = "MP3 320kbps"
    FLAC_CD = "FLAC (16-bit / 44.1kHz)"
    FLAC_HIRES = "FLAC (Hi-Res ≤96kHz)"
    FLAC_HIRES_ULTRA = "FLAC (Hi-Res Ultra >96kHz)"


@dataclass(frozen=True)
class QualityMeta:
    """Quality metadata for display and UI."""
    id: int
    label: str
    extension: str
    priority: int  # for sorting — higher is better

    @classmethod
    def from_quality(cls, q: QobuzQuality) -> QualityMeta:
        labels = {
            QobuzQuality.MP3_320: ("MP3 320kbps", "mp3", 1),
            QobuzQuality.FLAC_CD: ("FLAC (16-bit / 44.1kHz)", "flac", 2),
            QobuzQuality.FLAC_HIRES: ("FLAC (Hi-Res ≤96kHz)", "flac", 3),
            QobuzQuality.FLAC_HIRES_ULTRA: ("FLAC (Hi-Res Ultra >96kHz)", "flac", 4),
        }
        label, ext, prio = labels[q]
        return cls(id=q.value, label=label, extension=ext, priority=prio)


@dataclass
class Artist:
    name: str
    image: str | None = None
    slug: str = ""

    @property
    def image_small(self) -> str:
        if not self.image:
            return ""
        return self._resize(50)

    @property
    def image_large(self) -> str:
        if not self.image:
            return ""
        return self._resize(800)

    def _resize(self, size: int) -> str:
        if not self.image:
            return ""
        base = self.image.split("@")[0].split("/")[-1]
        return f"https://static.qobuz.com/images/artists/{base}@{size}.jpg"


@dataclass
class Album:
    title: str
    url: str = ""
    upc: str = ""
    image: str | None = None
    artist: Artist | None = None
    label: str = ""
    release_date: str = ""
    genres: list[str] = field(default_factory=list)

    @property
    def image_small(self) -> str:
        if not self.image:
            return ""
        return self._resize(50)

    @property
    def image_medium(self) -> str:
        if not self.image:
            return ""
        return self._resize(250)

    @property
    def image_large(self) -> str:
        if not self.image:
            return ""
        return self._resize(800)

    def _resize(self, size: int) -> str:
        if not self.image:
            return ""
        base = self.image.split("@")[0].split("/")[-1]
        return f"https://static.qobuz.com/images/albums/{base}@{size}.jpg"


@dataclass
class Track:
    id: int
    title: str
    duration: int
    track_number: int = 0
    disc_number: int = 1
    has_lyrics: bool = False
    artist: Artist | None = None
    album: Album | None = None
    stream_url: str | None = None
    quality: QobuzQuality | None = None
    download_url: str | None = None
    explicit: bool = False

    @property
    def duration_formatted(self) -> str:
        m, s = divmod(self.duration, 60)
        return f"{m}:{s:02d}"

    def safe_filename(self) -> str:
        """Generate a safe filename for this track."""
        parts = [
            f"{self.track_number:02d}",
            self._clean(self.title),
        ]
        if self.artist and self.artist.name:
            parts.append(self._clean(self.artist.name))
        return "-".join(parts)

    def _clean(self, text: str) -> str:
        text = re.sub(r'[\\/*?:"<>|]', "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()


@dataclass
class Playlist:
    id: int
    title: str
    url: str = ""
    description: str = ""
    image: str | None = None
    upc: str = ""
    track_count: int = 0
    duration: int = 0
    is_public: bool = False
    user_id: int | None = None
    tags: list[str] = field(default_factory=list)

    @property
    def image_large(self) -> str:
        if not self.image:
            return ""
        return self.image.replace("-250x250", "-800x800").replace("250x250", "800x800")

    @property
    def duration_formatted(self) -> str:
        h = self.duration // 3600
        m = (self.duration % 3600) // 60
        return f"{h}h {m}min"


@dataclass
class UserPlaylist(Playlist):
    """Playlist owned/followed by a user, with owner info."""
    creator: Artist | None = None
    follower_count: int = 0


@dataclass
class UserProfile:
    email: str = ""
    firstname: str = ""
    lastname: str = ""
    country_id: int = 0
    country_name: str = ""
    avatar: str | None = None
    subscription: dict[str, Any] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        return f"{self.firstname} {self.lastname}".strip() or self.email


@dataclass
class PlaylistItem:
    """An item in a playlist (track + position)."""
    track: Track
    position: int = 0
    added_at: str = ""


@dataclass
class BundleConfig:
    """Parsed Qobuz app credentials from bundle.js."""
    app_id: str = ""
    app_secret: str = ""
    user_auth_token: str = ""
    source_token: str = ""
