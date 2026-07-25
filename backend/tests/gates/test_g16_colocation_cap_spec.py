"""G16 — the co-location cap. Two batteries at one base are not one battery.

Authored from the session spec alone (`artifacts/plan/sessions/RK-COREF.md` scope 7 + gates), never from
the implementation. Abstract fixture, as the gate list requires: "the corpus holds essentially one numbered
formation, one stated basing and zero serials, so it cannot exercise them."

**This is anti-fabrication machinery, not OOB hygiene** (§7 RK-COREF 7, quoted):

    "because ``based-at`` is functional and unit-keyed, a formation over-merge makes two sites one unit's
    before/after and the supersede path then draws a relocation, removes the analyst, and deletes the
    retired edge's Known Gap."

and REVIEW-VERDICT §4 on why the earlier framing was one consequence short:

    "the over-merge does not merely *add* a fabricated relocation — it **silently removes an existing honest
    refusal**, turning an edge correctly labelled ``insufficient`` (with a Known Gap naming the missing
    corroboration) into ``stale`` **with no gap at all**. So the same identity bug both fabricates a claim
    and deletes the system's own admission of ignorance."

C2 fixes what the gate asserts:

    "**G16 asserts (i)** no ``confirmed`` formation-level pair verdict on co-location alone, **(ii)** the
    resulting formation node count is preserved (both survive), **and (iii)** no drawn relocation edge (the
    D1 clause) … **no Known-Gap deletion / no ``insufficient → stale``** on the retired edge. A presence-level
    merge in the same case is *expected* and must not fail the gate."

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

#: A generic descriptor, not a designation: exactly what two co-located batteries share in open sources.
DESCRIPTOR = "air defence battery"
OLDER_EDGE = "e:unit_a:based-at:site_old"


def _cfg():
    """The shipped config over the shipped ontology, with the supersede floor READ from ``credibility.yaml``.

    ``rk.SUPERSEDE_FLOOR`` exists because a hand-copy of this block "silently omits any knob added later —
    which is exactly what happened: S2 added ``require_earned_identity`` … and R1.4(a)'s guard
    short-circuited so the fixture could never turn it on."
    """
    return rc.bundle(supersede_floor=dict(rk.SUPERSEDE_FLOOR))


def _colocated(names: tuple[str, str] = (DESCRIPTOR, DESCRIPTOR)) -> list:
    """Two formation mentions sharing design + operator + **one site**, and nothing unit-level.

    ``names`` is the discriminating input: identical descriptors are the co-location case; two distinct
    designations are the control, where fusing is refused for an independent reason.
    """
    return [
        rc.ent("unit_a", "unit", names[0], doc="d1"),
        rc.ent("unit_b", "unit", names[1], doc="d2", sid="mid"),
        rc.site("site", "Alpha Cantonment", doc="d1"),
        rc.rel("r-ba-a", "unit_a", "based-at", "site", doc="d1", iso="2021-03-01"),
        rc.rel("r-ba-b", "unit_b", "based-at", "site", doc="d2", iso="2021-03-05", sid="mid"),
        *rc.shared_neighbours("unit_a", "unit_b"),
    ]


def _split_basings(names: tuple[str, str] = (DESCRIPTOR, DESCRIPTOR)) -> list:
    """The D1 chain: the same shared evidence, but each formation carries its own dated basing.

    Both sites are the **same normalized class** and the dates do **not** overlap, so this is not G18's
    relationship conflict — it is precisely the case where fusing the two mentions manufactures a movement.
    The older basing is stated by a weak source, so it is the under-evidenced position D1 turns into a lie.
    """
    return [
        rc.ent("unit_a", "unit", names[0], doc="d1"),
        rc.ent("unit_b", "unit", names[1], doc="d2", sid="mid"),
        rc.site("site_old", "Bravo Depot", doc="d1", sid="lo"),
        rc.site("site_new", "Charlie Cantonment", lat=32.0, lon=72.6, doc="d2", sid="mid"),
        rc.rel("r-ba-a", "unit_a", "based-at", "site_old", doc="d1", iso="2021-01-01", sid="lo"),
        rc.rel("r-ba-b", "unit_b", "based-at", "site_new", doc="d2", iso="2025-01-01", sid="mid"),
        *rc.shared_neighbours("unit_a", "unit_b"),
    ]


def _with_failing_sufficiency(monkeypatch: pytest.MonkeyPatch, element_id: str) -> None:
    """Make exactly one element's evidence template fail, so it raises a real Known Gap.

    The idiom is ``tests/gates/test_g8_insufficient_first_class.py``'s: ``rebuild`` binds ``check`` at
    import, so it is patched in the pipeline module's namespace.
    """
    import chanakya.view.pipeline as pipeline
    from chanakya.schemas import SufficiencyEval

    real = pipeline.check

    def check(assertion, claims, config):
        if assertion.element_id == element_id:
            return SufficiencyEval(
                satisfied=False, missing_slots=["imagery_confirmation"],
                next_coverage_due="2026-10-01", ceiling="confirmable",
            )
        return real(assertion, claims, config)

    monkeypatch.setattr(pipeline, "check", check)


def _relocations(view) -> list[str]:
    """Every drawn relocation — the derived ``supersedes`` edges plus any retired basing."""
    return sorted(
        [e.id for e in rk.edges_of(view, "supersedes")]
        + [f"{e.id}->{e.superseded_by}" for e in rk.edges_of(view, "based-at") if e.superseded_by]
    )


# ── (i) no confirmed formation merge on co-location alone ────────────────────────────────────────

def test_co_location_never_confirms_a_formation_merge() -> None:
    """D-13.14 / G16: "Two instances sharing only design+site+operator cannot reach ``confirmed``
    formation-merge without a unit-level discriminator."
    """
    part = rc.part_of(_colocated(), _cfg())

    assert not rc.fused(part, "unit_a", "unit_b"), (
        "two formation mentions sharing a base, a design and an operator — and nothing unit-level — were "
        "CONFIRMED as one unit. That is an order-of-battle undercount by construction: every battery at a "
        f"base shares exactly this evidence. same_as={part.same_as} "
        f"breakdown={rc.signals(part, 'unit_a', 'unit_b')}"
    )


def test_co_location_still_reaches_the_analyst() -> None:
    """The mirror. D8's terminology correction: the cap is "**not fused; queued and reported**" — "stronger,
    and testable". A cap that dropped the pair would hide a real question instead of asking it.
    """
    part = rc.part_of(_colocated(), _cfg())

    assert rc.status(part, "unit_a", "unit_b") in ("probable", "possible"), (
        f"the co-located pair reads {rc.status(part, 'unit_a', 'unit_b')!r}: it was either fused or dropped "
        "entirely, and the analyst is never asked whether these two mentions are one battery. 'Residual "
        f"surfaced as a coverage item' requires the link to exist and stay sub-confirmed. "
        f"candidates={part.candidates} possible={part.possible}"
    )


def test_a_unit_level_discriminator_still_confirms() -> None:
    """The other mirror, and the reason G16 is a *cap* rather than a ban: "confirming a formation needs a
    unit-level discriminator" — when one is present, the merge must be earned and taken.
    """
    claims = [
        rc.ent("unit_a", "unit", "8th AD Battalion",
               attrs={"service_branch": "PAF", "designator": "8"}, doc="d1"),
        rc.ent("unit_b", "unit", "the 8 AD Bn",
               attrs={"service_branch": "PAF", "designator": "8"}, doc="d2", sid="mid"),
        rc.site("site", "Alpha Cantonment", doc="d1"),
        rc.rel("r-ba-a", "unit_a", "based-at", "site", doc="d1", iso="2021-03-01"),
        rc.rel("r-ba-b", "unit_b", "based-at", "site", doc="d2", iso="2021-03-05", sid="mid"),
        *rc.shared_neighbours("unit_a", "unit_b"),
    ]
    part = rc.part_of(claims, _cfg())

    assert rc.fused(part, "unit_a", "unit_b"), (
        "two co-located mentions stating the SAME (service_branch, designator) were not fused. G16 caps "
        "co-location; it does not forbid identity. A gate that refuses this fragments the ORBAT and calls "
        f"it caution. status={rc.status(part, 'unit_a', 'unit_b')}"
    )


def test_a_presence_level_merge_in_the_same_case_is_expected() -> None:
    """C2: "A presence-level merge in the same case is *expected* and must not fail the gate."

    This is the clause that stops the cap being implemented as "co-located things never merge". The two
    citizens are different assertions: the equipment seen at this base is one presence; which *formations*
    are stationed there is a separate, harder question.
    """
    lat, lon = 33.61639, 73.09972
    claims = [
        rc.ent("pr1", "presence", "HQ-X at Alpha", attrs=rk.coords(lat, lon, "alpha"), doc="d1"),
        rc.ent("pr2", "presence", "a SAM battery at Alpha", attrs=rk.coords(lat, lon, "alpha"),
               doc="d2", sid="mid"),
        rc.ent("d", "variant", "HQ-X", doc="d1"),
        rc.ent("op", "operator", "Air Force", doc="d1"),
        rc.rel("r1", "pr1", "instance-of", "d", doc="d1", iso="2025-03-01"),
        rc.rel("r2", "pr2", "instance-of", "d", doc="d2", iso="2025-03-02", sid="mid"),
        rc.rel("r3", "pr1", "operated-by", "op", doc="d1", iso="2025-03-01"),
        rc.rel("r4", "pr2", "operated-by", "op", doc="d2", iso="2025-03-02", sid="mid"),
    ]
    part = rc.part_of(claims, _cfg())

    assert rc.fused(part, "pr1", "pr2"), (
        "the presence-level pair did not merge on identical site + design + operator + window. C6 makes "
        "that geography *constitutive* for a presence, and C2 says the presence merge is expected — so a "
        f"cap that swallowed it has over-corrected. status={rc.status(part, 'pr1', 'pr2')}"
    )


# ── (ii) the formation node count is preserved ───────────────────────────────────────────────────

def test_both_formation_nodes_survive_the_rebuild() -> None:
    """C2 (ii): "the resulting formation node count is preserved (both survive)".

    Asserted on the rebuilt view rather than the partition, because that is where the undercount is read.
    """
    view = rk.build_view(_cfg(), _colocated())
    units = sorted(n.id for n in rk.nodes_of(view, "unit"))

    assert units == ["unit_a", "unit_b"], (
        f"the view holds {units} — the two co-located batteries collapsed into one formation node. This is "
        "the OOB undercount G16 names, and it is invisible to every other gate."
    )


# ── (iii) no drawn relocation, no deleted refusal ────────────────────────────────────────────────

def test_the_control_fixture_draws_no_relocation_and_raises_a_real_gap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-vacuity for the three absences below: with the two formations distinguished, the same claims
    produce no relocation and one honest Known Gap. Without this control, "no relocation was drawn" could
    pass simply because the fixture never had one to draw.
    """
    _with_failing_sufficiency(monkeypatch, OLDER_EDGE)
    view = rk.build_view(_cfg(), _split_basings(("8th AD Battalion", "12th AD Battalion")))

    assert sorted(n.id for n in rk.nodes_of(view, "unit")) == ["unit_a", "unit_b"]
    assert _relocations(view) == [], f"the control already draws {_relocations(view)}"
    assert [g.related_ref for g in view.known_gaps] == [OLDER_EDGE], (
        f"the control raised {[(g.related_ref, g.what_missing) for g in view.known_gaps]} — it must raise "
        "exactly one Known Gap, on the older basing, or the deletion assertion is vacuous"
    )
    older = {e.id: e for e in rk.edges_of(view, "based-at")}[OLDER_EDGE]
    assert older.status == "insufficient", (
        f"the older basing reads {older.status!r} in the control rather than 'insufficient' — the honest "
        "refusal is the thing D1 says gets laundered into 'stale'"
    )


def test_a_co_location_over_merge_draws_no_relocation(monkeypatch: pytest.MonkeyPatch) -> None:
    """C2 (iii) / the D1 clause: "assert the absence of a derived ``supersedes`` / drawn relocation edge,
    not merely the absence of a confirmed merge."

    "An identity error therefore becomes a **fabricated movement assessment with the human removed** — the
    non-negotiable breached structurally. Without this clause G16 goes green one stage upstream of the harm."
    """
    _with_failing_sufficiency(monkeypatch, OLDER_EDGE)
    view = rk.build_view(_cfg(), _split_basings())

    assert _relocations(view) == [], (
        f"a relocation was drawn: {_relocations(view)}. Nobody stated that anything moved — two documents "
        "described two batteries, and the identity error turned that into a movement. `based-at` is "
        "functional and unit-keyed, so the fusion alone is enough to manufacture the before/after."
    )


def test_the_retired_edges_known_gap_is_not_deleted(monkeypatch: pytest.MonkeyPatch) -> None:
    """C2 (iii): "**no Known-Gap deletion**".

    The gap names what is missing (``imagery_confirmation``) and when the next look is due; deleting it
    deletes the system's own admission of ignorance.
    """
    _with_failing_sufficiency(monkeypatch, OLDER_EDGE)
    view = rk.build_view(_cfg(), _split_basings())

    assert OLDER_EDGE in [g.related_ref for g in view.known_gaps], (
        f"the older basing's Known Gap is gone (gaps left: "
        f"{[(g.related_ref, g.what_missing) for g in view.known_gaps]}). The same identity bug both "
        "fabricates a claim and removes the refusal that would have flagged it."
    )


def test_an_honest_insufficient_is_not_flipped_to_stale(monkeypatch: pytest.MonkeyPatch) -> None:
    """C2 (iii): "no ``insufficient → stale``" on the retired edge.

    S2's ruling recorded why the label matters: ``credibility/status.py`` defines ``stale`` as "demote
    confirmed→stale", so "``stale`` means 'this WAS confirmed and has since aged out'" — writing it over
    ``insufficient`` "**asserts something false in the system's own terms** … An assertion that was never
    established cannot go stale; there is nothing to age."
    """
    _with_failing_sufficiency(monkeypatch, OLDER_EDGE)
    view = rk.build_view(_cfg(), _split_basings())
    basings = {e.id: e for e in rk.edges_of(view, "based-at")}
    older = basings.get(OLDER_EDGE)

    assert older is not None, (
        f"the older basing edge no longer exists under its own unit id — the view holds "
        f"{sorted(basings)}, which means the two formations were fused and the edge re-keyed"
    )
    assert older.status != "stale", (
        f"the older basing's honest 'insufficient' became {older.status!r}: the system now claims it once "
        "established a position it never established."
    )
