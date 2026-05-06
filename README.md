# 🎵 Quobuz

**Qobuz playlist downloader** — Download, organize, and auto-sync your Qobuz playlists with a beautiful WebUI. Inspired by [yubal](https://github.com/guillevc/yubal) for YouTube Music.

![Port](https://img.shields.io/badge/port-3420-blue)
![Quality](https://img.shields.io/badge/quality-FLAC_Hi--Res-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

## Features

- 🎧 **Hi-Res Audio** — Download in MP3 320kbps up to FLAC Hi-Res Ultra (>96kHz)
- 📋 **Playlist Management** — Browse, subscribe, and download your Qobuz playlists
- 🔄 **Auto-Sync** — Scheduled cron-based sync for subscribed playlists
- 🎨 **WebUI** — Beautiful dark-themed dashboard with real-time progress
- 🏷️ **Auto-Tagging** — FLAC/MP3 files tagged with metadata + embedded cover art
- 📁 **Smart Organization** — Configurable folder/filename formats (e.g., `Artist/Album/01 - Title.flac`)
- ⚡ **Skip Existing** — Smart detection avoids re-downloading
- 🖼️ **Cover Art** — Automatically downloads and embeds album artwork
- 📊 **M3U Playlists** — Generates M3U files for each album
- 🔑 **Auto Credentials** — Extracts Qobuz app credentials automatically from their web player

## Quick Start

```bash
# Clone and configure
git clone https://github.com/chwps/quobuz.git
cd quobuz
cp .env.example .env

# Edit .env with your Qobuz credentials (optional — can also use WebUI)
nano .env

# Build and run
docker compose up -d --build

# Open http://localhost:3420
```

## Docker

### Single container (recommended)

```bash
docker run -d \
  --name quobuz \
  -p 3420:3420 \
  -v $(pwd)/quobuz_data:/app/quobuz_data \
  -v ~/Music/Qobuz:/music \
  -e SYNC_SCHEDULE="0 */6 * * *" \
  -e QOBUZ_EMAIL="your@email.com" \
  -e QOBUZ_PASSWORD="your_password" \
  chwps/quobuz:latest
```

### Docker Compose

```yaml
services:
  quobuz:
    build: .
    container_name: quobuz
    ports:
      - "3420:3420"
    volumes:
      - ./quobuz_data:/app/quobuz_data
      - ~/Music/Qobuz:/music
    env_file: .env
    restart: unless-stopped
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `3420` | Server port |
| `DATA_DIR` | `/app/quobuz_data` | Database and config storage |
| `OUTPUT_DIR` | `/music` | Download output directory |
| `SYNC_SCHEDULE` | `0 */6 * * *` | Cron expression for auto-sync |
| `LOG_LEVEL` | `INFO` | Logging level |
| `QOBUZ_EMAIL` | — | Qobuz account email |
| `QOBUZ_PASSWORD` | — | Qobuz account password |
| `QOBUZ_QUALITY` | `6` | Default quality (5/6/7/27) |

### WebUI Settings (all configurable in browser)

- **Qobuz Authentication** — Email, password, App ID, App Secret
- **Download Quality** — MP3 320, FLAC CD, FLAC Hi-Res, FLAC Hi-Res Ultra
- **Output Directory** — Where music files are saved
- **Folder Format** — `{album_artist}/{album_title}`, `{album_year}/{album_title}`, etc.
- **Filename Format** — `{track_number:02d} - {title}`, `{artist} - {title}`, etc.
- **Skip Existing** — Toggle on/off
- **Download Covers** — Toggle on/off
- **Create M3U** — Toggle on/off
- **Refresh Credentials** — Auto-extract App ID/Secret from Qobuz

### Audio Quality Options

| ID | Format | Description |
|----|--------|-------------|
| 5 | MP3 320kbps | Compressed, small files |
| 6 | FLAC 16-bit / 44.1kHz | CD Quality |
| 7 | FLAC Hi-Res ≤96kHz | Hi-Res Audio |
| 27 | FLAC Hi-Res Ultra >96kHz | Ultra Hi-Res |

### Folder Format Variables

- `{album_artist}` — Album artist name
- `{album_title}` — Album title
- `{album_year}` — Release year
- `{album_upc}` — UPC code

### Filename Format Variables

- `{track_number}` — Track number (use `:02d` for zero-padding)
- `{title}` — Track title
- `{artist}` — Track artist

## Architecture

```
quobuz/
├── packages/
│   ├── core/          # Qobuz API client, download, tagging
│   └── api/           # FastAPI server, SQLite, scheduler
├── web/               # React SPA (HeroUI + TanStack Router)
├── Dockerfile         # Multi-stage build (Node → Python)
├── docker-compose.yaml
└── .env.example
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | Authenticate with Qobuz |
| `GET` | `/api/auth/user` | Get user profile |
| `POST` | `/api/auth/refresh-credentials` | Auto-extract app credentials |
| `GET` | `/api/playlists` | List user playlists |
| `GET` | `/api/playlists/{id}/tracks` | Get playlist tracks |
| `POST` | `/api/playlists/{id}/subscribe` | Subscribe for auto-sync |
| `POST` | `/api/playlists/{id}/download` | Start download |
| `GET` | `/api/subscriptions` | List subscriptions |
| `GET` | `/api/jobs/active` | Active download jobs |
| `GET` | `/api/jobs/recent` | Recent job history |
| `GET` | `/api/settings` | Get all settings |
| `PUT` | `/api/settings` | Update settings |
| `GET` | `/api/logs` | Application logs |
| `GET` | `/api/stream` | SSE real-time stream |

## License

MIT
