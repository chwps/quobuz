"""quobuz-core — Qobuz playlist downloader core library."""

from .api import QobuzAPI, QobuzAuthError, QobuzAPIError
from .download import DownloadService, DownloadStats
from .models import (
    QobuzQuality,
    QualityLabel,
    QualityMeta,
    Artist,
    Album,
    Track,
    Playlist,
    UserPlaylist,
    UserProfile,
    PlaylistItem,
    BundleConfig,
)

__all__ = [
    "QobuzAPI",
    "QobuzAuthError",
    "QobuzAPIError",
    "DownloadService",
    "DownloadStats",
    "QobuzQuality",
    "QualityLabel",
    "QualityMeta",
    "Artist",
    "Album",
    "Track",
    "Playlist",
    "UserPlaylist",
    "UserProfile",
    "PlaylistItem",
    "BundleConfig",
]

__version__ = "0.1.0"
