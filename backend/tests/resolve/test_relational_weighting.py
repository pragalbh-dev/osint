"""Stage 3C — status/confidence-weighting of the relational identity signal.

The collective-ER relational term counts the *shared neighbours* of two entities. But a neighbour is
only "shared" once the two sides' neighbour-entities have been unified — and that unification carries a
confidence. Stage 3C weights each shared neighbour by that confidence: a neighbour shared because both
sides point to the SAME raw entity (or to two entities fused by a confidence-1.0 / bootstrap merge)
counts in FULL; a neighbour shared only because two DIFFERENT neighbour-entities were merged at LOW
confidence (a fuzzy per-type-floor merge) counts LESS. Equal weight — a single shared entity and a 1.0
merge being indistinguishable, both full — is the default when nothing was merged at low confidence.

Observable consequence: two entities whose shared-neighbourhood leans on a WEAK neighbour-merge earn a
strictly LOWER relational contribution — hence a lower merge score, and a lower identity band — than an
otherwise-identical pair whose corresponding neighbour is a single entity or a full-confidence merge.

Fixture shape (corpus-independent, deterministic). The SAME unit pair (unit_a / unit_b) is compared in
every scenario. The pair is anchored by ONE **direct** shared neighbour (comp_s — a single entity both
units point to) so the pair is always brought into scoring; on top of that sits ONE **merge-derived**
shared neighbour (unit_a→m_1, unit_b→m_2, with m_1/m_2 unified) whose merge confidence is the ONLY thing
that varies between scenarios:

  * STRONG — m_1/m_2 carry a seeded alias ⇒ a bootstrap merge at confidence 1.0 (full-weight neighbour).
  * WEAK   — m_1/m_2 are near-spelling-variants merged only by a per-type auto-merge FLOOR ⇒ a genuine
             sub-1.0 (fuzzy) merge (a discounted neighbour).
  * SINGLE — both units point to ONE neighbour entity m (no merge at all) ⇒ the full-weight baseline.

(A pair whose ONLY shared neighbour is merge-derived is never brought into comparison, which is why the
direct comp_s anchor is load-bearing here.) Each test pins its preconditions — the neighbours really
merged, at the stated confidence — so a mis-built fixture fails loudly rather than passing vacuously.
Written against the public ``resolve`` / ``Partition`` surface only; the internal scoring signature (which
the implementation owns) is deliberately untouched, and the exact aggregation is never pinned — only the
ordering the contract guarantees.
"""

from __future__ import annotations

from chanakya.resolve import resolve
from chanakya.schemas import pair_key
from tests.resolve._helpers import entity, mk_config, triple

# Two near-identical organisation names: high name overlap, one distinguishing token each side (so
# neither is a subset of the other → no containment/exact bootstrap; the SCORE decides). Seeded as an
# alias they bootstrap-merge at 1.0; under a per-type floor alone they auto-merge at a sub-1.0 score.
_ORG_A = "Zenith Precision Machinery Import Export Corporation North"
_ORG_B = "Zenith Precision Machinery Import Export Corporation South"

_PAIR = frozenset({"unit_a", "unit_b"})
_UKEY = pair_key("unit_a", "unit_b")
_NKEY = pair_key("m_1", "m_2")


def _as_pairs(pairs: list[tuple[str, str]]) -> set[frozenset[str]]:
    return {frozenset(p) for p in pairs}


def _cluster_of(part, eid: str) -> set[str]:
    """All ids fused with ``eid`` (via same_as / entity_canonical)."""
    members = {eid}
    for a, b in part.same_as:
        if a in members or b in members:
            members |= {a, b}
    for k, v in part.entity_canonical.items():
        if k in members or v in members:
            members |= {k, v}
    return members


def _claims() -> list:
    """The two units share ONE direct neighbour (comp_s) and ONE merge-derived neighbour (m_1≡m_2).

    The unit names are single-token and mutually dissimilar ⇒ the attribute signal is ~0; the direct
    comp_s guarantees the pair is scored; the merge-derived neighbour's contribution is entirely a
    function of the confidence of the m_1≡m_2 merge — which is exactly what Stage 3C weights.
    """
    return [
        entity("unit_a", "unit", "Zulu"),
        entity("unit_b", "unit", "Kappa"),
        entity("comp_s", "component", "Widget"),  # direct shared neighbour → the pair is always scored
        triple("unit_a", "fields", "comp_s"),
        triple("unit_b", "fields", "comp_s"),
        entity("m_1", "manufacturer", _ORG_A),  # merge-derived shared neighbour → the weighted variable
        entity("m_2", "manufacturer", _ORG_B),
        triple("unit_a", "sourced-from", "m_1"),
        triple("unit_b", "sourced-from", "m_2"),
    ]


def _single_claims() -> list:
    """Same anchor, but the second neighbour is ONE entity both units point to — the full-weight baseline."""
    return [
        entity("unit_a", "unit", "Zulu"),
        entity("unit_b", "unit", "Kappa"),
        entity("comp_s", "component", "Widget"),
        triple("unit_a", "fields", "comp_s"),
        triple("unit_b", "fields", "comp_s"),
        entity("m", "manufacturer", _ORG_A),
        triple("unit_a", "sourced-from", "m"),
        triple("unit_b", "sourced-from", "m"),
    ]


def _strong_cfg(*, possible_floor: float | None = None):
    """m_1/m_2 seeded as an alias ⇒ they bootstrap-merge at confidence 1.0 (a full-weight neighbour)."""
    return mk_config(alias_table={_ORG_A: [_ORG_B]}, possible_floor=possible_floor)


def _weak_cfg(*, possible_floor: float | None = None):
    """m_1/m_2 merged only by a per-type auto-merge FLOOR ⇒ a genuine sub-1.0 (fuzzy) merge."""
    return mk_config(auto_merge_by_type={"manufacturer": 0.37}, possible_floor=possible_floor)


# ── STRONG: a full-confidence shared neighbour → full relational → the pair reaches the analyst ────

def test_strong_shared_neighbour_reaches_candidate() -> None:
    """A shared neighbour fused at confidence 1.0 leaves the units' relational contribution at full."""
    cfg = _strong_cfg()
    part = resolve(_claims(), cfg)

    # precondition: the merge-derived neighbour exists because m_1 ≡ m_2, and that merge is full-confidence
    assert {"m_1", "m_2"} <= _cluster_of(part, "m_1"), "fixture: the two neighbour orgs did not merge"
    assert _NKEY in part.merge_confidence, "fixture: the neighbour merge recorded no confidence"
    assert part.merge_confidence[_NKEY] >= cfg.resolution.bands["auto_merge"], "neighbour merge is not full-confidence"

    # both shared neighbours count in full ⇒ the relational term is undiscounted ⇒ probable (candidate)
    assert _UKEY in part.merge_breakdown, "the unit pair was never scored"
    assert part.merge_breakdown[_UKEY]["relational"] == 1.0, "a full-confidence neighbourhood must count in full"
    assert _PAIR in _as_pairs(part.candidates)
    assert part.identity_status("unit_a", "unit_b") == "probable"


# ── WEAK: the shared neighbour rests on a sub-1.0 merge (the precondition Stage 3C weights against) ─

def test_weak_shared_neighbour_rests_on_a_low_confidence_merge() -> None:
    """Pin the WEAK fixture: the neighbour orgs really merge, and really at a sub-1.0 (floor) confidence."""
    cfg = _weak_cfg()
    part = resolve(_claims(), cfg)

    assert {"m_1", "m_2"} <= _cluster_of(part, "m_1"), "fixture: the fuzzy per-type floor did not merge the neighbours"
    assert _NKEY in part.merge_confidence, "fixture: the neighbour merge recorded no confidence"
    conf = part.merge_confidence[_NKEY]
    assert 0.0 < conf < 1.0, "the neighbour merge must be a genuine sub-1.0 (fuzzy) merge"
    assert conf < cfg.resolution.bands["auto_merge"], "the neighbour merge must sit below the strict global bar (a floor merge)"


# ── the heart of the contract: a weak neighbour yields a strictly LOWER relational (and total) ────

def test_weak_neighbour_yields_strictly_lower_relational_and_total() -> None:
    """Same unit pair, same anchor — only the merge-confidence of the second neighbour differs.

    Because the pairs are structurally identical, EVERY non-relational term must be unchanged; the whole
    of the difference lands on the relational term, which the low-confidence neighbour discounts.
    """
    strong = resolve(_claims(), _strong_cfg(possible_floor=0.01))
    weak = resolve(_claims(), _weak_cfg(possible_floor=0.01))

    # precondition: the ONLY thing that changed is the merge confidence of the shared neighbour
    assert strong.merge_confidence[_NKEY] > weak.merge_confidence[_NKEY], "fixture: neighbour confidences did not differ"

    assert _UKEY in strong.merge_breakdown, "strong: the unit pair was never scored"
    assert _UKEY in weak.merge_breakdown, "weak: the unit pair was never scored"
    s, w = strong.merge_breakdown[_UKEY], weak.merge_breakdown[_UKEY]

    # the strong pair is at full strength; the weak pair is discounted but not zeroed (the anchor holds it up)
    assert s["relational"] == 1.0
    assert 0.0 < w["relational"] < s["relational"]
    # the discount drags the total down with it ...
    assert w["total"] < s["total"]
    # ... while leaving every non-relational term identical (the two scenarios are otherwise the same pair)
    for term in ("attribute", "temporal_consistency", "source_asserted"):
        assert w[term] == s[term], f"{term} differs — the two scenarios are not otherwise identical"


# ── the band follows the score: a weak neighbour drops the pair to a strictly lower band ──────────

def test_weak_neighbour_lands_in_a_lower_band_than_strong() -> None:
    """STRONG reaches probable (candidate); WEAK, discounted, drops to a lower band (possible / separate)."""
    strong = resolve(_claims(), _strong_cfg(possible_floor=0.05))
    weak = resolve(_claims(), _weak_cfg(possible_floor=0.05))

    # strong: the full-strength neighbourhood lifts the pair to the analyst
    assert _PAIR in _as_pairs(strong.candidates)
    assert strong.identity_status("unit_a", "unit_b") == "probable"

    # weak: the discounted neighbour is not enough — a strictly lower band, never candidate
    assert _PAIR not in _as_pairs(weak.candidates)
    assert weak.identity_status("unit_a", "unit_b") in ("possible", None)

    # and neither run auto-merged the units themselves (the effect is at the band, not a runaway merge)
    assert _PAIR not in _as_pairs(strong.same_as)
    assert _PAIR not in _as_pairs(weak.same_as)


# ── the full-weight default: a single shared entity == a 1.0 merge, and both beat the weak merge ──

def test_single_shared_entity_counts_in_full_like_a_confirmed_merge() -> None:
    """Equal weight is the default: one raw entity and a 1.0 bootstrap merge are indistinguishable.

    Both give the full relational contribution; only the low-confidence (fuzzy) merge is discounted.
    """
    single = resolve(_single_claims(), mk_config(possible_floor=0.01))
    strong = resolve(_claims(), _strong_cfg(possible_floor=0.01))
    weak = resolve(_claims(), _weak_cfg(possible_floor=0.01))

    for label, part in (("single", single), ("strong", strong), ("weak", weak)):
        assert _UKEY in part.merge_breakdown, f"{label}: the unit pair was never scored"

    rel_single = single.merge_breakdown[_UKEY]["relational"]
    rel_strong = strong.merge_breakdown[_UKEY]["relational"]
    rel_weak = weak.merge_breakdown[_UKEY]["relational"]

    # a single raw neighbour and a 1.0-merge neighbour are indistinguishable — both count in full
    assert rel_single == rel_strong == 1.0
    # ... and both strictly exceed the low-confidence (fuzzy-merge) neighbour
    assert rel_weak < rel_single


# ── control: even where the band cannot tell them apart, the underlying score still ranks them ────

def test_weighting_lowers_the_score_even_when_the_band_is_unchanged() -> None:
    """Pull the HITL floor low enough that BOTH pairs are candidates — the band no longer distinguishes them.

    The weighting must still be observable in the underlying identity score: the weak-neighbour pair
    ranks strictly lower on both the relational term and the total, band parity notwithstanding.
    """
    strong_cfg = _strong_cfg(possible_floor=0.01)
    weak_cfg = _weak_cfg(possible_floor=0.01)
    strong_cfg.resolution.bands["hitl_low"] = 0.10
    weak_cfg.resolution.bands["hitl_low"] = 0.10
    strong = resolve(_claims(), strong_cfg)
    weak = resolve(_claims(), weak_cfg)

    # same band: both reach candidate
    assert _PAIR in _as_pairs(strong.candidates)
    assert _PAIR in _as_pairs(weak.candidates)

    # ... yet the identity score still ranks the weak-neighbour pair strictly lower
    assert weak.merge_breakdown[_UKEY]["relational"] < strong.merge_breakdown[_UKEY]["relational"]
    assert weak.merge_breakdown[_UKEY]["total"] < strong.merge_breakdown[_UKEY]["total"]
