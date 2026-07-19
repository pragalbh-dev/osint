"""``GET /health`` — the readiness gate (master §7, md/07).

Returns **503 until the boot ``rebuild()`` has completed**, then **200**. Cheap: no LLM, no rebuild on
call — it only reports the held state. The tunnel / container health check polls this to know the app is
serving a real view, not a half-initialised one.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from chanakya.api.routes.deps import get_state
from chanakya.api.state import AppState
from chanakya.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(response: Response, state: AppState = Depends(get_state)) -> HealthResponse:
    if not state.ready:
        response.status_code = 503
        return HealthResponse(status="starting", rebuilt=False)
    view = state.view()
    return HealthResponse(
        status="ok",
        rebuilt=True,
        node_count=len(view.nodes),
        edge_count=len(view.edges),
        config_version=state.config.version,
    )
