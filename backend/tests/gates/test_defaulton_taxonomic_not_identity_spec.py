"""DEFAULT-ON follow-up — **a CLASS is not an IDENTITY**, and it may not lift the name cap.

The measured hole this file closes. With both stage flags deleted the name cap became the ONLY guard on the
widest fusion lane, and the cap lifts on any agreeing "discriminator" — which was computed as
``agreeing / present`` over every declared critical/supporting attribute. A taxonomic attribute is therefore
a permanent skeleton key: **every member of a class shares its class by definition**, so "both are HQ-9
family", "both are S-band", "both are Pakistan Air Force" agree between any two mentions of the same kind of
thing. Measured on the booted corpus, that one term put HQ-9 ↔ HQ-9A, HQ-9 ↔ HQ-9B, HQ-9A ↔ HQ-9B and
HQ-9A ↔ HQ-9BE on the fusion path — four different missiles, the costliest over-merge class in an ORBAT —
and a lifted cap means no queue item, no watch-list entry, no wall and no gap: a silent fabrication of
identity.

The properties asserted, in the direction the reader cannot infer from the config file:

1. an agreeing **taxonomic** attribute does NOT clear the name cap (the pair stays unfused and RETAINED with
   a reason that names the ground);
2. an agreeing **identity-bearing** attribute still does (the permissive half of D-13.10 survives — this is
   not a ban dressed as a cap);
3. a taxonomic attribute keeps every NEGATIVE consequence: a stated difference on a critical taxonomic
   attribute still walls, and on a supporting one still penalises. The fix removes a false positive, not a
   real guard;
4. the declaration is exhaustively READ — nothing in the shipped ``attribute_roles`` can be marked taxonomic
   and then quietly counted anyway.

Abstract fixtures (ruling M4), so the property holds independently of what the corpus happens to state.
"""

from __future__ import annotations

import pytest

from chanakya.resolve.entities import Entity
from chanakya.resolve.rconfig import ROLE_CRITICAL, ResolveConfig
from chanakya.resolve.scoring import (
    attribute_signals,
    has_durable_identity_support,
)
from tests import _rk_coref as rc
from tests import _rk_layer as rk

#: A class label every member of the class shares — declared ``taxonomic: true`` in config/resolution.yaml.
TAXONOMIC = ("variant", "family", "HQ-9")
#: An individuating label — one production line, one customer.
IDENTITY_BEARING = ("variant", "export_designator", "FD-2000")


def _cfg() -> ResolveConfig:
    return ResolveConfig.from_bundle(rk.shipped_bundle())


def _pair(etype: str, name: str, attrs_a: dict, attrs_b: dict) -> list:
    return [
        rc.ent("a", etype, name, attrs=attrs_a, doc="d1"),
        rc.ent("b", etype, name, attrs=attrs_b, doc="d2", sid="mid"),
    ]


# ── 1. the class label does not clear the cap ────────────────────────────────────────────────────

def test_an_agreeing_class_attribute_does_not_lift_the_name_cap() -> None:
    """Two same-named designs agreeing on nothing but their FAMILY must not fuse.

    This is the fabrication path as measured: ``family`` is stated identically on HQ-9, HQ-9A, HQ-9B and
    HQ-9BE — that is what a family *is* — so counting it as an agreeing discriminator switched the cap off
    for exactly the pairs the cap exists for.
    """
    etype, attr, value = TAXONOMIC
    part = rc.part_of(_pair(etype, "Type Nine", {attr: value}, {attr: value}), rc.bundle())

    assert not rc.fused(part, "a", "b"), (
        f"two {etype} mentions agreeing only on the CLASS attribute {attr!r}={value!r} FUSED. Every member "
        f"of a class shares its class by definition, so this is a name-only merge with a taxonomic label "
        f"standing in for evidence. signals={rc.signals(part, 'a', 'b')}"
    )


def test_the_class_attribute_never_reaches_the_discriminator_signal() -> None:
    """The mechanism, not just the outcome: a taxonomic agreement scores ``discriminator == 0``.

    Asserted on the sub-signal because that is what the cap reads. An implementation that special-cased the
    *cap* while still crediting the class label would keep inflating ``attribute`` — i.e. the pair would
    climb the bands on a class agreement even where the cap held.
    """
    etype, attr, value = TAXONOMIC
    cfg = _cfg()
    ea, eb = _entities(etype, "Type Nine", {attr: value})

    _name, discriminator = attribute_signals(ea, eb, cfg)
    assert discriminator == 0.0, (
        f"a co-stated taxonomic {attr!r} scored discriminator={discriminator} — the class label is still "
        "being credited as positive identity evidence one layer below the cap."
    )
    assert not has_durable_identity_support(ea, eb, cfg), (
        f"a co-stated taxonomic {attr!r} counted as DURABLE identity support, which lifts the "
        "perishable-only confirmation cap as well. A class is not support of any durability."
    )


def test_the_capped_pair_is_retained_with_a_reason_that_names_the_ground() -> None:
    """Refuse AND escalate: the withheld pair keeps a readable record of why (the non-negotiable's 2nd half).

    A cap may withhold *attention* (ceiling ``possible`` ⇒ the watch-list rather than the queue); it may not
    withhold the *record*. A pair that is neither fused nor retained-with-a-reason is indistinguishable from
    one the resolver never scored.
    """
    etype, attr, value = TAXONOMIC
    part = rc.part_of(_pair(etype, "Type Nine", {attr: value}, {attr: value}), rc.bundle())

    assert rc.status(part, "a", "b") in ("probable", "possible"), (
        f"the capped pair reads {rc.status(part, 'a', 'b')!r} — a refused merge that is also dropped from "
        "every list destroys the finding along with the merge."
    )
    reason = rc.visible_rationale(part, "a", "b").lower()
    assert "name" in reason, (
        f"the surfaced reason does not name the ground that actually caused the refusal (a name-only "
        f"identity). reason={reason!r}"
    )


# ── 2. …and the identity-bearing one still does ──────────────────────────────────────────────────

def test_an_agreeing_identity_bearing_attribute_still_lifts_the_cap() -> None:
    """The permissive half of D-13.10 survives: "ONE more trivially-available signal clears it".

    Without this the fix would be a ban wearing a cap's clothes, and the design layer could never collapse —
    spine/13 §6 lever 2 has no rung left to stand on.
    """
    etype, attr, value = IDENTITY_BEARING
    part = rc.part_of(_pair(etype, "Type Nine", {attr: value}, {attr: value}), rc.bundle())

    assert rc.fused(part, "a", "b"), (
        f"a design pair agreeing on the individuating attribute {attr!r} did not fuse. The taxonomic "
        f"exclusion must remove the CLASS labels only — a cap that nothing can clear is a ban. "
        f"signals={rc.signals(part, 'a', 'b')}"
    )


# ── 3. every negative consequence is intact ─────────────────────────────────────────────────────

def test_a_stated_difference_on_a_critical_taxonomic_attribute_still_walls() -> None:
    """``unit.service_branch`` is critical AND taxonomic: agreement buys nothing, disagreement still walls.

    The two halves are independent, and conflating them is how a fix in one direction quietly disarms the
    other. A cross-service fusion is the costliest over-merge in an operator-scoped ORBAT.
    """
    cfg = _cfg()
    critical = [a for a in cfg.critical_role_attrs("unit") if cfg.attribute_is_taxonomic("unit", a)]
    assert critical, (
        "no unit attribute is declared both critical and taxonomic, so this property cannot be exercised — "
        f"critical={cfg.critical_role_attrs('unit')}"
    )
    attr = critical[0]
    part = rc.part_of(
        _pair("unit", "Ninth Air Defence Brigade", {attr: "PAF"}, {attr: "Pakistan Army"}),
        rc.bundle(),
    )

    assert not rc.fused(part, "a", "b"), (
        f"two units stating DIFFERENT {attr!r} values fused. Marking the attribute taxonomic removes its "
        "agreement from the positive signals; it must not disarm the wall."
    )
    assert rc.walled(part, "a", "b") or rc.status(part, "a", "b") in ("probable", "possible"), (
        f"a stated critical-attribute contradiction on {attr!r} left no wall and no queued/retained record."
    )


def test_the_taxonomic_flag_is_declared_on_a_class_attribute_and_read_everywhere() -> None:
    """Discovery, not a hand-copied list: whatever the shipped config marks taxonomic must be excluded.

    Guards the drift this codebase keeps finding — a validated declaration that one reader honours and
    another ignores. Both positive-signal readers are exercised for every declared row.
    """
    cfg = _cfg()
    types = sorted({etype for etype, _attr, _spec in rc.attribute_role_entries()})
    flat = sorted({(etype, attr) for etype in types for attr in cfg.taxonomic_attrs(etype)})
    assert flat, "no attribute in the shipped config is declared taxonomic — the axis is inert"

    for etype, attr in flat:
        ea, eb = _entities(etype, "Same Name", {attr: "X"})
        _name, discriminator = attribute_signals(ea, eb, cfg)
        assert discriminator == 0.0, (
            f"{etype}.{attr} is declared taxonomic yet a co-stated value scored discriminator="
            f"{discriminator}. A declaration one reader honours and another ignores is worse than no "
            "declaration: the config states a decision the code did not take."
        )
        assert not has_durable_identity_support(ea, eb, cfg), (
            f"{etype}.{attr} is declared taxonomic yet its agreement counted as durable identity support."
        )
        if attr in cfg.critical_role_attrs(etype):
            assert cfg.attribute_roles(etype)[attr].get("role") == ROLE_CRITICAL, (
                f"{etype}.{attr} lost its critical role while being marked taxonomic — the wall must survive."
            )


# ── helper ──────────────────────────────────────────────────────────────────────────────────────

def _entities(etype: str, name: str, attrs: dict):
    """Two same-typed, same-named entities stating the same attributes — the scorer's own input type."""
    return (
        Entity(eid="a", etype=etype, name=name, attrs=dict(attrs)),
        Entity(eid="b", etype=etype, name=name, attrs=dict(attrs)),
    )


@pytest.fixture(autouse=True)
def _no_clock_dependence() -> None:
    """These properties are pure functions of (claims, config) — nothing here reads a clock."""
    return None
