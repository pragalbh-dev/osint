# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────────────────
# Chanakya OSINT — production image (Session SHIP; supersedes X0's walking skeleton).
#
# ONE artifact holds the whole demo, so `docker run` locally is byte-identical to what the EC2 box
# serves (dev == prod by construction, md/07 "Clean-deploy strategy"):
#
#   stage `web`      Node builds the real SPA (frontend/) → static assets, vendored map tiles included.
#   stage `runtime`  Python installs backend/ (the full pyproject dep set), then bakes in
#                    config/*.yaml (DATA-C), the frozen corpus/** and its pre-extracted claim bundles
#                    (INGEST), and the built SPA. No network, no key, no volume needed to boot.
#
# The app resolves config/ + corpus/ + frontend/dist relative to CHANAKYA_ROOT (chanakya/settings.py).
# The package is pip-installed into site-packages, so its default "walk up from __file__" root would
# land in site-packages — CHANAKYA_ROOT=/app is REQUIRED here, not decoration.
#
# Entry point is the FastAPI **factory** `chanakya.api.app:create_app`; uvicorn needs --factory. The
# boot rebuild() runs in the lifespan, so /health is 503 until the view is live, then 200 (master §7).
#
# Runtime writes (ingest / HITL / config edits) land in the in-process append-only logs, i.e. they are
# container-local and reset to the clean baseline on restart — by design (md/07 "Runtime writes").
#
#   Build:  docker build -t ghcr.io/pragalbh-dev/osint:latest .        (context = repo root)
#   Run:    docker run --rm -p 8000:8000 ghcr.io/pragalbh-dev/osint:latest
#   Or:     make run          (build + run + wait for /health — one command from a clean clone)
# ─────────────────────────────────────────────────────────────────────────────

# ---- Stage 1: build the real SPA to static assets ----
# Node pinned (build-break risk, md/07 "Risks & mitigations"); npm ci installs from the lockfile only.
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# vite build → /web/dist (index.html + hashed assets + public/tiles → dist/tiles; all offline).
RUN npm run build

# ---- Stage 2: Python builder — compile the deps that ship no wheel, into a self-contained venv ----
# `pdqhash` (INGEST's perceptual image hash, used by the recycled-imagery integrity flex) publishes no
# cp312 manylinux wheel, so it is built from source here. The toolchain stays in THIS stage; the runtime
# image below copies only the finished venv, so g++ never ships to production.
FROM python:3.12-slim-bookworm AS pybuild
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
# Manifest + package tree only (layer cache): the full pyproject dep set, no `[dev]` / `[gemini]` /
# `[ocr]` extras — keyless boot needs none of them.
COPY backend/pyproject.toml /src/backend/pyproject.toml
COPY backend/chanakya /src/backend/chanakya
RUN pip install --no-cache-dir /src/backend

# ---- Stage 3: Python runtime — serves the API and the built SPA same-origin, one process ----
FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    CHANAKYA_ROOT=/app \
    CHANAKYA_DATA_DIR=/app/var/data
WORKDIR /app

COPY --from=pybuild /opt/venv /opt/venv

# The baked demo payload — everything the app reads at boot, all keyless:
#   config/  the pipeline YAMLs (credibility weights, ontology, observables, subject lenses, …)
#   corpus/  the frozen scenario documents AND corpus/scenarios/*/claims/** (pre-extracted bundles),
#            which the boot seed replays so the graph exists with no LLM call.
COPY config ./config
COPY corpus ./corpus
COPY --from=web /web/dist ./frontend/dist

# Non-root, with one writable dir for runtime scratch (settings.data_dir()).
RUN mkdir -p /app/var/data \
 && useradd --system --create-home --uid 10001 chanakya \
 && chown -R chanakya:chanakya /app/var
USER chanakya

EXPOSE 8000
# Readiness gate — 200 only once the boot rebuild() has landed (compose/tunnel poll the same path).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

# --factory: create_app() is a factory, not a module-level `app`. (X0's `main:app` never existed here.)
CMD ["uvicorn", "chanakya.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
