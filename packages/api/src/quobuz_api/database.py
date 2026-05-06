"""SQLite database — playlists, subscriptions, jobs, settings, logs."""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class Database:
    """SQLite database for persistent state."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        """Create tables if they don't exist."""
        with self.connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    qobuz_id TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    image_url TEXT DEFAULT '',
                    track_count INTEGER DEFAULT 0,
                    duration INTEGER DEFAULT 0,
                    last_synced TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    playlist_qobuz_id TEXT UNIQUE NOT NULL,
                    active INTEGER DEFAULT 1,
                    last_downloaded TEXT,
                    download_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now')),
                    FOREIGN KEY (playlist_qobuz_id) REFERENCES playlists(qobuz_id)
                );

                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    playlist_qobuz_id TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    total_tracks INTEGER DEFAULT 0,
                    downloaded INTEGER DEFAULT 0,
                    skipped INTEGER DEFAULT 0,
                    failed INTEGER DEFAULT 0,
                    progress REAL DEFAULT 0.0,
                    current_track TEXT DEFAULT '',
                    error TEXT DEFAULT '',
                    started_at TEXT,
                    completed_at TEXT,
                    FOREIGN KEY (playlist_qobuz_id) REFERENCES playlists(qobuz_id)
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT DEFAULT (datetime('now')),
                    level TEXT DEFAULT 'INFO',
                    message TEXT NOT NULL,
                    job_id INTEGER,
                    FOREIGN KEY (job_id) REFERENCES jobs(id)
                );

                CREATE INDEX IF NOT EXISTS idx_playlists_qobuz_id ON playlists(qobuz_id);
                CREATE INDEX IF NOT EXISTS idx_jobs_playlist ON jobs(playlist_qobuz_id);
                CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
                CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);
            """)

            # Insert default settings
            defaults = {
                "qobuz_email": "",
                "qobuz_password": "",
                "qobuz_app_id": "",
                "qobuz_app_secret": "",
                "qobuz_quality": "6",
                "output_dir": "~/Music/Qobuz",
                "download_skip_existing": "true",
                "download_covers": "true",
                "download_m3u": "true",
                "folder_format": "{album_artist}/{album_title}",
                "filename_format": "{track_number:02d} - {title}",
            }
            for key, value in defaults.items():
                conn.execute(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                    (key, value),
                )

    # --- Playlists ---

    def add_playlist(self, qobuz_id: str, title: str, description: str = "", image_url: str = "", track_count: int = 0, duration: int = 0) -> int:
        with self.connection() as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO playlists (qobuz_id, title, description, image_url, track_count, duration) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (qobuz_id, title, description, image_url, track_count, duration),
            )
            return cursor.lastrowid or self.get_playlist_id(qobuz_id)

    def get_playlist_id(self, qobuz_id: str) -> int:
        with self.connection() as conn:
            row = conn.execute("SELECT id FROM playlists WHERE qobuz_id = ?", (qobuz_id,)).fetchone()
            return row["id"] if row else 0

    def get_playlist(self, qobuz_id: str) -> dict | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM playlists WHERE qobuz_id = ?", (qobuz_id,)).fetchone()
            return dict(row) if row else None

    def get_all_playlists(self) -> list[dict]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM playlists ORDER BY updated_at DESC").fetchall()
            return [dict(r) for r in rows]

    def update_playlist(self, qobuz_id: str, **kwargs):
        if not kwargs:
            return
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [qobuz_id]
        with self.connection() as conn:
            conn.execute(f"UPDATE playlists SET {set_clause}, updated_at = datetime('now') WHERE qobuz_id = ?", values)

    def delete_playlist(self, qobuz_id: str):
        with self.connection() as conn:
            conn.execute("DELETE FROM subscriptions WHERE playlist_qobuz_id = ?", (qobuz_id,))
            conn.execute("DELETE FROM playlists WHERE qobuz_id = ?", (qobuz_id,))

    # --- Subscriptions ---

    def add_subscription(self, playlist_qobuz_id: str) -> int:
        with self.connection() as conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO subscriptions (playlist_qobuz_id) VALUES (?)",
                (playlist_qobuz_id,),
            )
            return cursor.lastrowid

    def get_subscription(self, playlist_qobuz_id: str) -> dict | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM subscriptions WHERE playlist_qobuz_id = ?", (playlist_qobuz_id,)).fetchone()
            return dict(row) if row else None

    def get_all_subscriptions(self) -> list[dict]:
        with self.connection() as conn:
            rows = conn.execute("""
                SELECT s.*, p.title, p.qobuz_id as playlist_qobuz_id_db
                FROM subscriptions s
                JOIN playlists p ON s.playlist_qobuz_id = p.qobuz_id
                ORDER BY s.created_at DESC
            """).fetchall()
            return [dict(r) for r in rows]

    def update_subscription(self, playlist_qobuz_id: str, **kwargs):
        if not kwargs:
            return
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [playlist_qobuz_id]
        with self.connection() as conn:
            conn.execute(f"UPDATE subscriptions SET {set_clause} WHERE playlist_qobuz_id = ?", values)

    def delete_subscription(self, playlist_qobuz_id: str):
        with self.connection() as conn:
            conn.execute("DELETE FROM subscriptions WHERE playlist_qobuz_id = ?", (playlist_qobuz_id,))

    # --- Jobs ---

    def create_job(self, playlist_qobuz_id: str, total_tracks: int = 0) -> int:
        with self.connection() as conn:
            cursor = conn.execute(
                "INSERT INTO jobs (playlist_qobuz_id, status, total_tracks, started_at) "
                "VALUES (?, 'running', ?, datetime('now'))",
                (playlist_qobuz_id, total_tracks),
            )
            return cursor.lastrowid

    def update_job(self, job_id: int, **kwargs):
        if not kwargs:
            return
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [job_id]
        with self.connection() as conn:
            conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values)

    def get_job(self, job_id: int) -> dict | None:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            return dict(row) if row else None

    def get_active_jobs(self) -> list[dict]:
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM jobs WHERE status = 'running' ORDER BY started_at DESC").fetchall()
            return [dict(r) for r in rows]

    def get_recent_jobs(self, limit: int = 50) -> list[dict]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE status != 'running' ORDER BY completed_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    # --- Settings ---

    def get_setting(self, key: str, default: str = "") -> str:
        with self.connection() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now')) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')",
                (key, value),
            )

    def get_all_settings(self) -> dict[str, str]:
        with self.connection() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            return {r["key"]: r["value"] for r in rows}

    # --- Logs ---

    def add_log(self, message: str, level: str = "INFO", job_id: int | None = None):
        with self.connection() as conn:
            conn.execute(
                "INSERT INTO logs (message, level, job_id) VALUES (?, ?, ?)",
                (message, level, job_id),
            )

    def get_logs(self, limit: int = 200, job_id: int | None = None) -> list[dict]:
        with self.connection() as conn:
            if job_id:
                rows = conn.execute(
                    "SELECT * FROM logs WHERE job_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (job_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]

    def clear_logs(self, days: int = 7):
        with self.connection() as conn:
            conn.execute("DELETE FROM logs WHERE timestamp < datetime('now', '-? days')", (days,))
