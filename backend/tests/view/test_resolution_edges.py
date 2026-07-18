"""rebuild() renders resolver decisions as edges (F0-amendment: candidate same-as + distinct-from).

Auto-merges collapse to one node (provenance stamped on the node); undecided HITL-band candidates +
explicit distinct-from surface as G4-exempt, never-scored edges carrying identity (never truth)
confidence (gate G5). These are the marquee "grain in the chaff, human in the loop" artifacts.
"""

from __future__ import annotations

import pytest

from chanakya.schemas import (
    ClaimRecord,
    ConfigBundle,
    DocRef,
    EntityDescriptor,
    GraphView,
    NodeView,
    Partition,
    ResolvedRef,
    Triple,
    pair_key,
)
from chanakya.view import pipeline
from chanakya.view.pipeline import _merge_provenance, _resolution_edges, rebuild


def test_resolution_edges_emitted_for_candidates_and_distinct() -> None:
    ids = {"ent:variant:hq9p", "ent:variant:ft2000", "ent:variant:hq9be"}
    ck = pair_key("ent:variant:hq9p", "ent:variant:ft2000")
    part = Partition(
        candidates=[("ent:variant:hq9p", "ent:variant:ft2000")],
        distinct_from=[("ent:variant:hq9p", "ent:variant:hq9be")],
        merge_confidence={ck: 0.72},
        merge_breakdown={ck: {"attribute": 0.9, "relational": 0.1, "total": 0.72}},
    )
    edges = _resolution_edges(ids, part)
    by_type = {e.type: e for e in edges}
    assert set(by_type) == {"same-as", "distinct-from"}

    sa = by_type["same-as"]
    assert sa.merge_confidence == 0.72
    assert sa.attrs["merge_band"] == "candidate"
    assert sa.attrs["breakdown"]["total"] == 0.72
    assert sa.status is None  # never scored (G5)
    assert sa.confidence is None  # no assertion_confidence on a resolution edge (G5)


def test_resolution_edge_skipped_when_endpoint_missing() -> None:
    part = Partition(candidates=[("a", "ghost")])
    assert _resolution_edges({"a"}, part) == []


def test_merge_provenance_stamped_on_canonical_node() -> None:
    nodes = {"canon": NodeView(id="canon", type="variant", claim_ids=["d1-l1"])}
    key = pair_key("member", "canon")
    part = Partition(
        same_as=[("member", "canon")],
        merge_confidence={key: 0.91},
        merge_breakdown={key: {"total": 0.91}},
    )
    _merge_provenance(nodes, part)
    assert nodes["canon"].attrs["resolved_from"] == [
        {"merged_ref": "member", "merge_confidence": 0.91, "breakdown": {"total": 0.91}}
    ]


def _entity_claim(cid: str, name: str) -> ClaimRecord:
    return ClaimRecord(
        claim_id=cid,
        source_id="src-x",
        doc_ref=DocRef(file="d1.txt", span=(0, 1)),
        kind="observation",
        asserts="entity",
        payload=EntityDescriptor(entity_type="variant", name=name),
    )


def test_merge_reconnects_edges_to_canonical_node() -> None:
    # An entity (var_fd2000) merges into var_hq9p; a triple about the merged-away entity must
    # reconnect to the canonical node, not dangle as an "unknown" node.
    entity = ClaimRecord(
        claim_id="d1-e1", source_id="s", doc_ref=DocRef(file="f", span=(0, 1)),
        kind="observation", asserts="entity",
        payload=EntityDescriptor(entity_type="variant", name="FD-2000"),
        resolved_ref=ResolvedRef(entity_id="var_hq9p"),  # RESOLVE rewrote it to canonical
    )
    edge = ClaimRecord(
        claim_id="d2-l1", source_id="s", doc_ref=DocRef(file="f", span=(0, 1)),
        kind="observation", asserts="relationship",
        payload=Triple(subject="var_fd2000", predicate="marketed-as", object="var_export"),
    )
    part = Partition(
        resolved_ref={"d1-e1": ResolvedRef(entity_id="var_hq9p")},
        same_as=[("var_fd2000", "var_hq9p")],
        entity_canonical={"var_fd2000": "var_hq9p"},
    )
    nodes, edges, _ = pipeline._assemble([entity, edge], part.entity_canonical)
    e = next(e for e in edges if e.type == "marketed-as")
    assert e.source == "var_hq9p"  # reconnected, not the merged-away "var_fd2000"
    assert "var_fd2000" not in {n.id for n in nodes.values()}


def test_assemble_identity_when_no_merges() -> None:
    # Empty merge map ⇒ endpoints untouched (the golden-path guarantee behind G2).
    edge = ClaimRecord(
        claim_id="d2-l1", source_id="s", doc_ref=DocRef(file="f", span=(0, 1)),
        kind="observation", asserts="relationship",
        payload=Triple(subject="a", predicate="rel", object="b"),
    )
    _, edges, _ = pipeline._assemble([edge], {})
    assert edges[0].source == "a" and edges[0].target == "b"


def test_resolve_receives_decisions(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def spy_resolve(claims, config, prev_view=None, decisions=None):  # type: ignore[no-untyped-def]
        seen["decisions"] = decisions
        return Partition()

    monkeypatch.setattr(pipeline, "resolve", spy_resolve)
    decision = {
        "event_id": "ev1", "ts": "2026-01-01", "actor": "analyst", "stage": "resolution",
        "type": "merge_adjudication", "subject_ref": "m1", "decision": {"accept": True},
    }
    from chanakya.schemas import DecisionRecord

    rebuild([], [DecisionRecord.model_validate(decision)], ConfigBundle())
    assert isinstance(seen["decisions"], list) and len(seen["decisions"]) == 1  # type: ignore[arg-type]


def test_rebuild_wires_in_candidate_edge(monkeypatch: pytest.MonkeyPatch) -> None:
    c1 = _entity_claim("d1-l1", "HQ-9P")
    c2 = _entity_claim("d1-l2", "FT-2000")
    id1, id2 = "ent:variant:HQ-9P", "ent:variant:FT-2000"
    ck = pair_key(id1, id2)

    def fake_resolve(
        claims: list[ClaimRecord],
        config: ConfigBundle,
        prev_view: GraphView | None = None,
        decisions: object = None,
    ) -> Partition:
        return Partition(
            resolved_ref={"d1-l1": ResolvedRef(entity_id=id1), "d1-l2": ResolvedRef(entity_id=id2)},
            candidates=[(id1, id2)],
            merge_confidence={ck: 0.7},
            merge_breakdown={ck: {"total": 0.7}},
        )

    monkeypatch.setattr(pipeline, "resolve", fake_resolve)
    view = rebuild([c1, c2], [], ConfigBundle())

    same_as = [e for e in view.edges if e.type == "same-as"]
    assert len(same_as) == 1
    assert same_as[0].merge_confidence == 0.7
    assert same_as[0].status is None  # G5: a resolution edge is never scored
