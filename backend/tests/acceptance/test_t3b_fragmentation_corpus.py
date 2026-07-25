"""T3b on the REAL corpus — the fragmentation defects the analyst actually saw, pinned end to end.

The unit tests in ``tests/resolve/test_t3b_fragmentation.py`` pin each mechanism on a hand-built graph.
These pin the *outcome* on the frozen scenario, because every one of these defects was invisible to the
unit suite: the graph was green while the review queue was full of pairs no analyst would look at twice
and the relocation beat said an air force had moved.

Stated as invariants, never as counts — a count would turn a data improvement into a red test.
"""

from __future__ import annotations

from collections import Counter

import pytest

from chanakya.schemas import GraphView

AREA_TYPE = "area_of_operations"


def _by_id(view: GraphView) -> dict[str, object]:
    return {n.id: n for n in view.nodes}


def _candidates(view: GraphView) -> list:
    return [e for e in view.edges if e.type == "same-as"]


# ── A. an area of operations is a different KIND of thing from a basing site ────────────────────

def test_sectors_belts_and_provinces_are_areas_not_basing_sites(view: GraphView) -> None:
    """md/13 §1: basing precision is site/pad level. "based at Punjab" is not a fact an analyst can act on."""
    types = {n.name: n.type for n in view.nodes if n.name}
    for area in ("Karachi air defence sector", "Karachi coastal air defence belt",
                 "central Punjab air defence sector", "Punjab", "Sindh"):
        assert types.get(area) == AREA_TYPE, f"{area!r} is typed {types.get(area)!r}, not an area"
    # ...and the retyping is surgical: a real site that merely *mentions* an admin area stays a site
    assert types.get("Army Air Defence Centre, Karachi") == "basing_site"
    assert types.get("Sargodha") == "basing_site"


def test_the_karachi_nodes_are_not_offered_as_duplicates_of_each_other(view: GraphView) -> None:
    """The user's complaint, answered honestly: they were never fragments of one node.

    An Army AD Centre, an air-defence sector and a coastal belt are three different kinds of thing. The
    fix is not to merge them — it is to stop presenting them to the analyst as candidate duplicates.
    """
    nodes = _by_id(view)
    karachi = {
        n.id for n in view.nodes
        if "karachi" in (n.id + " " + (n.name or "")).lower() and n.type in {"basing_site", AREA_TYPE}
    }
    assert len(karachi) > 1, "fixture drift: the Karachi cluster no longer has several nodes"
    for e in _candidates(view):
        if e.source in karachi and e.target in karachi:
            assert nodes[e.source].type == nodes[e.target].type, (
                f"{e.source} and {e.target} are different kinds of thing and must not be a merge candidate"
            )


def test_a_cross_type_merge_candidate_reaches_the_queue_ONLY_with_its_reason(view: GraphView) -> None:
    """T3b-A narrowed, deliberately: the resolver's own cross-type GUESSES are noise; an assertion is not.

    The rule used to be "no cross-type candidate, ever", on T3b-A's reasoning that asking an analyst whether
    an air-defence *sector* is the same thing as an air-defence *centre* "is not triage, it is noise". That
    half stands and is asserted by the unit gate (a cross-type pair nothing licensed a fusion for earns
    nothing at all). But the blanket rule also swallowed the case the candidate-collection loop has always
    documented as its deliberate escape hatch: **a source or the offline proposer explicitly asserting the
    identity of two differently-typed mentions**. That is an extraction error, a typing error, or deception,
    and all three are exactly what a human should see — while dropping it is a quiet drop of a stated
    assertion the system refused to act on, which is the half of the non-negotiable that is about the analyst
    actually receiving the refusal.

    So the rule is now about GROUNDS, not about existence: a cross-type pair may sit in the queue, and it must
    carry the reason it is there — naming the two conflicting types — so the analyst is not asked "are these
    the same?" with no way to see why the machine would not answer. Each such pair also owes a named gap
    (asserted by ``tests/gates/test_g19_cross_namespace_non_fusion.py``).
    """
    nodes = _by_id(view)
    crossing = [
        e for e in _candidates(view) if nodes[e.source].type != nodes[e.target].type
    ]
    for e in crossing:
        reason = (e.attrs or {}).get("reason") or ""
        assert "cross-type" in reason, (
            f"cross-type candidate {e.source}/{e.target} is in the analyst's queue with no stated ground "
            f"(reason={reason!r}). A queue item whose grounds are invisible is a question the analyst cannot "
            f"answer, and it is indistinguishable from the resolver merely guessing"
        )
        assert nodes[e.source].type in reason and nodes[e.target].type in reason, (
            f"the reason on {e.source}/{e.target} does not name the two conflicting types: {reason!r}"
        )


# ── B. an identical surface string resolves without an LLM call ─────────────────────────────────

@pytest.mark.xfail(
    strict=True,
    reason=(
        "DATA REFRESH (calibration ledger): the corpus types the string 'HT-233' as a `component` in one "
        "document and as a `variant` in another, so the view now holds two nodes — comp_ht233 and "
        "ent:variant:HT-233 — instead of one. That is the TARGET behaviour and it is deliberate: a type "
        "disagreement between two sources is an evidentiary contradiction, and the cross-type fusion wall "
        "refuses to resolve it silently in either direction (fusing would assert a type neither source "
        "states; dropping the resemblance would hide the disagreement). The refusal is not a quiet drop — the "
        "pair reaches the analyst as a candidate carrying 'not fusable: cross-type (component vs variant)' "
        "and each endpoint carries a named Known Gap saying the typing must be adjudicated. TO CLOSE: "
        "harmonise the stated type of HT-233 across the corpus documents (or declare a component<->variant "
        "refinement in config/ontology.yaml so the two mentions arrive as one type), re-extract and re-record "
        "the frozen bundles + answer key, then delete this marker. Do NOT close it by weakening the wall."
    ),
)
def test_the_identical_string_ht233_fragment_is_gone(view: GraphView) -> None:
    """``unknown:HT-233`` shared a document with ``comp_ht233`` under an IDENTICAL surface string.

    It failed to resolve because two documents typed the string differently and the resolver rightly
    refused to guess — leaving a nameless orphan that could never resolve at all. The ontology settles
    the type, so the fragment lands on the radar it was always identical to.
    """
    exact = [n.id for n in view.nodes if (n.name or "").strip() == "HT-233" or n.id == "HT-233"]
    assert exact == ["comp_ht233"], f"the HT-233 surface form is still fragmented across {exact}"


# ── C. three bills of lading are three import events ────────────────────────────────────────────

def test_distinct_bills_of_lading_are_held_apart_deterministically(view: GraphView) -> None:
    """Merging two would collapse two import events and silently corrupt the supply-chain count."""
    bols = sorted(n.id for n in view.nodes if (n.name or "").startswith("KPQA-HC-"))
    assert len(bols) >= 3, "fixture drift: the d05 manifest no longer yields three distinct bills"
    vetoed = {frozenset((e.source, e.target)) for e in view.edges if e.type == "distinct-from"}
    for i, a in enumerate(bols):
        for b in bols[i + 1 :]:
            assert frozenset((a, b)) in vetoed, f"{a} vs {b} has no deterministic do-not-merge rail"
    for e in _candidates(view):
        assert not (e.source in bols and e.target in bols), "a hard conflict is not an open question"


# ── D / E. a node the analyst can read ──────────────────────────────────────────────────────────

def test_every_node_renders_under_a_name_not_a_raw_id(view: GraphView) -> None:
    """An endpoint the ontology could not type still has a designator — the document's own words."""
    nameless = [n.id for n in view.nodes if not (n.name or "").strip()]
    assert not nameless, f"nodes that render by raw id in the UI: {nameless}"


def test_the_relocating_unit_is_not_named_after_its_operator(view: GraphView) -> None:
    """The demo's climactic moment read "Pakistan Air Force moved from Nur Khan to Rahwali".

    An air force did not relocate; one fire unit did. The corpus only ever names this formation by its
    service, which the registry deliberately seeds as an alias — so the honest name is the analyst's own
    curated ``display_name``, not the first surface form that happened to replay.
    """
    unit = _by_id(view).get("unit_hq9b")
    assert unit is not None, "fixture drift: unit_hq9b is not in the rebuilt view"
    assert unit.name and "air force" not in unit.name.casefold(), (
        f"unit_hq9b renders as {unit.name!r} — the operator, not the unit"
    )


# ── F. the relational term no longer saturates on a single shared link ──────────────────────────

def test_merge_candidates_are_not_dominated_by_single_shared_neighbours(view: GraphView) -> None:
    """Every surviving candidate must be justified by something other than one shared hub edge.

    Before the support discount, a pair whose only agreement was a single shared neighbour scored
    ``0.40*1.0 + 0.05 = 0.45`` — exactly ``hitl_low`` — and eighteen such pairs filled the queue.
    """
    for e in _candidates(view):
        bd = (e.attrs or {}).get("breakdown") or {}
        if not bd:
            continue
        assert bd.get("attribute", 0.0) > 0.0 or bd.get("source_asserted", 0.0) > 0.0, (
            f"{e.source} vs {e.target} rests on the relational term alone: {bd}"
        )


# ── G. one logical edge is one row — corroboration pools, it does not fragment ───────────────────

def test_no_two_edges_share_an_id_after_a_full_rebuild(view: GraphView) -> None:
    """An EdgeView ``id`` is the edge's resolved identity; two rows under one ``id`` is a fragmented edge.

    ``rebuild()`` buckets corroborating claims into edge rows by an ``edge_instance`` key, then mints each
    row's ``id`` from its canonical (post-merge) endpoints. When the key was read from a claim's
    PRE-resolution surface strings while the ``id`` came from the canonical endpoints, a single logical
    edge whose endpoint had merged split across several keys — several rows carrying one ``id``. Scoring
    then re-keys by ``id`` and keeps only the last row, stranding the other rows' claims (among them the
    ISPR induction announcement on ``e:var_hq9p:inducted-into:unit_paad``) on unscored duplicates that
    never contribute to corroboration (residual #16). The invariant that guards it, and that the unit
    suite never saw because the graph was green while the corroboration silently leaked away: after a full
    rebuild of the shipped corpus, an ``id`` names exactly one edge.
    """
    duplicated = {eid: n for eid, n in Counter(e.id for e in view.edges).items() if n > 1}
    assert not duplicated, f"one id names several edge rows (fragmented corroboration): {duplicated}"
