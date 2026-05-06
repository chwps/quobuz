"""Application settings — environment variables and defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    """Application settings from environment and config."""
    port: int = 3420
    data_dir: str = os.path.expanduser("~/quobuz_data")
    output_dir: str = os.path.expanduser("~/Music/Qobuz")
    sync_schedule: str = "0 */6 * * *"  # Every 6 hours by default
    api_key: str = ""
    log_level: str = "INFO"

    # Qobuz config (can be overridden in WebUI)
    qobuz_email: str = ""
    qobuz_password: str = ""
    qobuz_app_id: str = ""
    qobuz_app_secret: str = ""
    qobuz_quality: str = "6"  # FLAC CD quality by default

    # Download config (can be overridden in WebUI)
    download_skip_existing: bool = True
    download_covers: bool = True
    download_m3u: bool = True
    folder_format: str = "{album_artist}/{album_title}"
    filename_format: str = "{track_number:02d} - {title}"

    @classmethod
    def from_env(cls) -> Settings:
        """Load settings from environment variables."""
        return cls(
            port=int(os.getenv("PORT", "3420")),
            data_dir=os.getenv("DATA_DIR", os.path.expanduser("~/quobuz_data")),
            output_dir=os.getenv("OUTPUT_DIR", os.path.expanduser("~/Music/Qobuz")),
            sync_schedule=os.getenv("SYNC_SCHEDULE", "0 */6 * * *"),
            api_key=os.getenv("API_KEY", ""),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            qobuz_email=os.getenv("QOBUZ_EMAIL", ""),
            qobuz_password=os.getenv("QOBUZ_PASSWORD", ""),
            qobuz_app_id=os.getenv("QOBUZ_APP_ID", ""),
            qobuz_app_secret=os.getenv("QOBUZ_APP_SECRET", ""),
            qobuz_quality=os.getenv("QOBUZ_QUALITY", "6"),
            folder_format=os.getenv("FOLDER_FORMAT", "{album_artist}/{album_title}"),
            filename_format=os.getenv("FILENAME_FORMAT", "{track_number:02d} - {title}"),
        )
