# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────────────────
# Chanakya OSINT — walking-skeleton image (Session X0).
#
# Same SHAPE as the production image so SHIP can extend it in place: a Node stage
# builds the SPA to static assets; a Python stage installs the app's deps and
# serves the static bundle + the API same-origin under one Uvicorn process.
#
# Build context is ./app_skeleton (X0 is self-contained). SHIP repoints the
# context to the repo root to bake config/ + corpus/ + the seeded SQLite baseline
# + the real backend/, and swaps requirements.txt for backend/pyproject.toml.
#
#   Build:  docker build -f Dockerfile -t ghcr.io/pragalbh-dev/osint:skeleton app_skeleton
#   (or, simpler:)  docker compose build app
# ─────────────────────────────────────────────────────────────────────────────

# ---- Stage 1: build the placeholder SPA to static assets ----
FROM node:20-alpine AS web
WORKDIR /web
# Manifests first, for a layer-cached, reproducible install from the lockfile.
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build            # -> /web/dist

# ---- Stage 2: Python runtime that serves the static bundle + the API ----
FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /app
# X0 carries its OWN minimal deps — NOT F0's pyproject.toml.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py ./
COPY --from=web /web/dist ./web/dist
EXPOSE 8000
# Readiness gate: the compose/tunnel healthcheck hits /health.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
