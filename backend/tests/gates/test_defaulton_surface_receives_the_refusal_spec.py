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
        endpoints = {_canonical(partition, e) for e in partition.pair_members[pair_ref]}
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


# ── 4. the refusal reaches the NODE's own status, not only the gap register ───────────────────────

def test_a_node_whose_type_is_contradicted_is_never_confirmed(booted) -> None:
    """The refuse half, on the node. It fired nowhere: the same rebuild published `ent:variant:HT-233` as a
    first-class ORBAT variant at status CONFIRMED while emitting a Known Gap saying that mention's TYPE is
    contradicted. "Confirmed" asserts we have established this; what we have established is that two sources
    disagree about what it is.

    Asserted over every refusal on the corpus, not just that one node, and only for the reading the refusal
    actually lands on — the weaker-attested side (see ``rebuild`` step 4b: one flaky mention must not shatter a
    well-corroborated node, which is why the better-attested reading keeps its assessment and its gap).
    """
    view, partition = booted
    nodes = {n.id: n for n in view.nodes}
    refused_nodes = set()
    for pair_ref in partition.identity_refusals:
        ends = [_canonical(partition, e) for e in partition.pair_members[pair_ref]]
        refused_nodes.update(e for e in ends if e in nodes)
    assert refused_nodes, "no identity refusal reaches a node on this corpus — the property is untested"

    unassessable = [
        nid for nid in sorted(refused_nodes)
        if nodes[nid].sufficiency is not None and not nodes[nid].sufficiency.satisfied
    ]
    assert unassessable, (
        f"every node under an identity refusal still reads as assessable ({sorted(refused_nodes)}) — the "
        "escalate half fired and the refuse half did not."
    )
    for nid in unassessable:
        node = nodes[nid]
        assert node.status == "insufficient", (
            f"{nid} carries an unmet identity requirement yet reads status={node.status!r}. "
            "'insufficient' dominates by design: if we structurally cannot assess, we say so."
        )
        assert "identity" in node.sufficiency.missing_slots, (
            f"{nid} is unassessable but does not NAME identity as what is missing — the non-negotiable "
            f"requires naming it. missing_slots={node.sufficiency.missing_slots}"
        )


def test_the_refusal_does_not_shatter_the_better_attested_reading(booted) -> None:
    """The mirror, and the calibration: a single mis-typed mention may not unassess a corroborated node.

    ``comp_ht233`` is the hero chokepoint — five claims, several independent looks — and one lone extraction
    typed the same string as a *variant*. Downgrading the corroborated side to "cannot assess" would be the
    "one flaky source shatters a well-corroborated cluster" failure that ``critical_veto_min_grade`` exists to
    prevent one rail over. It keeps its assessment; it does NOT get to keep quiet about the disagreement, so
    the gap must still hang off it.
    """
    view, partition = booted
    nodes = {n.id: n for n in view.nodes}
    gap_refs = {g.related_ref for g in view.known_gaps if g.id.startswith("gap:identity:")}
    looks = {
        n.id: sum(g.weight for g in n.supporting_claims) for n in view.nodes
    }
    for pair_ref in sorted(partition.identity_refusals):
        ends = [
            e for e in dict.fromkeys(
                _canonical(partition, e) for e in partition.pair_members[pair_ref]
            ) if e in nodes
        ]
        if len(ends) < 2:
            continue
        best = max(ends, key=lambda e: looks.get(e, 0.0))
        if looks[best] == min(looks.get(e, 0.0) for e in ends):
            continue  # a tie: neither reading wins, both carry the refusal
        assert best in gap_refs, (
            f"{best} is the better-attested side of the refusal {pair_ref!r} and carries NO identity gap — "
            "keeping its assessment must not mean keeping the disagreement quiet."
        )


# ── 5. one place, one node: an id-namespace artefact is not two entities ──────────────────────────

def test_no_place_is_split_across_two_id_namespaces(booted) -> None:
    """Five duplicate place nodes, each splitting one place's geocode from its edges. Zero at baseline.

    An entity id is minted from the base type the CLAIM declared (``ent:<base>:<name>``) and node-type
    refinement re-types the entity while deliberately leaving the id alone. So a province arriving once as a
    ``based-at`` object (range ``basing_site``) and once as an ``area_of_operations`` ended up as two nodes
    whose ids disagree with their own shared type — one carrying the gazetteer coordinates, the other the
    connections. There is only ONE mention string here; the pair is a keying artefact, not a name coincidence,
    which is why it is an earned trigger rather than something the name cap should have been withholding.
    """
    view, _partition = booted
    by_identity: dict[tuple[str, str], list[str]] = {}
    for node in view.nodes:
        if node.name:
            by_identity.setdefault((node.type, node.name.lower()), []).append(node.id)

    split = {key: ids for key, ids in sorted(by_identity.items()) if len(ids) > 1}
    assert not split, (
        f"{len(split)} entities are split across two ids of the same type and name — one place, two nodes, "
        f"and the analyst has to guess which one holds the truth: {split}"
    )
