"""RK-COREF (S3) — the discriminator ladder (D-13.20), the per-layer policy (D-13.10) and C7's third state.

Authored from the session spec alone. The ladder, quoted from §7 RK-COREF 6:

    "differing designation (veto) > composite unique id > temporally-witnessed continuity > shared
    designation > operator (post-normalization) > geography (perishable) > relational > name"

with two load-bearing riders:

* "**A shared designation is NOT a unique identifier**: ``hard_id_fields.unique`` is a list of **composite
  AND-keys** (``(service_branch, designator)``), because designations are reused across armies and across
  time."
* "Preserve the bill-of-lading asymmetry: **differing identifiers veto, shared ones do not confirm.**"

and D-13.10's per-layer profile: "design collapses readily but *never on name alone* (name is a
rarity-graded contributor, capped at *possible*); instance fully earned" — which "**Requires splitting
``attribute_score`` into two signals (``name`` / ``discriminator``)** … without the split D-13.10 cannot
function at all."

The widest hole this file aims at is §5b's second review finding: "**Name is a verdict in Phase 1, at every
type** … The widest name-only fusion path **bypasses the bands entirely** via the Phase-1 bootstrap
disjunction, and applies to ``unit``, ``variant``, ``basing_site`` and every other type."
"""

from __future__ import annotations

import pytest

from tests import _rk_coref as rc

# One designator, two armies — the reuse D-13.20 is about.
BRANCH_A, BRANCH_A_LONG = "PAF", "Pakistan Air Force"
BRANCH_B = "Pakistan Army"
UNNORMALIZABLE = "P.A.F. (Northern)"


def _named_pair(etype: str, name: str, *, attrs_a=None, attrs_b=None, scaffold: bool = False) -> list:
    claims = [
        rc.ent("a", etype, name, attrs=attrs_a or {}, doc="d1"),
        rc.ent("b", etype, name, attrs=attrs_b or {}, doc="d2", sid="mid"),
    ]
    return claims + (rc.shared_neighbours("a", "b") if scaffold else [])


# ── name is not a verdict: the cap binds the Phase-1 bootstrap, at every layer ───────────────────

@pytest.mark.parametrize("etype", ["variant", "unit", "basing_site", "manufacturer"])
def test_an_identical_name_alone_never_fuses_at_any_type(etype: str) -> None:
    """§5b: "name is a verdict in Phase 1 at every type, and the caps exist only in Phase 2.
    R1.2/R3.1/R3.2 must bind **the bootstrap disjunction**."

    D-13.10: name is "capped at *possible*" — and the shipped config already asks for it
    (``name_alone_caps_at_possible: true``), which today the bootstrap never consults.
    """
    part = rc.part_of(_named_pair(etype, "Type Nine"), rc.bundle())

    assert not rc.fused(part, "a", "b"), (
        f"two {etype} mentions sharing nothing but an identical name FUSED at confidence 1.0 through the "
        "Phase-1 bootstrap, bypassing the bands and the name cap entirely. That is the widest over-merge "
        f"path in the substrate. same_as={part.same_as} breakdown={rc.signals(part, 'a', 'b')}"
    )


@pytest.mark.parametrize("etype", ["variant", "unit", "basing_site", "manufacturer"])
def test_a_name_alone_pair_still_reaches_the_watch_list(etype: str) -> None:
    """The mirror: capped is not deleted. The shipped comment on ``name_alone_caps_at_possible`` states the
    intent — "it is capped at ``possible`` (the watch-list)" — and ``possible_floor`` exists so "the capped
    pair land[s] somewhere". A cap that dropped the pair would turn a recall tool into a silent filter.
    """
    part = rc.part_of(_named_pair(etype, "Type Nine"), rc.bundle())

    assert rc.status(part, "a", "b") == "possible", (
        f"a name-alone {etype} pair reads {rc.status(part, 'a', 'b')!r}. D-13.10 caps name at *possible* — "
        "the watch-list link the analyst can see but is not pestered by — it does not delete the pair."
    )


def test_a_design_pair_collapses_on_the_name_plus_one_more_signal() -> None:
    """D-13.10, the permissive half: "design collapses readily … one more trivially-available signal clears
    it" (REVIEW-VERDICT rk-17: "D-13.10's per-layer profile is unimplemented, so designs never collapse").

    Two variant mentions of one name that also agree on a durable declared attribute must fuse. Without
    this, spine/13 §6's lever 2 cannot exist and the anchor layer never crystallizes.
    """
    part = rc.part_of(
        _named_pair("variant", "Type Nine", attrs_a={"family": "HQ-9"}, attrs_b={"family": "HQ-9"}),
        rc.bundle(),
    )

    assert rc.fused(part, "a", "b"), (
        "a design-layer pair agreeing on its name AND on a durable declared attribute did not collapse. "
        "The per-layer profile is 'one judge, a permissive per-layer *profile*' — a cap on the instance "
        f"layer must not be applied to the design layer wholesale. status={rc.status(part, 'a', 'b')}"
    )


def test_an_instance_pair_is_not_confirmed_by_the_name_plus_one_more_signal() -> None:
    """The other side of the same profile: "instance fully earned."

    D-13.14: "confirming a formation needs a unit-level discriminator" — an operator agreement is not one,
    because every formation in an ORBAT shares it.
    """
    part = rc.part_of(
        _named_pair("unit", "air defence battery",
                    attrs_a={"service_branch": BRANCH_A}, attrs_b={"service_branch": BRANCH_A},
                    scaffold=True),
        rc.bundle(),
    )

    assert not rc.fused(part, "a", "b"), (
        "two formation mentions were confirmed as one unit on a shared descriptor name plus a shared "
        "operator/design — every battery in the order of battle shares those. Confirming a formation needs "
        f"a unit-level discriminator. same_as={part.same_as} breakdown={rc.signals(part, 'a', 'b')}"
    )


# ── the split: `name` and `discriminator` are separate signals ───────────────────────────────────

def test_the_merge_breakdown_reports_name_and_discriminator_separately() -> None:
    """D-13.20's first code change: "**Split ``attribute_score`` into two signals (``name`` /
    ``discriminator``).** They are already computed independently and fused at a single ``max`` … **Without
    it, D-13.10 cannot function at all**: 'a name match reaches at most *possible*, and one more
    trivially-available signal clears it' is unexpressible while the two live in one number."

    Asserted on the stored breakdown because that is the analyst-facing accounting (``identity_ledger``
    reads it), and because a cap that cannot see the two apart cannot be expressed.
    """
    part = rc.part_of(
        _named_pair("unit", "8th AD Battalion",
                    attrs_a={"service_branch": BRANCH_A, "designator": "8"},
                    attrs_b={"service_branch": BRANCH_A, "designator": "8"}, scaffold=True),
        rc.bundle(),
    )
    keys = set(rc.signals(part, "a", "b"))
    named = {k for k in keys if "name" in k.lower()}
    discriminator = {k for k in keys if "discrimin" in k.lower()}

    assert named and discriminator, (
        "the merge breakdown carries no separate name / discriminator signals — it reports "
        f"{sorted(keys)}. While both live in one fused `attribute` number, 'name caps at possible' and "
        "'one more signal clears it' cannot be expressed, so D-13.10 has nothing to act on."
    )


def test_the_two_signals_are_weighted_in_config_not_in_code() -> None:
    """G6 still binds: "the per-layer merge floors … and any discriminator-priority weights live in
    ``config/``, never as code literals." A new scored signal needs a declared weight.
    """
    weights = rc.resolution_keys().get("merge_weights") or {}
    named = [k for k in weights if "name" in k.lower()]
    disc = [k for k in weights if "discrimin" in k.lower()]

    assert named and disc, (
        f"config/resolution.yaml merge_weights declares {sorted(weights)} — no separate name/discriminator "
        "weights. Splitting the signal in code while leaving one weight in config buries the new number in "
        "the source (gate G6)."
    )


# ── the designation rungs: composite AND-key, not a bare designation ─────────────────────────────

def test_a_shared_bare_designation_never_confirms() -> None:
    """D-13.20: "Designations are **reused across armies and across time**. One shared designation string
    may **never** confirm a formation merge." The mechanism: ``hard_id_fields.unique`` "is a list of
    composite AND-keys — ``(service_branch, designator)`` is an identifier; a bare ``designator`` is not."
    """
    part = rc.part_of(
        [
            rc.ent("a", "unit", "Alpha Battery", attrs={"designator": "8"}, doc="d1"),
            rc.ent("b", "unit", "Bravo Battery", attrs={"designator": "8"}, doc="d2", sid="mid"),
            *rc.shared_neighbours("a", "b"),
        ],
        rc.bundle(),
    )

    assert not rc.fused(part, "a", "b"), (
        "a shared bare designator '8' confirmed a formation merge. Declaring `designator` as a standalone "
        "`hard_id_fields.unique` entry is exactly the reading D-13.20 forbids: the unique key is the "
        f"composite (service_branch, designator). same_as={part.same_as}"
    )


def test_the_composite_key_declaration_exists_and_is_composite() -> None:
    """The config shape the behaviour rests on — "a list of **composite AND-keys**".

    Ruling **M3**: "**The composite identifier has no declaration site in config at all** — D-13.20's
    ``(service_branch, designator)`` AND-key needs ``hard_id_fields.unique``, which does not exist (the spike
    measured ``_shared_unique_id`` as always False for exactly this reason). Declare it, or the ladder's fast
    path stays unreachable."
    """
    unique = rc.hard_id_unique()
    assert unique, (
        "config/resolution.yaml declares no `hard_id_fields.unique`, so `_shared_unique_id` is always "
        "False and the strongest rung of the ladder is unwired (code facts B6: 'the \"shared unique "
        "identifier ⇒ fast path to confirmed\" mechanism is not wired')."
    )
    flat = {etype: keys for etype, keys in unique.items()
            if not all(isinstance(k, (list, tuple)) for k in (keys or []))}
    assert not flat, (
        f"`hard_id_fields.unique` declares bare attribute lists for {sorted(flat)} ({flat}). D-13.20: a "
        "unique identifier is an AND-key over several attributes; a flat list makes every single attribute "
        "individually sufficient, which is the shared-designation confirm the ladder exists to refuse."
    )
    unit_keys = [set(map(str, k)) for k in (unique.get("unit") or [])]
    assert any({"service_branch", "designator"} <= k for k in unit_keys), (
        f"the formation type declares {unit_keys} — none of them is the worked AND-key D-13.20 names, "
        "(service_branch, designator). That key is what 'makes the operator requirement **structural in the "
        "identifier declaration**' rather than dependent on a namespace check the spike measured as broken."
    )


def test_a_shared_composite_key_does_confirm() -> None:
    """The mirror — the composite rung "lifts all caps", so the ladder is not a wall in disguise.

    Two mentions agreeing on branch **and** designator are one formation by construction; a system that
    refused this would fragment the order of battle rather than protect it. Deliberately given **no** shared
    neighbours and **dissimilar** names, so the composite identifier is the only rung that can carry it —
    i.e. this asserts the declaration is *consumed*, not merely present (M3: "Assert that these declarations
    exist and are **consumed**").
    """
    part = rc.part_of(
        [
            rc.ent("a", "unit", "8th Air Defence Battalion",
                   attrs={"service_branch": BRANCH_A, "designator": "8"}, doc="d1"),
            rc.ent("b", "unit", "Sargodha AD element",
                   attrs={"service_branch": BRANCH_A, "designator": "8"}, doc="d2", sid="mid"),
        ],
        rc.bundle(),
    )

    assert rc.fused(part, "a", "b"), (
        "two mentions stating the SAME (service_branch, designator) composite were not fused, and nothing "
        "else in this fixture could have earned it. That rung 'lifts all caps' — an unconsumed declaration "
        f"leaves the fast path unreachable exactly as the spike measured. status={rc.status(part, 'a', 'b')} "
        f"breakdown={rc.signals(part, 'a', 'b')}"
    )


def test_a_differing_designation_is_a_hard_and_visible_veto() -> None:
    """Top of the ladder: "differing designation (veto)". Two differently-numbered battalions of one
    branch are two units, whatever else they share — and the wall must be the **transitive, visible**
    channel, not a pairwise consultation (§5a G18: the geo-veto shape "is non-transitive *and* unreported").
    """
    part = rc.part_of(
        [
            rc.ent("a", "unit", "air defence battery",
                   attrs={"service_branch": BRANCH_A, "designator": "8"}, doc="d1"),
            rc.ent("b", "unit", "air defence battery",
                   attrs={"service_branch": BRANCH_A, "designator": "12"}, doc="d2", sid="mid"),
            *rc.shared_neighbours("a", "b"),
        ],
        rc.bundle(),
    )

    assert not rc.fused(part, "a", "b"), (
        "the 8th and the 12th battalion were fused into one unit. A stated differing designation is the "
        f"strongest wall on the ladder. same_as={part.same_as}"
    )
    assert rc.visible_rationale(part, "a", "b"), (
        "the pair was held apart with nothing an analyst can read — no `distinct_from` membership and no "
        "candidate reason. A wall consulted only inside `vetoed()` is 'hard, pairwise and invisible': the "
        "D9 bridge alarm, `finalise` and the surfaced distinct-from edge all ignore it."
    )


def test_the_existing_bill_of_lading_veto_still_fires() -> None:
    """Regression on the rail D-13.20 says to *preserve*: "The codebase already embodies exactly this
    asymmetry for bills of lading: differing identifiers veto, shared ones do not confirm. **Preserve that
    asymmetry; do not 'fix' it.**"
    """
    part = rc.part_of(
        [
            rc.ent("e1", "contract_import_event", "KPQA-HC-2020-118834", doc="d1"),
            rc.ent("e2", "contract_import_event", "KPQA-HC-2020-118835", doc="d1"),
        ],
        rc.bundle(),
    )

    assert not rc.fused(part, "e1", "e2") and rc.walled(part, "e1", "e2"), (
        "two customs events stating DIFFERENT bills of lading are no longer vetoed "
        f"(fused={rc.fused(part, 'e1', 'e2')}, walled={rc.walled(part, 'e1', 'e2')}). Merging them "
        "collapses two import events and silently corrupts the supply-chain count."
    )


# ── C7: normalization is a prerequisite for walling on ANY slot, and the third state ─────────────

def _branch_pair(value_b: str) -> list:
    """One designator, one name, two *stated* branch values — the discriminating input is ``value_b``.

    Stated explicitly per the S2 lesson: "when a mechanism has a three-way outcome, a mirror must state the
    discriminating input explicitly, or it silently tests the wrong branch."
    """
    return [
        rc.ent("a", "unit", "8th AD Battalion",
               attrs={"service_branch": BRANCH_A, "designator": "8"}, doc="d1"),
        rc.ent("b", "unit", "8th AD Battalion",
               attrs={"service_branch": value_b, "designator": "8"}, doc="d2", sid="mid"),
        *rc.shared_neighbours("a", "b"),
    ]


def test_the_operator_slot_is_declared_critical() -> None:
    """§7 RK-COREF 6: "**S3 owns** the per-instance-type critical-discriminator declaration
    (operator/branch critical) and value normalization (PAF ≡ 'Pakistan Air Force')."

    The shipped config records why it was not critical yet — "promoting them to critical needs value
    normalisation first (a later stage)". S3 is that stage.
    """
    entry = dict(rc.resolution_keys().get("attribute_roles", {}).get("unit", {}).get("service_branch") or {})
    assert entry.get("role") == "critical", (
        f"unit.service_branch is declared {entry!r}. Once normalization exists, a different service branch "
        "is a different entity — that promotion is the whole reason C7 makes normalization a prerequisite."
    )


def test_a_genuinely_different_branch_walls() -> None:
    """The wall the promotion buys: a PAF battalion and a Pakistan Army battalion sharing a designator are
    two units. D-13.20 gives the operator rung "conflict ⇒ hard veto, **gated on normalization**".
    """
    part = rc.part_of(_branch_pair(BRANCH_B), rc.bundle())

    assert not rc.fused(part, "a", "b"), (
        f"a {BRANCH_A} unit and a {BRANCH_B} unit sharing designator '8' were fused — the reuse of "
        f"designations across armies is precisely why the composite key exists. same_as={part.same_as}"
    )
    assert rc.visible_rationale(part, "a", "b"), (
        "the branch conflict held the pair apart with no analyst-visible reason attached."
    )


def test_a_normalizable_branch_variant_does_not_wall() -> None:
    """The mirror, and the reason normalization comes *first*: "a critical veto compares values exactly …
    so walling them SHATTERS legitimate merges — it split the three SINO-GALAXY trading-org spellings and
    would false-wall 'PAF' from 'PAF air defense units'."

    Note this also pins the *ordering*: normalization "must apply **before conflict detection *and* before
    namespace derivation**" (`resolve/entities.py` derives the namespace from raw attrs), so a
    cross-namespace guard added without normalization will fail this test rather than pass quietly.
    """
    part = rc.part_of(_branch_pair(BRANCH_A_LONG), rc.bundle())

    assert not rc.walled(part, "a", "b"), (
        f"{BRANCH_A!r} and {BRANCH_A_LONG!r} — the same branch, spelled two ways — were walled apart as a "
        "stated contradiction. An exact-match wall on unnormalised values shatters legitimate merges."
    )
    assert rc.fused(part, "a", "b"), (
        f"{BRANCH_A!r} vs {BRANCH_A_LONG!r} did not fuse even though, once normalized, the pair states the "
        f"same composite (service_branch, designator). status={rc.status(part, 'a', 'b')} — either "
        "normalization does not run before conflict detection, or it does not run before namespace "
        "derivation (both are required)."
    )


def test_an_unnormalizable_critical_value_neither_walls_nor_fuses() -> None:
    """C7, the third state: "an unnormalizable stated critical value ⇒ **no wall AND no fusion** + a named
    gap. **A gap must bind the fusion path, not merely annotate it.**"

    The prototype bug this closes (REVIEW-VERDICT rk-14-probe, critical): "The prototype **names the missing
    operator gap and then asserts the assessment anyway** … A gap that does not bind the fusion path is
    decoration."
    """
    part = rc.part_of(_branch_pair(UNNORMALIZABLE), rc.bundle())

    assert not rc.walled(part, "a", "b"), (
        f"an unmappable stated value {UNNORMALIZABLE!r} was treated as a stated contradiction and walled. "
        "'We cannot compare these two values' is not 'these two values disagree'."
    )
    assert not rc.fused(part, "a", "b"), (
        f"the pair FUSED while its critical discriminator {UNNORMALIZABLE!r} could not be normalized — the "
        "gap annotated the answer instead of binding it. This is the rk-14-probe critical bug verbatim: "
        f"name the gap, then assert the assessment anyway. same_as={part.same_as}"
    )
    assert rc.visible_rationale(part, "a", "b"), (
        "the third state produced no named gap and no analyst-visible reason: the pair simply sat "
        f"unresolved. C7 requires the gap to be *named*. candidate_reasons={part.candidate_reasons}"
    )
