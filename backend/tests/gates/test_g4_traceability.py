"""G4 — unit=claim traceability. Every node/edge carries ≥1 claim_id resolving to a real claim→doc_ref.

This is the structural form of "one click to truth" (master §1 #5, §5). Resolution edges
(``same-as``/``distinct-from``) are exempt — they cite a merge decision, not a claim — but every
*assertion* node/edge must trace to evidence.
"""

from __future__ import annotations

from tests.fixtures import loaders

_RESOLUTION_EDGE_TYPES = {"same-as", "distinct-from"}


def test_every_node_and_assertion_edge_cites_a_real_claim() -> None:
    view = loaders.golden_view()
    claims_by_id = {c.claim_id: c for c in loaders.golden_evidence_log().replay()}

    def resolves_to_a_doc(cid: str) -> bool:
        claim = claims_by_id.get(cid)
        return claim is not None and len(claim.doc_refs()) >= 1 and all(r.file for r in claim.doc_refs())

    for n in view.nodes:
        assert n.claim_ids, f"node {n.id} has no claim_ids (naked assertion)"
        assert all(resolves_to_a_doc(c) for c in n.claim_ids), f"node {n.id} cites a non-existent claim"

    for e in view.edges:
        if e.type in _RESOLUTION_EDGE_TYPES:
            continue
        assert e.claim_ids, f"edge {e.id} has no claim_ids (naked assertion)"
        assert all(resolves_to_a_doc(c) for c in e.claim_ids), f"edge {e.id} cites a non-existent claim"
