"""``POST /hitl/{merge|status|alert}`` — analyst adjudication writeback (API.md scope 6; product/03 D).

The three ★ control points. Each endpoint reconstructs the review card from **live view state** (there is
no server-side queue endpoint in §4.8 — the card's effects preview reflects the *current* graph, not a
stale client snapshot), disposes it through the merged HITL service, and rebuilds. **No status is ever
set directly (G5):** ``dispose`` only appends a ``DecisionRecord``; the following
:meth:`AppState.rebuild_and_swap` lets ``rebuild()`` apply the recorded ``effects`` — so propagation is
structural and needs **no restart** (G12, §1 invariant 3). The response is the rebuilt view, so the UI
sees the propagated change in one round-trip.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from chanakya.api.routes.deps import get_state
from chanakya.api.routes.lookup import find_assessed
from chanakya.api.state import AppState
from chanakya.hitl import (
    bind_writeback,
    build_alert_disposition_item,
    build_merge_item,
    build_status_override_item,
    dispose,
)
from chanakya.schemas import GraphView, HitlDecision, ReviewQueueItem

router = APIRouter()

# One step along the confidence-magnitude ladder (spine/08 §3.4). Demote steps down, promote steps up;
# the ends are fixed points. Off-axis statuses (contradicted/stale/insufficient) default toward possible.
_DEMOTE = {"confirmed": "probable", "probable": "possible", "possible": "possible"}
_PROMOTE = {"possible": "probable", "probable": "confirmed", "confirmed": "confirmed"}


def _apply(state: AppState, item: ReviewQueueItem, decision: HitlDecision) -> GraphView:
    """Dispose the card → append the decision → rebuild so its effects propagate. Returns the new view."""
    if decision.decision not in item.options:
        raise HTTPException(
            400,
            detail={"error": "invalid decision", "decision": decision.decision, "options": item.options},
        )
    writeback = bind_writeback(item, state.decision, ts=state.now())
    dispose(item, decision.decision, writeback, actor=decision.actor, rationale=decision.rationale)
    state.rebuild_and_swap()
    return state.view()


@router.post("/hitl/status", response_model=GraphView)
def hitl_status(decision: HitlDecision, state: AppState = Depends(get_state)) -> GraphView:
    element = find_assessed(state.view(), decision.subject)
    if element is None:
        raise HTTPException(404, detail={"error": "unknown subject", "id": decision.subject})
    current = element.status
    item = build_status_override_item(
        item_id=decision.item_id or f"override:{decision.subject}",
        subject_ref=decision.subject,
        current_status=current,
        promote_to=_PROMOTE.get(current or "possible", "confirmed"),
        demote_to=_DEMOTE.get(current or "probable", "possible"),
        confidence=element.confidence.model_dump(mode="json") if element.confidence else None,
    )
    return _apply(state, item, decision)


@router.post("/hitl/alert", response_model=GraphView)
def hitl_alert(decision: HitlDecision, state: AppState = Depends(get_state)) -> GraphView:
    alert = next(
        (a for a in reversed(state.alerts) if decision.subject in (a.observable_id, a.subject)),
        None,
    )
    if alert is None:
        raise HTTPException(404, detail={"error": "no fired alert for subject", "id": decision.subject})
    item = build_alert_disposition_item(
        item_id=decision.item_id or f"alert:{alert.observable_id}",
        observable_id=alert.observable_id,
        subject_ref=alert.subject or alert.observable_id,
        before=alert.before,
        after=alert.after,
        severity=alert.severity,
    )
    view = _apply(state, item, decision)
    # Reflect the disposition on the in-memory feed so the UI shows it resolved (MONITOR reads the log).
    if decision.decision in ("real", "noise", "needs-more"):
        alert.disposition = decision.decision  # type: ignore[assignment]
    return view


@router.post("/hitl/merge", response_model=GraphView)
def hitl_merge(decision: HitlDecision, state: AppState = Depends(get_state)) -> GraphView:
    edge = next(
        (e for e in state.view().edges if e.id == decision.subject and e.type == "same-as"),
        None,
    )
    if edge is None:
        raise HTTPException(
            404, detail={"error": "no candidate same-as edge for subject", "id": decision.subject}
        )
    breakdown = edge.attrs.get("breakdown") or {}
    item = build_merge_item(
        item_id=decision.item_id or f"merge:{edge.id}",
        candidate_a={"id": edge.source},
        candidate_b={"id": edge.target},
        signals=[breakdown] if breakdown else [],
        merge_score=edge.merge_confidence or 0.0,
        band="needs-you",
    )
    return _apply(state, item, decision)
