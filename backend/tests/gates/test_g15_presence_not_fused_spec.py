"""G15 (amended) — **presence is not fused into formation**, and a truncated attribution names its gap.

The gate row (plan §5): "An ``observed-at`` equipment sighting never becomes a ``based-at`` formation basing
without organizational evidence (``inducted-into`` or a stated formation); the two citizens stay distinct."

The amendment (plan §5a, defect **D2**) is the half that bites, and it is why this file exists:

    "As written it **passes vacuously** — ``basing.find_candidates`` already skips when no formation link
    exists (``ingest/basing.py:296-300``), so the asserted behaviour is *current* behaviour. Keep it as a
    regression guard and **add the clause that bites**: an **ambiguous or truncated formation attribution
    must produce a named gap**. Today ``formations[:max_units]`` (``basing.py:301``,
    ``max_units_per_site: 1``) silently discards a second candidate formation while **every other rejection
    path appends a ``SkipRecord``** — an order-of-battle undercount with **no merge involved**, which is why
    neither G15 nor G16 can currently see it. *Two candidate formations ⇒ two attributions, or one plus an
    explicit named gap. Never a silent pick.*"

D2 also fixes where the requirement lands: "This is a requirement on **S2's replacement** (the pass itself is
deleted and replaced by a rebuild-derived edge — plan §7 RK-LAYER item 4), so it must be carried forward
rather than patched into a doomed file." Hence every assertion here is over ``rebuild()``, never over
``find_candidates`` — a test written against the deleted function would die with it.

**Non-vacuity.** The D2 clause is asserted *differentially*: the same fixture is rebuilt with one candidate
formation and with two, and the two-candidate rebuild must show the second candidate somewhere. A gate that
merely asserted "one attribution exists" would go green on the silent pick.
"""

from __future__ import annotations

from tests import _rk_layer as rk

DESIGN, SITE = "hq9p", "site_rahwali"
UNIT_A, UNIT_B = "unit_8ad", "unit_12ad"
BASING, SIGHTING, INDUCTION = "based-at", "observed-at", "inducted-into"


def _cfg():
    return rk.fixture_config()


def _base_claims() -> list:
    return [
        rk.entity_claim(DESIGN, "variant", name="HQ-9/P"),
        rk.entity_claim(SITE, "basing_site", name="Rahwali",
                        attrs=rk.coords(32.28, 74.13, "rahwali") | {"occupancy_state": "occupied"}),
        rk.rel_claim("c-obs", DESIGN, SIGHTING, SITE, iso="2025-03-29"),
    ]


def _formation(unit: str, cid: str, sid: str = "s", designator: str = "8th AD Bn") -> list:
    return [
        rk.entity_claim(unit, "unit", name=designator, attrs={"designator": designator},
                        cid=f"ent-{unit}", sid=sid),
        rk.rel_claim(cid, DESIGN, INDUCTION, unit, iso="2021-06-01", sid=sid),
    ]


def _gap_texts(view) -> list[str]:
    return [
        f"{g.related_ref}|{g.what_missing}|{'/'.join(g.missing_slots)}" for g in view.known_gaps
    ]


# ── the regression clause (keep) ─────────────────────────────────────────────────────────────────

def test_a_sighting_without_organizational_evidence_never_becomes_a_basing() -> None:
    """G15 as originally written — kept as a regression guard.

    spine/13 §3a: a satellite frame "can honestly state that equipment is at a place, not that a named
    formation is based there". The corpus "contains a recycled-image trap and a grade-E relocation spoof built
    to punish a system that collapses 'kit was photographed here' into 'this formation is stationed here'"
    (``ingest/basing.py``).
    """
    view = rk.build_view(_cfg(), _base_claims())

    assert not rk.edges_of(view, BASING), (
        f"a bare sighting produced a formation basing "
        f"{[(e.source, e.target) for e in rk.edges_of(view, BASING)]} with no organizational evidence — "
        "G15: the two citizens stay distinct"
    )


def test_a_sighting_plus_an_induction_does_derive_one_attribution() -> None:
    """The precondition for the D2 clause below: with exactly one candidate formation the derivation fires.

    Asserted separately so the differential test cannot pass by deriving *nothing* in both arms — "a gate
    that cannot fail is a gate that lies" (§5a).
    """
    view = rk.build_view(_cfg(), _base_claims() + _formation(UNIT_A, "c-ind-a"))
    derived = rk.edges_of(view, BASING)

    assert [(e.source, e.target) for e in derived] == [(UNIT_A, SITE)], (
        f"one candidate formation derived {[(e.source, e.target) for e in derived]} — §7 RK-LAYER 4 has "
        f"rebuild() materialize the derived `based-at` from the triangle. {rk.flag_report()}"
    )


# ── the D2 clause: never a silent pick ───────────────────────────────────────────────────────────

def test_two_candidate_formations_are_never_silently_truncated() -> None:
    """**D2 / G15 amended**: "*Two candidate formations ⇒ two attributions, or one plus an explicit named
    gap. Never a silent pick.*"

    The harm is an order-of-battle undercount with **no merge involved** — "the second vanishes: no skip
    record, no coverage item, no gap … which means **neither G15 nor G16 can see it**". For an order-of-battle
    product, quietly dropping a formation is the harmful direction (D-13.14).
    """
    one = rk.build_view(_cfg(), _base_claims() + _formation(UNIT_A, "c-ind-a"))
    two = rk.build_view(
        _cfg(),
        _base_claims()
        + _formation(UNIT_A, "c-ind-a")
        + _formation(UNIT_B, "c-ind-b", sid="s2", designator="12th AD Bn"),
    )

    attributions_one = [(e.source, e.target) for e in rk.edges_of(one, BASING)]
    attributions_two = [(e.source, e.target) for e in rk.edges_of(two, BASING)]
    assert attributions_one, (
        f"the single-candidate control derived nothing, so the differential below is vacuous. "
        f"{rk.flag_report()}"
    )

    two_attributions = len(attributions_two) >= 2
    new_gaps = sorted(set(_gap_texts(two)) - set(_gap_texts(one)))
    named_second = two_attributions or bool(new_gaps)

    assert named_second, (
        f"two candidate formations produced {attributions_two} and no new gap relative to the "
        f"single-candidate control (gaps: {_gap_texts(two)}) — the second candidate was discarded with no "
        "record at all. D2: 'two attributions, or one plus an explicit named gap. Never a silent pick.' "
        "Every other rejection path in the old pass appended a SkipRecord; the truncation appended nothing, "
        f"which is exactly the invisibility this clause closes. {rk.flag_report()}"
    )


def test_a_truncated_attribution_names_which_candidate_it_dropped() -> None:
    """The stronger reading of "an **explicitly named** gap" (§5a G15): if only one attribution is drawn, the
    analyst must be able to see *which* other formation was in contention.

    "the residual is a first-class coverage item ('presence confirmed; formation count unresolved;
    designation coverage needed')" — D-13.14. A gap that says only "ambiguous" cannot be tasked.
    """
    view = rk.build_view(
        _cfg(),
        _base_claims()
        + _formation(UNIT_A, "c-ind-a")
        + _formation(UNIT_B, "c-ind-b", sid="s2", designator="12th AD Bn"),
    )
    drawn = {e.source for e in rk.edges_of(view, BASING)}

    if {UNIT_A, UNIT_B} <= drawn:
        return  # both attributions drawn — nothing was dropped, so there is nothing to name

    dropped = sorted({UNIT_A, UNIT_B} - drawn)
    haystack = " ".join(_gap_texts(view)) + " ".join(
        str(v) for e in rk.edges_of(view, BASING) for v in (e.attrs or {}).values()
    )
    assert dropped and any(unit in haystack for unit in dropped), (
        f"the attribution was truncated to {sorted(drawn)} and nothing names the dropped candidate(s) "
        f"{dropped}. Gaps: {_gap_texts(view)}; derived-edge attrs: "
        f"{[e.attrs for e in rk.edges_of(view, BASING)]} — D2 requires the dropped candidate to be "
        f"recorded, not merely the existence of ambiguity. {rk.flag_report()}"
    )


def test_the_undercount_is_visible_without_any_merge_being_involved() -> None:
    """D2's framing, asserted as a property of the fixture: "an order-of-battle undercount with **no merge
    involved**, which is why neither G15 nor G16 can currently see it."

    If the two candidate formations were to *fuse*, this suite would be measuring the co-location cap (S3's
    G16) instead of D2. The fixture keeps them distinct on purpose — two different designators — and says so.
    """
    view = rk.build_view(
        _cfg(),
        _base_claims()
        + _formation(UNIT_A, "c-ind-a")
        + _formation(UNIT_B, "c-ind-b", sid="s2", designator="12th AD Bn"),
    )
    units = {n.id for n in rk.nodes_of(view, "unit")}

    assert units == {UNIT_A, UNIT_B}, (
        f"the two candidate formations resolved to {sorted(units)} — this gate must exercise the "
        "no-merge undercount path (D2); a fusion here would make it a G16/S3 test instead"
    )
