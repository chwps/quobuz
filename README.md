# Quobuz

Qobuz playlist downloader avec WebUI — télécharge, organise et sync automatiquement tes playlists Qobuz en qualité FLAC.

![Quobuz](https://img.shields.io/badge/Port-3420-blue)
![Docker](https://img.shields.io/badge/Docker-chwps%2Fquobuz-orange)

## Docker (recommandé)

```bash
# 1. Pull l'image
docker pull ghcr.io/chwps/quobuz:latest

# 2. Configurer
mkdir -p quobuz
cd quobuz
cp /path/to/quobuz/.env.example .env
# Éditer .env (ou laisser les valeurs par défaut)

# 3. Lancer
docker run -d \
  --name quobuz \
  -p 3420:3420 \
  -v $(pwd)/quobuz_data:/app/quobuz_data \
  -v $(pwd)/Music/Qobuz:/app/Music/Qobuz \
  --env-file .env \
  --restart unless-stopped \
  ghcr.io/chwps/quobuz:latest

# 4. Accéder à la WebUI
# http://localhost:3420
```

### Docker Compose

```yaml
services:
  quobuz:
    image: ghcr.io/chwps/quobuz:latest
    container_name: quobuz
    ports:
      - "3420:3420"
    volumes:
      - ./quobuz_data:/app/quobuz_data
      - ./Music/Qobuz:/app/Music/Qobuz
    env_file:
      - .env
    restart: unless-stopped
```

```bash
docker compose up -d
```

## Configuration

### Variables d'environnement (.env)

| Variable | Défaut | Description |
|----------|--------|-------------|
| `QOBUZ_EMAIL` | *vide* | Email Qobuz (aussi configurable WebUI) |
| `QOBUZ_PASSWORD` | *vide* | Mot de passe Qobuz (aussi configurable WebUI) |
| `QOBUZ_QUALITY` | `6` | Qualité: 5=MP3, 6=FLAC CD, 7=Hi-Res, 27=Hi-Res Ultra |
| `SYNC_SCHEDULE` | `0 */6 * * *` | Cron pour sync auto (seul paramètre cron en ENV) |
| `OUTPUT_DIR` | `/app/Music/Qobuz` | Répertoire de sortie |
| `DATA_DIR` | `/app/quobuz_data` | Répertoire de données |
| `WEBUI_DIR` | `/app/webui_build` | Répertoire du build React (hors DATA_DIR) |
| `API_KEY` | *vide* | Clé API optionnelle |
| `LOG_LEVEL` | `INFO` | DEBUG, INFO, WARNING, ERROR |

### Configuration via WebUI (recommandé)

La majorité des paramètres sont configurables directement depuis l'interface web :
- **Qualité audio** : MP3 320 / FLAC CD / FLAC Hi-Res / FLAC Hi-Res Ultra
- **Organisation des dossiers** : format des dossiers et fichiers
- **Options de téléchargement** : skip existants, covers, fichiers M3U
- **Authentification Qobuz** : email + mot de passe
- **Planification** : fréquence de synchronisation automatique

## Qualité audio

| ID | Format | Détails |
|----|--------|---------|
| 5 | MP3 320kbps | Qualité standard |
| 6 | FLAC CD | 16-bit / 44.1kHz |
| 7 | FLAC Hi-Res | 24-bit / ≤96kHz |
| 27 | FLAC Hi-Res Ultra | 24-bit / >96kHz |

## Architecture

```
quobuz/
├── packages/core/     # API Qobuz, download, tagging
├── packages/api/      # FastAPI server, scheduler, SSE
├── web/               # React SPA (HeroUI + TanStack Router)
├── Dockerfile         # Multi-stage build
└── docker-compose.yaml
```

## Développement local

```bash
# Backend
cd packages/core && pip install -e .
cd ../api && pip install -e .
python -m quobuz_api

# Frontend
cd web && npm install && npm run dev
```

## Docker Hub

L'image est automatiquement construite et publiée sur [GitHub Container Registry](https://github.com/chwps/quobuz/pkgs/container/quobuz) à chaque push sur `main`.

**Tags disponibles :**
- `latest` — dernière version de `main`
- `vX.Y.Z` — version spécifique
- `sha-<hash>` — commit spécifique

## Features

- ✅ Téléchargement playlists Qobuz en FLAC natif
- ✅ Organisation automatique par artiste/album
- ✅ Tagging complet + couverture intégrée
- ✅ Sync automatique configurable (cron)
- ✅ Skip des fichiers existants
- ✅ Génération M3U
- ✅ WebUI moderne (HeroUI + Tailwind)
- ✅ Temps réel (SSE) pour suivi des téléchargements
- ✅ Gestion des playlists favorites et abonnements
- ✅ Extraction automatique des credentials Qobuz
- ✅ Image Docker multi-arch (AMD64 + ARM64)
