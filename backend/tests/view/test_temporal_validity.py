"""Stage 1B — temporal validity carried onto derived values, ADDITIVELY (spine/11 §1B; D7).

The contract under test:

* the **scalar** ``node.attrs[k]`` stays first-claim-wins (every existing consumer reads it) — unchanged;
* a role-agnostic **sidecar** ``node.attr_history[k]`` retains the *full time-ordered series* of EVERY
  asserted value (including a conflicting value first-claim-wins drops), each entry carrying
  ``value``/``event_time``/``report_time``/``claim_id`` + a report-bounded validity window;
* an ``EdgeView`` carries a ``time_interval`` populated from its claim times (mirrors ``EventView``);
* the two carriers are **in-memory only** — excluded from the wire dump, so the frozen view JSON is
  byte-unchanged (the additive risk-control principle).
"""

from __future__ import annotations

import json

from chanakya.schemas import (
    ClaimRecord,
    DocRef,
    EntityDescriptor,
    ExactDate,
    Period,
    ResolvedRef,
    Triple,
)
from chanakya.schemas.values import report_bounded_validity
from chanakya.view import view_to_json
from chanakya.view.pipeline import _assemble
from chanakya.view.supersede import build_instance_edges
from tests.fixtures import loaders


# ── the pure report-as-upper-bound helper ───────────────────────────────────────────────────────

def test_report_bound_point_anchor_uses_report_as_upper_bound() -> None:
    # A point event_time is a *when-true* anchor, not a "valid until" — so report_time bounds it above.
    vf, vu = report_bounded_validity(ExactDate(iso_date="2024-03-01"), ExactDate(iso_date="2024-06-01"))
    assert (vf, vu) == ("2024-03-01", "2024-06-01")


def test_report_bound_explicit_interval_end_beats_report() -> None:
    # A closed Period range states its own validity end; report_time does not override it.
    ev = Period(period_type="range", start=ExactDate(iso_date="2024-01-01"), end=ExactDate(iso_date="2024-02-01"))
    vf, vu = report_bounded_validity(ev, ExactDate(iso_date="2024-12-01"))
    assert (vf, vu) == ("2024-01-01", "2024-02-01")


def test_report_bound_no_event_time_anchor_is_none() -> None:
    vf, vu = report_bounded_validity(None, ExactDate(iso_date="2024-06-01"))
    assert (vf, vu) == (None, "2024-06-01")


def test_report_bound_both_missing() -> None:
    assert report_bounded_validity(None, None) == (None, None)


# ── node attribute history: retain ALL asserted values, time-ordered ─────────────────────────────

def _entity_claim(cid: str, value: str, event_iso: str, report_iso: str) -> ClaimRecord:
    return ClaimRecord(
        claim_id=cid,
        source_id="src-register",
        doc_ref=DocRef(file="t.txt", line=1),
        kind="observation",
        asserts="entity",
        payload=EntityDescriptor(entity_type="widget", name="W1", attrs={"color": value}),
        event_time=ExactDate(iso_date=event_iso),
        report_time=ExactDate(iso_date=report_iso),
        resolved_ref=ResolvedRef(entity_id="widget1"),
    )


def test_node_attr_history_retains_conflicting_value_first_claim_wins_would_drop() -> None:
    # Two claims assert `color` for the SAME node at different times, with a CONFLICT.
    early = _entity_claim("cA", "red", "2024-01-01", "2024-03-01")
    late = _entity_claim("cB", "blue", "2024-06-01", "2024-08-01")

    nodes, _edges, _events = _assemble([early, late])
    node = nodes["widget1"]

    # 1. scalar contract UNCHANGED: first claim wins.
    assert node.attrs["color"] == "red"

    # 2. sidecar retains BOTH values (the conflicting "blue" is NOT dropped), time-ordered.
    series = node.attr_history["color"]
    assert [e.value for e in series] == ["red", "blue"]
    assert [e.claim_id for e in series] == ["cA", "cB"]
    assert [e.event_time.iso_date for e in series] == ["2024-01-01", "2024-06-01"]
    assert [e.report_time.iso_date for e in series] == ["2024-03-01", "2024-08-01"]

    # 3. each entry carries its report-bounded validity window (report_time as the upper bound).
    assert (series[0].valid_from, series[0].valid_until) == ("2024-01-01", "2024-03-01")
    assert (series[1].valid_from, series[1].valid_until) == ("2024-06-01", "2024-08-01")


def test_node_attr_history_is_time_ordered_regardless_of_replay_order() -> None:
    # Late claim replayed FIRST — the series is still ordered oldest→newest by event_time.
    late = _entity_claim("cB", "blue", "2024-06-01", "2024-08-01")
    early = _entity_claim("cA", "red", "2024-01-01", "2024-03-01")
    nodes, _e, _ev = _assemble([late, early])
    series = nodes["widget1"].attr_history["color"]
    assert [e.event_time.iso_date for e in series] == ["2024-01-01", "2024-06-01"]
    # scalar is still whoever replayed first (unchanged contract) — here the late claim.
    assert nodes["widget1"].attrs["color"] == "blue"


# ── edge validity interval ───────────────────────────────────────────────────────────────────────

def _triple_claim(cid: str, event_iso: str) -> ClaimRecord:
    return ClaimRecord(
        claim_id=cid,
        source_id="src-register",
        doc_ref=DocRef(file="t.txt", line=1),
        kind="observation",
        asserts="relationship",
        payload=Triple(subject="unit_x", predicate="fields", object="comp_y"),
        event_time=ExactDate(iso_date=event_iso),
    )


def test_edge_carries_time_interval_from_its_claim() -> None:
    edges = build_instance_edges("ei", [_triple_claim("cE", "2023-05-01")])
    assert len(edges) == 1
    assert edges[0].time_interval == ExactDate(iso_date="2023-05-01")


def test_edge_time_interval_is_the_earliest_dated_claim_on_corroboration() -> None:
    edges = build_instance_edges("ei", [_triple_claim("cLate", "2023-09-01"), _triple_claim("cEarly", "2023-01-01")])
    assert len(edges) == 1  # same (s,p,o) → one corroborated edge
    assert edges[0].time_interval == ExactDate(iso_date="2023-01-01")


# ── real pipeline: populated end-to-end AND excluded from the wire (frozen JSON byte-unchanged) ──

def test_golden_pipeline_populates_attr_history_and_edge_interval() -> None:
    view = loaders.golden_view()
    nodes = {n.id: n for n in view.nodes}
    edges = {e.id: e for e in view.edges}

    # A claim-asserted attribute is retained in the sidecar with its claim + report_time.
    hist = nodes["unit_acme"].attr_history["echelon"]
    assert [e.value for e in hist] == ["battalion"]
    assert hist[0].claim_id == "d01-e1"

    # An edge with a dated claim now carries its validity interval (d02-l1 → 2021-03-01).
    assert edges["e:unit_acme:fields:comp_gizmo"].time_interval == ExactDate(iso_date="2021-03-01")


def test_new_carriers_are_surfaced_on_the_wire() -> None:
    # SURFACED (D7, §1B — reversing the earlier exclude=True): the timeline carriers now appear in
    # view_to_json — a target output ("store previous values, makes the KG more useful"), not hidden to
    # keep a fixture byte-stable. The frozen expected_view.json must be regenerated (data-refresh ledger §A).
    body = json.loads(view_to_json(loaders.golden_view()))
    assert any(n.get("attr_history") for n in body["nodes"]), "attr_history not surfaced on the wire"
    assert any(e.get("time_interval") for e in body["edges"]), "time_interval not surfaced on the wire"
