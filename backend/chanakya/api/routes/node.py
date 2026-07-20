"""``GET /node/{id}`` — the node inspector (product/03 B) — and ``GET /evidence/{id}`` — the provenance
drawer (product/03 C). Both are pure reads off the held view + the evidence-log claim bodies.

``/node`` returns the resolved entity with its computed status/confidence/freshness/materiality;
``/evidence`` renders the "how do you know that?" breakdown for any assessed element (node/edge/event),
with claim clusters grouped by independence and **every cited claim resolved to its exact ``doc_ref``**
(claim → doc_ref: the one-click-to-source non-negotiable) *and* to the **verbatim text at that
locator** — a byte offset is a pointer, not a source, and an analyst must be able to read the
evidence without leaving the drawer (see ``chanakya.api.quotes``).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from chanakya.api.quotes import quotes_for
from chanakya.api.routes.deps import get_state
from chanakya.api.routes.lookup import find_assessed
from chanakya.api.state import AppState
from chanakya.schemas import NodeView, ProvenanceDrawer

router = APIRouter()


# Both id params use the ``:path`` converter: extraction mints descriptive ids that can contain
# ``/`` ("…Kala Chitta / Attock Cantt area"), and ASGI decodes %2F before routing — a plain
# single-segment param would 404 at the router before the handler ever sees the id.
@router.get("/node/{node_id:path}", response_model=NodeView)
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


@router.get("/evidence/{element_id:path}", response_model=ProvenanceDrawer)
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

    # "Who says so?" — the registry entry behind every cited source_id. A source id is an internal key
    # (``d17b_withheld_gap`` is a filename, not an attribution); the class + reliability grade that make
    # it readable live in config/sources.yaml, which no GET route previously exposed. Verbatim passthrough
    # of the registry entry: an id with no entry is omitted rather than described from guesswork.
    registry = state.config.snapshot().sources.as_map()
    sources = {cid: registry[cid] for cid in {c.source_id for c in claims} if cid in registry}

    return ProvenanceDrawer(
        subject_ref=element.id,
        status=element.status,
        confidence=element.confidence,
        freshness=element.freshness,
        clusters=element.supporting_claims,
        opposing_claims=element.opposing_claims,
        sufficiency=element.sufficiency,
        claims=claims,
        quotes=quotes_for(claims),
        sources=sources,
    )
