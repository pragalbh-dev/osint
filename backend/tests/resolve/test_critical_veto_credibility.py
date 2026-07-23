"""Stage 3A-i — a SOURCE-CREDIBILITY FLOOR on the declared-critical-attribute veto (D5 take-care a).

The critical-attribute veto (``resolve._critical_attribute_walls``) is a hard wall: two same-type
entities stating different values of a declared-``critical`` attribute cannot be one entity, no score may
cross it. D5 take-care (a) adds the discipline that **one flaky low-grade source must not be able to
shatter a well-corroborated merge**: a critical conflict WALLS only when the conflicting value on
*both* sides is asserted by at least one source graded at/above a configured STANAG floor
(``critical_veto_min_grade``). Below the floor the pair is not walled and not silently merged — it is
**raised to the analyst** as a ``probable`` candidate, with a reason, so a human adjudicates.

These tests pin the MECHANISM on synthetic entities (corpus-independent): the floor is exercised with a
NON-namespace critical attribute (``serial``) so what we observe is the credibility gate on the role
veto, not the older namespace/blocking behaviour. Grades are STANAG letters, A (best) → F (worst); the
floor here is ``C`` so B walls and E raises.
"""

from __future__ import annotations

from chanakya.resolve import resolve
from chanakya.resolve.entities import AttrClaim, Entity
from chanakya.resolve.rconfig import ResolveConfig, grade_meets_floor
from chanakya.resolve.scoring import critical_conflict_disposition
from chanakya.schemas import pair_key
from tests.resolve._helpers import entity, mk_config

CRITICAL = {"gadget": {"serial": {"role": "critical"}}}
FLOOR = "C"


def _same_as(part) -> set[frozenset[str]]:
    return {frozenset(p) for p in part.same_as}


def _candidates(part) -> set[frozenset[str]]:
    return {frozenset(p) for p in part.candidates}


def _drawn_vetoes(part) -> set[frozenset[str]]:
    return {frozenset(p) for p in part.distinct_from}


# ── (a) a CREDIBLE critical conflict (both sides at/above floor) still WALLS ────────────────────

def test_credible_high_grade_conflict_walls() -> None:
    """Two same-name gadgets stating different serials, each value from a grade-B (>= floor C) source.

    The conflict is trustworthy on both sides, so the wall stands exactly as before the floor: never
    fused, never a candidate (a hard wall is not an open question), but drawn so the analyst sees it.
    """
    claims = [
        entity("g_a", "gadget", "Widget", source="d_hi_a", serial="SN-1"),
        entity("g_b", "gadget", "Widget", source="d_hi_b", serial="SN-2"),
    ]
    cfg = mk_config(
        attribute_roles=CRITICAL,
        critical_veto_min_grade=FLOOR,
        source_reliability_grades={"d_hi_a": "B", "d_hi_b": "B"},
    )
    part = resolve(claims, cfg)
    assert frozenset({"g_a", "g_b"}) not in _same_as(part)
    assert frozenset({"g_a", "g_b"}) not in _candidates(part)
    assert frozenset({"g_a", "g_b"}) in _drawn_vetoes(part)
    assert pair_key("g_a", "g_b") not in part.candidate_reasons


# ── (b) a BELOW-FLOOR critical conflict RAISES to HITL — not walled, not merged ─────────────────

def test_below_floor_conflict_raises_to_hitl_instead_of_walling() -> None:
    """The same conflict, but each conflicting value comes only from a grade-E (< floor C) source.

    One flaky low-grade source must not shatter the merge: the pair is NOT walled (absent from the
    drawn do-not-merge set) and NOT silently merged — it is a ``probable`` HITL candidate carrying a
    reason that names the offending critical attribute, so a human adjudicates.
    """
    claims = [
        entity("g_a", "gadget", "Widget", source="d_lo_a", serial="SN-1"),
        entity("g_b", "gadget", "Widget", source="d_lo_b", serial="SN-2"),
    ]
    cfg = mk_config(
        attribute_roles=CRITICAL,
        critical_veto_min_grade=FLOOR,
        source_reliability_grades={"d_lo_a": "E", "d_lo_b": "E"},
    )
    part = resolve(claims, cfg)
    pair = frozenset({"g_a", "g_b"})
    assert pair not in _same_as(part)          # never silently allowed
    assert pair not in _drawn_vetoes(part)     # never silently shattered
    assert pair in _candidates(part)           # raised to the analyst
    assert part.identity_status("g_a", "g_b") == "probable"
    reason = part.candidate_reasons.get(pair_key("g_a", "g_b"))
    assert reason and "serial" in reason


def test_one_side_below_floor_still_raises() -> None:
    """"Each side" is load-bearing: high-grade on one side, low-grade-only on the other ⇒ still raise.

    The difference is only trustworthy if BOTH values are credibly attested; a well-graded value facing
    a flaky one is exactly the case the analyst should adjudicate, not a wall.
    """
    claims = [
        entity("g_a", "gadget", "Widget", source="d_hi", serial="SN-1"),
        entity("g_b", "gadget", "Widget", source="d_lo", serial="SN-2"),
    ]
    cfg = mk_config(
        attribute_roles=CRITICAL,
        critical_veto_min_grade=FLOOR,
        source_reliability_grades={"d_hi": "B", "d_lo": "E"},
    )
    part = resolve(claims, cfg)
    pair = frozenset({"g_a", "g_b"})
    assert pair not in _drawn_vetoes(part)
    assert pair in _candidates(part)


# ── (c) a below-floor conflict is never AUTO-merged (the "silently allowed" guard) ──────────────

def test_below_floor_conflict_never_auto_merges_even_at_alias_score_1() -> None:
    """Alias-equivalent names would bootstrap a confidence-1.0 merge; the raised pair must not merge.

    A wall was refused (below the floor), but the pair still disagrees on a critical attribute — so it
    may not slip through to an auto/bootstrap merge either. It is forced to the analyst queue.
    """
    claims = [
        entity("g_a", "gadget", "Widget Alpha", source="d_lo_a", serial="SN-1"),
        entity("g_b", "gadget", "Widget Beta", source="d_lo_b", serial="SN-2"),
    ]
    cfg = mk_config(
        attribute_roles=CRITICAL,
        critical_veto_min_grade=FLOOR,
        alias_table={"Widget Alpha": ["Widget Beta"]},  # forces name score 1.0 → would bootstrap-merge
        source_reliability_grades={"d_lo_a": "E", "d_lo_b": "E"},
    )
    part = resolve(claims, cfg)
    pair = frozenset({"g_a", "g_b"})
    assert pair not in _same_as(part)      # the alias bootstrap is blocked
    assert pair in _candidates(part)       # ...and surfaced, not dropped


# ── (d) absence is never a conflict (no wall, no raise) ─────────────────────────────────────────

def test_absence_never_walls_or_raises() -> None:
    """One silent side is unknown, not different — the pair simply merges, no reason recorded."""
    claims = [
        entity("g_a", "gadget", "Widget", source="d_lo_a", serial="SN-1"),
        entity("g_b", "gadget", "Widget", source="d_lo_b"),  # states no serial
    ]
    cfg = mk_config(
        attribute_roles=CRITICAL,
        critical_veto_min_grade=FLOOR,
        source_reliability_grades={"d_lo_a": "E", "d_lo_b": "E"},
    )
    part = resolve(claims, cfg)
    pair = frozenset({"g_a", "g_b"})
    assert pair in _same_as(part)
    assert pair not in _candidates(part)
    assert pair not in _drawn_vetoes(part)
    assert pair_key("g_a", "g_b") not in part.candidate_reasons


# ── (e) floor OFF ⇒ the veto is unconditional (pre-Stage-3A behaviour, byte-unchanged) ──────────

def test_floor_off_walls_unconditionally() -> None:
    """With no ``critical_veto_min_grade`` configured, even a grade-E conflict walls, as before 3A."""
    claims = [
        entity("g_a", "gadget", "Widget", source="d_lo_a", serial="SN-1"),
        entity("g_b", "gadget", "Widget", source="d_lo_b", serial="SN-2"),
    ]
    cfg = mk_config(  # NB: no critical_veto_min_grade
        attribute_roles=CRITICAL,
        source_reliability_grades={"d_lo_a": "E", "d_lo_b": "E"},
    )
    part = resolve(claims, cfg)
    pair = frozenset({"g_a", "g_b"})
    assert pair in _drawn_vetoes(part)
    assert pair not in _candidates(part)


# ── unit-level: the config gate + the ordinal grade comparison ──────────────────────────────────

def test_grade_meets_floor_is_stanag_ordinal() -> None:
    assert grade_meets_floor("A", "C")      # A is more reliable than the floor
    assert grade_meets_floor("C", "C")      # at the floor
    assert not grade_meets_floor("D", "C")  # below the floor
    assert not grade_meets_floor("E", "C")
    assert not grade_meets_floor(None, "C")       # unknown grade fails closed
    assert not grade_meets_floor("Z", "C")        # not a STANAG letter fails closed


def test_source_meets_floor_reads_the_registry_grade() -> None:
    cfg = ResolveConfig.from_bundle(mk_config(
        critical_veto_min_grade=FLOOR,
        source_reliability_grades={"d_b": "B", "d_c": "C", "d_e": "E"},
    ))
    assert cfg.critical_veto_min_grade == "C"
    assert cfg.source_grade("d_b") == "B"
    assert cfg.source_meets_critical_veto_floor("d_b")
    assert cfg.source_meets_critical_veto_floor("d_c")
    assert not cfg.source_meets_critical_veto_floor("d_e")
    assert not cfg.source_meets_critical_veto_floor("unregistered")  # unknown source fails closed


def test_source_meets_floor_when_floor_off_is_always_true() -> None:
    """Floor unset ⇒ every source clears it ⇒ the veto is unconditional (byte-unchanged)."""
    cfg = ResolveConfig.from_bundle(mk_config(source_reliability_grades={"d_e": "E"}))
    assert cfg.critical_veto_min_grade is None
    assert cfg.source_meets_critical_veto_floor("d_e")
    assert cfg.source_meets_critical_veto_floor(None)


# ── unit-level: the disposition classifier (none / wall / raise) ────────────────────────────────

def _cfg() -> ResolveConfig:
    return ResolveConfig.from_bundle(mk_config(
        attribute_roles=CRITICAL,
        critical_veto_min_grade=FLOOR,
        source_reliability_grades={"d_b": "B", "d_e": "E"},
    ))


def _ent(eid: str, serial: str | None, grade_source: str | None) -> Entity:
    """A gadget stating ``serial``, whose value is attested by ``grade_source`` (None ⇒ no source-attribution)."""
    attrs = {"serial": serial} if serial is not None else {}
    history = {}
    if serial is not None and grade_source is not None:
        history = {"serial": [AttrClaim(value=serial, claim_id=f"c-{eid}", source_id=grade_source)]}
    return Entity(eid=eid, etype="gadget", name="Widget", attrs=attrs, attr_history=history)


def test_disposition_none_when_no_stated_conflict() -> None:
    cfg = _cfg()
    disp, attrs = critical_conflict_disposition(_ent("a", "SN-1", "d_b"), _ent("b", None, None), cfg)
    assert disp == "none" and attrs == ()


def test_disposition_wall_when_credible_on_both_sides() -> None:
    cfg = _cfg()
    disp, attrs = critical_conflict_disposition(_ent("a", "SN-1", "d_b"), _ent("b", "SN-2", "d_b"), cfg)
    assert disp == "wall" and "serial" in attrs


def test_disposition_raise_when_below_floor() -> None:
    cfg = _cfg()
    disp, attrs = critical_conflict_disposition(_ent("a", "SN-1", "d_e"), _ent("b", "SN-2", "d_e"), cfg)
    assert disp == "raise" and "serial" in attrs


def test_disposition_curated_value_with_no_source_is_credible() -> None:
    """A critical value with no source-attributed claim (a curated/registry seed) is not a flaky source.

    Such a value counts as credible, so a conflict against a high-grade side WALLS; but against a
    low-grade-only side it still RAISES (that side is the flaky one).
    """
    cfg = _cfg()
    curated = _ent("a", "SN-1", None)          # attrs set, no attr_history entry ⇒ no source
    high = _ent("b", "SN-2", "d_b")
    low = _ent("c", "SN-2", "d_e")
    assert critical_conflict_disposition(curated, high, cfg)[0] == "wall"
    assert critical_conflict_disposition(curated, low, cfg)[0] == "raise"
