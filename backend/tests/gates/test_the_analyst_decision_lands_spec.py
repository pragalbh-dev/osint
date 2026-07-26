"""The write path, measured where the analyst actually stands: the live API over the real booted corpus.

Every defect this file pins returned ``200``, and every one of them was invisible to a fixture. They share
one shape — **the system accepted an instruction and did not tell the truth about what it did with it** —
and the worst of them landed on the project's headline pair: an analyst rejecting the fusion of the two
co-located batteries got ``200`` and a byte-identical ``GET /view``. No wall, no gap, no acknowledgement,
and the same fusion still proposed on the next rebuild. The HITL rule is that an override mutates graph
state, not just a log; that was a log entry and nothing else.

Assertions here are INVARIANTS, never counts: the corpus is a regenerable fixture and a number would rot on
the next extraction. "Every reject produces a durable wall" survives a re-extraction; "8 of 14" does not.

The booted app is module-scoped for reads. Anything that WRITES boots its own app, because a decision log is
append-only and a test that inherited another's decisions would be measuring the wrong graph.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from chanakya.api import create_app
from chanakya.api.state import build_default_state, scenario_bundles_dir

FIXED_TS = "2026-07-26T00:00:00+00:00"


def _fresh() -> Iterator[TestClient]:
    state = build_default_state(clock=lambda: FIXED_TS)
    state.boot()
    with TestClient(create_app(state)) as client:
        yield client


@pytest.fixture(scope="module")
def corpus() -> Any:
    if not scenario_bundles_dir().is_dir():
        pytest.skip(f"no frozen claim bundles at {scenario_bundles_dir()} — corpus invariants cannot run")
    client = next(_fresh())
    view = client.get("/view").json()
    coverage = client.get("/coverage").json()
    assert view.get("nodes"), "the booted corpus rendered an empty graph — nothing to assert against"
    return type("Corpus", (), {"view": view, "coverage": coverage})


def _client() -> TestClient:
    if not scenario_bundles_dir().is_dir():
        pytest.skip(f"no frozen claim bundles at {scenario_bundles_dir()}")
    return next(_fresh())


def _same_as(view: dict) -> list[dict]:
    return [e for e in view["edges"] if e["type"] == "same-as"]


def _pair(edge: dict) -> tuple[str, str]:
    return tuple(sorted((edge["source"], edge["target"])))  # type: ignore[return-value]


def _adjudicate(client: TestClient, subject: str, decision: str) -> Any:
    return client.post(
        "/hitl/merge",
        json={"item_id": f"merge:{subject}", "type": "merge", "subject": subject,
              "decision": decision, "actor": "analyst", "rationale": "adjudicated in the spec"},
    )


# ── BLOCKER A: a reject must MUTATE graph state, not merely be logged ────────────────────────────

def test_every_reject_on_the_real_corpus_produces_a_durable_analyst_sourced_wall() -> None:
    """The one adjudication this system exists to make possible, asserted over every pair it is offered on.

    A ``reject`` that leaves ``GET /view`` unchanged is not a decision, it is a comment. The measured
    failure was worse than partial: on the headline pair (the Army PAAD unit against the PAF HQ-9B fire
    unit) the whole response was byte-identical, because the learned do-not-merge was keyed on NAMES and the
    names that reach the replay are the analyst's surface labels, which for that pair are not the resolver's
    entity names. The bar is a WALL, not merely the candidate disappearing: a pair that silently stops being
    proposed is indistinguishable, from outside, from the decision having been dropped.
    """
    client = _client()
    subjects = [e["id"] for e in _same_as(client.get("/view").json())]
    assert subjects, "no candidate same-as edges on the booted corpus — nothing to adjudicate"

    failures, unacknowledged = [], []
    for subject in subjects:
        c = next(_fresh())
        before = c.get("/view").json()
        edge = next(e for e in before["edges"] if e["id"] == subject)
        response = _adjudicate(c, subject, "reject")
        after = c.get("/view").json()
        walls = {_pair(e) for e in after["edges"] if e["type"] == "distinct-from"}
        if response.status_code != 200 or _pair(edge) not in walls:
            failures.append((subject, response.status_code, _pair(edge) in walls))
        # The receipt is asserted in the same loop rather than its own, purely so the suite boots the app
        # once per pair instead of twice — the property is the sibling test's, stated there.
        receipt = (response.json() or {}).get("adjudication") if response.status_code == 200 else None
        if not receipt or not receipt.get("ground") or receipt.get("applied") is not True:
            unacknowledged.append((subject, receipt))
    assert not failures, (
        f"{len(failures)} of {len(subjects)} rejects did not become a wall on GET /view: {failures[:4]}. "
        "The analyst said 'these are not the same' and the graph does not record it, so the same fusion is "
        "proposed again on the next rebuild. An override must mutate graph state, not just a log."
    )
    assert not unacknowledged, (
        f"{len(unacknowledged)} rejects landed and did not report that they had: {unacknowledged[:2]}. The "
        "acknowledgement is derived by reading the rebuilt view, so a receipt that does not say 'applied' "
        "means the write path cannot see its own effect."
    )


def test_the_rejected_pair_stops_being_proposed_and_the_wall_states_a_human_decided_it() -> None:
    """Two halves of the same decision: it leaves the queue, and the wall says WHO decided it.

    The SPA derives its review queue purely from live ``same-as`` edges, so a rejected pair still drawn is a
    question the analyst is asked forever. And a wall the analyst cannot attribute is the most confusing
    wall there is — it appears in no config file, so it must say that a human put it there.
    """
    client = _client()
    subject = _same_as(client.get("/view").json())[0]["id"]
    c = next(_fresh())
    edge = next(e for e in c.get("/view").json()["edges"] if e["id"] == subject)
    _adjudicate(c, subject, "reject")
    after = c.get("/view").json()

    assert not any(e["id"] == subject for e in after["edges"]), (
        f"the adjudicated pair {subject} is STILL drawn as a same-as candidate, so it never leaves the "
        "review queue and the analyst is asked the same question forever."
    )
    wall = next(e for e in after["edges"] if e["type"] == "distinct-from" and _pair(e) == _pair(edge))
    assert "ANALYST" in (wall["attrs"].get("reason") or ""), (
        f"the wall an analyst created does not say so: {wall['attrs'].get('reason')!r}. It appears in no "
        "config file, so an unattributed one reads as a machine finding nobody can trace."
    )


def test_no_pair_on_the_real_corpus_carries_both_a_same_as_and_a_distinct_from(corpus: Any) -> None:
    """The graph may not assert "same" and "not same" about one pair at once — before or after a decision.

    Measured at 7 of 14 after a reject: ``finalise`` prunes a walled candidate over RAW ids while the view
    draws CANONICAL pairs, and two different raw pairs routinely collapse onto one canonical pair.
    """
    for view, when in ((corpus.view, "on the booted graph"), (_after_all_rejects(), "after adjudication")):
        same = {_pair(e) for e in view["edges"] if e["type"] == "same-as"}
        walls = {_pair(e) for e in view["edges"] if e["type"] == "distinct-from"}
        assert not (same & walls), (
            f"{len(same & walls)} pairs carry a same-as proposal AND a do-not-merge wall {when}: "
            f"{sorted(same & walls)[:4]}. One of the two is false, and the analyst is offered a merge the "
            "wall can never let through."
        )


def _after_all_rejects() -> dict:
    """One app, every candidate rejected in turn — the state an analyst reaches by working the queue."""
    c = next(_fresh())
    for subject in [e["id"] for e in _same_as(c.get("/view").json())]:
        _adjudicate(c, subject, "reject")
    return c.get("/view").json()


# ── BLOCKER A, second half: a REFUSED instruction must say so ───────────────────────────────────

def test_every_adjudication_is_acknowledged_with_whether_it_was_applied_and_on_what_ground() -> None:
    """A silent 200 on a refused instruction is the escalate half missing on the write path.

    The cross-type rail declining to fuse a ``component`` with a ``variant`` is CORRECT — that is not the
    defect. The defect is that nothing told the analyst the instruction was not applied, or why, so a
    refusal was byte-indistinguishable from success. Measured: 3 of 14 accepts changed nothing and said
    nothing. Scoped to ``accept`` because the reject side is asserted in the same loop that checks the wall
    (one boot per pair rather than two); the property is identical.
    """
    client = _client()
    subjects = [e["id"] for e in _same_as(client.get("/view").json())]
    missing, unexplained = [], []
    for subject in subjects:
        c = next(_fresh())
        body = _adjudicate(c, subject, "accept").json()
        receipt = body.get("adjudication")
        if not receipt:
            missing.append((subject, "accept"))
            continue
        if not receipt.get("ground") or not receipt.get("recorded"):
            unexplained.append((subject, "accept", receipt))
    assert not missing, f"{len(missing)} adjudications returned 200 with NO receipt: {missing[:4]}"
    assert not unexplained, (
        f"{len(unexplained)} receipts state neither that the instruction was recorded nor a ground for what "
        f"happened to it: {unexplained[:2]}"
    )


def test_an_instruction_the_resolver_refuses_is_still_visible_on_the_view_after_the_round_trip() -> None:
    """The receipt is transient; a page reload must not erase the fact that the analyst already answered."""
    client = _client()
    refused = None
    for subject in [e["id"] for e in _same_as(client.get("/view").json())]:
        c = next(_fresh())
        receipt = _adjudicate(c, subject, "accept").json().get("adjudication") or {}
        if receipt.get("applied") is False:
            refused = (c, subject, receipt)
            break
    if refused is None:
        pytest.skip("the corpus offers no accept the resolver refuses — nothing to assert here today")
    c, subject, receipt = refused
    edge = next((e for e in c.get("/view").json()["edges"] if e["id"] == subject), None)
    assert edge is not None, f"{subject} vanished from the view after a refused accept — a silent drop"
    stamp = (edge.get("attrs") or {}).get("adjudication_not_applied")
    assert stamp and stamp.get("ground"), (
        f"the refused instruction on {subject} reaches GET /view with no record: {edge.get('attrs')}. The "
        "analyst reloads and is asked the identical question with no memory that they answered it."
    )


def test_a_malformed_writeback_is_a_validation_error_not_a_server_fault() -> None:
    """A 500 makes a REJECTED adjudication indistinguishable from a broken server — the same confusion class
    as a dropped decision. ``DecisionRecord.actor`` was always a Literal; accepting a bare string at the
    boundary only moved the failure somewhere it could not be reported."""
    client = _client()
    subject = _same_as(client.get("/view").json())[0]["id"]
    response = client.post(
        "/hitl/merge",
        json={"item_id": "m", "type": "merge", "subject": subject, "decision": "reject", "actor": "audit"},
    )
    assert response.status_code == 422, (
        f"an unknown actor returned {response.status_code}, not 422: {response.text[:200]}"
    )
    assert "analyst" in response.text, "the validation error does not name the actors that ARE accepted"


# ── BLOCKER D / J: what the analyst RECEIVES ────────────────────────────────────────────────────

def test_every_known_gap_states_when_next_coverage_is_due_or_that_none_is(corpus: Any) -> None:
    """The second clause of the non-negotiable. A bare ``next_coverage_due: null`` states nothing — it is
    indistinguishable from a field nobody filled in — and 34 of 37 gaps carried exactly that. A date is
    never invented: where none is derivable the statement says which class could close the gap and why that
    class has no revisit interval."""
    silent = [g["id"] for g in corpus.view["known_gaps"] if not g.get("coverage_statement")]
    assert not silent, (
        f"{len(silent)} Known Gaps say nothing about when next coverage is due: {silent[:5]}. Naming what "
        "is missing is only half the rule."
    )
    for gap in corpus.view["known_gaps"]:
        if gap.get("next_coverage_due"):
            assert gap["next_coverage_due"] in gap["coverage_statement"], (
                f"{gap['id']} carries a date the statement does not mention — two channels, one of which "
                "the analyst reads, disagreeing about the same fact"
            )


def test_one_node_and_one_statement_is_one_known_gap(corpus: Any) -> None:
    """Five renderings of one finding read as five findings, which is how a register teaches an analyst to
    skim it. Measured: 14 identity gaps were 4 distinct (node, statement) pairs, one node receiving the
    identical sentence five times in a single drawer."""
    seen: dict[tuple[str, str], str] = {}
    dupes = []
    for gap in corpus.view["known_gaps"]:
        if not gap.get("related_ref"):
            continue
        key = (gap["related_ref"], gap["what_missing"])
        if key in seen:
            dupes.append((gap["related_ref"], seen[key], gap["id"]))
        seen[key] = gap["id"]
    assert not dupes, f"{len(dupes)} Known Gaps restate an identical finding about the same node: {dupes[:4]}"


# ── E: the watch-list reaches its channel in full ───────────────────────────────────────────────

def test_every_retained_watch_list_pair_reaches_the_coverage_channel(corpus: Any) -> None:
    """``GET /coverage`` is the ONLY channel carrying the ``possible`` tier (it is deliberately not drawn on
    the view), so a pair omitted from it reaches no surface at all. The builder listed only pairs with a
    RECORDED reason, and a pair that scored into the band on its own evidence had none to record — 24 of 355
    silently dropped. "No cap fired" is not a reason to be invisible; it is itself the reason."""
    coverage = corpus.coverage
    assert len(coverage["withheld"]) == coverage["possible"], (
        f"{coverage['possible'] - len(coverage['withheld'])} of {coverage['possible']} retained pairs reach "
        "no surface anywhere — byte-indistinguishable, from outside, from pairs the resolver never scored."
    )
    unexplained = [w for w in coverage["withheld"] if not w.get("reason")]
    assert not unexplained, f"{len(unexplained)} withheld pairs are listed with no ground at all"


# ── H: a missing discriminator is not permission to cross a wall ────────────────────────────────

def test_a_fragment_proposed_against_both_sides_of_a_wall_says_so(corpus: Any) -> None:
    """One mention proposed as the same entity as BOTH sides of a hard do-not-merge wall is a two-step
    bridge: at most one proposal can be true, and accepting either is choosing a side rather than confirming
    a resemblance. Measured on a single-claim unit fragment stating no ``service_branch`` that was a live
    candidate against both an Air Force and an Army formation the critical-attribute rail holds apart."""
    view = corpus.view
    walls = {_pair(e) for e in view["edges"] if e["type"] == "distinct-from"}
    by_node: dict[str, set[str]] = {}
    edge_of: dict[tuple[str, str], dict] = {}
    for e in _same_as(view):
        by_node.setdefault(e["source"], set()).add(e["target"])
        by_node.setdefault(e["target"], set()).add(e["source"])
        edge_of[_pair(e)] = e

    silent = []
    for fragment, others in sorted(by_node.items()):
        for x in sorted(others):
            for y in sorted(others):
                if x >= y or tuple(sorted((x, y))) not in walls:
                    continue
                for other in (x, y):
                    edge = edge_of[tuple(sorted((fragment, other)))]
                    if "CAUTION" not in ((edge.get("attrs") or {}).get("reason") or ""):
                        silent.append(edge["id"])
    assert not silent, (
        f"{len(silent)} candidate merges bridge a hard wall in two hops and say nothing about it: "
        f"{sorted(set(silent))[:4]}. A missing discriminator must not read as permission to cross a wall."
    )


# ── the shape of the whole thing: adjudicating does not corrupt determinism ──────────────────────

def test_the_same_decision_replayed_gives_the_same_graph() -> None:
    """The wall is DERIVED from the append-only log on every rebuild, so it must be reproducible — that is
    what "survives rebuild" means, and it is the difference between an override and an edit."""
    subject = _same_as(_client().get("/view").json())[0]["id"]
    views = []
    for _ in range(2):
        c = next(_fresh())
        _adjudicate(c, subject, "reject")
        views.append(json.dumps(c.get("/view").json(), sort_keys=True))
    assert views[0] == views[1], "the same reject replayed produced two different graphs"
