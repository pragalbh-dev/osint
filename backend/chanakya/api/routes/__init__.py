"""Route registration — one ``APIRouter`` per endpoint group, wired onto the app in ``create_app``.

Routers are registered **before** the SPA static mount so the JSON API always wins over the catch-all
(see ``chanakya.api.spa``). Each module owns one slice of master §4.8.
"""

from __future__ import annotations

from fastapi import FastAPI

from chanakya.api.routes import ask, config, health, hitl, ingest, node, pending, view


def register_routes(app: FastAPI) -> None:
    """Include every JSON API router on ``app`` (call before mounting the SPA)."""
    app.include_router(health.router)
    app.include_router(view.router)
    app.include_router(node.router)
    app.include_router(ask.router)
    app.include_router(ingest.router)
    app.include_router(pending.router)
    app.include_router(hitl.router)
    app.include_router(config.router)
