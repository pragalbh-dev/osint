"""Stage 1A — per-type attribute ROLES (D5/D6): critical / supporting / neutral.

Every attribute is declared, per entity type, into one of three roles:

* **critical** — a *stated* disagreement is a hard **veto** (a cannot-link no similarity score may
  cross), enforced before scoring and transitively — the D5 wall generalised from the geographic and
  identifier walls to any declared-critical attribute;
* **supporting** — agreement raises the score, a *stated* disagreement is a **soft** penalty, never a
  wall;
* **neutral** (and any undeclared attribute) — **no identity effect** at all.

Absence is never disagreement (a silent side is *unknown*, not *different*), mirroring the existing
``has_hard_conflict`` / geo doctrine. These tests pin the MECHANISM, not the shipped taxonomy, so they
stay valid as the authored ``config/resolution.yaml`` roles grow.
"""

from __future__ import annotations

from chanakya.resolve import resolve
from chanakya.resolve.entities import Entity
from chanakya.resolve.rconfig import ResolveConfig
from chanakya.resolve.scoring import attribute_score, critical_attribute_conflict, has_hard_conflict
from tests.resolve._helpers import entity, mk_config

# A critical unique-identifier attribute that is deliberately NOT a namespace field (namespace() reads
# country/operator_branch/service_branch/domain), so the wall we observe is the ROLE veto and not the
# older namespace/blocking behaviour.
CRITICAL = {"gadget": {"serial": {"role": "critical"}}}


def _same_as(part) -> set[frozenset[str]]:
    return {frozenset(p) for p in part.same_as}


def _candidates(part) -> set[frozenset[str]]:
    return {frozenset(p) for p in part.candidates}


def _drawn_vetoes(part) -> set[frozenset[str]]:
    return {frozenset(p) for p in part.distinct_from}


def _cluster_of(part, eid: str) -> set[str]:
    members = {eid}
    for a, b in part.same_as:
        if a in members or b in members:
            members |= {a, b}
    for k, v in part.entity_canonical.items():
        if k in members or v in members:
            members |= {k, v}
    return members


# ── (a) a critical disagreement never merges — even at a perfect alias/name score — and is transitive ──

def test_critical_conflict_never_merges_even_at_alias_score_1() -> None:
    """Two gadgets the alias table forces to name-score 1.0, but stating DIFFERENT serials ⇒ walled.

    The alias equivalence would otherwise bootstrap an immediate confidence-1.0 merge; the critical
    veto beats it, exactly as a curated ``distinct_from`` beats a perfect name match. The refused pair
    stays DRAWN (like the identifier veto), so the analyst can see the wall rather than a silent gap.
    """
    claims = [
        entity("g_a", "gadget", "Widget Alpha", serial="SN-1"),
        entity("g_b", "gadget", "Widget Beta", serial="SN-2"),
    ]
    cfg = mk_config(attribute_roles=CRITICAL, alias_table={"Widget Alpha": ["Widget Beta"]})
    part = resolve(claims, cfg)
    assert frozenset({"g_a", "g_b"}) not in _same_as(part)      # never fused
    assert frozenset({"g_a", "g_b"}) not in _candidates(part)   # a hard wall is not an open question
    assert frozenset({"g_a", "g_b"}) in _drawn_vetoes(part)     # ...but it is visible


def test_critical_conflict_is_refused_transitively() -> None:
    """A and C conflict on the critical attr; a bridge B (silent, alias-equivalent to both) cannot fuse them.

    The wall holds A–B–C, not just A–B: B may attach to at most one side. This is the transitivity the
    existing veto machinery already enforces (``violates_veto_transitively``); the role veto rides it.
    """
    claims = [
        entity("g_a", "gadget", "Widget Alpha", serial="SN-1"),
        entity("g_c", "gadget", "Widget Gamma", serial="SN-2"),
        entity("g_b", "gadget", "Widget Bravo"),  # the bridge — states no serial
    ]
    cfg = mk_config(
        attribute_roles=CRITICAL,
        alias_table={"Widget Alpha": ["Widget Bravo", "Widget Gamma"]},  # one name-class
    )
    part = resolve(claims, cfg)
    assert "g_c" not in _cluster_of(part, "g_a")
    assert "g_a" not in _cluster_of(part, "g_c")


def test_has_hard_conflict_reuses_the_critical_detection() -> None:
    """The critical role feeds the shared ``has_hard_conflict`` detector too (absence exempt)."""
    cfg = ResolveConfig.from_bundle(mk_config(attribute_roles=CRITICAL))
    a = Entity(eid="a", etype="gadget", name="W", attrs={"serial": "SN-1"})
    b = Entity(eid="b", etype="gadget", name="W", attrs={"serial": "SN-2"})
    silent = Entity(eid="c", etype="gadget", name="W", attrs={})
    assert has_hard_conflict(a, b, cfg)
    assert not has_hard_conflict(a, silent, cfg)


# ── (b) a supporting disagreement lowers the score (soft), it does not wall ─────────────────────

def test_supporting_conflict_lowers_score_but_does_not_wall() -> None:
    """Soft negative evidence: the score drops but stays positive, and the pair may still merge."""
    cfg_support = ResolveConfig.from_bundle(mk_config(
        attribute_roles={"gadget": {"colour": {"role": "supporting"}}},
        attribute_scoring={"conflict_penalty": 0.5},
    ))
    cfg_off = ResolveConfig.from_bundle(mk_config(attribute_scoring={"conflict_penalty": 0.5}))
    a = Entity(eid="a", etype="gadget", name="Acme Ranger", attrs={"colour": "red"})
    b = Entity(eid="b", etype="gadget", name="Acme Ranger", attrs={"colour": "blue"})
    s_support = attribute_score(a, b, cfg_support)
    s_off = attribute_score(a, b, cfg_off)
    assert 0.0 < s_support < s_off           # lowered, never zeroed
    assert not critical_attribute_conflict(a, b, cfg_support)  # supporting is not a wall

    # ...and at resolve level a supporting disagreement never produces a veto: two identically-named
    # gadgets still merge despite the colour disagreement (bootstrap bypasses the soft penalty).
    part = resolve(
        [entity("a", "gadget", "Acme Ranger", colour="red"),
         entity("b", "gadget", "Acme Ranger", colour="blue")],
        mk_config(attribute_roles={"gadget": {"colour": {"role": "supporting"}}}),
    )
    assert frozenset({"a", "b"}) in _same_as(part)
    assert frozenset({"a", "b"}) not in _drawn_vetoes(part)


# ── (c) a neutral / unlisted disagreement has no identity effect at all ─────────────────────────

def test_neutral_and_unlisted_have_no_identity_effect() -> None:
    """An explicitly-neutral attribute and an undeclared one both leave identity untouched."""
    cfg = ResolveConfig.from_bundle(mk_config(
        attribute_roles={"gadget": {"colour": {"role": "neutral"}}},
        attribute_scoring={"conflict_penalty": 0.5},
    ))
    a = Entity(eid="a", etype="gadget", name="Acme Ranger", attrs={"colour": "red", "finish": "matte"})
    b = Entity(eid="b", etype="gadget", name="Acme Ranger", attrs={"colour": "blue", "finish": "gloss"})
    assert attribute_score(a, b, cfg) == 1.0                # neutral (colour) + unlisted (finish) → no penalty
    assert cfg.critical_role_attrs("gadget") == []
    assert cfg.supporting_role_attrs("gadget") == []
    assert not critical_attribute_conflict(a, b, cfg)

    part = resolve(
        [entity("a", "gadget", "Acme Ranger", colour="red", finish="matte"),
         entity("b", "gadget", "Acme Ranger", colour="blue", finish="gloss")],
        mk_config(attribute_roles={"gadget": {"colour": {"role": "neutral"}}}),
    )
    assert frozenset({"a", "b"}) in _same_as(part)          # a neutral disagreement never walls


# ── (d) absence on one side never vetoes ────────────────────────────────────────────────────────

def test_critical_absence_never_walls() -> None:
    """One silent side is unknown, not different — the contrast a stated conflict is measured against."""
    cfg = ResolveConfig.from_bundle(mk_config(attribute_roles=CRITICAL))
    stated = Entity(eid="a", etype="gadget", name="Widget", attrs={"serial": "SN-1"})
    silent = Entity(eid="b", etype="gadget", name="Widget", attrs={})
    other = Entity(eid="c", etype="gadget", name="Widget", attrs={"serial": "SN-2"})
    assert not critical_attribute_conflict(stated, silent, cfg)   # absence ≠ conflict
    assert critical_attribute_conflict(stated, other, cfg)        # both stated + different ⇒ conflict

    part = resolve(
        [entity("a", "gadget", "Widget", serial="SN-1"),
         entity("b", "gadget", "Widget"),               # silent
         entity("c", "gadget", "Widget", serial="SN-2")],
        mk_config(attribute_roles=CRITICAL),
    )
    assert frozenset({"a", "b"}) in _same_as(part)               # the silent pair still merges
    assert "c" not in _cluster_of(part, "a")                     # the stated conflict walls
    assert frozenset({"a", "c"}) in _drawn_vetoes(part)


# ── (e) the reader + compiler + the (behaviourless) perishable schema ───────────────────────────

def test_reader_compiles_roles_and_reads_perishable_schema() -> None:
    cfg = ResolveConfig.from_bundle(mk_config(attribute_roles={
        "gadget": {
            "serial": {"role": "critical"},
            "country": {"role": "critical"},
            "colour": {"role": "supporting", "perishable": False},
            "status": {"role": "supporting", "perishable": True},
            "nickname": {"role": "neutral"},
        }
    }))
    assert cfg.critical_role_attrs("gadget") == ["country", "serial"]   # sorted, criticals only
    assert cfg.supporting_role_attrs("gadget") == ["colour", "status"]  # sorted, supporting only
    both = cfg.critical_role_attrs("gadget") + cfg.supporting_role_attrs("gadget")
    assert "nickname" not in both                                       # neutral contributes to neither
    # perishable: schema-only in 1A (read, not yet consumed)
    assert cfg.attribute_perishable("gadget", "status") is True
    assert cfg.attribute_perishable("gadget", "colour") is False
    assert cfg.attribute_perishable("gadget", "serial") is None         # perishability undeclared
    assert cfg.attribute_perishable("gadget", "unknown_attr") is None
    # an undeclared type ⇒ no roles (the safe, extendable default)
    assert cfg.critical_role_attrs("other") == []
    assert cfg.supporting_role_attrs("other") == []


def test_unconfigured_is_inert() -> None:
    """No ``attribute_roles`` block ⇒ every attribute is neutral, no wall, no penalty (byte-unchanged)."""
    cfg = ResolveConfig.from_bundle(mk_config())
    assert cfg.attribute_roles("variant") == {}
    assert cfg.critical_role_attrs("variant") == []
    assert cfg.supporting_role_attrs("variant") == []
    a = Entity(eid="a", etype="variant", name="HQ-9", attrs={"operator_branch": "PLA"})
    b = Entity(eid="b", etype="variant", name="HQ-9", attrs={"operator_branch": "PAF"})
    assert not critical_attribute_conflict(a, b, cfg)
