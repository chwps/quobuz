"""Qobuz API client — authenticated requests to api.qobuz.com."""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone

import httpx

from .models import (
    Album,
    Artist,
    BundleConfig,
    Playlist,
    PlaylistItem,
    QobuzQuality,
    Track,
    UserPlaylist,
    UserProfile,
)

logger = logging.getLogger(__name__)

QOBUZ_API = "https://api.qobuz.com/api.json"
QOBUZ_DOMAIN = "https://play.qobuz.com"


class QobuzAuthError(Exception):
    """Authentication failed — check credentials."""


class QobuzAPIError(Exception):
    """API returned an error."""


class QobuzAPI:
    """Authenticated Qobuz API client."""

    def __init__(
        self,
        app_id: str = "",
        app_secret: str = "",
        user_auth_token: str = "",
        source_token: str = "",
        email: str = "",
        password: str = "",
        timeout: float = 30.0,
    ):
        self.app_id = app_id
        self.app_secret = app_secret
        self._user_auth_token = user_auth_token
        self._source_token = source_token
        self.email = email
        self.password = password
        self._client = httpx.Client(base_url=QOBUZ_API, timeout=timeout)
        self._country_id = 0
        self._user_id = 0

    def _get_credentials(self) -> dict:
        """Build the credential headers for API calls."""
        creds = {
            "app_id": str(self.app_id),
            "request_ts": str(int(datetime.now(timezone.utc).timestamp())),
            "method": "qobuz.oauthConsumerConsumer",
        }

        if self._user_auth_token:
            creds["user_auth"] = self._user_auth_token
            creds["user_auth_ts"] = creds["request_ts"]

        if self._source_token:
            creds["user_credential"] = self._source_token

        secret = self.app_secret
        payload_str = json.dumps(creds, separators=(",", ":"))
        sig_input = f"{payload_str}{secret}"
        creds["signature"] = hashlib.md5(sig_input.encode("utf-8")).hexdigest()

        return creds

    async def authenticate(self) -> dict:
        """Authenticate via email/password. Returns user info dict."""
        if not self.email or not self.password:
            raise QobuzAuthError("Email and password are required for authentication")

        params = {
            "app_id": self.app_id,
            "grant_type": "password",
            "username": self.email,
            "password": self.password,
        }
        url = f"{QOBUZ_DOMAIN}/api/v1/user/login"

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        if "user_auth_token" in data:
            self._user_auth_token = data["user_auth_token"]
            self._source_token = data.get("source_token", "")
            logger.info("Authenticated as %s", self.email)
        elif "message" in data:
            raise QobuzAuthError(data["message"])
        else:
            raise QobuzAuthError("Unexpected auth response")

        return data

    async def get_user_info(self) -> UserProfile:
        """Get current user profile."""
        data = await self._request("user/getCurrent", {})
        profile = UserProfile(
            email=data.get("email", ""),
            firstname=data.get("firstname", ""),
            lastname=data.get("lastname", ""),
            country_id=data.get("country_id", 0),
            country_name=data.get("country", {}).get("name", ""),
            avatar=data.get("avatar", ""),
            subscription=data.get("subscription", {}),
        )
        self._country_id = data.get("country_id", 0)
        return profile

    async def get_playlists(self) -> list[UserPlaylist]:
        """Get user's playlists (owned + followed)."""
        results = []

        for method in ["playlist/listMyPlaylists", "playlist/listFollowedPlaylists"]:
            offset = 0
            limit = 100
            while True:
                data = await self._request(method, {"offset": offset, "limit": limit})
                items = data.get("playlists", [])
                if not items:
                    break
                for item in items:
                    pl = self._parse_playlist(item)
                    creator_raw = item.get("user", {}) or item.get("creator", {})
                    if creator_raw:
                        pl.creator = Artist(
                            name=creator_raw.get("name", ""),
                            image=creator_raw.get("image", creator_raw.get("picture", "")),
                        )
                    results.append(pl)
                offset += limit
                if offset > 1000:
                    break

        return results

    async def get_playlist_tracks(self, playlist_id: str | int) -> list[PlaylistItem]:
        """Get all tracks in a playlist with full details."""
        tracks = []
        offset = 0
        limit = 100

        while True:
            data = await self._request(
                "playlist/get",
                {"playlist_id": str(playlist_id), "offset": offset, "limit": limit},
            )
            items = data.get("playlist", {}).get("tracks", {}).get("items", [])
            if not items:
                break

            track_ids = [t["id"] for t in items]
            track_details = await self.get_tracks(track_ids)
            detail_map = {t.id: t for t in track_details}

            for idx, item in enumerate(items):
                tid = item["id"]
                if tid in detail_map:
                    track = detail_map[tid]
                else:
                    track = self._parse_track(item)
                tracks.append(PlaylistItem(track=track, position=idx))

            offset += limit
            if offset > 10000:
                break

        return tracks

    async def get_tracks(self, track_ids: list[int], quality: QobuzQuality | None = None) -> list[Track]:
        """Get detailed info for multiple tracks."""
        ids_str = ",".join(str(t) for t in track_ids)
        params = {"track_ids": ids_str}
        if quality:
            params["format"] = str(quality.value)

        data = await self._request("track/getListFromIds", params)
        items = data.get("tracks", [])
        return [self._parse_track(t) for t in items]

    async def get_stream_url(self, track_id: int, quality: QobuzQuality) -> str | None:
        """Get the signed download URL for a track at given quality."""
        params = {"track_id": str(track_id), "format": str(quality.value)}

        try:
            data = await self._request("track/getFileUrl", params)
            return data.get("flow_url") or data.get("file_url")
        except QobuzAPIError as e:
            logger.warning("Could not get stream URL for track %d: %s", track_id, e)
            return None

    async def extract_bundle_config(self) -> BundleConfig:
        """Extract app_id, app_secret, tokens from play.qobuz.com bundle.js."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{QOBUZ_DOMAIN}/config.json")
            resp.raise_for_status()
            config = resp.json()

        bundle = BundleConfig()

        # Try multiple patterns from the config
        app_config = config.get("app", {})
        qobuz_config = config.get("qobuz", {})
        api_config = config.get("api", {})

        # Merge all config sources
        merged = {}
        merged.update(api_config)
        merged.update(qobuz_config)
        merged.update(app_config)

        # Direct keys
        bundle.app_id = str(merged.get("app-id", merged.get("appId", merged.get("app_id", ""))))
        bundle.app_secret = merged.get("app-secret", merged.get("appSecret", merged.get("app_secret", ""))) or ""
        bundle.user_auth_token = merged.get("user-auth-token", merged.get("userAuthToken", merged.get("user_auth_token", ""))) or ""
        bundle.source_token = merged.get("source-token", merged.get("sourceToken", merged.get("source_token", ""))) or ""

        # If we didn't get values from config.json, try to parse from main JS file
        if not bundle.app_id:
            try:
                resp = await client.get(f"{QOBUZ_DOMAIN}/static/js/main.js")
                resp.raise_for_status()
                content = resp.text
                bundle = self._parse_bundle_content(content)
            except Exception as e:
                logger.warning("Could not extract bundle config: %s", e)

        return bundle

    @staticmethod
    def _parse_bundle_content(content: str) -> BundleConfig:
        """Parse app_id and secrets from JavaScript bundle content."""
        config = BundleConfig()

        # Pattern 1: Object literal with app_id
        match = re.search(r'app_id["\':]\s*["\'](\d+)["\']', content)
        if match:
            config.app_id = match.group(1)

        # Pattern 2: app-secret / appSecret
        for pattern in [
            r'app[_-]?secret["\':]\s*["\']([^"\']+)["\']',
            r'appSecret["\':]\s*["\']([^"\']+)["\']',
        ]:
            match = re.search(pattern, content)
            if match:
                config.app_secret = match.group(1)
                break

        return config

    async def _request(self, method: str, params: dict) -> dict:
        """Make an authenticated API request."""
        creds = self._get_credentials()
        params = {**creds, "page": "1", **params}

        async with httpx.AsyncClient(
            base_url=QOBUZ_API, timeout=30.0
        ) as client:
            resp = await client.get(method, params=params)
            resp.raise_for_status()
            data = resp.json()

        status = data.get("status", {})
        if isinstance(status, dict):
            code = status.get("code", 0)
        else:
            code = 0

        if code < 0:
            msg = status.get("text", "Unknown error") if isinstance(status, dict) else str(status)
            raise QobuzAPIError(f"API error {code}: {msg}")

        return data

    def _parse_artist(self, raw: dict) -> Artist:
        return Artist(
            name=raw.get("name", ""),
            image=raw.get("image", raw.get("picture", "")),
            slug=raw.get("slug", ""),
        )

    def _parse_album(self, raw: dict) -> Album:
        return Album(
            title=raw.get("title", ""),
            url=raw.get("url", ""),
            upc=raw.get("upc", ""),
            image=raw.get("image", raw.get("picture", "")),
            artist=self._parse_artist(raw.get("artist", {})),
            label=raw.get("label", {}).get("name", ""),
            release_date=raw.get("release_date", raw.get("releaseDate", "")),
        )

    def _parse_track(self, raw: dict) -> Track:
        return Track(
            id=raw.get("id", 0),
            title=raw.get("title", ""),
            duration=raw.get("duration", 0),
            track_number=raw.get("track_index", raw.get("trackNumber", 0)) or 0,
            disc_number=raw.get("disk_number", raw.get("discNumber", 1)) or 1,
            has_lyrics=raw.get("has_lyrics", raw.get("hasLyrics", False)),
            artist=self._parse_artist(raw.get("artist", {})),
            album=self._parse_album(raw.get("album", {})),
            explicit=raw.get("explicit_content", raw.get("explicit", False)),
        )

    def _parse_playlist(self, raw: dict) -> UserPlaylist:
        return UserPlaylist(
            id=raw.get("id", 0),
            title=raw.get("title", ""),
            url=raw.get("url", ""),
            description=raw.get("description", ""),
            image=raw.get("image", raw.get("picture", "")),
            upc=raw.get("upc", ""),
            track_count=raw.get("tracks_count", raw.get("trackCount", 0)) or raw.get("total_tracks", 0),
            duration=raw.get("total_time", raw.get("duration", 0)),
            is_public=raw.get("is_public", raw.get("isPublic", False)),
            follower_count=raw.get("followers_count", raw.get("followerCount", 0)),
        )
