"""Chanakya OSINT — walking-skeleton app (Session X0).

Self-contained FastAPI app whose only job is to prove the deploy pipeline end to
end with a trivial payload:

  * ``GET /health`` -> ``200 {"status": "ok"}`` — the readiness gate the compose
    healthcheck and the tunnel hit.
  * ``GET /``        -> the built placeholder SPA ("it boots"), served via
    ``StaticFiles`` same-origin.

X0 invariant (see sessions/X0.md): this module MUST NOT import ``chanakya/`` or
anything from the F0 backend. X0 is independent of F0 so the two Wave-0 sessions
stay conflict-free and the skeleton boots before any spine code exists. SHIP
later reconciles this skeleton into the production image.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Chanakya OSINT — walking skeleton (X0)")

# The Node build stage emits the SPA here; the Python image COPYs it in.
WEB_DIST = Path(__file__).resolve().parent / "web" / "dist"


@app.get("/health")
def health() -> JSONResponse:
    """Readiness probe — 200 whenever the process is up and serving.

    SHIP later gates this on ``rebuild()`` completion; in X0 it is unconditional.
    """
    return JSONResponse({"status": "ok"})


if WEB_DIST.is_dir():
    # Serve the built SPA at "/". html=True returns index.html for "/".
    # Mounted AFTER the /health route so /health wins its exact path.
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="spa")
else:
    # Fallback so ``uvicorn main:app`` runs even before the Node build (local dev,
    # tests). The Docker image always has web/dist, so this branch is dev-only.
    @app.get("/", response_class=HTMLResponse)
    def placeholder() -> str:
        return (
            "<!doctype html><meta charset=utf-8>"
            "<title>Chanakya OSINT — skeleton</title>"
            "<body style='font-family:ui-monospace,monospace;background:#0a0e13;"
            "color:#d6e4f5;display:grid;place-items:center;height:100vh;margin:0'>"
            "<main style='text-align:center'><h1>Chanakya OSINT</h1>"
            "<p>Walking skeleton — it boots. (SPA not built; run the Node stage.)</p>"
            "<p><a style='color:#6db3ff' href='/health'>/health</a></p></main>"
        )
