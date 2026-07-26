"""DEFAULT-ON P4 + P5 — **refuse AND escalate**, and every refusal names its real ground.

Authored from the session spec alone, implementation-blind. The two properties, quoted:

    "REFUSE **AND** ESCALATE — both halves. Whenever the system declines to fuse or declines to assert, the
    analyst must RECEIVE it: a named gap or a queued candidate carrying the reason and the quote. Write
    tests that fail if a refusal leaves both halves orphaned with no gap, and if a pair capped at a ceiling
    loses its reason and silently leaves the analyst's view. 'Retained but never surfaced' must fail."

    "EVERY REFUSAL NAMES ITS REAL GROUND. A declined identity's analyst-facing reason must state the ground
    that actually caused it, not a fixed default. Write a test that fails when the surfaced reason and the
    computed reason disagree."

**Why this is the non-negotiable and not a UX nicety.** The runtime rule has two halves: where evidence is
absent, ambiguous or contradictory the system returns an explicit refusal, **names what is missing**, and
**escalates to the analyst**. Refusing to assert is only the first half. A pair the resolver withheld from
fusion and then dropped from every list is indistinguishable, from outside, from a pair it never scored —
so a silent non-merge destroys the finding along with the merge. Worse, the resemblance was itself
intelligence: a look-alike that straddles two operators, or two co-located batteries with no designation,
is either an extraction error or deliberate conflation, and both are exactly what a human should see.

**"Retained but never surfaced" has a precedent in this codebase, quoted from ``resolve/cluster.py``:** a
``NAME_VARIANT`` cluster "whose whole justification is that the analyst receives it WITH the licensing
quote" scored into the auto band, matched none of the enumerated blockers, "and landed in ``possible``.
Retained but never surfaced, i.e. raise-only had become a quiet drop rather than a referral." That bug was
fixed for one enumeration; this gate asserts the *property* instead, so it cannot come back through a
different cap.

**A cap may withhold ATTENTION; it may not withhold the RECORD.** The design distinguishes a ceiling of
``probable`` ("withheld from fusion but guaranteed a queue place") from ``possible`` ("has not earned
attention"). This file does not argue with that triage decision: it asserts only that the *reason survives
and is readable*, and that it states the ceiling actually applied. A pair may sit on the watch-list rather
than the review queue — it may not sit there with no record of why it was refused.

**These fixtures put the identity machinery LIVE rather than testing the shipped flag state.** That is
deliberate: the sibling gate ``test_defaulton_no_staging_switch_spec.py`` owns "the machinery is on by
default", and if these tests inherited the flag-off graph they would fail for *its* reason and say nothing
about escalation. So the stage is stated live here, and each failure below is genuinely about whether a
refusal reaches a human.

Abstract fixtures throughout (ruling M4): the corpus carries zero coreference annotations and one numbered
formation, so this family is untestable on it in principle. Principle #4 — logic correctness may never rest
on a corpus-dependent test.
"""

from __future__ import annotations

from typing import Any, NamedTuple

import pytest

from chanakya.resolve.rconfig import BAND_POSSIBLE, BAND_PROBABLE
from chanakya.schemas import pair_key
from tests import _rk_coref as rc
from tests import _rk_layer as rk


def _live(**block: Any):
    """The shipped bundle with the identity stage LIVE — see the module docstring for why.

    Today that means pinning the stage flag on; once the flag is deleted the same call is simply the shipped
    default with the named tunables overridden, so this helper keeps working in both worlds and neither
    reading changes what the assertions mean.
    """
    base = rc.bundle(flag_on=True, supersede_floor=dict(rk.SUPERSEDE_FLOOR))
    shipped = rc.earned_identity_block()
    return rc.with_resolution(base, earned_identity={**shipped, "enabled": True, **block})


#: Gap text that marks a Known Gap as being about *this identity question* rather than about the element's
#: own evidence template. A generic "insufficient evidence" gap on a node is not the analyst receiving the
#: withheld-merge reason, so it must not count as escalation.
_IDENTITY_GAP_TOKENS = (
    "identity", "merge", "same-as", "duplicate", "co-location", "colocation", "conflation", "normalis",
    "normaliz", "namespace", "designation",
)


def _received(part: Any, a: str, b: str, view: Any = None) -> dict[str, str]:
    """Everything analyst-facing the system carries about this refused pair, in ANY channel.

    Deliberately searched rather than assumed: the spec fixes that the analyst *receives* the refusal, never
    which structure carries it. Counted are every ``pair_key``-indexed mapping of strings on the partition,
    a drawn do-not-merge edge, and (when a view is supplied) a Known Gap that names one endpoint AND reads
    as being about the identity question. A new channel is therefore found automatically; a generic
    sufficiency gap is not mistaken for one.
    """
    key = pair_key(*sorted((a, b)))
    out: dict[str, str] = {}
    for name in type(part).model_fields:
        value = getattr(part, name, None)
        if isinstance(value, dict) and isinstance(value.get(key), str) and value[key].strip():
            out[f"partition.{name}"] = value[key]
    if any({x, y} == {a, b} for x, y in getattr(part, "distinct_from", [])):
        out["partition.distinct_from"] = f"drawn do-not-merge edge {a}|{b}"
    for gap in getattr(view, "known_gaps", []) or []:
        text = f"{gap.what_missing or ''} {' '.join(gap.missing_slots or [])}".lower()
        if gap.related_ref in (a, b, key) and any(tok in text for tok in _IDENTITY_GAP_TOKENS):
            out[f"gap.{gap.id}"] = text
    return out


# ── the four refusal grounds, each with the ground it must name ──────────────────────────────────

class Refusal(NamedTuple):
    claims: list
    config: Any
    pair: tuple[str, str]
    #: Substrings any one of which shows the reason naming THIS ground (never the prose itself — G6).
    ground_tokens: tuple[str, ...]


_ORG = "Alpha Precision Machinery"
_ORG_QUOTE = f"{_ORG}, also known as {_ORG}, per the register"
_DESCRIPTOR = "air defence battery"


def _name_alone() -> Refusal:
    """The shipped ``name_ceiling: possible`` case: identical names and *nothing else*.

    "Designations and organisation names are reused across armies and across time, so a name match is
    recall evidence, not a verdict." Recall evidence is still evidence — the pair is the analyst's to accept
    with one click, and it must arrive saying that one more trivially-available signal would clear the cap.
    """
    name = "Zeta Machine Works"
    return Refusal(
        claims=[
            rc.ent("z1", "trading_org", name, doc="d1"),
            rc.ent("z2", "trading_org", name, doc="d2", sid="mid"),
        ],
        config=_live(),
        pair=("z1", "z2"),
        ground_tokens=("name", "designation"),
    )


def _colocation_at(ceiling: str) -> Refusal:
    """Two formations agreeing on nothing but where they are standing (D-13.14/G16)."""
    return Refusal(
        claims=[
            rc.ent("unit_a", "unit", _DESCRIPTOR, doc="d1"),
            rc.ent("unit_b", "unit", _DESCRIPTOR, doc="d2", sid="mid"),
            rc.site("site", "Alpha Cantonment", doc="d1"),
            rc.rel("r-ba-a", "unit_a", "based-at", "site", doc="d1", iso="2021-03-01"),
            rc.rel("r-ba-b", "unit_b", "based-at", "site", doc="d2", iso="2021-03-05", sid="mid"),
            *rc.shared_neighbours("unit_a", "unit_b"),
        ],
        config=_live(colocation_ceiling=ceiling),
        pair=("unit_a", "unit_b"),
        ground_tokens=("co-location", "colocation", "standing", "based-at"),
    )


def _cross_operator() -> Refusal:
    """A same-named pair straddling two stated operators — the costliest over-merge for an ORBAT."""
    return Refusal(
        claims=[
            rc.ent("org_cn", "trading_org", _ORG, doc="d1", attrs={"origin_country": "China"}),
            rc.ent("org_pk", "trading_org", _ORG, doc="d1", sid="mid",
                   attrs={"origin_country": "Pakistan"}),
            rc.coref("org_cn", "org_pk", quote=_ORG_QUOTE, doc="d1"),
        ],
        config=_live(),
        pair=("org_cn", "org_pk"),
        ground_tokens=("namespace", "operator", "china", "pakistan"),
    )


def _unreadable_value() -> Refusal:
    """C7's third state: a wall-eligible slot stating a value no declared equivalence class covers.

    Neither a conflict nor an agreement — so it may not wall (that would shatter a legitimate merge) and it
    may not fuse (that would assert an identity the evidence does not support). It must do neither, and say
    which slot it could not read: "a gap that does not bind the fusion path is decoration."
    """
    return Refusal(
        claims=[
            rc.ent("u1", "unit", "8th AD Battalion", doc="d1",
                   attrs={"service_branch": "PAF", "designator": "8"}),
            rc.ent("u2", "unit", "8th AD Battalion", doc="d2", sid="mid",
                   attrs={"service_branch": "Blue Force Air Arm", "designator": "8"}),
            *rc.shared_neighbours("u1", "u2"),
        ],
        config=_live(),
        pair=("u1", "u2"),
        ground_tokens=("service_branch", "normalis", "normaliz", "equivalence class"),
    )


REFUSALS: dict[str, Any] = {
    "name-alone": _name_alone,
    "co-location-capped-at-probable": lambda: _colocation_at(BAND_PROBABLE),
    "co-location-capped-at-possible": lambda: _colocation_at(BAND_POSSIBLE),
    "cross-operator": _cross_operator,
    "unreadable-stated-value": _unreadable_value,
}


# ── P4: both halves — refuse, and let the analyst receive it ─────────────────────────────────────

@pytest.mark.parametrize("ground", sorted(REFUSALS))
def test_a_refusal_is_never_left_with_both_halves_orphaned(ground: str) -> None:
    """The gate. Every declined fusion must be refused **and** received.

    Two ways to fail, and the second is the quiet one:

    * the pair fuses anyway — the refusal did not happen;
    * the pair is refused and no channel carries the reason — the refusal happened and nobody was told, so
      from the analyst's side it is identical to a pair that never scored.
    """
    case = REFUSALS[ground]()
    part = rc.part_of(case.claims, case.config)
    a, b = case.pair
    view = rk.build_view(case.config, case.claims)
    received = _received(part, a, b, view)

    assert not rc.fused(part, a, b), (
        f"[{ground}] the pair FUSED, so there is no refusal to escalate "
        f"(signals={rc.signals(part, a, b)}). Fix the refusal before the escalation."
    )
    assert received, (
        f"[{ground}] the merge was withheld and the analyst was told NOTHING. Searched every pair-keyed "
        f"channel on the partition, the drawn do-not-merge edges and the Known Gap register; the pair reads "
        f"{rc.status(part, a, b)!r} with no reason anywhere. 'Retained but never surfaced' is a quiet drop "
        "wearing the clothes of a referral — the same defect a NAME_VARIANT cluster hit once already. The "
        "non-negotiable has two halves: decline to assert, AND escalate to the analyst."
    )


@pytest.mark.parametrize("ground", sorted(REFUSALS))
def test_the_surfaced_reason_names_the_ground_that_actually_caused_it(ground: str) -> None:
    """P5. A reason that does not name its ground is a fixed default wearing a rationale's clothes.

    The analyst's next action depends entirely on *which* question was withheld: adjudicate two stated
    countries, add a normalisation row, look for a unit-level discriminator, or accept a name match. A
    generic "not merged" leaves all four indistinguishable and teaches the analyst to skim the queue.
    """
    case = REFUSALS[ground]()
    part = rc.part_of(case.claims, case.config)
    a, b = case.pair
    received = _received(part, a, b, rk.build_view(case.config, case.claims))
    text = " ".join(received.values()).lower()

    assert received, (
        f"[{ground}] no reason was surfaced at all, so it cannot name a ground — see "
        "test_a_refusal_is_never_left_with_both_halves_orphaned, which owns that half"
    )
    assert any(tok in text for tok in case.ground_tokens), (
        f"[{ground}] the surfaced reason never names the ground that caused the refusal. Wanted any of "
        f"{list(case.ground_tokens)}; got {received}. The reason must state the ground the system actually "
        "computed — not a fixed default — because the ground IS the analyst's instruction."
    )


def test_no_two_refusal_grounds_collapse_to_one_reason() -> None:
    """P5's sharper form: different grounds must not share a reason string.

    A single generic rationale reused across grounds passes every "a reason exists" test and still tells the
    analyst nothing. Comparing the grounds against each other is what makes "names its REAL ground"
    testable: if two computed grounds produce one surfaced string, at most one of them is being reported.
    """
    reasons: dict[str, str] = {}
    for ground in sorted(REFUSALS):
        case = REFUSALS[ground]()
        part = rc.part_of(case.claims, case.config)
        a, b = case.pair
        received = _received(part, a, b, rk.build_view(case.config, case.claims))
        reasons[ground] = " ".join(sorted(received.values())).strip()

    missing = sorted(g for g, r in reasons.items() if not r)
    assert not missing, (
        f"these grounds surfaced no reason at all: {missing}. Every one of them refused a fusion, so every "
        "one of them owes the analyst a rationale before this comparison can mean anything."
    )
    collisions = {
        (x, y) for x in reasons for y in reasons
        if x < y and reasons[x] == reasons[y]
    }
    assert not collisions, (
        f"two different refusal grounds produced the SAME analyst-facing reason: {sorted(collisions)}. "
        "That is a fixed default, and it makes 'the reason states the ground' false while every "
        "existence check still passes."
    )


# ── P4 + P5 together: a ceiling must not cost the pair its record, and must be reported accurately ──

@pytest.mark.parametrize("ceiling", [BAND_PROBABLE, BAND_POSSIBLE])
def test_a_pair_capped_at_a_ceiling_keeps_its_reason_and_that_reason_states_the_ceiling(
    ceiling: str,
) -> None:
    """"…if a pair capped at a ceiling loses its reason and silently leaves the analyst's view."

    A ceiling is a statement about *how much attention* a pair has earned. It is not a statement that the
    refusal never happened, so lowering it may move the pair from the review queue to the watch-list — it
    may not erase the record. And whichever ceiling was applied is part of the ground: a pair the operator
    capped at ``possible`` and one capped at ``probable`` are being told two different things, so a reason
    that hard-codes one band while the config applied the other is the surfaced reason disagreeing with the
    computed one (P5) even though it looks specific.
    """
    case = _colocation_at(ceiling)
    part = rc.part_of(case.claims, case.config)
    a, b = case.pair
    received = _received(part, a, b, rk.build_view(case.config, case.claims))
    text = " ".join(received.values()).lower()

    assert received, (
        f"capped at {ceiling!r}, the co-located pair left the analyst's view entirely — no queue item, no "
        f"gap, no reason (status {rc.status(part, a, b)!r}). The cap withholds a FUSION, and may withhold "
        "the analyst's attention; it may not withhold the record of the refusal. This is the exact shape of "
        "the quiet-drop defect the register already names."
    )
    assert ceiling in text, (
        f"capped at {ceiling!r}, the surfaced reason states a different band: {received}. The reason must "
        "name the ceiling the system actually applied — a hard-coded band in the prose makes the rationale "
        "diverge from the decision the moment an operator retunes the dial, and the analyst then reads a "
        "verdict nobody computed."
    )


# ── the mirrors ─────────────────────────────────────────────────────────────────────────────────

def test_a_pair_with_nothing_to_refuse_is_not_handed_a_refusal_reason() -> None:
    """Mirror: this must not be satisfied by attaching a rationale to everything.

    A queue full of reasons for merges that were never withheld is the same failure as a queue with none —
    the analyst cannot tell which items are real. So an earned merge carries no refusal rationale.
    """
    name = "Zeta Machine Works"
    claims = [
        rc.ent("z1", "trading_org", name, doc="d1", attrs={"origin_country": "China"}),
        rc.ent("z2", "trading_org", name, doc="d1", sid="mid", attrs={"origin_country": "CHINA"}),
        rc.coref("z1", "z2", quote=f"{name}, also known as {name}, per the register", doc="d1"),
    ]
    config = _live()
    part = rc.part_of(claims, config)

    assert rc.fused(part, "z1", "z2"), (
        f"the control pair did not fuse ({rc.status(part, 'z1', 'z2')!r}) — one name, one country spelled "
        "two ways, and a document stating the equivalence. If this is refused, the refusals above are "
        "measuring timidity rather than judgement."
    )
    assert not _received(part, "z1", "z2", rk.build_view(config, claims)), (
        f"an accepted merge carries a refusal rationale: {_received(part, 'z1', 'z2')}. A reason on every "
        "pair is as useless as a reason on none."
    )


def test_the_escalation_carries_the_licensing_quote_where_a_document_supplied_one() -> None:
    """Mirror / regression pin for the other half of "a queued candidate carrying the reason **and the quote**".

    This half already works with the machinery live, and it is pinned here because the P4 fix above touches
    the same code path: a raised coreference link is only acceptable *because* the analyst is handed the exact
    sentence that licensed it, and an audit already found that justification fictional once — the quote was
    stamped on the claim and read nowhere, so "the analyst is handed the sentence" described a screen nobody
    could see. Whatever channel the ``possible`` tier gains must not lose this one.

    ``NAME_VARIANT`` is the right category to pin it on: it is raise-only **permanently** (because an
    authoritative bind bypasses banding, a licensed NAME_VARIANT *is* the exact-name auto-merge lane the
    design exists to delete), so its whole value is the referral.
    """
    name = "Alpha Air Defence Regiment"
    quote = f"the {name} (AADR) was inducted in March"
    claims = [
        rc.ent("reg_long", "unit", name, doc="d1"),
        rc.ent("reg_short", "unit", "AADR", doc="d1", sid="mid",
               attrs={"service_branch": "Pakistan Army"}),
        rc.coref("reg_long", "reg_short", evidence=rc.NAME_VARIANT, quote=quote, doc="d1"),
    ]
    config = _live()
    part = rc.part_of(claims, config)
    received = _received(part, "reg_long", "reg_short", rk.build_view(config, claims))
    text = " ".join(received.values())

    assert received, (
        "a raise-only coreference link reached the analyst with no rationale at all — NAME_VARIANT is "
        "raise-only *permanently*, and its whole justification is that the pair arrives with the licensing "
        f"quote attached. candidates={part.candidates} possible={part.possible}"
    )
    assert quote in text or "AADR" in text, (
        f"the escalation does not carry the document's own words: {received}. The quote is the only thing "
        "that lets an analyst adjudicate the proposal in one read; without it the queue item is an "
        "unfalsifiable assertion that two mentions might be one thing."
    )
