"""DEFAULT-ON P3 — **the fabrication path is closed**, all four consequences, on the shipped default.

Authored from the session spec alone, implementation-blind. The property, quoted:

    "THE FABRICATION PATH IS CLOSED, all four consequences: a sub-confirmed identity does not drive a
    supersession; the analyst's candidate is NOT popped off the queue; a retired assertion is NOT restated
    as 'stale' (an assertion never established cannot age — 'stale' means demoted FROM confirmed); and no
    relocation edge is drawn from an unearned identity."

**The chain, in one paragraph, because every assertion below is one link of it.** Two co-located batteries
with no designations look nearly identical to the identity judge, so fusing them is the path of least
resistance. ``based-at`` is *functional* and keyed on the unit, so the instant they fuse their two distinct
sites become **one unit's before and after**. The supersede pass then finds an ordered pair, clears the
credibility floor on the newer look, writes the retirement, **pops the pair out of the analyst's queue**
("adjudicated by the machine"), **draws a relocation edge**, and — because the retired assertion is
re-labelled — turns an honest ``insufficient`` into ``stale`` and **drops its Known Gap**. One identity
error becomes a positively-asserted movement assessment the analyst is never asked about, with the system's
own admission of ignorance deleted on the way. The non-negotiable is breached without any component lying.

**Why 'stale' is the wrong word and not merely an imprecise one.** ``credibility/status.py`` defines
``stale`` as *"the freshest supporting look older than one half-life → demote **confirmed**→stale"*. So in
this system's own vocabulary ``stale`` asserts **"this WAS confirmed and has since aged out."** Writing it
over an ``insufficient`` claims the position was once established. **An assertion never established cannot
age — there is nothing to age.** That is an over-claim about provenance, i.e. the disqualifying class, so
the rule cannot be conditional on anything.

**Both barriers are asserted, and they are different mechanisms.** The *upstream* one stops the fusion
(the co-location cap); the *downstream* one keeps the human in the loop if a fusion happens anyway (the
earned-identity gate on promotion). Testing only one leaves the other free to regress, and the register is
explicit that the downstream guard is "the backstop that keeps a human in the loop if it does".

**Every refusal has a mirror.** Timidity is a failure mode here, not a safe default: a guard that simply
stopped promoting would satisfy three of the four consequences and delete the relocation beat instead of
protecting it. So the earned relocation must still promote, still draw its edge, and an assessable retired
position must still read ``stale``.

Every fixture is abstract (ruling M4 — the corpus holds one numbered formation and cannot exercise this).
"""

from __future__ import annotations

from typing import Any

import pytest

from chanakya.credibility.supersession import CANDIDATE, GATE, GATE_PROMOTED
from tests import _rk_coref as rc
from tests import _rk_layer as rk

BASING, DRAWN = "based-at", "supersedes"

# ── barrier 1 (upstream): two co-located batteries must not become one unit's before/after ───────

#: A generic descriptor, not a designation — exactly what two co-located batteries share in open sources.
DESCRIPTOR = "air defence battery"
OLDER_EDGE = f"e:unit_a:{BASING}:site_old"


def _shipped(**credibility: Any):
    """The bundle the app actually boots with — **no flag is turned on by this file**.

    That is the whole point of a default-on gate: the fixture states the shipped configuration and asserts
    the target behaviour. ``rk.SUPERSEDE_FLOOR`` is READ from ``config/credibility.yaml`` rather than
    hand-copied, because a hand-copy silently omits any knob added later — which has already cost one round.
    """
    return rc.bundle(flag_on=False, supersede_floor=dict(rk.SUPERSEDE_FLOOR), **credibility)


def _split_basings(names: tuple[str, str] = (DESCRIPTOR, DESCRIPTOR)) -> list:
    """Two formation mentions sharing design + operator, each with its own dated basing.

    Both sites carry the **same** normalised class and the dates do **not** overlap, so this is not a stated
    relationship conflict — it is precisely the case where fusing the two mentions *manufactures a movement*.
    The older basing is stated by a weak source, so it is the under-evidenced position the chain turns into
    an assertion.
    """
    return [
        rc.ent("unit_a", "unit", names[0], doc="d1"),
        rc.ent("unit_b", "unit", names[1], doc="d2", sid="mid"),
        rc.site("site_old", "Bravo Depot", doc="d1", sid="lo"),
        rc.site("site_new", "Charlie Cantonment", lat=32.0, lon=72.6, doc="d2", sid="mid"),
        rc.rel("r-ba-a", "unit_a", BASING, "site_old", doc="d1", iso="2021-01-01", sid="lo"),
        rc.rel("r-ba-b", "unit_b", BASING, "site_new", doc="d2", iso="2025-01-01", sid="mid"),
        *rc.shared_neighbours("unit_a", "unit_b"),
    ]


def _failing_sufficiency(monkeypatch: pytest.MonkeyPatch, element_id: str) -> None:
    """Make exactly one element's evidence template fail, so it raises a real Known Gap.

    ``rebuild`` binds ``check`` at import, so it is patched in the pipeline module's namespace — the idiom
    ``tests/gates/test_g8_insufficient_first_class.py`` established.
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
    """Every drawn relocation — the derived node→node ``supersedes`` edges plus any retired basing."""
    return sorted(
        [e.id for e in rk.edges_of(view, DRAWN)]
        + [f"{e.id}->{e.superseded_by}" for e in rk.edges_of(view, BASING) if e.superseded_by]
    )


def test_the_control_distinguishes_the_two_formations_and_fabricates_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-vacuity control for the four absences below.

    With the two formations carrying *different designations* the same claims produce no relocation and one
    honest Known Gap. Without this control, "no relocation was drawn" could pass because the fixture never
    had one to draw, and "the gap survived" because none was ever raised.
    """
    _failing_sufficiency(monkeypatch, OLDER_EDGE)
    view = rk.build_view(_shipped(), _split_basings(("8th AD Battalion", "12th AD Battalion")))

    assert sorted(n.id for n in rk.nodes_of(view, "unit")) == ["unit_a", "unit_b"]
    assert _relocations(view) == [], f"the control already draws {_relocations(view)}"
    assert [g.related_ref for g in view.known_gaps] == [OLDER_EDGE], (
        f"the control raised {[(g.related_ref, g.what_missing) for g in view.known_gaps]} — it must raise "
        "exactly one Known Gap, on the older basing, or every deletion assertion below is vacuous"
    )
    older = {e.id: e for e in rk.edges_of(view, BASING)}[OLDER_EDGE]
    assert older.status == "insufficient", (
        f"the older basing reads {older.status!r} in the control rather than 'insufficient' — the honest "
        "refusal is the very thing that gets laundered into 'stale'"
    )


def test_a_co_location_over_merge_cannot_start_the_chain() -> None:
    """Link 0: the two batteries must remain two formations on the shipped configuration.

    An order-of-battle undercount is bad on its own; here it is also the *precondition* for everything
    below, because ``based-at`` is unit-keyed and the fusion alone is enough to manufacture the before/after.
    """
    view = rk.build_view(_shipped(), _split_basings())
    units = sorted(n.id for n in rk.nodes_of(view, "unit"))

    assert units == ["unit_a", "unit_b"], (
        f"the view holds {units} — two co-located batteries sharing a design, an operator and a generic "
        "descriptor collapsed into ONE formation node on the default configuration. Every battery at a base "
        "shares exactly that evidence, so this is an undercount by construction and the first link of the "
        "fabricated-relocation chain (D-13.14/G16)."
    )


def test_no_relocation_edge_is_drawn_from_an_unearned_identity() -> None:
    """Consequence (4): "no relocation edge is drawn from an unearned identity."

    Asserted on the *drawn* artefacts rather than on the merge verdict, because that is where the harm is
    read: an analyst sees a ``supersedes`` edge between two places and reads "it moved". Nobody stated that
    anything moved — two documents described two batteries.
    """
    view = rk.build_view(_shipped(), _split_basings())

    assert _relocations(view) == [], (
        f"a relocation was drawn or an assertion retired: {_relocations(view)}. Nobody reported a movement; "
        "an identity error was laundered into a positively-asserted movement assessment. This is defect D1 — "
        "'a structural path from an identity error to a fabricated movement assessment with the human "
        "explicitly taken out of the loop'."
    )


def test_the_retired_edges_known_gap_is_not_deleted(monkeypatch: pytest.MonkeyPatch) -> None:
    """Consequence (3), first half: the Known Gap must survive.

    A gap is a *collection requirement* about what could not be assessed. Being overtaken by a later
    position does not answer it, and dropping it removes the analyst's only record that the retired position
    was never established in the first place. The same identity bug both fabricates a claim and deletes the
    system's own admission of ignorance.
    """
    _failing_sufficiency(monkeypatch, OLDER_EDGE)
    view = rk.build_view(_shipped(), _split_basings())

    assert OLDER_EDGE in [g.related_ref for g in view.known_gaps], (
        f"the older basing's Known Gap is gone (gaps left: "
        f"{[(g.related_ref, g.what_missing) for g in view.known_gaps]}). It named what was missing "
        "(imagery_confirmation) and when the next look was due; deleting it tells the analyst there is "
        "nothing left to collect on a position that was never established."
    )


def test_an_assertion_never_established_is_not_restated_as_stale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Consequence (3), second half — the label, in the system's own vocabulary.

    ``stale`` is defined as a freshness demotion **from confirmed**. Writing it over ``insufficient``
    therefore asserts that the position was once established and has merely gone out of date. An assertion
    never established cannot age. Retirement itself is carried by ``superseded_by``, which is independent of
    the label — so protecting the label costs the beat nothing.
    """
    _failing_sufficiency(monkeypatch, OLDER_EDGE)
    view = rk.build_view(_shipped(), _split_basings())
    basings = {e.id: e for e in rk.edges_of(view, BASING)}
    older = basings.get(OLDER_EDGE)

    assert older is not None, (
        f"the older basing no longer exists under its own unit id — the view holds {sorted(basings)}, which "
        "means the two formations were fused and the edge re-keyed onto the survivor"
    )
    assert older.status != "stale", (
        f"an honest 'insufficient' became {older.status!r}: the system now claims it once established a "
        "position it never established. That is an over-claim about provenance — the disqualifying class."
    )


def test_the_analysts_identity_question_is_not_popped_off_the_queue() -> None:
    """Consequence (2), upstream form: the refused fusion must arrive as a question, not vanish.

    "Not fused; queued and reported." A cap that dropped the pair would hide a real question instead of
    asking it — the analyst is exactly who should decide whether two co-located batteries are one battery.
    """
    part = rc.part_of(_split_basings(), _shipped())
    status = rc.status(part, "unit_a", "unit_b")

    assert status in ("probable", "possible"), (
        f"the co-located pair reads {status!r}: it was either fused or dropped entirely, so the analyst is "
        f"never asked whether these two mentions are one battery. candidates={part.candidates} "
        f"possible={part.possible}"
    )
    assert rc.visible_rationale(part, "unit_a", "unit_b").strip(), (
        "the pair was retained with NO analyst-facing rationale. 'Retained but never surfaced' is a quiet "
        "drop wearing the clothes of a referral: the queue item has to say why the merge was withheld and "
        "what would lift it."
    )


# ── barrier 2 (downstream): the earned-identity gate on the promotion itself ─────────────────────

UNIT, RIVAL, SITE_A, SITE_B, DESIGN = "unit_1", "unit_2", "site_a", "site_b", "hq9p"
OLDER_BASING_ID = f"e:{UNIT}:{BASING}:{SITE_A}"


def _relocation(*, rival: bool) -> list:
    """One unit, two dated basings at two sites of the **same declared class** — a genuine relocation shape.

    ``rival`` adds a second, name-similar unit mention that lands as an open ``candidate`` merge: the
    subject's identity is then a question the analyst has been handed and nobody has answered. Both
    discriminating inputs are stated explicitly, because two independent three-way mechanisms decide the
    outcome and a fixture that left either implicit would silently test the wrong branch.
    """
    cls = rk.same_class_pair()[0]
    claims = [
        rk.entity_claim(UNIT, "unit", name="8th AD Battery"),
        rk.entity_claim(SITE_A, "basing_site", name="Alpha Cantonment",
                        attrs=rk.coords(33.60, 73.10, "alpha") | {"site_type": cls}),
        rk.entity_claim(SITE_B, "basing_site", name="Bravo Forward Site", sid="s2",
                        attrs=rk.coords(32.05, 72.68, "bravo") | {"site_type": cls}),
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


def _floor_config(*, floor: dict[str, Any] | None = None):
    """The layer/supersede fixture bundle on its **shipped** flag state — nothing is switched on here.

    ``floor=None`` keeps the shipped ``supersede_floor``; pass a dict to vary one knob.
    """
    return rk.fixture_config(
        flag_on=False,
        resolution=rk.HITL_RESOLUTION,
        supersede_floor=dict(rk.SUPERSEDE_FLOOR) if floor is None else floor,
    )


def _basings(view) -> dict[str, Any]:
    return {e.target: e for e in rk.edges_of(view, BASING)}


def _identity_questions(view, *ids: str) -> list:
    wanted = set(ids)
    return [e for e in view.edges if e.type == "same-as" and {e.source, e.target} & wanted]


def test_the_rival_mention_really_is_an_unadjudicated_identity_question() -> None:
    """The premise of the next two tests, asserted separately so neither can pass for the wrong reason.

    "Sub-confirmed" is read in the merge-band vocabulary: an open ``candidate`` merge *is* a sub-confirmed
    identity, because the graph is simultaneously asking "who is this?" while the machine answers "and it
    moved". It is expressly **not** the node's assessed status — the legitimate flagship relocation sits at
    ``probable``, so reading the confidence label would delete the beat instead of protecting it.
    """
    view = rk.build_view(_floor_config(), _relocation(rival=True))
    units = {n.id for n in rk.nodes_of(view, "unit")}
    questions = _identity_questions(view, UNIT, RIVAL)

    assert units == {UNIT, RIVAL}, (
        f"the two unit mentions fused ({sorted(units)}) — then the identity is not *sub*-confirmed and this "
        "fixture tests nothing. Retune the fixture, not the assertion."
    )
    assert any(e.attrs.get("merge_band") == "candidate" for e in questions), (
        f"the subject's identity is not an open question in the analyst's queue: "
        f"{[(e.id, e.attrs.get('merge_band')) for e in questions]}"
    )


def test_a_sub_confirmed_identity_does_not_drive_a_supersession() -> None:
    """Consequences (1) and (4), downstream: nothing is retired and nothing is drawn.

    Machine promotion is legitimate only over an identity the system actually earned. An adversary does not
    even need to plant a lie — publishing two real, similarly-described co-located units is enough.
    """
    view = rk.build_view(_floor_config(), _relocation(rival=True))
    older, newer = _basings(view)[SITE_A], _basings(view)[SITE_B]

    assert not rk.edges_of(view, DRAWN), (
        "a node→node relocation was DRAWN while the subject's own identity was still an open question for "
        f"the analyst ({[e.id for e in _identity_questions(view, UNIT, RIVAL)]}). The supersede pass "
        "asked four questions about the newer CLAIM and none about whether the SUBJECT is one thing."
    )
    assert older.superseded_by is None and newer.supersedes is None, (
        "the older position was retired over an identity we did not earn — the identity error is now a "
        "positively-asserted movement claim (defect register D1)"
    )
    assert older.attrs.get(GATE) != GATE_PROMOTED, (
        f"the pair was gated {older.attrs.get(GATE)!r}; it must not read 'promoted' over a sub-confirmed "
        "identity"
    )


def test_the_analysts_supersede_candidate_is_not_popped_off_the_queue() -> None:
    """Consequence (2), downstream form — and the half that is easiest to lose.

    A guard that promoted anyway and merely declined to pop the queue would be the wrong lever (it leaves
    the machine asserting a movement it did not earn); a guard that held the pair but *also* dropped it from
    the queue would be worse, because the fabrication is gone and so is the question. Holding means the pair
    stays with the analyst — which the supersede floor already makes the DEFAULT outcome, not the exception.
    """
    view = rk.build_view(_floor_config(), _relocation(rival=True))
    older, newer = _basings(view)[SITE_A], _basings(view)[SITE_B]

    assert older.attrs.get(CANDIDATE) and newer.attrs.get(CANDIDATE), (
        "the supersede pair was popped out of the analyst's queue ('adjudicated by the machine') although "
        f"the subject's identity is unadjudicated (older={dict(older.attrs)}, newer={dict(newer.attrs)}). "
        "Recall-biased triage: with the identity in question the analyst is exactly who should decide."
    )


@pytest.mark.parametrize(
    "floor_id, floor",
    [
        ("require-key-absent", {k: v for k, v in rk.SUPERSEDE_FLOOR.items()
                                if k != "require_earned_identity"}),
        ("require-key-false", {**rk.SUPERSEDE_FLOOR, "require_earned_identity": False}),
    ],
)
def test_the_earned_identity_prohibition_is_not_defeatable_by_config(
    floor_id: str, floor: dict[str, Any],
) -> None:
    """P1 applied to R1.4: a boolean that reopens the fabrication path is a staging switch under a longer name.

    ``supersede_floor.require_earned_identity`` names no value an operator chooses between — it can only
    mean "apply the anti-fabrication guard or do not". Under "default on, no compatibility mode" it must not
    be honourable: whether the key is absent or explicitly ``false``, promoting a relocation over an
    unadjudicated identity stays forbidden. (If the key is instead retained and *ignored*, it is a validated
    no-op, which the sibling gate forbids — deletion is the only consistent outcome.)
    """
    view = rk.build_view(_floor_config(floor=floor), _relocation(rival=True))
    older = _basings(view)[SITE_A]

    assert not rk.edges_of(view, DRAWN) and older.superseded_by is None, (
        f"[{floor_id}] a relocation was drawn / an assertion retired over an unadjudicated identity because "
        "the earned-identity requirement was switched off in config. The four floor conditions are all "
        "about the newer CLAIM; none asks whether the subject is one thing, so this guard is the only thing "
        "standing between an identity error and a fabricated movement assessment."
    )


# ── the mirrors: the relocation beat must survive all four prohibitions ──────────────────────────

def test_an_earned_relocation_is_still_promoted_and_still_drawn() -> None:
    """Mirror for (1)/(2)/(4). One unit named by one mention, nothing contesting it, both sites in one
    declared class: nothing had to be earned, so the relocation is real and must be asserted and drawn.

    Without this the four refusals above could be satisfied by disabling supersession altogether — deleting
    the beat instead of protecting it. Timidity is a failure mode here.
    """
    view = rk.build_view(_floor_config(), _relocation(rival=False))
    older, newer = _basings(view)[SITE_A], _basings(view)[SITE_B]

    assert not _identity_questions(view, UNIT), (
        "fixture premise broken: this is the *uncontested* identity case, but the resolver has an open "
        "identity question about the subject"
    )
    assert older.superseded_by == newer.id, (
        f"the earned relocation was not promoted (gate={older.attrs.get(GATE)!r}, "
        f"hold={older.attrs.get('supersede_hold_reason')!r}). Both sites state the same class and nothing "
        "contests the subject's identity, so neither the site-class de-confliction nor the earned-identity "
        "guard has anything to withhold here."
    )
    assert rk.edges_of(view, DRAWN), (
        "no node→node `supersedes` edge was drawn for the earned relocation — an analyst must be able to "
        "see and click the movement, not infer it from two basing edges"
    )


def test_a_well_evidenced_retired_position_still_reads_stale() -> None:
    """Mirror for (3): where the retired position *was* assessable, ``stale`` is the right word.

    Only the laundering of an honest refusal is forbidden. Retiring a real former position — "we knew this,
    it is now history" — is the beat itself, and a guard that suppressed the label would make every
    relocation's origin look like an open collection gap forever.
    """
    view = rk.build_view(_floor_config(), _relocation(rival=False))
    older = _basings(view)[SITE_A]

    assert older.status == "stale", (
        f"an assessable retired position reads {older.status!r}. The protection is scoped to an assertion "
        "that was never established; it does not disable retirement."
    )
    assert not view.known_gaps, (
        f"the assessable mirror raised gaps {[g.related_ref for g in view.known_gaps]} — it is only "
        "meaningful while the retired edge has no honest refusal to protect"
    )
