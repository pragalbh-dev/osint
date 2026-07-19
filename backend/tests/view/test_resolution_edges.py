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
    Location,
    NodeView,
    Partition,
    PlaceRef,
    ResolvedRef,
    Triple,
    pair_key,
)
from chanakya.view import pipeline
from chanakya.view.pipeline import _merge_provenance, _resolution_edges, _stamp_place_refs, rebuild


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


def test_place_ref_is_stamped_onto_the_node_with_its_evidence() -> None:
    """RES-3: the writer ``Location.resolved_place_ref`` never had — plus the distance/band that earned it."""
    nodes = {
        "site_rahwali": NodeView(
            id="site_rahwali", type="basing_site", name="Rahwali airfield", claim_ids=["d1-l1"],
            location=Location(raw="32°14′20″N 074°07′52″E", wgs84_lat=32.239, wgs84_lon=74.131),
        ),
        "site_pin": NodeView(id="site_pin", type="basing_site", name="an unnamed compound", claim_ids=["d1-l2"]),
    }
    frozen = nodes["site_rahwali"].location
    part = Partition(
        place_refs={"site_rahwali": PlaceRef(place_id="pl_rahwali", band="auto", distance_m=16.17, via="toponym")}
    )
    _stamp_place_refs(nodes, part)

    stamped = nodes["site_rahwali"]
    assert stamped.location is not None and stamped.location.resolved_place_ref == "pl_rahwali"
    assert stamped.location.wgs84_lat == 32.239  # the frozen coord survives the stamp
    assert frozen is not None and frozen.resolved_place_ref is None  # the value object was NOT mutated
    assert stamped.attrs["place_match_band"] == "auto"
    assert stamped.attrs["place_match_distance_m"] == 16.17
    assert stamped.attrs["place_match_via"] == "toponym"
    # A mention that matched no curated anchor stays an honest pin: no ref, no place attrs.
    assert nodes["site_pin"].location is None
    assert "place_match_band" not in nodes["site_pin"].attrs


def test_frozen_location_reaches_the_node_from_the_claim() -> None:
    """The coordinate was always on the claim; it just had no home on the view element (RES-3)."""
    claim = ClaimRecord(
        claim_id="d1-l1", source_id="s", doc_ref=DocRef(file="f", span=(0, 1)),
        kind="observation", asserts="entity",
        payload=EntityDescriptor(
            entity_type="basing_site", name="Rahwali airfield",
            attrs={"coordinates": {"raw": "32°14′20″N 074°07′52″E", "wgs84_lat": 32.239, "wgs84_lon": 74.131}},
        ),
    )
    nodes, _, _ = pipeline._assemble([claim], {})
    node = nodes["ent:basing_site:Rahwali airfield"]
    assert node.location is not None and node.location.wgs84_lat == 32.239
    assert node.location.resolved_place_ref is None  # RESOLVE's slot, still unfilled at assembly


def test_entity_without_a_coordinate_keeps_no_location() -> None:
    claim = _entity_claim("d1-l1", "HQ-9P")
    nodes, _, _ = pipeline._assemble([claim], {})
    assert nodes["ent:variant:HQ-9P"].location is None  # golden path unchanged (gate G2)


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
        # A real RELATIONSHIP predicate. An *identity* predicate ("marketed-as", "same-as") is consumed as
        # a merge signal and deliberately never drawn (D-2.5), so it could not show reconnection at all.
        payload=Triple(subject="var_fd2000", predicate="equips", object="var_export"),
    )
    part = Partition(
        resolved_ref={"d1-e1": ResolvedRef(entity_id="var_hq9p")},
        same_as=[("var_fd2000", "var_hq9p")],
        entity_canonical={"var_fd2000": "var_hq9p"},
    )
    nodes, edges, _ = pipeline._assemble([entity, edge], part.entity_canonical)
    e = next(e for e in edges if e.type == "equips")
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
