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

# ── Copy Python package manifests first (for layer caching) ──
COPY packages/core/pyproject.toml packages/core/uv.lock* ./packages/core/
COPY packages/api/pyproject.toml packages/api/uv.lock* ./packages/api/

# ── Copy source code ──
COPY packages/core/src ./packages/core/src
COPY packages/api/src ./packages/api/src

# ── Install Python dependencies ──
# --system: Docker = single process, no venv needed
# --break-system-packages: safety for Debian-based images with PEP 668
UV_FLAGS="--system --break-system-packages"

RUN if [ -f packages/core/uv.lock ]; then \
      uv pip install $UV_FLAGS \
        -r packages/core/uv.lock \
        -r packages/api/uv.lock \
        -e ./packages/core \
        -e ./packages/api; \
    else \
      uv pip install $UV_FLAGS \
        -e ./packages/core \
        -e ./packages/api; \
    fi

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
