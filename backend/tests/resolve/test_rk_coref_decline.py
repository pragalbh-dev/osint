"""RK-COREF (S3) — D-13.18: the rebuild may **DECLINE** a grouping (and C3: on relationships too).

Authored from the session spec alone. The mechanism, quoted from `rk-spike-DECISIONS.md`:

    "**The referent atom is *evidence about a grouping*, never the address of the provisional instance.**
    Rebuild groups **claim atoms**; the referent atom is a strong (or authoritative) grouping *signal* the
    grouping step consults. An intra-referent critical-discriminator conflict makes the rebuild **decline**
    the grouping — de-grouping to claim-atom granularity and raising for an analyst. **No atom splits; the
    grouping declines.**"

Why it is load-bearing: "As spine/13 and plan/01 are written, S3 would make intra-document over-merge
permanent." The decline is the only route by which a wrong bind is undone.

**The trap this file is built around.** §7 RK-COREF 3: "**The check must read ``attr_history``, not
``attrs``** — first-claim-wins scalar storage makes the conflict invisible otherwise." So the conflicting
value is deliberately placed in a **non-first** position: a fixture that puts it first is checking the
scalar and proves nothing.

C3: "the decline fires on **relationship** conflicts too, using the same overlapping-time predicate as G18
under C1's rule" — "a coref cluster that binds two mentions the *relationships* say are different things
must decline, for the same reason and by the same test as the cross-document wall."
"""

from __future__ import annotations

import pytest

from tests import _rk_coref as rc

QUOTE = "the 8th AD Battalion … the battalion"


def _opted():
    return rc.with_resolution(rc.bundle(), coref_authoritative_evidence=[rc.EXPLICIT_EQUIVALENCE])


def _grouping(second_designator: str) -> list:
    """An authoritative in-document bind over a member whose SECOND claim restates its designation.

    ``e2``'s first claim agrees with ``e1``; only its second disagrees. ``Entity.attrs`` is first-claim-wins
    (``setdefault``), so a check that compares ``attrs`` sees two agreeing '8's and binds; only the retained
    ``attr_history`` series carries the '12'. That is the whole point of the trap.
    """
    return [
        rc.ent("e1", "unit", "8th AD Battalion",
               attrs={"service_branch": "PAF", "designator": "8"}, doc="d1", cid="c-e1"),
        rc.ent("e2", "unit", "the battalion",
               attrs={"service_branch": "PAF", "designator": "8"}, doc="d1", cid="c-e2-first",
               iso="2025-01-01"),
        rc.ent("e2", "unit", "the battalion",
               attrs={"service_branch": "PAF", "designator": second_designator}, doc="d1",
               cid="c-e2-second", iso="2025-06-01"),
        rc.coref("e1", "e2", doc="d1", quote=QUOTE),
    ]


def test_the_fixture_hides_its_conflict_from_the_scalar_attrs() -> None:
    """Non-vacuity, and it guards the *test* rather than the code.

    If ``attrs`` ever exposed the conflicting value, the decline test below would pass through the ordinary
    ``has_hard_conflict`` rail and would no longer be asserting D-13.18's "read history, not attrs" clause.
    """
    from chanakya.resolve import entities as rentities

    graph = rentities.build(_grouping("12"))
    member = graph.entities["e2"]
    history = [ac.value for ac in member.attr_history.get("designator", [])]

    assert member.attrs.get("designator") == "8", (
        f"the member's scalar attrs already show {member.attrs.get('designator')!r}; the conflict is no "
        "longer hidden and this file would stop testing the history path"
    )
    assert "12" in history, f"the conflicting value never reached attr_history ({history})"


def test_a_conflicting_grouping_declines() -> None:
    """D-13.18: an intra-referent critical-discriminator conflict "makes the rebuild **decline** the
    grouping — de-grouping to claim-atom granularity".
    """
    part = rc.part_of(_grouping("12"), _opted())

    assert not rc.fused(part, "e1", "e2"), (
        "the grouping stood even though one of the claim atoms it groups asserts a different designation. "
        "The referent atom is 'evidence about a grouping, never the address' — if a conflicting grouping "
        "cannot decline, S3 makes intra-document over-merge permanent, which the decision calls "
        f"disqualifying. same_as={part.same_as}"
    )


def test_a_declined_grouping_is_raised_not_dropped() -> None:
    """"…and raising for an analyst." The decline hands the question over; it does not bury it."""
    part = rc.part_of(_grouping("12"), _opted())

    assert not rc.fused(part, "e1", "e2") and (
        rc.status(part, "e1", "e2") is not None or rc.visible_rationale(part, "e1", "e2")
    ), (
        "the declined grouping left no trace: no candidate link and no analyst-visible reason. A decline "
        f"is a referral, not a deletion. candidates={part.candidates} possible={part.possible} "
        f"reasons={part.candidate_reasons}"
    )


def test_a_consistent_grouping_still_binds() -> None:
    """The mirror — a second claim that *restates* the designation is corroboration, not a conflict.

    Same fixture, one changed input, so the decline cannot be implemented as "any member with more than one
    claim declines". Absence of disagreement is not disagreement (the doctrine the conflict machinery
    already follows).
    """
    part = rc.part_of(_grouping("8"), _opted())

    assert rc.fused(part, "e1", "e2"), (
        "a well-licensed bind whose member merely restates the same designation twice was declined. That "
        "turns the decline into a blanket refusal of any multiply-claimed member and forfeits lever 1 "
        f"entirely. status={rc.status(part, 'e1', 'e2')}"
    )


# ── C3: the same decline on a RELATIONSHIP conflict ──────────────────────────────────────────────

def _relationship_grouping(iso_b: str, class_b: str = "garrison") -> list:
    """The same bind, with the conflict on the ``based-at`` relationship instead of an attribute.

    The discriminating inputs are stated explicitly (the S2 lesson): the second basing's **time** and its
    **site class**. Same class + overlapping time ⇒ conflict; anything else ⇒ not a conflict.
    """
    return [
        rc.ent("e1", "unit", "8th AD Battalion", doc="d1"),
        rc.ent("e2", "unit", "the battalion", doc="d1"),
        rc.site("s1", "Bravo Depot", doc="d1"),
        rc.site("s2", "Charlie Cantonment", site_class=class_b, lat=32.0, lon=72.6, doc="d1"),
        rc.rel("rb1", "e1", "based-at", "s1", doc="d1", iso="2021-01-01"),
        rc.rel("rb2", "e2", "based-at", "s2", doc="d1", iso=iso_b),
        rc.coref("e1", "e2", doc="d1", quote=QUOTE),
    ]


def test_a_grouping_whose_relationships_conflict_declines() -> None:
    """C3: "the check is **the same overlapping-time conflict test G18 uses, under C1's ``site_type``
    rule**" — two mentions stated at two garrisons at the same time are two units, whatever the prose says.
    """
    part = rc.part_of(_relationship_grouping("2021-01-01"), _opted())

    assert not rc.fused(part, "e1", "e2"), (
        "an authoritative bind fused two mentions the document's own *relationships* place at two "
        "same-class sites at the same time. The decline and the wall must share one predicate rather than "
        f"drifting apart. same_as={part.same_as}"
    )


@pytest.mark.parametrize(
    "iso_b,class_b,why",
    [
        ("2025-01-01", "garrison", "non-overlapping times are a relocation, not a contradiction"),
        ("2021-01-01", "airfield", "a differing site_type is NOT a conflict (C1)"),
    ],
)
def test_a_non_conflicting_relationship_pair_still_binds(iso_b: str, class_b: str, why: str) -> None:
    """The two mirrors C1 forces, both of them live cases in this corpus.

    C1: "A differing ``site_type`` is NOT a conflict … One unit at its garrison *and* concurrently at a
    forward site is one unit with two basings (the wall does not fire)." And a later basing at another
    garrison is the flagship relocation — walling it would delete the beat the system exists to show.
    """
    part = rc.part_of(_relationship_grouping(iso_b, class_b), _opted())

    assert rc.fused(part, "e1", "e2"), f"the bind was declined, but {why}. same_as={part.same_as}"
