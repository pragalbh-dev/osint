"""DEFAULT-ON P4/P5, asserted where the ANALYST is — on the rendered GraphView, over the booted corpus.

**Why this file exists at all.** Every sibling spec in this directory asserts on the ``Partition`` — the
resolver's internal intermediate — and one of them synthesised its own reason string out of mere partition
membership and credited that as "received". So 219 gates stayed green while the property was FALSE on the
running system: measured on the booted corpus, 20 of 42 candidate merges and 11 of 76 walls were nowhere on
the analyst's surface (and therefore un-adjudicable, since ``POST /hitl/merge`` 404s without the drawn edge),
28 of 30 drawn walls did not name their ground, and 19 of them claimed to be an "explicit" analyst veto while
being machine-derived. A green artifact carrying a false claim is worse than a red one, because it switches
off the next reader's scepticism.

The fix in the code is that raw entity ids are canonicalised before the membership test. The fix in the SUITE
is this file: the assertions run on ``rebuild()``'s output, reached exactly the way the API reaches it
(``build_default_state().boot()``), so nothing can pass here that the analyst cannot see.

Corpus-dependent on purpose, and that is not a violation of principle #4 — the sibling files own the abstract
properties; what cannot be established abstractly is *"the surface renders what the resolver decided"*, which
is a statement about the real graph. If the frozen bundles are absent the module skips loudly.
"""

from __future__ import annotations

import pytest

from chanakya.api.state import build_default_state
from chanakya.resolve import resolve
from chanakya.schemas import GraphView, pair_key
from chanakya.schemas.stage_io import Partition
from chanakya.view.pipeline import _prepare_active_claims
from eval import harness

#: The generic label the drawn wall used to fall back to for THREE different derived grounds. Its presence on
#: any drawn edge is now a defect: the word "explicit" tells an analyst a person ruled on this pair.
RETIRED_GENERIC_WALL_LABEL = "explicit do-not-merge (hard veto)"


@pytest.fixture(scope="module")
def booted() -> tuple[GraphView, Partition]:
    """The real booted view AND the partition it was rendered from — the two sides of the property."""
    if not harness.bundles_dir().is_dir():
        pytest.skip(f"no frozen claim bundles at {harness.bundles_dir()}")
    state = build_default_state()
    state.boot()
    snapshot = state.config.snapshot()
    active, decisions = _prepare_active_claims(state.evidence, state.decision, snapshot)
    return state.view(), resolve(active, snapshot, None, decisions)


def _canonical(partition: Partition, eid: str) -> str:
    return partition.entity_canonical.get(eid, eid)


def _expected(partition: Partition, pairs: list[tuple[str, str]], node_ids: set[str]) -> set[tuple[str, str]]:
    """The canonical pairs a decision list *should* put on the surface, minus the two honest exclusions."""
    out = set()
    for a, b in pairs:
        ca, cb = _canonical(partition, a), _canonical(partition, b)
        if ca == cb:
            continue  # merged along another chain: no pair left to draw
        if ca in node_ids and cb in node_ids:
            out.add(tuple(sorted((ca, cb))))
    return out


def _drawn(view: GraphView, etype: str) -> dict[tuple[str, str], object]:
    return {tuple(sorted((e.source, e.target))): e for e in view.edges if e.type == etype}


# ── 1. every refusal and every open question REACHES the surface ──────────────────────────────────

def test_every_candidate_merge_reaches_the_analysts_surface(booted) -> None:
    """A queued merge the analyst cannot see is a queued merge the analyst cannot act on.

    The drawn edge is not decoration: ``POST /hitl/merge`` resolves the pair through it, so a candidate with
    no edge is un-adjudicable — the refusal to auto-merge stands and the human is locked out of overriding it.
    """
    view, partition = booted
    node_ids = {n.id for n in view.nodes}
    expected = _expected(partition, partition.candidates, node_ids)
    drawn = set(_drawn(view, "same-as"))

    missing = sorted(expected - drawn)
    assert not missing, (
        f"{len(missing)} of {len(expected)} candidate merges are on no drawn edge, so they are invisible AND "
        f"un-adjudicable: {missing[:5]}"
    )


def test_every_wall_reaches_the_analysts_surface(booted) -> None:
    """A wall nobody can see is indistinguishable from a merge nobody proposed — the costliest silence here.

    The cross-country / cross-service walls are the ones that matter most in an operator-scoped ORBAT, and
    they were among the ones being dropped.
    """
    view, partition = booted
    node_ids = {n.id for n in view.nodes}
    expected = _expected(partition, partition.distinct_from, node_ids)
    drawn = set(_drawn(view, "distinct-from"))

    missing = sorted(expected - drawn)
    assert not missing, (
        f"{len(missing)} of {len(expected)} hard walls are on no drawn edge — a refusal the analyst never "
        f"receives: {missing[:5]}"
    )


def test_every_identity_refusal_gap_reaches_a_node_on_the_surface(booted) -> None:
    """G19's escalate half, per endpoint: the refusal is a gap hanging off a node the analyst can open."""
    view, partition = booted
    node_ids = {n.id for n in view.nodes}
    gap_refs = {g.related_ref for g in view.known_gaps if g.id.startswith("gap:identity:")}

    for pair_ref in sorted(partition.identity_refusals):
        endpoints = {_canonical(partition, e) for e in pair_ref.split("|")}
        reachable = {e for e in endpoints if e in node_ids}
        assert reachable & gap_refs, (
            f"the identity refusal {pair_ref!r} raised no Known Gap on any node the analyst can open "
            f"(endpoints resolve to {sorted(endpoints)}). Refusing to fuse without telling anyone is the "
            "half of the non-negotiable that reaches nobody."
        )


# ── 2. …carrying a reason that names its OWN ground ───────────────────────────────────────────────

def test_every_drawn_wall_names_the_ground_that_caused_it(booted) -> None:
    """28 of 30 drawn walls carried no ground. Every rail that can draw a wall must state its own."""
    view, partition = booted
    unreasoned = [
        key for key, edge in _drawn(view, "distinct-from").items()
        if not str(getattr(edge, "attrs", {}).get("reason", "")).strip()
        # A source-asserted distinct-from arrives as an ordinary CLAIM edge: its ground is the cited
        # sentence, one click away through ``claim_ids``, which is a stronger record than any prose.
        and not getattr(edge, "claim_ids", [])
    ]
    assert not unreasoned, (
        f"{len(unreasoned)} drawn walls state neither a reason nor a citation: {unreasoned[:5]}"
    )


def test_no_drawn_wall_claims_to_be_an_explicit_curated_veto_unless_it_is_one(booted) -> None:
    """The word "explicit" says a PERSON ruled on this pair. 19 of 30 derived findings were saying it.

    Three distinct grounds — a curated registry entry, a gazetteer place pair, two differing bills of lading —
    rendered one identical string, so the analyst could not tell a human decision from a machine inference and
    had no way to know which of the three to go and check.
    """
    view, _partition = booted
    offenders = [
        key for key, edge in _drawn(view, "distinct-from").items()
        if RETIRED_GENERIC_WALL_LABEL in str(getattr(edge, "attrs", {}).get("reason", ""))
    ]
    assert not offenders, (
        f"{len(offenders)} drawn walls still render the retired generic label {RETIRED_GENERIC_WALL_LABEL!r}: "
        f"{offenders[:5]}"
    )


def test_the_derived_wall_grounds_are_distinguishable_from_one_another(booted) -> None:
    """Three grounds, three texts. Collapsing them is how "a reason exists" passes and instructs nobody."""
    view, _partition = booted
    texts = {
        str(getattr(edge, "attrs", {}).get("reason", ""))[:60]
        for edge in _drawn(view, "distinct-from").values()
        if str(getattr(edge, "attrs", {}).get("reason", "")).strip()
    }
    assert len(texts) >= 3, (
        f"the drawn walls speak with {len(texts)} distinct voice(s); the corpus exercises at least three "
        f"different rails (gazetteer place, hard identifier, stated critical attribute). texts={sorted(texts)}"
    )


def test_every_queued_merge_states_a_basis(booted) -> None:
    """A confidence number is not a basis. 21 drawn candidates had nothing else.

    Either the pair carries a stated basis or it does not reach the queue — this asserts the first half, and
    the name cap (which moved four variant-family pairs off the queue and onto the watch-list with their
    reason) is the second.
    """
    view, _partition = booted
    bare = [
        key for key, edge in _drawn(view, "same-as").items()
        if not str(getattr(edge, "attrs", {}).get("reason", "")).strip()
    ]
    assert not bare, (
        f"{len(bare)} drawn candidate merges give the analyst a confidence number and no stated basis: "
        f"{bare[:5]}"
    )


# ── 3. …and the retained watch-list keeps its record too ─────────────────────────────────────────

def test_a_capped_pair_is_retained_with_its_reason_rather_than_dropped(booted) -> None:
    """A ceiling of ``possible`` withholds ATTENTION, never the RECORD (the "retained but never surfaced" bug).

    The four variant-family pairs the name cap moved off the queue must still be findable, with the ground
    that moved them.
    """
    _view, partition = booted
    reasons = 0
    for a, b in partition.possible:
        if partition.candidate_reasons.get(pair_key(a, b)):
            reasons += 1
    assert reasons, "not one retained watch-list link carries a reason — the cap became a silent filter"
