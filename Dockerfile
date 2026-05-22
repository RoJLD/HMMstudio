# Stage 1: build the React frontend
FROM node:20-slim AS frontend-builder
WORKDIR /build
COPY src/hmm_studio/frontend/package.json src/hmm_studio/frontend/package-lock.json ./
RUN npm ci
COPY src/hmm_studio/frontend/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.12-slim AS runtime

# System deps for sklearn/numpy wheels on slim base
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy package metadata first to leverage Docker layer cache on deps
COPY pyproject.toml README.md ./
COPY src/ ./src/

# Install hmm-studio with the [web] extra (FastAPI + uvicorn + sqlmodel etc.)
RUN pip install --no-cache-dir -e ".[web]"

# Drop in the pre-built React assets where FastAPI's StaticFiles mount expects them
COPY --from=frontend-builder /build/dist/ /app/src/hmm_studio/server/static/

# Persistent data lives at /data/hmm-studio (mount a host volume here)
RUN mkdir -p /data/hmm-studio
ENV HMM_STUDIO_DB_PATH=/data/hmm-studio/studio.db \
    HMM_STUDIO_RESULTS_DIR=/data/hmm-studio/results \
    HMM_STUDIO_UPLOADS_DIR=/data/hmm-studio/uploads

EXPOSE 8000

# Healthcheck used by docker compose to gate startup
HEALTHCHECK --interval=10s --timeout=3s --retries=12 --start-period=15s \
    CMD curl -sf http://127.0.0.1:8000/health || exit 1

CMD ["hmm-studio", "--host", "0.0.0.0", "--port", "8000"]
