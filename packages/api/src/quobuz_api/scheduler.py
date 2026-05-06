"""Sync scheduler — APScheduler-based periodic playlist sync."""

from __future__ import annotations

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .database import Database

logger = logging.getLogger(__name__)


class SyncScheduler:
    """Manages periodic sync jobs for subscribed playlists."""

    def __init__(self, db: Database, sync_handler):
        self.db = db
        self.sync_handler = sync_handler
        self.scheduler = AsyncIOScheduler()
        self._job = None

    def start(self, cron_expression: str):
        """Start the scheduler with the given cron expression."""
        self.stop()

        try:
            self.scheduler.add_job(
                self._run_sync,
                "cron",
                id="playlist_sync",
                replace_existing=True,
                **self._parse_cron(cron_expression),
            )
            self.scheduler.start()
            logger.info("Sync scheduler started: %s", cron_expression)
        except Exception as e:
            logger.error("Failed to start scheduler: %s", e)

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Sync scheduler stopped")

    def _run_sync(self):
        """Run sync for all subscribed playlists."""
        subscriptions = self.db.get_all_subscriptions()
        active = [s for s in subscriptions if s.get("active", 1)]

        if not active:
            logger.info("No active subscriptions to sync")
            return

        logger.info("Running sync for %d subscribed playlists", len(active))

        for sub in active:
            playlist_id = sub["playlist_qobuz_id"]
            try:
                self.sync_handler(playlist_id)
            except Exception as e:
                logger.error("Sync failed for playlist %s: %s", playlist_id, e)

    @staticmethod
    def _parse_cron(expression: str) -> dict:
        """Parse a cron expression into APScheduler kwargs."""
        parts = expression.strip().split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {expression}")

        minute, hour, day, month, dow = parts

        return {
            "minute": minute,
            "hour": hour,
            "day": day,
            "month": month,
            "day_of_week": dow,
        }
