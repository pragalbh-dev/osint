# `app_skeleton/` — Chanakya OSINT walking skeleton (Session X0)

A **self-contained** FastAPI + placeholder-SPA app that exists only to stand up
and prove the deploy pipeline (image → GHCR → `docker compose` on EC2 →
Cloudflare Tunnel → https URL) **before any feature work, while failures are
cheap** (master plan §7; `md/06` M-TIMELINE-1).

## Why it's self-contained

X0 shares **no code** with F0. This app carries its **own minimal deps**
(`requirements.txt`: fastapi + uvicorn only) and **must not import `chanakya/`**.
That keeps the two Wave-0 sessions (F0, X0) conflict-free and lets the skeleton
boot before any spine code exists. **SHIP** reconciles this skeleton into the
production image (`Dockerfile`/`docker-compose.yml` are `X0(skeleton) →
SHIP(production)` in the ownership map).

## What it serves

| Route | Response |
|-------|----------|
| `GET /health` | `200 {"status": "ok"}` — readiness gate for compose/tunnel |
| `GET /` | the built placeholder SPA ("it boots"), via `StaticFiles` |

## Layout

```
app_skeleton/
  requirements.txt     # fastapi + uvicorn (minimal, NOT F0's pyproject.toml)
  main.py              # FastAPI: /health + StaticFiles mount for the SPA
  .dockerignore        # keep node_modules/dist out of the build context
  web/                 # minimal Vite build (vanilla JS) -> dist/ static bundle
    package.json
    package-lock.json
    vite.config.js
    index.html
    src/main.js
    src/style.css
```

## Run it

- **Whole image (what EC2 runs):** from the repo root,
  `docker compose up --build app` → http://127.0.0.1:8000
- **Python only (dev, no Node build):** `pip install -r requirements.txt && uvicorn main:app`
  (serves the inline fallback page + `/health`; build `web/` for the real SPA).
- **SPA only (dev):** `cd web && npm ci && npm run dev`.

See `deploy/README.md` for the full GHCR + EC2 + tunnel runbook.
