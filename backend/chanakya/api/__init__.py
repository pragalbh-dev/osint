"""API stage — the FastAPI app serving the view JSON + provenance + HITL/ingest/ask (owned by API).

Thin HTTP layer over the merged Wave-1 modules (master §4.8): it re-derives no schema, owns no module
logic, and calls no LLM directly — ``/ask`` and ``/ingest`` delegate to ASK / INGEST. ``/health`` is
gated on a successful ``rebuild()``; the built SPA is mounted same-origin (the frontend seam).

``fastapi`` (and the route/state modules that import it) load lazily inside :func:`create_app`, so
``import chanakya.api`` stays side-effect-free for the structural import scans.

Frozen signature: ``create_app() -> FastAPI``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

    from chanakya.api.state import AppState

__all__ = ["create_app"]


def create_app(state: AppState | None = None) -> FastAPI:
    """Build the FastAPI application (master §4.8). ``state`` is an optional pre-built runtime state for
    tests; production passes nothing and a keyless default state is assembled + booted on startup."""
    from chanakya.api.app import create_app as _create_app

    return _create_app(state)
