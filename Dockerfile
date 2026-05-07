# ──────────────────────────────────────────────
# Stage 1 — Build WebUI (React + Vite)
# ──────────────────────────────────────────────
FROM node:18-alpine AS webui-builder

WORKDIR /app/web

COPY web/package.json web/package-lock.json* ./

# --legacy-peer-deps: @heroui/theme wants tailwindcss>=4 but project uses v3
RUN npm install --legacy-peer-deps

COPY web/ ./

RUN npm run build

# ──────────────────────────────────────────────
# Stage 2 — Runtime (Python + FastAPI + ffmpeg)
# ──────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# System deps: build tools (for mutagen native extensions) + ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
RUN pip install --no-cache-dir uv

WORKDIR /app

# ── Copy Python package manifests ──
COPY packages/core/pyproject.toml ./packages/core/
COPY packages/api/pyproject.toml ./packages/api/

# ── Copy source code ──
COPY packages/core/src ./packages/core/src
COPY packages/api/src ./packages/api/src

# ── Install Python dependencies ──
RUN uv pip install --system --break-system-packages \
    -e ./packages/core \
    -e ./packages/api

# ── Copy built WebUI ──
# Vite outDir: ../quobuz_data/webui_build (relative to /app/web)
COPY --from=webui-builder /app/quobuz_data/webui_build /app/quobuz_data/webui_build

# ── Copy entrypoint ──
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# ── Environment defaults ──
ENV PYTHONPATH=/app
ENV DATA_DIR=/app/quobuz_data

EXPOSE 3420

ENTRYPOINT ["/app/docker-entrypoint.sh"]
