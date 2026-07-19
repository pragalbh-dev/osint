"""``GET /node/{id}`` — the node inspector (product/03 B) — and ``GET /evidence/{id}`` — the provenance
drawer (product/03 C). Both are pure reads off the held view + the evidence-log claim bodies.

``/node`` returns the resolved entity with its computed status/confidence/freshness/materiality;
``/evidence`` renders the "how do you know that?" breakdown for any assessed element (node/edge/event),
with claim clusters grouped by independence and **every cited claim resolved to its exact ``doc_ref``**
(claim → doc_ref: the one-click-to-source non-negotiable).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from chanakya.api.routes.deps import get_state
from chanakya.api.routes.lookup import find_assessed
from chanakya.api.state import AppState
from chanakya.schemas import NodeView, ProvenanceDrawer

router = APIRouter()


@router.get("/node/{node_id}", response_model=NodeView)
def get_node(node_id: str, state: AppState = Depends(get_state)) -> NodeView:
    for node in state.view().nodes:
        if node.id == node_id:
            return node
    raise HTTPException(
        status_code=404,
        detail={
            "error": "unknown node id",
            "id": node_id,
            "hint": "if this id is an edge or event, use GET /evidence/{id} for its provenance drawer",
        },
    )


@router.get("/evidence/{element_id}", response_model=ProvenanceDrawer)
def get_evidence(element_id: str, state: AppState = Depends(get_state)) -> ProvenanceDrawer:
    element = find_assessed(state.view(), element_id)
    if element is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "unknown id",
                "id": element_id,
                "hint": "expected a node, edge, or event id from GET /view",
            },
        )

    # Resolve every referenced claim id (element + supporting clusters + opposing) to its full atom,
    # ordered + de-duplicated, so the drawer is one-click-to-source (claim → doc_ref).
    claims_map = state.claims_map()
    ordered_ids: list[str] = []
    seen: set[str] = set()
    for cid in element.claim_ids:
        if cid not in seen:
            seen.add(cid)
            ordered_ids.append(cid)
    for group in element.supporting_claims:
        for cid in group.claim_ids:
            if cid not in seen:
                seen.add(cid)
                ordered_ids.append(cid)
    for cid in element.opposing_claims:
        if cid not in seen:
            seen.add(cid)
            ordered_ids.append(cid)
    claims = [claims_map[cid] for cid in ordered_ids if cid in claims_map]

    return ProvenanceDrawer(
        subject_ref=element.id,
        status=element.status,
        confidence=element.confidence,
        freshness=element.freshness,
        clusters=element.supporting_claims,
        opposing_claims=element.opposing_claims,
        sufficiency=element.sufficiency,
        claims=claims,
    )
