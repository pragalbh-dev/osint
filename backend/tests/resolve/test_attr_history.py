"""Stage 3-prep — per-attribute provenance on the resolver's ``Entity`` (mirrors view's Stage 1B, §1B).

The contract under test:

* the **scalar** ``Entity.attrs[k]`` stays first-claim-wins (every existing resolve reader depends on
  it) — unchanged;
* a role-agnostic sidecar ``Entity.attr_history[k]`` retains the *full time-ordered series* of EVERY
  value any claim asserted for that attribute — including a conflicting later value first-claim-wins
  would silently drop — each entry carrying ``value``/``claim_id``/``event_time``/``report_time``;
* the series is time-ordered oldest→newest (``event_time`` lower bound, then ``report_time`` lower
  bound, then ``claim_id``) regardless of claim replay order — deterministic, no clock/RNG (G1/G2);
* this is data availability only: no resolution decision (merge/veto/band) changes here, and the
  Partition output built on top of ``resolve.entities.build`` stays byte-unchanged (covered by the
  acceptance/gates runs, not re-asserted here).
"""

from __future__ import annotations

from chanakya.resolve.entities import build
from chanakya.schemas import ClaimRecord, DocRef, EntityDescriptor, ExactDate, ResolvedRef


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


def test_entity_attr_history_retains_conflicting_value_first_claim_wins_would_drop() -> None:
    # Two claims assert `color` for the SAME entity at different times, with a CONFLICT.
    early = _entity_claim("cA", "red", "2024-01-01", "2024-03-01")
    late = _entity_claim("cB", "blue", "2024-06-01", "2024-08-01")

    graph = build([early, late])
    ent = graph.entities["widget1"]

    # 1. scalar contract UNCHANGED: first claim wins.
    assert ent.attrs["color"] == "red"

    # 2. sidecar retains BOTH values (the conflicting "blue" is NOT dropped), time-ordered.
    series = ent.attr_history["color"]
    assert [e.value for e in series] == ["red", "blue"]
    assert [e.claim_id for e in series] == ["cA", "cB"]
    assert [e.event_time.iso_date for e in series] == ["2024-01-01", "2024-06-01"]
    assert [e.report_time.iso_date for e in series] == ["2024-03-01", "2024-08-01"]


def test_entity_attr_history_is_time_ordered_regardless_of_replay_order() -> None:
    # Late claim replayed FIRST — the series is still ordered oldest→newest by event_time.
    late = _entity_claim("cB", "blue", "2024-06-01", "2024-08-01")
    early = _entity_claim("cA", "red", "2024-01-01", "2024-03-01")

    graph = build([late, early])
    ent = graph.entities["widget1"]

    series = ent.attr_history["color"]
    assert [e.event_time.iso_date for e in series] == ["2024-01-01", "2024-06-01"]
    # scalar is still whoever replayed first (unchanged contract) — here the late claim.
    assert ent.attrs["color"] == "blue"


def test_entity_attr_history_undated_entries_sort_last_and_stay_deterministic() -> None:
    dated = _entity_claim("cB", "blue", "2024-06-01", "2024-08-01")
    undated = ClaimRecord(
        claim_id="cA",
        source_id="src-register",
        doc_ref=DocRef(file="t.txt", line=1),
        kind="observation",
        asserts="entity",
        payload=EntityDescriptor(entity_type="widget", name="W1", attrs={"color": "green"}),
        resolved_ref=ResolvedRef(entity_id="widget1"),
    )

    graph = build([dated, undated])
    series = graph.entities["widget1"].attr_history["color"]
    # the undated claim sorts LAST no matter its claim_id or replay order.
    assert [e.claim_id for e in series] == ["cB", "cA"]


def test_entity_attr_history_is_empty_for_an_attribute_free_entity() -> None:
    claim = ClaimRecord(
        claim_id="cZ",
        source_id="src-register",
        doc_ref=DocRef(file="t.txt", line=1),
        kind="observation",
        asserts="entity",
        payload=EntityDescriptor(entity_type="widget", name="W2", attrs={}),
        resolved_ref=ResolvedRef(entity_id="widget2"),
    )
    graph = build([claim])
    assert graph.entities["widget2"].attr_history == {}
    assert graph.entities["widget2"].attrs == {}
