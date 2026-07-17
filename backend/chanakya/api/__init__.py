"""API stage — the FastAPI app serving the view JSON + provenance + HITL/ingest/ask (owned by API).

F0 ships a stub. The API session builds the real app (endpoints in master §4.8), gating ``/health``
on a successful ``rebuild()`` and mounting the built SPA same-origin via ``StaticFiles`` (the frontend
seam). ``fastapi`` is imported lazily so importing this package (e.g. for the G9 import-boundary scan)
has no heavy side effects.

Frozen signature: ``create_app() -> FastAPI``.
"""

from __future__ import annotations

from typing import Any


def create_app() -> Any:
    """STUB: build the FastAPI app. API session implements all endpoints (master §4.8)."""
    raise NotImplementedError("API session builds the FastAPI application")
