"""R1.4 + C1/L1 — the supersede path must not manufacture a relocation, nor remove the analyst.

This is the **D1 tail**: the defect register calls D1 "the most severe finding of the spike … a structural
path from an identity error to a **fabricated movement assessment with the human explicitly taken out of the
loop** — the one non-negotiable, breached without any component 'lying'."

The clauses asserted here, quoted:

* **R1.4** (defect register D1): "A supersede that would **draw** a relocation across differing targets must
  not be machine-adjudicated out of the analyst's queue when the underlying identity is itself
  sub-confirmed. Machine promotion is only legitimate over an identity the system actually earned."
* **§7 RK-LAYER 7**: "``promote_supersessions`` currently promotes, pops the pair out of the analyst's queue
  ('adjudicated by the machine'), draws the edge, **and deletes the retired edge's Known Gap** — turning an
  honest ``insufficient`` into ``stale``."
* **C2**: the outcome to assert is "no drawn relocation · **no Known-Gap deletion / no ``insufficient →
  stale``** on the retired edge".
* **C1 / R1.3 / ruling L1**: a unit at a garrison *and* concurrently at a forward site is "**two concurrent
  valid basings, not a relocation**"; the key is the **normalized class**, never the stated string; and an
  **unmappable** value "⇒ the third state: no de-confliction, no fusion, and a **named gap**. It must never
  silently de-conflict (the evasion direction is over-merge) and must never silently kill a supersede."
* **§7 RK-LAYER 5**: "Carry forward the relocation/relational mitigation (``co_instances``) … A naive
  ``site_type`` re-key changes the ``edge_instance`` shape and would **silently drop** this mitigation, so a
  confirmed relocation would manufacture relational evidence that origin ≡ destination. Gate-fixture it."

**"Sub-confirmed identity" is read in the codebase's own vocabulary.** Defect register D8: the verdicts
"confirmed/probable/possible are a *derived read of set membership* … where **only ``same_as`` fuses**". So a
node carrying an open ``candidate`` merge *is* a sub-confirmed identity: the graph is simultaneously asking
the analyst "who is this?" while the machine answers "and it moved". The fixture asserts its own premise (the
rival pair is a *candidate*, not a fusion), so it cannot decay into testing something else.

A suite that only tested refusal would be testing timidity, so every refusal has a mirror: the earned
relocation must still promote and still draw its edge.
"""

from __future__ import annotations

import pytest

from chanakya.credibility.supersession import CANDIDATE, GATE, GATE_PROMOTED
from tests import _rk_layer as rk

UNIT, RIVAL, SITE_A, SITE_B = "unit_1", "unit_2", "site_a", "site_b"
DESIGN = "hq9p"
BASING, DRAWN = "based-at", "supersedes"

_A = rk.coords(33.60, 73.10, "alpha")
_B = rk.coords(32.05, 72.68, "bravo")


def _cfg(**kw):
    return rk.fixture_config(
        resolution=rk.HITL_RESOLUTION, supersede_floor=dict(rk.SUPERSEDE_FLOOR), **kw
    )


#: Sentinel for "state one identical site class at both ends" — the DEFAULT, deliberately.
#:
#: The site-class pair is a **three-way discriminator** (absent / same / different), so a fixture that leaves it
#: absent lands in L1's third state by construction: held, gap-named, nothing promoted. An earlier version of
#: this file defaulted to absent, which made the *earned-promotion mirror* unpassable — it was asserting "this
#: relocation must promote" over an input that (correctly) forbids promotion. The rule this bakes in, and it
#: generalises to S3: **when a mechanism has a three-way outcome, a mirror must state the discriminating input
#: explicitly**, or it silently tests the wrong branch. So the default here is the branch that *is* a
#: relocation, and ``None`` must now be passed on purpose.
SAME_CLASS = "<same-class>"


def _relocation(
    *, rival: bool = False, site_types: tuple[str, str] | None | str = SAME_CLASS,
    names: tuple[str, str] = ("Alpha Cantonment", "Bravo Forward Site"),
) -> list:
    """One unit, two dated basings at two different sites — the relocation shape, in the abstract.

    ``site_types`` is the discriminating input: :data:`SAME_CLASS` (default) states one identical class at both
    ends — a genuine relocation; a 2-tuple states whatever you pass; ``None`` states nothing at all, which is
    L1's third state (*we do not know the class*).

    ``rival`` adds a second, name-similar unit mention that lands as a **candidate** merge (probable, not
    fused): the subject's identity is then an open question the analyst has been handed.
    """
    if site_types == SAME_CLASS:
        site_types = rk.same_class_pair()
    attrs_a = dict(_A) | ({"site_type": site_types[0]} if site_types else {})
    attrs_b = dict(_B) | ({"site_type": site_types[1]} if site_types else {})
    claims = [
        rk.entity_claim(UNIT, "unit", name="8th AD Battery"),
        rk.entity_claim(SITE_A, "basing_site", name=names[0], attrs=attrs_a),
        rk.entity_claim(SITE_B, "basing_site", name=names[1], attrs=attrs_b, sid="s2"),
        rk.entity_claim(DESIGN, "variant", name="HQ-9/P"),
        rk.rel_claim("c-ind-1", DESIGN, "inducted-into", UNIT, iso="2020-01-01"),
        rk.rel_claim("c-ba-1", UNIT, BASING, SITE_A, iso="2021-01-01"),
        rk.rel_claim("c-ba-2", UNIT, BASING, SITE_B, iso="2025-01-01", sid="s2"),
    ]
    if rival:
        claims += [
            rk.entity_claim(RIVAL, "unit", name="8 AD Battery", sid="s2"),
            rk.rel_claim("c-ind-2", DESIGN, "inducted-into", RIVAL, iso="2020-06-01", sid="s2"),
        ]
    return claims


def _drawn(view) -> list:
    return rk.edges_of(view, DRAWN)


def _basings(view) -> dict[str, object]:
    return {e.target: e for e in rk.edges_of(view, BASING)}


def _named_site_class_gaps(view, *edges) -> list:
    """Gaps that name this relocation or the missing site class — L1 rule 3's "**named gap**".

    Permissive on purpose: nothing in the spec fixes whether the gap hangs off the basing edge, the sites, the
    unit, or names ``site_type`` in its text. What it may **not** be is absent.
    """
    refs = {e.id for e in edges} | {SITE_A, SITE_B, UNIT}
    return [
        g for g in view.known_gaps
        if g.related_ref in refs
        or "site_type" in (g.what_missing or "") + " ".join(g.missing_slots)
    ]


def _candidate_identity_edges(view, *ids: str) -> list:
    """The resolver's *unadjudicated* identity questions touching ``ids`` (rendered as same-as edges)."""
    wanted = set(ids)
    return [
        e for e in view.edges
        if e.type == "same-as" and {e.source, e.target} & wanted
    ]


# ── the mirror: an earned relocation must still work ────────────────────────────────────────────

def test_a_relocation_over_an_unquestioned_identity_is_still_promoted() -> None:
    """The mirror. R1.4 forbids machine promotion over an identity we did *not* earn — it does not forbid
    promotion. "Machine promotion is only legitimate over an identity the system actually earned", and one
    unit named by one mention, with nothing contesting it, is that case (nothing had to be earned).

    Without this test the refusals below could be satisfied by disabling supersession altogether, which
    would delete the relocation beat instead of protecting it.

    **Both discriminating inputs are stated explicitly**, because two separate three-way mechanisms decide
    this outcome and a mirror that leaves either implicit tests the wrong branch: the identity is
    uncontested (no rival mention ⇒ no open ``candidate``), and the two sites share **one** site class
    (:data:`SAME_CLASS`) so C1 reads them as one position over time rather than two concurrent basings.
    """
    view = rk.build_view(_cfg(), _relocation(site_types=rk.same_class_pair()))
    edges = _basings(view)

    assert set(edges) == {SITE_A, SITE_B}, f"fixture broken: basings are {sorted(edges)}"
    assert edges[SITE_A].superseded_by == edges[SITE_B].id, (
        "the earned relocation was not promoted — the supersede beat must survive R1.4's guard. Both sites "
        f"state the same class ({rk.same_class_pair()[0]!r}) and nothing contests the subject's identity, so "
        "neither C1's de-confliction nor R1.4's guard has anything to withhold here"
    )
    assert _drawn(view), "no node→node `supersedes` edge was drawn for the earned relocation (D-P4.11)"
    assert not _candidate_identity_edges(view, UNIT), (
        "fixture premise broken: this fixture is the *unquestioned* identity case, but the resolver has an "
        "open identity question about the subject"
    )


# ── R1.4(a): no machine adjudication over a sub-confirmed identity ──────────────────────────────

def test_the_rival_mention_really_is_an_unadjudicated_identity_question() -> None:
    """The premise of the next two tests, asserted separately so they cannot pass for the wrong reason.

    The rival must be a **candidate** (D8: "``candidates``→probable"), i.e. queued for the analyst and NOT
    fused — if it fused there would be one node and no open question; if it scored nothing there would be no
    question at all.
    """
    view = rk.build_view(_cfg(), _relocation(rival=True))
    units = {n.id for n in rk.nodes_of(view, "unit")}
    pairs = _candidate_identity_edges(view, UNIT, RIVAL)

    assert units == {UNIT, RIVAL}, (
        f"the two unit mentions fused ({sorted(units)}) — then the identity is not *sub*-confirmed and this "
        "fixture tests nothing. Retune the fixture, not the assertion."
    )
    assert pairs, "the resolver raised no identity question about the subject — the fixture is inert"
    assert any(e.attrs.get("merge_band") == "candidate" for e in pairs), (
        f"the identity question is not in the analyst's queue band: "
        f"{[(e.id, e.attrs.get('merge_band')) for e in pairs]} — D8: only `candidates` is 'probable'"
    )


def test_a_relocation_is_not_machine_adjudicated_over_a_sub_confirmed_identity() -> None:
    """**R1.4**: "A supersede that would **draw** a relocation across differing targets must not be
    machine-adjudicated out of the analyst's queue when the underlying identity is itself sub-confirmed."

    The harm, from the register: "one identity error ⇒ a drawn, positively-asserted relocation that the
    analyst is never asked about. An adversary does not even need to plant a lie — publishing two real,
    similarly-described co-located units is enough."

    **Carrier, ruled 2026-07-25:** "sub-confirmed" is the **merge-band** vocabulary — an *open ``candidate``
    merge* is sub-confirmed (D8: "``candidates``→probable … only ``same_as`` fuses"). It is expressly **not**
    the node's own ``status``: in the legitimate flagship case the subject unit node sits at ``probable`` and
    still promotes correctly, so gating on node status would delete the relocation beat rather than protect it.
    """
    view = rk.build_view(_cfg(), _relocation(rival=True))
    edges = _basings(view)
    older, newer = edges[SITE_A], edges[SITE_B]

    assert not _drawn(view), (
        "a node→node relocation was DRAWN while the subject's own identity was still an open question for "
        f"the analyst ({[e.id for e in _candidate_identity_edges(view, UNIT, RIVAL)]}) — R1.4: machine "
        f"promotion is legitimate only over an identity the system actually earned. {rk.flag_report()}"
    )
    assert older.superseded_by is None and newer.supersedes is None, (
        "the older position was retired on an identity we did not earn — an identity error becomes a "
        "positively-asserted movement claim (defect register D1)"
    )
    assert older.attrs.get(GATE) != GATE_PROMOTED, (
        f"the pair was gated {older.attrs.get(GATE)!r} — it must not be 'promoted' over a sub-confirmed "
        "identity"
    )
    assert older.attrs.get(CANDIDATE) and newer.attrs.get(CANDIDATE), (
        "the pair was popped out of the analyst's queue ('adjudicated by the machine') — with the identity "
        "unearned the analyst is exactly who should decide (§7 RK-LAYER 7, spine/05 recall-biased triage)"
    )


# ── R1.4(b): the Known Gap must survive, and an honest `insufficient` must not become `stale` ───

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


OLDER_EDGE_ID = f"e:{UNIT}:{BASING}:{SITE_A}"


def test_the_gap_fixture_raises_a_real_known_gap_when_nothing_is_retired(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-vacuity control: with no supersede floor configured nothing is retired, so the gap must be there.

    Without this control, "the gap survived" could pass simply because the fixture never raised one.
    """
    _with_failing_sufficiency(monkeypatch, OLDER_EDGE_ID)
    view = rk.build_view(rk.fixture_config(resolution=rk.HITL_RESOLUTION), _relocation())

    assert [g.related_ref for g in view.known_gaps] == [OLDER_EDGE_ID], (
        f"the control fixture raised {[g.related_ref for g in view.known_gaps]} — it must raise exactly one "
        "Known Gap, on the older basing, or the deletion test below is vacuous"
    )
    older = _basings(view)[SITE_A]
    assert older.status == "insufficient", (
        f"the older basing reads {older.status!r} rather than 'insufficient' — the honest refusal is the "
        "thing R1.4(b) says must not be laundered into 'stale'"
    )


def test_a_retired_edges_known_gap_is_not_deleted(monkeypatch: pytest.MonkeyPatch) -> None:
    """**§7 RK-LAYER 7 / C2**: the promotion path "deletes the retired edge's Known Gap — turning an honest
    ``insufficient`` into ``stale``"; C2 requires "**no Known-Gap deletion / no ``insufficient → stale``** on
    the retired edge".

    D-13.14 names the same harm: the supersede path "draws a relocation, removes the pair from the analyst's
    queue, **and deletes the retired edge's Known Gap** — turning an honest ``insufficient`` into ``stale``".
    A gap is a *collection requirement* about what we could not assess; being overtaken by a later position
    does not answer it, and silently dropping it removes the analyst's only record that the retired position
    was never established in the first place.
    """
    _with_failing_sufficiency(monkeypatch, OLDER_EDGE_ID)
    view = rk.build_view(_cfg(), _relocation())

    assert OLDER_EDGE_ID in [g.related_ref for g in view.known_gaps], (
        "the retired edge's Known Gap was deleted by the promotion "
        f"(gaps left: {[g.related_ref for g in view.known_gaps]}) — §7 RK-LAYER 7 / C2 forbid exactly this"
    )


def test_an_honest_insufficient_is_not_flipped_to_stale(monkeypatch: pytest.MonkeyPatch) -> None:
    """The second half of the same clause: "turning an honest ``insufficient`` into ``stale``" (C2).

    ``stale`` says *we knew this and it is now history*; ``insufficient`` says *we never established it*.
    Overwriting the second with the first upgrades an unassessed position to a former fact.
    """
    _with_failing_sufficiency(monkeypatch, OLDER_EDGE_ID)
    view = rk.build_view(_cfg(), _relocation())
    older = _basings(view)[SITE_A]

    assert older.status != "stale", (
        f"the older basing's honest 'insufficient' became {older.status!r} — C2: no `insufficient → stale` "
        "on the retired edge"
    )


def test_a_well_evidenced_retired_position_still_reads_stale(monkeypatch: pytest.MonkeyPatch) -> None:
    """The mirror of the two tests above: where the retired position *was* assessable, ``stale`` is right.

    "the older assertion is re-run through the status machine carrying ``SUPERSEDED`` (→ *stale*, not
    *insufficient* — it is history, not a gap: product/02 §7)" (``credibility/supersession.py``). Only the
    laundering of an *honest refusal* is forbidden; retiring a real former position is the beat itself.
    """
    view = rk.build_view(_cfg(), _relocation())
    older = _basings(view)[SITE_A]

    assert older.status == "stale", (
        f"an assessable retired position reads {older.status!r} — R1.4(b) protects an honest `insufficient`, "
        "it does not disable retirement"
    )
    assert not view.known_gaps, (
        f"the assessable case raised gaps {[g.related_ref for g in view.known_gaps]} — this mirror is only "
        "meaningful while the retired edge had no honest refusal to protect"
    )


# ── C1 / ruling L1: site_type de-confliction, on the normalized class ───────────────────────────

def _vocabulary_pair() -> tuple[str, str]:
    """Two values from the **config-declared** ``site_type`` vocabulary (ruling L1 rule 1).

    Read from config rather than hardcoded, because L1 rule 2 is that keying happens on the normalized
    class: a test that invented its own strings would be asserting against a mapping nobody declared.
    """
    vocab = rk.site_type_vocabulary()
    assert vocab, (
        "config declares no closed `site_type` vocabulary, so C1's de-confliction has no classes to key on "
        "(ruling L1 rule 1). See tests/config/test_rk_layer_a2_layer_tags.py"
        "::test_a_closed_site_type_vocabulary_is_declared_in_config"
    )
    values = next(iter(vocab.values()))
    assert len(values) >= 2, f"the declared vocabulary {values} cannot express two different classes"
    return values[0], values[1]


def test_two_concurrent_basings_at_different_site_classes_are_not_a_relocation() -> None:
    """**C1 / R1.3**: "One unit at its garrison *and* concurrently at a forward site is one unit with two
    basings (the wall does not fire)" — "**two concurrent valid basings, not a relocation**".

    Today ``based-at``'s supersede key is the unit alone (``config/ontology.yaml``: ``instance_key: [from]``)
    and the ontology rests that on the corpus — "Subject-only keying is correct while the corpus has no such
    simultaneous pair" — which working-principles #1 forbids as a design input.
    """
    garrison, forward = _vocabulary_pair()
    view = rk.build_view(_cfg(), _relocation(site_types=(garrison, forward)))
    edges = _basings(view)
    older, newer = edges[SITE_A], edges[SITE_B]

    assert not _drawn(view), (
        f"a relocation was drawn between two basings of different declared site classes "
        f"({garrison!r} → {forward!r}) — C1: 'a differing site_type is NOT a conflict'. {rk.flag_report()}"
    )
    assert older.superseded_by is None and newer.supersedes is None, (
        "the garrison basing was retired by the forward deployment — both are live, and retiring one "
        "under-reports the order of battle while asserting a move that never happened"
    )
    assert not older.attrs.get("contradiction") and not newer.attrs.get("contradiction"), (
        "two valid concurrent basings were reported to the analyst as a contradiction"
    )
    assert older.edge_instance != newer.edge_instance, (
        f"both basings still share one supersede instance ({older.edge_instance!r}) — the key is not "
        "site-class-tagged, so any future relocation logic will keep reading them as one position"
    )


def test_an_unmappable_site_type_lands_in_the_third_state() -> None:
    """**Ruling L1 rule 3** — the highest-value clause here: "An unmappable stated value ⇒ **the third
    state**: no de-confliction, no fusion, and a **named gap**. It must never silently de-conflict (the
    evasion direction is over-merge) and must never silently kill a supersede."

    L1 verified that the corpus's own relocation carries exactly this shape: "the two ends of the flagship
    relocation carry **unrelated** strings (``observed-imagery-site`` vs ``stated_destination``). A supersede
    key built on the raw string gives them **different instance keys**, so they never co-locate ⇒ **the
    relocation silently stops firing** while the code still looks deterministic."
    """
    view = rk.build_view(
        _cfg(), _relocation(site_types=("observed-imagery-site", "stated_destination")),
    )
    edges = _basings(view)
    older, newer = edges[SITE_A], edges[SITE_B]

    assert older.edge_instance == newer.edge_instance, (
        f"two unmappable site_type strings de-conflicted the supersede instance "
        f"({older.edge_instance!r} vs {newer.edge_instance!r}) — L1: an unmappable value must NEVER silently "
        "de-conflict, because the evasion direction is over-merge, and it must never silently kill a "
        "supersede (which is exactly what the flagship's own two strings would do)"
    )
    assert not _drawn(view), (
        "a relocation was drawn from two site_type values the config cannot classify — L1's third state is "
        f"'no de-confliction, no fusion': the analyst decides. {rk.flag_report()}"
    )
    assert older.superseded_by is None, (
        "the older position was retired on an unclassifiable site_type — 'no fusion' (L1 rule 3)"
    )
    assert _named_site_class_gaps(view, older, newer), (
        "the unmappable site_type produced no NAMED gap "
        f"(gaps: {[(g.related_ref, g.what_missing, g.missing_slots) for g in view.known_gaps]}) — L1's third "
        "state is 'no de-confliction, no fusion, **and a named gap**'; C7 adds that 'a gap must bind the "
        "fusion path, not merely annotate it'"
    )


def test_an_absent_site_type_lands_in_the_same_third_state_as_an_unmappable_one() -> None:
    """The fail-safe, **as ruled 2026-07-25**: absence and unmappability are one condition.

    §7 RK-LAYER 5 gave absence a weaker fail-safe of its own — "**State the absent ``site_type`` default
    explicitly and fail safe:** ``unknown`` ⇒ same bucket (the wall fires) or ⇒ raise — **never** ⇒
    de-conflicted, since the evasion direction is over-merge" — written before ruling **L1**. The two were
    reconciled in L1's favour: *absence and unmappability are the same condition for keying purposes — we do
    not know the class* — so both land in the third state: **no de-confliction, no fusion, and a named gap**.

    The one-bucket half is the over-merge safety property; the no-fusion half is what stops the machine
    adjudicating a relocation between two sites whose kind it cannot even name.

    ``site_types=None`` is passed **explicitly** — this is the one place absence is the thing under test.
    """
    view = rk.build_view(_cfg(), _relocation(site_types=None))
    edges = _basings(view)
    older, newer = edges[SITE_A], edges[SITE_B]

    assert older.edge_instance == newer.edge_instance, (
        f"an absent site_type de-conflicted the supersede instance ({older.edge_instance!r} vs "
        f"{newer.edge_instance!r}) — 'never ⇒ de-conflicted, since the evasion direction is over-merge'"
    )
    assert not _drawn(view), (
        "a relocation was drawn between two sites whose class is unknown (no site_type stated at all) — "
        "absence is the same condition as an unmappable value, so L1's third state applies: no "
        f"de-confliction, no fusion, plus a named gap. {rk.flag_report()}"
    )
    assert older.superseded_by is None and newer.supersedes is None, (
        "the older position was retired although neither site's class is known — 'no fusion' (L1 rule 3)"
    )
    assert _named_site_class_gaps(view, older, newer), (
        "an absent site_type produced no NAMED gap "
        f"(gaps: {[(g.related_ref, g.what_missing, g.missing_slots) for g in view.known_gaps]}) — the third "
        "state is 'no de-confliction, no fusion, **and a named gap**'"
    )


# ── the real-corpus consequence, pinned as INTENDED (ruled 2026-07-25) ──────────────────────────

#: The flagship relocation's two ends in the frozen corpus (``hq9p_primary``).
FLAGSHIP_SITES = ("site_rahwali", "site_rawalpindi")


def test_the_flagship_relocation_is_held_while_its_site_classes_are_unknown() -> None:
    """**This outcome is INTENDED — do not "fix" it by loosening the vocabulary.**

    Ruled 2026-07-25: with the flag on and no ``site_type`` mapping yet, the flagship relocation lands in
    L1's third state — **held, gap-named, no drawn edge** — and *that is the honest outcome, not a
    regression*. "A held relocation with a named gap is the system saying 'I cannot classify these sites
    yet' — which is precisely the non-negotiable behaving." L1 rule 4 puts the mapping with DATA: "Until it
    lands, the third state is the correct, honest behaviour."

    The assertion self-adjusts to whatever DATA lands, because it reads the two sites' *classes* rather than
    assuming them:

    * neither class known, or the two classes differ  ⇒ **no drawn relocation** (third state / C1);
    * both resolve to the **same** class              ⇒ the relocation is a genuine one and **must** promote.

    So it cannot be silenced by a mapping that quietly sends every string to one class — that path is
    asserted too, and it has to produce the drawn edge it claims.
    """
    from eval import harness

    if not harness.bundles_dir().is_dir():
        pytest.skip(f"no frozen claim bundles at {harness.bundles_dir()}")

    from chanakya.view import rebuild

    scenario = harness.load_scenario()
    config = rk.enable_layer_routing(scenario.config_store.snapshot())
    view = rebuild(scenario.evidence, [], config)

    nodes = {n.id: n for n in view.nodes}
    missing = [s for s in FLAGSHIP_SITES if s not in nodes]
    assert not missing, (
        f"the frozen corpus no longer carries {missing} — this test pins the flagship relocation, so a "
        "renamed site means it is measuring nothing (re-anchor it deliberately, do not delete the assertion)"
    )
    stated = {s: (nodes[s].attrs or {}).get("site_type") for s in FLAGSHIP_SITES}
    classes = {s: rk.classify_site_type(v) for s, v in stated.items()}
    drawn = [
        e for e in view.edges
        if e.type == DRAWN and {e.source, e.target} == set(FLAGSHIP_SITES)
    ]

    known = [c for c in classes.values() if c is not None]
    if len(known) == 2 and known[0] == known[1]:
        assert drawn, (
            f"both flagship sites resolve to the same declared class ({known[0]!r}) — that is a genuine "
            "relocation and it must still be drawn; C1 de-conflicts differing classes, it does not disable "
            f"supersession. Stated: {stated}. {rk.flag_report()}"
        )
        return

    assert not drawn, (
        f"a relocation was drawn between the flagship sites while their classes are {classes} "
        f"(stated: {stated}) — INTENDED behaviour is L1's third state: held for the analyst with a named "
        "gap. If this fails because a mapping now sends both strings to one class, check that the mapping is "
        f"about the *kind of place* axis and not the other three concepts L1 separates. {rk.flag_report()}"
    )
    basings = [e for e in view.edges if e.type == BASING and e.target in FLAGSHIP_SITES]
    held = [e for e in basings if e.attrs.get(CANDIDATE) or e.attrs.get(GATE) != GATE_PROMOTED]
    assert held, (
        f"the flagship basings were machine-adjudicated although their site classes are {classes} — the "
        "third state hands the pair to the analyst rather than answering it "
        f"({[(e.id, e.attrs.get(GATE)) for e in basings]})"
    )


# ── the whole three-way outcome, in one place ───────────────────────────────────────────────────

def test_the_site_class_pair_decides_the_relocation_three_ways() -> None:
    """C1/R1.3 + L1 have **three** outcomes, and all three are asserted together so none can drift.

    Verified by the orchestrator against the implementation (2026-07-25), holding everything else constant:

    | ``site_type`` pair | outcome |
    |---|---|
    | absent / unmappable | **held** — L1's third state: no de-confliction, no fusion, a named gap |
    | **same class both ends** | **promotes** — a genuine relocation |
    | different classes | **no relocation** — two concurrently valid basings (C1) |

    The middle row is the one that makes C1 *precision* rather than mere refusal, and the row a broad
    over-correction silently loses: a guard that simply stopped promoting would satisfy rows 1 and 3 and look
    safe. This test is the single place that reads the whole table, so tightening one row cannot quietly break
    another.
    """
    same = rk.same_class_pair()
    different = _vocabulary_pair()
    outcomes = {}
    for label, site_types in (("absent", None), ("same", same), ("different", different)):
        view = rk.build_view(_cfg(), _relocation(site_types=site_types))
        edges = _basings(view)
        outcomes[label] = (
            edges[SITE_A].superseded_by,
            bool(_drawn(view)),
            edges[SITE_A].edge_instance == edges[SITE_B].edge_instance,
        )

    absent, promoted, differing = outcomes["absent"], outcomes["same"], outcomes["different"]

    assert absent == (None, False, True), (
        f"absent site classes did not land in the third state: {absent} (want no retirement, no drawn edge, "
        f"one shared instance) — L1 rule 3. Measured table: {outcomes}"
    )
    assert promoted[0] is not None and promoted[1], (
        f"one identical site class at both ends did not promote: {promoted} — that is a genuine relocation, "
        "and C1 exists to de-conflict *differing* classes, not to disable supersession. This is the row a "
        f"broad guard loses. Measured table: {outcomes}"
    )
    assert differing == (None, False, False), (
        f"two different site classes were not read as two concurrently valid basings: {differing} (want no "
        f"retirement, no drawn edge, two separate instances) — C1/R1.3. Measured table: {outcomes}"
    )


# ── §7 RK-LAYER 5: the co_instances relocation/relational mitigation must survive the re-key ────

def _colocated_pair(site_types: tuple[str, str] | None) -> list:
    """A relocation whose two ends are *name-similar* sites, so the resolver actually scores the pair.

    ``resolve/scoring.py`` excludes the shared edge-instance from the relational overlap
    (``co_instances``), so origin and destination gain no identity evidence from sharing the unit. With a
    naive site_type re-key the two basings fall into different instances, the exclusion stops firing, and the
    two ends of a confirmed relocation start looking like one place.
    """
    return _relocation(site_types=site_types, names=("Alpha Cantonment", "Alpha Cantonement"))


@pytest.mark.parametrize("same_class", [True, False])
def test_the_two_ends_of_a_relocation_never_become_merge_candidates(same_class: bool) -> None:
    """§7 RK-LAYER 5: "a dated relationship to the same neighbour at two different times is **not** the same
    relationship. A naive ``site_type`` re-key changes the ``edge_instance`` shape and would **silently
    drop** this mitigation, so a confirmed relocation would manufacture relational evidence that origin ≡
    destination. **Gate-fixture it.**"

    Parametrized over both site-class shapes, because the re-key is exactly what splits the instance in the
    differing-class case: the mitigation has to survive *both*, or C1's fix buys a new over-merge.
    """
    site_types = rk.same_class_pair() if same_class else _vocabulary_pair()

    view = rk.build_view(_cfg(), _colocated_pair(site_types))
    sites = {n.id for n in rk.nodes_of(view, "basing_site")}
    questions = _candidate_identity_edges(view, SITE_A, SITE_B)

    assert sites == {SITE_A, SITE_B}, (
        f"the two ends of the relocation fused into one place ({sorted(sites)}) — 'origin ≡ destination' is "
        "the manufactured conclusion the co_instances mitigation exists to prevent"
    )
    assert not questions, (
        f"the two ends of one unit's relocation were offered to the analyst as duplicate candidates "
        f"({[(e.id, e.attrs.get('merge_band')) for e in questions]}) — their only shared neighbour is the "
        "relocating unit itself, and 'a dated relationship to the same neighbour at two different times is "
        "not the same relationship' (§7 RK-LAYER 5; resolve/scoring.py co_instances)"
    )
