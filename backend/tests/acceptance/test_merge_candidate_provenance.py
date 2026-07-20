"""T10 on the REAL corpus — an identity call an analyst is asked to make must be checkable.

The merge card states "a source calls them the same · 0.70" and the analyst has to weigh *that source*
before merging. Identity assertions are consumed as merge signals rather than drawn as edges (D-2.5), so
the candidate ``same-as`` edge is the only place that evidence can hang — and ``GET /evidence/{edge_id}``
is what serves it. These pin the invariant, never a count: a data change may move which pairs are
proposed, but it must never make the ``source_asserted`` score and the citations behind it disagree.
"""

from __future__ import annotations

from chanakya.schemas import GraphView

SOURCE_ASSERTED = "source_asserted"


def _candidates(view: GraphView) -> list:
    return [e for e in view.edges if e.type == "same-as"]


def _source_asserted(edge) -> float:  # noqa: ANN001 — EdgeView, kept loose like the sibling suites
    breakdown = edge.attrs.get("breakdown") or {}
    return float(breakdown.get(SOURCE_ASSERTED) or 0.0)


def test_a_source_asserted_signal_always_cites_the_claims_that_make_it(view: GraphView) -> None:
    """Score above zero ⇒ the sentences behind it are on the edge. No unfalsifiable number."""
    scored = [e for e in _candidates(view) if _source_asserted(e) > 0]
    assert scored, "expected at least one candidate pair a source asserts an identity for"
    for edge in scored:
        assert edge.claim_ids, f"{edge.id} scores source_asserted but cites no claim"


def test_no_source_asserted_signal_means_no_citation_to_click(view: GraphView) -> None:
    """…and the converse, so the card can never offer a link that opens an empty drawer."""
    for edge in _candidates(view):
        if _source_asserted(edge) == 0:
            assert not edge.claim_ids, f"{edge.id} cites claims but scores no source_asserted signal"


def test_every_cited_identity_claim_resolves_to_an_exact_source_locator(scenario, view: GraphView) -> None:
    """The one-click-to-source non-negotiable, on the adjudication screen: file + span, not just an id."""
    claims = {c.claim_id: c for c in scenario.evidence.replay()}
    cited = [cid for e in _candidates(view) for cid in e.claim_ids]
    assert cited, "expected the corpus to assert at least one candidate identity out loud"
    for cid in cited:
        claim = claims.get(cid)
        assert claim is not None, f"candidate edge cites {cid}, which is not in the evidence log"
        refs = claim.doc_refs()
        assert refs and all(r.file for r in refs), f"{cid} has no readable source locator"
        assert claim.source_id, f"{cid} names no source — nothing for an analyst to weigh"
