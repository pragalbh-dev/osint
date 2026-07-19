"""The app factory — the single deployable artifact (master §4.8, API.md scope 1).

One FastAPI + Uvicorn process, same-origin (so no CORS middleware), wrapping the F0 store + config store
+ ``rebuild()`` view and delegating the two LLM-touching endpoints (``/ask``, ``/ingest``) to ASK /
INGEST. The boot ``rebuild()`` runs in the background on startup so the server accepts connections
immediately and ``/health`` shows the honest 503→200 readiness transition (master §7).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

from chanakya.api.routes import register_routes
from chanakya.api.spa import mount_spa
from chanakya.api.state import AppState, build_default_state

_log = logging.getLogger("chanakya.api")


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Boot the held view in the background so startup never blocks the event loop; ``/health`` reports
    503 until the first ``rebuild()`` lands, then 200."""
    state: AppState = app.state.chanakya
    if not state.ready:
        try:
            await run_in_threadpool(state.boot)
        except Exception:  # noqa: BLE001 — a boot failure must leave /health at 503, not crash startup
            _log.exception("boot rebuild() failed — /health stays 503 until resolved")
    yield


def create_app(state: AppState | None = None) -> FastAPI:
    """Build the FastAPI app. Pass a pre-built (optionally pre-booted) ``AppState`` for tests; otherwise
    a keyless default state is assembled and booted on startup."""
    app = FastAPI(title="Chanakya OSINT", version="0.1.0", lifespan=_lifespan)
    app.state.chanakya = state if state is not None else build_default_state()
    register_routes(app)
    mount_spa(app)  # last: the SPA catch-all must not shadow the JSON API
    return app
