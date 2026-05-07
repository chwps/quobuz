FROM node:18-alpine AS webui-builder

WORKDIR /app/web

COPY web/package.json web/package-lock.json* ./

RUN npm install --legacy-peer-deps

COPY web/ ./

RUN npm run build

FROM python:3.11-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY packages/core/pyproject.toml packages/core/uv.lock* ./packages/core/
COPY packages/api/pyproject.toml packages/api/uv.lock* ./packages/api/
COPY packages/core/src ./packages/core/src
COPY packages/api/src ./packages/api/src

RUN if [ -f packages/core/uv.lock ]; then \
      uv pip sync packages/core/uv.lock packages/api/uv.lock; \
    else \
      uv pip install -e ./packages/core -e ./packages/api; \
    fi

ENV PYTHONPATH=/app
ENV DATA_DIR=/app/quobuz_data

RUN mkdir -p /app/quobuz_data/webui_build

COPY --from=webui-builder /app/web/dist /app/quobuz_data/webui_build

COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 3420

ENTRYPOINT ["/app/docker-entrypoint.sh"]
