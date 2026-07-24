"""Stage 3B-ii — TIME-AWARE attribute conflict (``resolve/scoring.attribute_is_conflict``).

Written **purely against the published contract**, blind to the implementation: ``resolve/scoring.py`` is
NOT read (only ``attribute_is_conflict`` / ``attribute_score`` are imported from it). These tests assert
what *correct* behaviour IS, not what any observed output happens to be.

Contract under test::

    attribute_is_conflict(a: Entity, b: Entity, attr: str, cfg) -> bool

returns True **iff** ``a`` and ``b`` BOTH state ``attr`` with DIFFERENT values, EXCEPT it returns False
when the attribute is perishable (``cfg.attribute_perishable(type, attr) is True``) AND the two sides'
combined series (``a.attr_history[attr] + b.attr_history[attr]``) classifies as an ``ordered`` succession
(a clean update over time). Absence on a side → False. Same value → False.

Higher-level behaviour this feeds: a perishable ORDERED-succession disagreement must NOT trigger the
critical wall NOR the soft attribute penalty; a ``contradiction`` / ``unorderable`` / non-perishable
disagreement still does.

Case map (each maps to a numbered contract bullet):

1. perishable, different values at distinct times (ordered)     → ``test_perishable_ordered_update_is_not_a_conflict``
2. perishable, different values at the same/overlapping time     → ``test_perishable_contradiction_is_a_conflict``
3. perishable, different values, one side undated (unorderable)  → ``test_perishable_unorderable_is_a_conflict``
4. NON-perishable, different values at different times           → ``test_non_perishable_ordered_is_still_a_conflict``
5. one side absent / same value on both                          → ``test_absence_is_not_a_conflict`` /
                                                                    ``test_same_value_is_not_a_conflict``
6. integration: critical perishable ordered does not wall, contradiction does
                                                                 → ``test_critical_perishable_ordered_does_not_wall``
7. integration: supporting perishable ordered incurs no penalty, contradiction does
                                                                 → ``test_supporting_perishable_ordered_incurs_no_penalty``

Corpus-independent; real ``AttrClaim`` + real date value types; deterministic (fixed dates, no clock/RNG).
"""

from __future__ import annotations

from chanakya.resolve import resolve
from chanakya.resolve.entities import AttrClaim, Entity
from chanakya.resolve.rconfig import ResolveConfig
from chanakya.resolve.scoring import attribute_is_conflict, attribute_score
from chanakya.resolve.succession import classify_succession
from chanakya.schemas import (
    ClaimRecord,
    DocRef,
    EntityDescriptor,
    ExactDate,
    ResolvedRef,
)
from tests.resolve._helpers import mk_config

ATTR = "config"  # deliberately NOT a namespace field (namespace() reads country/*_branch/domain), so any
# wall we observe is the role veto and not the older namespace/blocking behaviour.

# Perishable declarations. The role value is incidental to ``attribute_is_conflict`` itself (it is
# role-agnostic — the role only decides wall-vs-penalty at the higher level); ``perishable`` is the flag
# the time-aware exception reads.
PERISHABLE_CRITICAL = {"gadget": {ATTR: {"role": "critical", "perishable": True}}}
PERISHABLE_SUPPORTING = {"gadget": {ATTR: {"role": "supporting", "perishable": True}}}
NONPERISHABLE_CRITICAL = {"gadget": {ATTR: {"role": "critical", "perishable": False}}}
UNDECLARED_PERISHABLE = {"gadget": {ATTR: {"role": "critical"}}}  # role set, perishable omitted ⇒ None


# ── builders (real value types; no parsing / clock / RNG) ───────────────────────────────────────


def _exact(iso: str) -> ExactDate:
    return ExactDate(iso_date=iso)


def _ac(value: object, cid: str, event: object | None = None) -> AttrClaim:
    return AttrClaim(value=value, claim_id=cid, event_time=event)


def _ent(eid: str, series: list[AttrClaim], *, name: str = "Widget") -> Entity:
    """A gadget stating ``ATTR`` via an ``AttrClaim`` series.

    ``attrs[ATTR]`` (the first-claim-wins scalar every resolve reader depends on) mirrors the first
    entry's value, and ``attr_history[ATTR]`` carries the full time-ordered series the succession core
    consumes. An empty series ⇒ the attribute is absent (states nothing).
    """
    attrs = {ATTR: series[0].value} if series else {}
    hist = {ATTR: list(series)} if series else {}
    return Entity(eid=eid, etype="gadget", name=name, attrs=attrs, attr_history=hist)


def _cfg(roles: dict | None) -> ResolveConfig:
    return ResolveConfig.from_bundle(
        mk_config(attribute_roles=roles) if roles is not None else mk_config()
    )


def _combined_status(a: Entity, b: Entity) -> str:
    """The succession status of the two sides' combined series — the shape the exception keys on."""
    return classify_succession(a.attr_history.get(ATTR, []) + b.attr_history.get(ATTR, [])).status


# ── direct unit tests of ``attribute_is_conflict`` ───────────────────────────────────────────────


def test_perishable_ordered_update_is_not_a_conflict() -> None:
    """(1) Perishable attr, DIFFERENT values at DISTINCT disjoint times ⇒ ordered succession ⇒ NOT a conflict.

    A value that changed cleanly over time is an *update*, not a disagreement — the whole point of the
    perishable exception.
    """
    cfg = _cfg(PERISHABLE_CRITICAL)
    a = _ent("a", [_ac("cfg-A", "c1", event=_exact("2019-01-01"))])
    b = _ent("b", [_ac("cfg-B", "c2", event=_exact("2023-01-01"))])
    assert _combined_status(a, b) == "ordered"  # fixture precondition: a clean succession
    assert not attribute_is_conflict(a, b, ATTR, cfg)


def test_perishable_contradiction_is_a_conflict() -> None:
    """(2) Perishable attr, DIFFERENT values at the SAME/overlapping time ⇒ contradiction ⇒ a conflict.

    Two different values true simultaneously cannot be an update; the perishable exception does not fire.
    """
    cfg = _cfg(PERISHABLE_CRITICAL)
    a = _ent("a", [_ac("cfg-A", "c1", event=_exact("2022-06-01"))])
    b = _ent("b", [_ac("cfg-B", "c2", event=_exact("2022-06-01"))])  # same date
    assert _combined_status(a, b) == "contradiction"  # fixture precondition
    assert attribute_is_conflict(a, b, ATTR, cfg)


def test_perishable_unorderable_is_a_conflict() -> None:
    """(3) Perishable attr, DIFFERENT values but one side UNDATED ⇒ unorderable ⇒ a conflict.

    A value that cannot be placed on the timeline can't be shown to be a clean update, so it is NOT
    excused: only ``ordered`` is.
    """
    cfg = _cfg(PERISHABLE_CRITICAL)
    a = _ent("a", [_ac("cfg-A", "c1", event=_exact("2019-01-01"))])
    b = _ent("b", [_ac("cfg-B", "c2")])  # no usable date
    assert _combined_status(a, b) == "unorderable"  # fixture precondition
    assert attribute_is_conflict(a, b, ATTR, cfg)


def test_non_perishable_ordered_is_still_a_conflict() -> None:
    """(4) NON-perishable attr, DIFFERENT values at DISTINCT times ⇒ STILL a conflict — time does not excuse it.

    Identical fixture to case (1) (a clean ordered succession); the ONLY difference is the perishable flag,
    which is what flips the verdict. Covered for ``perishable: False``, a role without ``perishable``
    (⇒ None), and no ``attribute_roles`` block at all (⇒ None).
    """
    a = _ent("a", [_ac("cfg-A", "c1", event=_exact("2019-01-01"))])
    b = _ent("b", [_ac("cfg-B", "c2", event=_exact("2023-01-01"))])
    assert _combined_status(a, b) == "ordered"  # same clean succession as case (1)

    for cfg in (_cfg(NONPERISHABLE_CRITICAL), _cfg(UNDECLARED_PERISHABLE), _cfg(None)):
        assert attribute_is_conflict(a, b, ATTR, cfg)


def test_absence_is_not_a_conflict() -> None:
    """(5a) One side does not state the attribute ⇒ unknown, not different ⇒ NOT a conflict (symmetric)."""
    cfg = _cfg(PERISHABLE_CRITICAL)
    stated = _ent("a", [_ac("cfg-A", "c1", event=_exact("2019-01-01"))])
    silent = Entity(eid="b", etype="gadget", name="Widget")  # states no ``config`` at all
    assert not attribute_is_conflict(stated, silent, ATTR, cfg)
    assert not attribute_is_conflict(silent, stated, ATTR, cfg)  # order-independent


def test_same_value_is_not_a_conflict() -> None:
    """(5b) BOTH sides state the SAME value ⇒ NOT a conflict, regardless of perishability or timing."""
    a = _ent("a", [_ac("cfg-A", "c1", event=_exact("2019-01-01"))])
    b = _ent("b", [_ac("cfg-A", "c2", event=_exact("2023-01-01"))])  # same value, different times
    assert _combined_status(a, b) == "single"  # one distinct value ⇒ settled, not a succession
    for cfg in (_cfg(PERISHABLE_CRITICAL), _cfg(NONPERISHABLE_CRITICAL), _cfg(None)):
        assert not attribute_is_conflict(a, b, ATTR, cfg)


# ── integration via ``resolve(...)`` — the wall and the soft penalty ─────────────────────────────


def _same_as(part) -> set[frozenset[str]]:
    return {frozenset(p) for p in part.same_as}


def _drawn_vetoes(part) -> set[frozenset[str]]:
    return {frozenset(p) for p in part.distinct_from}


def _entity_claim(eid: str, event_iso: str, *, name: str = "Widget", **attrs: object) -> ClaimRecord:
    """An entity-form claim carrying an ``event_time`` (the ``entity()`` helper omits it), so ``build()``
    stamps the attribute's ``AttrClaim`` with a real date and the succession core can place it in time."""
    return ClaimRecord(
        claim_id=f"clm-{eid}",
        source_id="src-t",
        doc_ref=DocRef(file="d.txt", span=(0, 1)),
        kind="observation",
        asserts="entity",
        payload=EntityDescriptor(entity_type="gadget", name=name, attrs=attrs),
        event_time=_exact(event_iso),
        resolved_ref=ResolvedRef(entity_id=eid),
    )


def test_critical_perishable_ordered_does_not_wall() -> None:
    """(6) A CRITICAL perishable attr: an ordered succession does NOT wall (the pair merges); a
    contradiction on the same attr DOES wall.

    Two same-name gadgets that would merge on name alone, distinguished only by the temporal shape of
    their differing ``config`` value. The ordered update is a benign state change ⇒ no wall ⇒ merge; the
    simultaneous disagreement is a genuine critical conflict ⇒ walled (drawn, never fused).
    """
    cfg = mk_config(attribute_roles=PERISHABLE_CRITICAL)
    pair = frozenset({"g_a", "g_b"})

    ordered = resolve(
        [
            _entity_claim("g_a", "2019-01-01", config="cfg-A"),
            _entity_claim("g_b", "2023-01-01", config="cfg-B"),
        ],
        cfg,
    )
    assert pair not in _drawn_vetoes(ordered)  # a clean update is not a wall
    assert pair in _same_as(ordered)           # ...it is a benign succession ⇒ the pair merges

    contradiction = resolve(
        [
            _entity_claim("g_a", "2022-06-01", config="cfg-A"),
            _entity_claim("g_b", "2022-06-01", config="cfg-B"),  # same date ⇒ contradiction
        ],
        cfg,
    )
    assert pair in _drawn_vetoes(contradiction)     # a real critical conflict still walls
    assert pair not in _same_as(contradiction)


def test_supporting_perishable_ordered_incurs_no_penalty() -> None:
    """(7) A SUPPORTING perishable attr: an ordered succession incurs NO soft penalty; a contradiction
    lowers the score.

    Mirrors ``test_supporting_conflict_lowers_score``'s baseline pattern: ``cfg_off`` (no roles) is the
    un-penalised reference. The ordered-succession score must equal it (the update is not counted as
    negative evidence), while the contradiction score must fall below it.
    """
    cfg = ResolveConfig.from_bundle(
        mk_config(attribute_roles=PERISHABLE_SUPPORTING, attribute_scoring={"conflict_penalty": 0.5})
    )
    cfg_off = ResolveConfig.from_bundle(mk_config(attribute_scoring={"conflict_penalty": 0.5}))

    ordered_a = _ent("a", [_ac("cfg-A", "ca", event=_exact("2019-01-01"))])
    ordered_b = _ent("b", [_ac("cfg-B", "cb", event=_exact("2023-01-01"))])
    contra_a = _ent("a", [_ac("cfg-A", "ca", event=_exact("2022-06-01"))])
    contra_b = _ent("b", [_ac("cfg-B", "cb", event=_exact("2022-06-01"))])
    assert _combined_status(ordered_a, ordered_b) == "ordered"        # fixture preconditions
    assert _combined_status(contra_a, contra_b) == "contradiction"

    baseline = attribute_score(ordered_a, ordered_b, cfg_off)        # attr not a role ⇒ no effect
    s_ordered = attribute_score(ordered_a, ordered_b, cfg)           # supporting + perishable, ordered
    s_contra = attribute_score(contra_a, contra_b, cfg)              # supporting + perishable, contradiction

    assert s_ordered == baseline    # the ordered update incurs NO soft penalty
    assert s_contra < baseline      # the contradiction lowers the score
    assert s_contra < s_ordered     # ...and the only difference is the temporal shape
