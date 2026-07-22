"""Per-type auto-merge floor (P3.5) — the mechanism, pinned on hand-built graphs.

The global ``auto_merge`` sits at the deterministic score ceiling so the fuzzy fixpoint never auto-merges
(precision floor). ``auto_merge_by_type`` lowers that floor for types where a near-identical name reliably
denotes ONE entity (organisations / trading-orgs), leaving every identity-sensitive type at the strict
global bar. These tests pin the mechanism; ``tests/acceptance/test_per_type_automerge_corpus.py`` pins the
outcome on the frozen corpus.
"""

from __future__ import annotations

from chanakya.resolve import resolve
from chanakya.resolve.rconfig import ResolveConfig
from tests.resolve._helpers import entity, mk_config


def _cluster_of(part, eid: str) -> set[str]:
    members = {eid}
    for a, b in part.same_as:
        if a in members or b in members:
            members |= {a, b}
    return members


# ── the accessor: floor is per-type only when BOTH sides share a listed type ─────────────────────

def test_auto_merge_for_pair_applies_only_to_listed_same_type_pairs() -> None:
    cfg = ResolveConfig.from_bundle(mk_config(auto_merge_by_type={"manufacturer": 0.37}))
    # both sides the listed type → the lowered floor
    assert cfg.auto_merge_for_pair("manufacturer", "manufacturer") == 0.37
    # unlisted type → the strict global default
    assert cfg.auto_merge_for_pair("variant", "variant") == cfg.auto_merge
    assert cfg.auto_merge_for_pair("unit", "unit") == cfg.auto_merge
    # cross-type is never a spelling variant → the strict global default even if one side is listed
    assert cfg.auto_merge_for_pair("manufacturer", "variant") == cfg.auto_merge


def test_absent_map_is_the_global_floor_for_every_type() -> None:
    """G2: with no ``auto_merge_by_type`` the accessor returns the global floor everywhere (byte-unchanged)."""
    cfg = ResolveConfig.from_bundle(mk_config())
    for a, b in (("manufacturer", "manufacturer"), ("variant", "variant"), ("unit", "unit")):
        assert cfg.auto_merge_for_pair(a, b) == cfg.auto_merge


# ── end-to-end: the floor activates a listed type without touching the rest ─────────────────────

# Two spelling variants of one organisation: high name similarity, one distinguishing token each side
# (so neither is a subset of the other → no containment/exact-name bootstrap; the SCORE decides), and no
# shared neighbours (relational == 0). Deterministic subtotal ≈ 0.40·attr + 0.05 ≈ 0.40 — above the 0.37
# manufacturer floor, below the 0.85 global bar and even below hitl_low, i.e. "separate" without the floor.
_ORG_A = "Zenith Precision Machinery Import Export Corporation North"
_ORG_B = "Zenith Precision Machinery Import Export Corporation South"


def test_listed_type_auto_merges_a_spelling_variant() -> None:
    cfg = mk_config(auto_merge_by_type={"manufacturer": 0.37})
    part = resolve([entity("m_a", "manufacturer", _ORG_A), entity("m_b", "manufacturer", _ORG_B)], cfg)
    assert {"m_a", "m_b"} <= _cluster_of(part, "m_a"), "the manufacturer spelling variant did not auto-merge"


def test_same_pair_does_not_merge_without_the_floor() -> None:
    """G2: identical inputs, no per-type map → the pair stays split (reaches the analyst at most, never auto)."""
    cfg = mk_config()  # no auto_merge_by_type
    part = resolve([entity("m_a", "manufacturer", _ORG_A), entity("m_b", "manufacturer", _ORG_B)], cfg)
    assert part.same_as == [], "the fuzzy pair auto-merged with no per-type floor configured"


def test_floor_is_scoped_to_its_type_a_variant_pair_is_untouched() -> None:
    """The SAME names under an identity-sensitive type keep the strict 0.85 bar — no auto-merge."""
    cfg = mk_config(auto_merge_by_type={"manufacturer": 0.37})
    part = resolve([entity("v_a", "variant", _ORG_A), entity("v_b", "variant", _ORG_B)], cfg)
    assert part.same_as == [], "a variant pair auto-merged under the manufacturer floor — the floor leaked across types"


def test_a_same_type_trap_below_the_floor_stays_split() -> None:
    """Two genuinely different orgs whose names are only loosely similar score below the floor → not merged.

    'Acme …' vs 'Zenith …' share only the generic descriptor tokens, so the name signal is low and the
    deterministic subtotal falls below 0.37 even for the listed type — the floor admits spelling variants,
    not any two same-type entities.
    """
    cfg = mk_config(auto_merge_by_type={"manufacturer": 0.37})
    part = resolve(
        [entity("m_x", "manufacturer", "Acme Rocket Motors Institute"),
         entity("m_y", "manufacturer", "Zenith Radar Systems Bureau")],
        cfg,
    )
    assert part.same_as == [], "an unrelated same-type pair merged — the floor is too low / not name-gated"
