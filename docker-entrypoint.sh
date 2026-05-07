#!/bin/sh
set -e

echo "=== Quobuz Playlist Downloader ==="
echo "Port: ${PORT:-3420}"
echo "Data: ${DATA_DIR:-/app/quobuz_data}"
echo "WebUI: ${WEBUI_DIR:-/app/webui_build}"
echo "Output: ${OUTPUT_DIR:-/music}"
echo "Sync: ${SYNC_SCHEDULE:-0 */6 * * *}"
echo ""

exec python -m uvicorn quobuz_api.app:create_app --factory \
    --host 0.0.0.0 \
    --port "${PORT:-3420}" \
    --log-level "${LOG_LEVEL:-info}"
