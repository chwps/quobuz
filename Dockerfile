# ---- Stage 1: Build React WebUI ----
FROM node:20-alpine AS webui-builder

WORKDIR /app/web
COPY web/package.json web/package-lock.json* ./
RUN npm install --production=false
COPY web/ ./
RUN npm run build

# ---- Stage 2: Python runtime ----
FROM python:3.11-slim AS runtime

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python deps
RUN pip install --no-cache-dir uv

# Copy Python packages
COPY packages/core/pyproject.toml packages/core/src/ ./packages/core/
COPY packages/api/pyproject.toml packages/api/src/ ./packages/api/

# Install with uv
RUN uv pip install --system ./packages/core ./packages/api

# Copy WebUI build
COPY --from=webui-builder /app/quobuz_data/webui_build /app/quobuz_data/webui_build

# Create data directory
RUN mkdir -p /app/quobuz_data

# Entry point
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

ENV PORT=3420
ENV DATA_DIR=/app/quobuz_data
ENV OUTPUT_DIR=/music
ENV SYNC_SCHEDULE="0 */6 * * *"

EXPOSE 3420

ENTRYPOINT ["./docker-entrypoint.sh"]
