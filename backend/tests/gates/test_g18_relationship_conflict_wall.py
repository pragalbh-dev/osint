"""G18 — the relationship-conflict wall: the channel, the reason, and C1's per-subject site-class rule.

**The judge had no relationship discriminator at all.** ``relational_score`` is a Jaccard over *shared*
neighbour keys, so it could only ever say "these two look alike because they touch the same things"; nothing
ever compared two candidates' basing or operator **values**, and there was therefore no way for the system to
notice that two profiles are in different places at the same time. Two units at different sites at overlapping
times are **different units** — a cannot-link, not a low score.

Three things this asserts that the gate as first written did not, each because it would otherwise pass while
the harm it names is realized:

1. **the channel.** ``veto`` membership is hard **and transitive**, re-applied in ``finalise``, visible to the
   D9 bridge alarm and **drawn**. Consultation inside ``vetoed()`` only — how the geographic veto is wired —
   is hard but **pairwise and invisible**. Built the second way the wall is non-transitive *and* unreported
   and G18 still goes green, so the gate names the channel and proves the transitive property.
2. **an analyst-visible reason.** A wall nobody can read is indistinguishable from a missing edge.
3. **C1's rule, per (subject, predicate).** A differing site class is NOT a conflict — a unit at its garrison
   and concurrently at a forward site is one unit with two valid basings. And any *unreadable* class collapses
   the whole subject to one bucket: separation IS de-confliction, so a partial tag is worse than none (S2
   measured a per-edge tag silently killing the flagship relocation).

Abstract fixtures (ruling M4). The corpus holds essentially one stated basing and no ``operated-by`` data at
all, so neither arm can fire on it — the mechanism is at full strength and the data is sparse.
"""

from __future__ import annotations

from chanakya.resolve import resolve
from chanakya.schemas import OntologyConfig
from tests.resolve._helpers import entity, mk_config, triple

EARNED = {
    "enabled": True,
    "name_ceiling": "possible",
    "wall_predicates": ["based-at", "operated-by"],
    "wall_scope_attr": "site_type",
}

#: A minimal ontology declaring the site-class tag on ``based-at`` plus the closed vocabulary the wall scopes
#: within. Read from S2's ``layer_routing`` block on purpose — C1 is "one declaration, two consumers", and a
#: second vocabulary would drift from the supersede key's.
ONTOLOGY = OntologyConfig(
    node_types=[],
    edge_types=[{"name": "based-at", "from": "unit", "to": "basing_site", "instance_key": ["from"],
                 "instance_key_tag": "site_type"},
                {"name": "operated-by", "from": "unit", "to": "operator"}],
    layer_routing={
        "enabled": False,
        "site_type_vocabulary": ["garrison", "airfield", "emplacement"],
        "site_type_aliases": {"air base": "airfield"},
        "absent_bucket": "unknown",
    },
)

ROLES = {"unit": {"service_branch": {"role": "supporting", "time_role": "durable"}}}


def _cfg(**over):
    over.setdefault("attribute_roles", ROLES)
    over.setdefault("ontology", ONTOLOGY)
    return mk_config(earned_identity={**EARNED, **over.pop("earned", {})},
                     name_alone_caps_at_possible=True, **over)


def _two_units_at(site_a_class: str, site_b_class: str, *, iso_a="2024-03-01", iso_b="2024-03-01"):
    """Two same-branch units at two different sites, each site carrying its own stated class."""
    return [
        entity("site_x", "basing_site", "Xray Field", site_type=site_a_class),
        entity("site_y", "basing_site", "Yankee Field", site_type=site_b_class),
        entity("u1", "unit", "Alpha Battery", service_branch="Air Force"),
        entity("u2", "unit", "Alpha Battery Unit", service_branch="Air Force"),
        triple("u1", "based-at", "site_x", iso=iso_a),
        triple("u2", "based-at", "site_y", iso=iso_b),
    ]


# ── the wall fires, on the right channel, with a reason ───────────────────────────────────────────

def test_a_stated_basing_conflict_at_overlapping_times_within_one_class_hard_walls() -> None:
    """Two units at two garrisons at the same time are two units — and the wall is DRAWN, not silent."""
    part = resolve(_two_units_at("garrison", "garrison"), _cfg())

    assert not [p for p in part.same_as if {p[0], p[1]} <= {"u1", "u2"}], (
        "a stated basing conflict at overlapping times did not stop the merge (G18)"
    )
    assert ("u1", "u2") in part.distinct_from, (
        "the wall is not on the `veto` channel: it must be hard AND transitive AND drawn. Consulted inside "
        "`vetoed()` only — how the geo veto is wired — it would be pairwise and invisible while G18 still "
        "passed (§5a)"
    )


def test_the_wall_carries_an_analyst_visible_reason() -> None:
    """A wall nobody can read is indistinguishable from a missing edge."""
    part = resolve(_two_units_at("garrison", "garrison"), _cfg())
    reason = part.wall_reasons.get("u1|u2", "")

    assert "based-at" in reason and "overlapping times" in reason, (
        f"the wall's grounds are not stated: {reason!r}. A curated do-not-merge needs no explanation — an "
        "analyst wrote it — but a wall the SYSTEM derived is a finding, and a finding with no readable "
        "grounds cannot be argued with"
    )
    assert "garrison" in reason, "the reason must name the site class the wall fired within (C1)"


def test_the_wall_holds_transitively_not_merely_pairwise() -> None:
    """The property the channel buys: no CHAIN of merges may fuse the two either.

    A third profile that looks like both would, on a pairwise-only wall, merge with each in turn and put the
    walled pair in one cluster by transitivity — the wall holding on the pair while failing at the thing the
    pair stands for.
    """
    claims = _two_units_at("garrison", "garrison") + [
        entity("u3", "unit", "Alpha Battery", service_branch="Air Force"),
    ]
    part = resolve(claims, _cfg())
    canonical = {**part.entity_canonical}

    def root(x: str) -> str:
        return canonical.get(x, x)

    assert root("u1") != root("u2"), (
        "a chain of merges through a third look-alike put the walled pair into one cluster — the wall is "
        "pairwise, not transitive (§5a: the geo-veto wiring, which G18 would pass over)"
    )


# ── C1: a DIFFERING class is not a conflict ───────────────────────────────────────────────────────

def test_a_differing_site_class_is_not_a_conflict() -> None:
    """One unit at its garrison and concurrently at a forward site is ONE unit with two basings (C1).

    This is the clause R1.3 needed and G18 originally contradicted: without it the wall would fire on the very
    scenario R1.3 describes, and no amount of relational evidence could ever put the two mentions together.
    """
    part = resolve(_two_units_at("garrison", "airfield"), _cfg())

    assert ("u1", "u2") not in part.distinct_from, (
        "the wall fired across two DIFFERENT site classes — a garrison and a forward airfield are two valid "
        "concurrent basings, not two units (C1)"
    )


def test_an_unreadable_class_neither_walls_nor_fuses_and_says_so() -> None:
    """C7's third state on the relationship rail — all three parts, or none.

    An unmappable stated class must not wall (that would shatter a legitimate merge on a value we cannot read)
    and must not let the pair confirm (that would assert an identity the evidence does not support). And it
    must say which — a gap that does not bind the fusion path is decoration.
    """
    part = resolve(_two_units_at("garrison", "some improvised revetment thing"), _cfg())
    reason = " ".join(part.candidate_reasons.values())

    assert ("u1", "u2") not in part.distinct_from, (
        "an unreadable site class WALLED the pair — a false wall shatters legitimate merges (C7)"
    )
    assert not [p for p in part.same_as if {p[0], p[1]} <= {"u1", "u2"}], (
        "an unreadable site class let the pair FUSE — the gap must bind the fusion path, not annotate it (C7)"
    )
    assert "unreadable" in reason and "closed vocabulary" in reason, (
        f"the third state is silent: {reason!r}"
    )


def test_a_partial_tag_over_one_subject_collapses_to_one_bucket() -> None:
    """C1 as amended by S2: the decision is per (subject, predicate) over EVERY basing of that subject.

    One unit with two basings, one class readable and one not. A **per-edge** tag would put them in different
    buckets — and separation IS de-confliction, so the other unit's garrison basing would silently stop
    conflicting with the readable one. S2 measured exactly this killing the flagship relocation, with no gap
    and no flag, while the code still looked deterministic. So an unreadable class anywhere in a subject's
    basings must collapse **all** of them to one bucket.
    """
    claims = [
        entity("site_x", "basing_site", "Xray Field", site_type="garrison"),
        entity("site_y", "basing_site", "Yankee Field", site_type="not in the vocabulary"),
        entity("site_z", "basing_site", "Zulu Field", site_type="garrison"),
        entity("u1", "unit", "Alpha Battery", service_branch="Air Force"),
        entity("u2", "unit", "Alpha Battery Unit", service_branch="Air Force"),
        triple("u1", "based-at", "site_x", iso="2024-03-01"),
        triple("u1", "based-at", "site_y", iso="2024-03-01"),
        triple("u2", "based-at", "site_z", iso="2024-03-01"),
    ]
    part = resolve(claims, _cfg())

    assert not [p for p in part.same_as if {p[0], p[1]} <= {"u1", "u2"}], (
        "with one of u1's basings unreadable the pair still FUSED — the per-subject rule collapsed nothing, so "
        "a partial tag de-conflicted the readable pair by separation (C1 as amended)"
    )
    assert ("u1", "u2") not in part.distinct_from, (
        "an unreadable class produced a hard WALL rather than the third state (C7)"
    )


# ── C11: the operated-by arm has a real producer, so it can actually fire ─────────────────────────

def test_a_stated_operator_conflict_walls_with_no_site_class_scoping() -> None:
    """G18's other arm. A change of operator is never a relocation, so nothing de-conflicts it.

    S2 declared ``operated-by`` non-extractor, so nothing could emit a *stated* one and this arm was
    fixture-only forever — a declared predicate with no producer makes the gate lie, going green while half
    the behaviour it names is unreachable. C11 gave it a producer; this is the behaviour that producer feeds.
    """
    claims = [
        entity("op_a", "operator", "Air Force"),
        entity("op_b", "operator", "Army"),
        entity("u1", "unit", "Alpha Battery"),
        entity("u2", "unit", "Alpha Battery Unit"),
        triple("u1", "operated-by", "op_a", iso="2024-03-01"),
        triple("u2", "operated-by", "op_b", iso="2024-03-01"),
    ]
    part = resolve(claims, _cfg())

    assert ("u1", "u2") in part.distinct_from, (
        "a stated operator conflict at overlapping times did not wall — for an operator-scoped order of "
        "battle this is the costliest conflation there is (D-13.8/G18/C11)"
    )
    assert "operated-by" in part.wall_reasons.get("u1|u2", "")


# ── the biting clauses ────────────────────────────────────────────────────────────────────────────

def test_sequential_basings_are_a_relocation_not_a_wall() -> None:
    """Non-overlapping times are one unit that MOVED — the flagship beat, which the wall must not eat.

    Without this the gate would pass by walling every basing pair, and walling the relocation is precisely how
    an over-broad guard destroys the thing it was protecting (S2's round-1 defect, in a different place).
    """
    claims = _two_units_at("garrison", "garrison", iso_a="2021-05-01", iso_b="2024-03-01")
    part = resolve(claims, _cfg())

    assert ("u1", "u2") not in part.distinct_from, (
        "two basings at DIFFERENT times were walled — that is a relocation, and walling it destroys the "
        "supersede beat the system exists to draw"
    )


def test_a_derived_basing_never_walls_on_its_own() -> None:
    """Only a **stated** relationship walls. A rebuild-derived basing is not a source saying "it is there".

    The derivation supplies the usual unstated case from a sighting plus an induction; letting it wall would
    let one inference refuse an identity, which inverts the confidence ordering the whole two-layer basing
    model rests on.
    """
    claims = _two_units_at("garrison", "garrison")
    derived = [c.model_copy(update={"kind": "inference", "premises": ["seed-1"]})
               if c.asserts == "relationship" else c for c in claims]
    part = resolve(derived, _cfg())

    assert ("u1", "u2") not in part.distinct_from, (
        "a DERIVED basing walled a merge — only a stated relationship may (D-13.8)"
    )


def test_with_the_stage_flag_off_no_wall_exists() -> None:
    """Flag off ⇒ the whole rail is absent. Asserted, not assumed."""
    part = resolve(_two_units_at("garrison", "garrison"),
                   mk_config(attribute_roles=ROLES, ontology=ONTOLOGY,
                             name_alone_caps_at_possible=True))

    assert ("u1", "u2") not in part.distinct_from and not part.wall_reasons, (
        "the relationship wall fired with the flag OFF — flag-off must be byte-identical to S2"
    )
