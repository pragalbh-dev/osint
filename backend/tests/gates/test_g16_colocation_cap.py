"""G16 — the co-location cap, asserted on the **observable outcome** (C2's three parts).

**This is anti-fabrication machinery, not order-of-battle hygiene, and the distinction is the whole gate.**
``based-at`` is FUNCTIONAL and keyed on the unit alone, so fusing two co-located batteries makes their two
sites *one unit's before-and-after*. ``promote_supersessions`` then promotes the pair, **draws** a relocation
edge nobody reported, **pops the pair out of the analyst's queue** as machine-adjudicated, and — the
consequence the spike itself missed — **deletes the retired edge's Known Gap**, turning an edge correctly
labelled ``insufficient`` into ``stale`` with no gap at all. So one identity error both fabricates a movement
assessment *and* deletes the system's own admission of ignorance, with the human removed. A gate that asserts
only "no confirmed merge" goes green one stage upstream of that harm.

Hence C2: assert (i) no confirmed formation merge, (ii) both formation nodes survive, (iii) no drawn
relocation — and expect a **presence-level** merge in the same case, which must not fail the gate.

Abstract fixtures throughout (ruling M4): the corpus holds essentially one numbered formation, so it cannot
exercise this at all.
"""

from __future__ import annotations

from chanakya.resolve import resolve
from tests.resolve._helpers import entity, mk_config, triple

#: Everything the cap needs, and nothing else — so a failure names the mechanism rather than the config.
EARNED = {
    "name_ceiling": "possible",
    "colocation_ceiling": "probable",
    "formation_types": ["unit"],
    "presence_types": ["presence"],
    "colocation_predicates": ["based-at", "observed-at", "instance-of", "operated-by", "equips",
                              "inducted-into"],
    "formation_discriminators": ["equipment_fingerprint", "parent_unit"],
}


#: The unit attributes this fixture declares identity-bearing. Needed for the cap to be *load-bearing* at all:
#: with no declared role the discriminator sub-signal is 0, the pair never reaches the auto band, and the cap
#: would be asserting the absence of a merge that was never going to happen. Declaring `service_branch`
#: (shared by construction in a co-location case, and NOT a unit-level discriminator) is what puts the pair in
#: the auto band on co-location alone — so the cap has something real to withhold.
ROLES = {
    "unit": {
        "service_branch": {"role": "supporting", "time_role": "durable"},
        "parent_unit": {"role": "supporting", "time_role": "durable"},
        "equipment_fingerprint": {"role": "supporting", "time_role": "durable"},
    }
}


def _cfg(**over):
    over.setdefault("attribute_roles", ROLES)
    return mk_config(earned_identity={**EARNED, **over.pop("earned", {})},
                     name_alone_caps_at_possible=True, **over)


def _two_colocated_formations(**unit_attrs):
    """Two formations that share their design, their site and their operator — and nothing else.

    Deliberately given DIFFERENT names, so the pair is reached by *relational* blocking rather than by any
    name route: the point is that co-location alone carries them, and a name similarity would confound it.
    """
    return [
        entity("site_a", "basing_site", "Alpha Airfield", site_type="airfield"),
        entity("var_x", "variant", "System-X"),
        entity("u1", "unit", "First Battery", service_branch="Air Force", **unit_attrs),
        entity("u2", "unit", "Second Battery", service_branch="Air Force", **unit_attrs),
        triple("u1", "based-at", "site_a", iso="2024-01-01"),
        triple("u2", "based-at", "site_a", iso="2024-01-01"),
        triple("var_x", "inducted-into", "u1", iso="2024-01-01"),
        triple("var_x", "inducted-into", "u2", iso="2024-01-01"),
    ]


# ── C2 (i) + (ii): no confirmed formation merge, both nodes survive ───────────────────────────────

def test_co_location_alone_never_confirms_a_formation_merge() -> None:
    """Shared design + site + operator is a fact about dispersal, not about identity.

    Two batteries at one airfield running one system under one branch share every one of those links **by
    construction**. The relational term reads that as "identical neighbourhood" — which is exactly the signal
    the cap exists to distrust.
    """
    part = resolve(_two_colocated_formations(), _cfg())
    fused = [(a, b) for a, b in part.same_as if {a, b} <= {"u1", "u2"}]

    assert not fused, (
        f"two co-located formations were CONFIRMED as one: {fused}. `based-at` is functional and unit-keyed, "
        "so this merge makes their two sites one unit's before/after — the supersede path then draws a "
        "relocation nobody reported and removes the analyst (D-13.14/G16)"
    )


def test_the_capped_pair_reaches_the_analyst_with_a_reason_naming_what_is_missing() -> None:
    """Capped at ``probable`` means *queued*, not dropped: the cap states what would lift it.

    Withholding a merge silently would mis-task the analyst as surely as merging wrongly fabricates — an
    honest system says "these two might be one unit; here is the discriminator nobody stated".
    """
    part = resolve(_two_colocated_formations(), _cfg())
    reasons = " ".join(part.candidate_reasons.values())

    assert any({a, b} <= {"u1", "u2"} for a, b in part.candidates), (
        "the capped formation pair is not in the analyst's queue — a cap must block the merge AND guarantee "
        "the review, never silently withhold"
    )
    assert "co-location is not identity" in reasons and "unit-level discriminator" in reasons, (
        f"the reason does not name the cap or what would lift it: {reasons!r}"
    )


# ── C2 (iii): no drawn relocation ────────────────────────────────────────────────────────────────

def test_no_relocation_edge_is_drawn_between_the_two_sites() -> None:
    """The D1 clause. The harm is not the merge — it is the *fabricated movement* the merge licenses.

    Two co-located formations at ONE site cannot produce a supersede pair at all once they stay apart, so this
    asserts the absence at the level the analyst would actually see it: no ``supersedes`` link anywhere in the
    partition's own decisions, and nothing claiming the two sites are one unit's before/after.
    """
    part = resolve(_two_colocated_formations(), _cfg())

    assert not [p for p in part.same_as if "site" in p[0] and "site" in p[1]], (
        "the two sites were fused, which is how a relocation gets manufactured out of an identity error"
    )
    assert "u1" not in part.entity_canonical and "u2" not in part.entity_canonical, (
        "one formation was collapsed onto the other — the before/after the supersede path would then draw"
    )


# ── the biting clause: the cap LIFTS on a unit-level discriminator ────────────────────────────────

def test_an_agreeing_unit_level_discriminator_lifts_the_cap() -> None:
    """*"Confirming a formation needs a unit-level discriminator"* — so one must actually confirm it.

    Without this the gate would pass by refusing every formation merge, and an implementation that never
    confirms anything passes every absence assertion while mis-tasking the analyst on all of them. The cap is
    a cap, not a ban: a discriminator that is about the *formation* rather than about where it is standing
    clears it.
    """
    claims = _two_colocated_formations(parent_unit="1 AD Command", equipment_fingerprint="4x TEL")
    part = resolve(claims, _cfg())
    fused = [(a, b) for a, b in part.same_as if {a, b} <= {"u1", "u2"}]

    assert fused, (
        "an agreeing unit-level discriminator did not lift the co-location cap — G16 has become a blanket "
        "refusal of formation merges, and a gate that passes by refusing everything is a gate that lies"
    )


def test_a_presence_level_merge_in_the_same_case_is_not_capped() -> None:
    """C2 explicitly: *a presence-level merge in the same case is EXPECTED and must not fail the gate.*

    A presence asserts only "this kit was seen at this place in this window", which is precisely what two
    co-located reports DO corroborate. Capping it would be the mirror error — refusing the weaker claim the
    evidence actually supports because the stronger one is unsupported.
    """
    claims = [
        entity("site_a", "basing_site", "Alpha Airfield", site_type="airfield"),
        entity("p1", "presence", "System-X at Alpha", operator_branch="Air Force", design="System-X"),
        entity("p2", "presence", "System-X at Alpha", operator_branch="Air Force", design="System-X"),
        triple("p1", "observed-at", "site_a", iso="2024-01-01"),
        triple("p2", "observed-at", "site_a", iso="2024-01-01"),
    ]
    part = resolve(claims, _cfg())

    assert not [(a, b) for a, b in part.candidates if {a, b} <= {"p1", "p2"}], (
        "the presence pair was pushed into the review queue by the co-location cap — the cap is scoped to "
        "FORMATIONS, and a presence merge in a co-location case is the expected outcome (C2)"
    )


# ── the ceiling's VALUE means what it says ─────────────────────────────────────────────────────────

def test_a_ceiling_declared_confirmed_PERMITS_the_fusion() -> None:
    """``colocation_ceiling: confirmed`` lifts the cap — the value is honoured, not merely truthy.

    The three ceilings were read as a truthiness test, so ANY non-empty value withheld identically:
    ``confirmed`` behaved exactly like ``probable``, and the only way to lift a cap was to DELETE the key. A
    config author who wrote ``confirmed`` — "co-location may confirm a formation on this deployment" — got the
    opposite of what they asked for, silently, in the block whose header promises to hold every cap. Config
    that reads as a decision the code never took is worse than a missing feature.

    Asserted on the outcome rather than on the reader, because the reader is not where the harm was: the cap
    must actually not fire.
    """
    part = resolve(_two_colocated_formations(), _cfg(earned={"colocation_ceiling": "confirmed"}))
    reasons = " ".join(part.candidate_reasons.values())

    assert "co-location is not identity" not in reasons, (
        "the co-location cap fired at ceiling `confirmed` — the declared value is being read as a bare "
        "truthiness test, which is what made `confirmed` and `probable` indistinguishable"
    )


def test_an_undeclared_ceiling_leaves_the_cap_with_nothing_to_apply() -> None:
    """The absent case is the same as every other absent threshold in the reader: the mechanism is inert."""
    part = resolve(_two_colocated_formations(), _cfg(earned={"colocation_ceiling": ""}))

    assert "co-location is not identity" not in " ".join(part.candidate_reasons.values())


def test_a_ceiling_outside_the_BAND_VOCABULARY_is_rejected_at_load() -> None:
    """The other half: a value the code does not honour must be refused, not read as a withholding cap.

    Honouring ``confirmed`` is only safe if an unrecognised string cannot quietly take the withholding path —
    otherwise a typo (``possibly``, ``none``, ``off``) still caps, and the config still says something the code
    does not do.
    """
    from chanakya.resolve.rconfig import CeilingValueError, ResolveConfig

    for bad in ("possibly", "none", "off", "true"):
        try:
            ResolveConfig.from_bundle(_cfg(earned={"colocation_ceiling": bad}))
        except CeilingValueError:
            continue
        raise AssertionError(f"colocation_ceiling={bad!r} loaded silently instead of being refused")
