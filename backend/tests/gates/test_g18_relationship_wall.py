"""G18 — the relationship-conflict wall: two units at different sites at overlapping times are two units.

Authored from the session spec alone. The rule (§7 RK-COREF 8, quoted):

    "A **stated** ``based-at`` / ``operated-by`` conflict at overlapping times **within one ``site_type``**
    hard-walls a merge. **C1 as amended by S2: the rule is per ``(subject, predicate)`` over every basing of
    that subject, applied as a post-pass after derivation — never a key input.** A per-edge tag silently
    killed the flagship relocation: **separation *is* de-confliction, so a partial tag is worse than none.**
    **G18 must name the wall channel and assert an analyst-visible reason** — built the geo-veto way it would
    be non-transitive *and* invisible while the gate passed."

Why the channel matters (§5a G18): "membership in ``veto`` is hard **and transitive** and re-applied in
``finalise``, whereas consultation inside ``vetoed()`` only is hard, **pairwise and invisible** to
``finalise``, the D9 bridge alarm and ``res.distinct_from`` (how the geo veto is wired)."

C1's boundary, in both directions: "Two candidate instances both at a *garrison* at overlapping times are
different units (the wall fires). One unit at its garrison *and* concurrently at a forward site is one unit
with two basings (the wall does not fire)." And ``unknown`` ``site_type`` "must **fail safe** (same bucket /
raise, never de-conflicted)".

**Fixture-only, by measurement — ruling M4.** "Zero coreference annotations exist anywhere in the frozen
bundles, and three fixture families are untestable **in principle** rather than merely uncovered. So **G16,
G18 and G19 are all fixture-only** for now. That is the §5a-bis *inert-because-the-data-is-sparse* case with
the mechanism at full strength — **not** hidden-to-protect-a-fixture." So do **not** add a corpus-dependent
assertion to this gate: it would fail for the wrong reason and pressure someone to weaken the mechanism.

"""

from __future__ import annotations

import pytest

from tests import _rk_coref as rc
from tests import _rk_layer as rk

DESCRIPTOR = "air defence battery"

#: Read from the shipped vocabulary rather than hand-picked, so a config change cannot leave the gate
#: asserting on a class the ontology no longer declares.
SAME_CLASS = rk.same_class_pair()

#: **A gate's control must use an evidence class no other gate restrains** — the standing rule ruling M15
#: already applied to G19, applied here after this file was measured failing it.
#:
#: The measurement: stub ``_relationship_walls`` to return nothing — i.e. **delete the wall this file is
#: about** — and the file went 11 passed / 1 failed. Delete G16's co-location cap as well and it went
#: 5 passed / 7 failed. So six of the twelve tests were being satisfied by the *cap*, not by the wall, and
#: ``visible_rationale`` was reading the cap's reason string rather than ``distinct_from`` membership.
#: A gate that stays green while its own mechanism is deleted certifies nothing.
#:
#: The cause was structural: two same-named formations sharing a design and an operator and nothing else is
#: **exactly** G16's co-location evidence class, so G16 was always going to refuse the pair first. The fix
#: is the one the cap itself documents — "a unit-level discriminator agrees ⇒ more than co-location ⇒ the
#: cap lifts". Both mentions state an agreeing ``parent_unit``, read from the shipped
#: ``formation_discriminators``, so the pair has a legitimate route to fusion that G16 permits and the wall
#: is the only thing left that can refuse it. Nothing is relaxed and neither gate bends: G16 governs
#: co-location, and this file now stands on its own mechanism.
DISCRIMINATOR_ATTR = "parent_unit"
DISCRIMINATOR_VALUE = "12 Air Defence Brigade"


def _vocabulary_pair() -> tuple[str, str]:
    """Two DIFFERENT **config-declared** site classes — a garrison and a forward site, in C1's language.

    Read from config, never invented: "**The raw stated string is NEVER the key.** Keying happens on the
    normalized class" (ruling L1 rule 2), so a test that made up its own strings would assert against a
    mapping nobody declared.
    """
    vocab = rk.site_type_vocabulary()
    assert vocab, "config declares no closed `site_type` vocabulary, so C1 has no classes to key on (L1)"
    values = next(iter(vocab.values()))
    assert len(values) >= 2, f"the declared vocabulary {values} cannot express two different classes"
    return values[0], values[1]


def _stated_conflict(
    *,
    iso_b: str = "2021-01-01",
    classes: tuple[str, str] | None = None,
    predicate: str = "based-at",
    second_basing: tuple[str, str, str] | None = None,
) -> list:
    """Two formation mentions, each with a **stated** placement — the discriminating inputs are explicit.

    ``iso_b``  — overlapping (default) vs later; ``classes`` — one class at both ends (default) vs two;
    ``second_basing`` — an extra basing of *subject A* (site id, class, date), which is what makes C1's
    per-``(subject, predicate)`` rule observable.
    """
    class_a, class_b = classes or SAME_CLASS
    target = "operator" if predicate == "operated-by" else "basing_site"
    # The agreeing unit-level discriminator (see DISCRIMINATOR_ATTR) lifts G16's co-location cap, so the
    # only mechanism that can refuse this pair is the wall under test.
    unit_attrs = {DISCRIMINATOR_ATTR: DISCRIMINATOR_VALUE}
    claims = [
        rc.ent("unit_a", "unit", DESCRIPTOR, attrs=dict(unit_attrs), doc="d1"),
        rc.ent("unit_b", "unit", DESCRIPTOR, attrs=dict(unit_attrs), doc="d2", sid="mid"),
        *rc.shared_neighbours("unit_a", "unit_b"),
    ]
    if target == "basing_site":
        claims += [
            rc.site("site_1", "Bravo Depot", site_class=class_a, doc="d1"),
            rc.site("site_2", "Charlie Cantonment", site_class=class_b, lat=32.0, lon=72.6,
                    doc="d2", sid="mid"),
            rc.rel("r-ba-a", "unit_a", predicate, "site_1", doc="d1", iso="2021-01-01"),
            rc.rel("r-ba-b", "unit_b", predicate, "site_2", doc="d2", iso=iso_b, sid="mid"),
        ]
    else:
        claims += [
            rc.ent("op_1", "operator", "Pakistan Air Force", doc="d1"),
            rc.ent("op_2", "operator", "Pakistan Army", doc="d2", sid="mid"),
            rc.rel("r-op-a2", "unit_a", predicate, "op_1", doc="d1", iso="2021-01-01"),
            rc.rel("r-op-b2", "unit_b", predicate, "op_2", doc="d2", iso=iso_b, sid="mid"),
        ]
    if second_basing is not None:
        eid, klass, iso = second_basing
        claims += [
            rc.site(eid, "Delta Forward Site", site_class=klass, lat=31.5, lon=71.9, doc="d1"),
            rc.rel(f"r-ba-{eid}", "unit_a", "based-at", eid, doc="d1", iso=iso),
        ]
    return claims


# ── the wall fires, in the transitive channel, with a reason ─────────────────────────────────────

def test_a_stated_conflict_at_overlapping_times_walls_the_merge() -> None:
    """The core rule: "two units at different sites at overlapping times are different units"."""
    part = rc.part_of(_stated_conflict(), rc.bundle())

    assert not rc.fused(part, "unit_a", "unit_b"), (
        "two formation mentions stated at two different same-class sites at the same time were FUSED. The "
        "conflict is stated, not inferred, so this is not a low score to be out-weighed — D-13.8 makes it a "
        f"hard wall. same_as={part.same_as} breakdown={rc.signals(part, 'unit_a', 'unit_b')}"
    )


def test_the_wall_is_the_transitive_visible_channel_not_a_pairwise_consultation() -> None:
    """§5a G18: "The gate must name the channel and assert an analyst-visible reason."

    The channel is named by observing the two properties only the ``veto`` membership channel has: the pair
    is **surfaced** (``distinct_from`` / a candidate reason an analyst can read) and the wall is
    **transitive** — a bridge mention cannot fuse the two clusters it holds apart. Built the geo-veto way,
    the wall "is non-transitive *and unreported* and G18 still passes".
    """
    part = rc.part_of(_stated_conflict(), rc.bundle())

    assert rc.visible_rationale(part, "unit_a", "unit_b"), (
        "the pair was held apart with nothing an analyst can read: it is absent from `distinct_from` and "
        "carries no candidate reason. A wall consulted only inside `vetoed()` is invisible to `finalise`, "
        f"to the D9 bridge alarm and to the surfaced distinct-from edge. reasons={part.candidate_reasons} "
        f"distinct_from={part.distinct_from}"
    )


def test_the_wall_holds_transitively_through_a_bridge_mention() -> None:
    """The transitivity half, stated as behaviour: a third mention that looks like both ends must not fuse
    the two clusters the wall separates (``violates_veto_transitively`` is what only the ``veto`` set gets).
    """
    claims = _stated_conflict()
    claims += [
        rc.ent("unit_c", "unit", DESCRIPTOR, doc="d3", sid="mid"),
        rc.rel("r-ind-c", "d", "inducted-into", "unit_c", doc="d3", iso="2020-03-01", sid="mid"),
        rc.rel("r-op-c", "unit_c", "operated-by", "op", doc="d3", sid="mid"),
    ]
    part = rc.part_of(claims, rc.bundle())

    assert "unit_b" not in rc.cluster_of(part, "unit_a"), (
        "a third look-alike mention bridged the wall: unit_a and unit_b ended in one cluster via unit_c. "
        f"A cannot-link that only holds pairwise is not a wall. cluster={sorted(rc.cluster_of(part, 'unit_a'))}"
    )


def test_no_relational_score_can_out_weigh_the_wall() -> None:
    """G18's row: the wall is "**never overridable by a relational score**". Here the two mentions share
    every neighbour the graph has, which is the maximum the relational term can offer.
    """
    claims = _stated_conflict()
    claims += [
        rc.ent("ev", "contract_import_event", "KPQA-HC-2020-118834", doc="d1"),
        rc.rel("r-imp-a", "ev", "imported-by", "unit_a", doc="d1", iso="2020-05-01"),
        rc.rel("r-imp-b", "ev", "imported-by", "unit_b", doc="d2", iso="2020-05-01", sid="mid"),
    ]
    part = rc.part_of(claims, rc.bundle())

    assert not rc.fused(part, "unit_a", "unit_b"), (
        "a maximal shared neighbourhood carried the pair over a stated placement conflict. 'A hard wall no "
        f"similarity score may cross' is the whole distinction between a wall and a penalty. "
        f"breakdown={rc.signals(part, 'unit_a', 'unit_b')}"
    )


# ── the mirrors C1 forces (a wall that is too broad kills the flagship) ──────────────────────────

def test_a_later_placement_is_a_relocation_not_a_conflict() -> None:
    """C1's boundary in time. Non-overlapping placements are the relocation the system exists to show;
    walling them would delete the flagship beat — "separation *is* de-confliction".
    """
    part = rc.part_of(_stated_conflict(iso_b="2025-01-01"), rc.bundle())

    assert not rc.walled(part, "unit_a", "unit_b"), (
        "a placement four years later was read as a contradiction and walled. Two dated positions of one "
        "unit are its history; if that walls, no relocation can ever be earned."
    )


def test_a_differing_site_class_is_not_a_conflict() -> None:
    """C1 verbatim: "**A differing ``site_type`` is NOT a conflict**" — "One unit at its garrison *and*
    concurrently at a forward site is one unit with two basings (the wall does not fire)."
    """
    part = rc.part_of(_stated_conflict(classes=_vocabulary_pair()), rc.bundle())

    assert not rc.walled(part, "unit_a", "unit_b"), (
        f"a garrison basing and a {_vocabulary_pair()[1]} basing at overlapping times were walled as a "
        "contradiction. R1.3's scenario — a unit at its garrison and concurrently forward — is two valid "
        "basings, and this is the exact contradiction C1 was written to resolve."
    )


# ── C1 as amended: per (subject, predicate), and a PARTIAL classification never splits ───────────

def test_an_unmappable_site_class_neither_walls_nor_fuses() -> None:
    """C1 inherits C7 (ruling L1): an unmappable stated class "⇒ the third state: no de-confliction, no
    fusion, and a **named gap**. It must never silently de-conflict (the evasion direction is over-merge)
    and must never silently kill a supersede."

    ``site_type`` is unenumerated free text whose 15 corpus values "conflate **four different concepts**",
    so this is the common case, not the exotic one.
    """
    part = rc.part_of(_stated_conflict(classes=(SAME_CLASS[0], "observed-imagery-site")), rc.bundle())

    assert not rc.fused(part, "unit_a", "unit_b"), (
        "the pair fused while one end's stated site class could not be mapped to the declared vocabulary. "
        "Unknown must fail safe: 'we do not know whether these are the same kind of place' is not "
        f"'they are different kinds of place, so no conflict'. same_as={part.same_as}"
    )
    assert rc.visible_rationale(part, "unit_a", "unit_b"), (
        "the third state produced no named gap and no reason — the pair simply sat unresolved, which is how "
        f"an unmappable value silently becomes a non-event. reasons={part.candidate_reasons}"
    )


def test_a_partial_classification_does_not_silently_de_conflict_the_subject() -> None:
    """C1 as amended by S2, the clause that killed the flagship once:

        "over **every** basing of that subject, all classes known ⇒ de-conflict; **any** unknown ⇒ one
        untagged instance, nomination withdrawn, **named gap**. And because 'every basing' includes the
        rebuild-derived ones, the tag must be a **post-pass after derivation**, not a key input."

    Here subject A has two basings — one mappable, one not. A per-edge tag puts them in different buckets,
    the conflict quietly stops being visible, and the merge goes through with "code still deterministic".
    """
    part = rc.part_of(
        _stated_conflict(second_basing=("site_3", "stated_destination", "2021-01-01")),
        rc.bundle(),
    )

    assert not rc.fused(part, "unit_a", "unit_b"), (
        "the subject's own second, unclassifiable basing made the stated conflict invisible and the pair "
        "fused. Per-edge tagging is worse than none: 'separation IS de-confliction, so a partial tag is "
        f"worse than none'. same_as={part.same_as}"
    )
    assert rc.visible_rationale(part, "unit_a", "unit_b"), (
        "nothing names why the subject's placements could not be compared — the nomination was withdrawn "
        "in silence, which is exactly how the flagship relocation died with 'no gap, no flag'."
    )


# ── C11: the operated-by arm must have a producer, or say out loud that it does not ──────────────

def test_operated_by_is_extractor_emittable() -> None:
    """C11: "**S3 adds ``operated-by`` to the extractor contract.**" Otherwise "**nothing can emit a
    *stated* ``operated-by``**" and "a declared predicate with no producer makes the gate lie": G18 goes
    green while half the behaviour it names is unreachable.

    The declared fallback is *not* silence — "G18 must then declare in the gate itself that its
    ``operated-by`` arm is fixture-only, and it goes in the design-note disclosures" — which is what the
    companion test below does.
    """
    edges = {e["name"]: e for e in rk.shipped_ontology_yaml()["edge_types"]}
    declaration = edges.get("operated-by")

    assert declaration is not None, f"the ontology declares no `operated-by` edge: {sorted(edges)}"
    assert declaration.get("extractor") is True, (
        f"`operated-by` is declared {declaration!r} — non-extractor, so no source can ever state one and "
        "G18's operator arm is fixture-only forever. If that is the accepted outcome it must be stated in "
        "the gate and disclosed, never discovered later."
    )


def test_a_stated_operator_conflict_walls_the_merge() -> None:
    """The ``operated-by`` arm of G18 itself: "a **stated** ``based-at``/``operated-by`` conflict at
    overlapping times … hard-walls a merge". One unit is not operated by two services at once.
    """
    part = rc.part_of(_stated_conflict(predicate="operated-by"), rc.bundle())

    assert not rc.fused(part, "unit_a", "unit_b"), (
        "two mentions stated under two different operators at the same time were fused. Operator is the "
        "namespace of an order-of-battle map: 'never across operators within the instance layer'. "
        f"same_as={part.same_as}"
    )


@pytest.mark.parametrize("predicate", ["based-at", "operated-by"])
def test_both_arms_of_the_gate_are_exercised_on_stated_evidence(predicate: str) -> None:
    """A guard on the *gate*, not the code: both predicates named in G18 must actually be reachable here.

    §5a's lesson is that "a gate that cannot fail is a gate that lies" — so if one arm can only ever run on
    a fixture, this test is where that has to be admitted.
    """
    claims = _stated_conflict(predicate=predicate)
    stated = [c for c in claims if getattr(c.payload, "predicate", None) == predicate]

    assert len(stated) >= 2, f"the fixture states fewer than two {predicate} claims: {len(stated)}"
    edges = {e["name"]: e for e in rk.shipped_ontology_yaml()["edge_types"]}
    assert edges.get(predicate, {}).get("extractor") is True, (
        f"{predicate!r} is not extractor-emittable, so this arm of G18 can only ever fire on hand-written "
        "fixtures. That is C11's 'the gate half-lies' condition; declare it and disclose it."
    )
