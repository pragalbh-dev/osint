"""``POST /ask`` — the cited multi-hop answer (product/03 E), delegated to the merged ASK agent.

The API adds **no reasoning**: it builds the ``(question, view, config, claims)`` call and forwards ASK's
validated output verbatim — the decomposed sub-questions, the ordered per-hop path with real per-hop
citations, the observed-vs-inferred tags (read from each claim's ``kind``), and — on an evidence gap —
the **first-class refusal payload** (what's-missing + ``next_coverage_due`` + the surfaced Known Gap),
never a fabricated assessment (the non-negotiable). ``ask()`` resolves its own LLM client (the live ReAct
planner if keyed — which reaches a multi-hop judgement via the general ``graph_analyze`` tool, no query
special-cased — or an honest capability refusal when keyless), so the API passes no ``llm``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from chanakya.agent import ask
from chanakya.api.routes.deps import get_state
from chanakya.api.state import AppState
from chanakya.schemas import AskAnswer, AskRequest
from chanakya.view import apply_lens

router = APIRouter()


@router.post("/ask", response_model=AskAnswer)
def post_ask(req: AskRequest, state: AppState = Depends(get_state)) -> AskAnswer:
    config = state.config.snapshot()
    view = state.view()
    if req.subject is not None:
        lens = config.subjects.as_map().get(req.subject)
        if lens is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "unknown subject lens",
                    "subject": req.subject,
                    "available_subjects": sorted(config.subjects.as_map()),
                },
            )
        view = apply_lens(view, lens, config=config)  # config enables registry/alias anchor tiers (AR-2)
    # claims map: the view cites claims by id; ASK needs the bodies for source/date/span + observed-vs-inferred.
    return ask(req.question, view, config, claims=state.claims_map())
