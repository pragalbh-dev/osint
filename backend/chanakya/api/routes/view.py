"""``GET /view`` — the rebuilt knowledge graph as JSON (master §4.2/§4.3; product/03 B).

Serves the held view: nodes/edges/events with computed status, confidence breakdown, freshness,
independence-grouped supporting claims, opposing claims, sufficiency, and per-type/materiality attrs —
plus the accumulating alert feed and the Known Gaps. An optional ``?subject=`` applies F0's
``apply_lens`` (N-hops-from-anchors ∩ materiality filter) so a subject reads as a query-time lens and
distractors don't leak (§4.3, G10). No LLM, no mutation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from chanakya.api.routes.deps import get_state
from chanakya.api.state import AppState
from chanakya.schemas import GraphView
from chanakya.view import apply_lens

router = APIRouter()


@router.get("/view", response_model=GraphView)
def get_view(subject: str | None = None, state: AppState = Depends(get_state)) -> GraphView:
    view = state.view()
    if subject is None:
        return view
    lenses = state.config.snapshot().subjects.as_map()
    lens = lenses.get(subject)
    if lens is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "unknown subject lens",
                "subject": subject,
                "available_subjects": sorted(lenses),
            },
        )
    return apply_lens(view, lens)
