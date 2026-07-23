"""Stage 2 (D4) — identity as a three-status hypothesis: the retained ``possible`` watch-list tier,
the status-label helper, and the name-alone policy dial.

``possible`` is the antidote to fragmentation: a scored-but-sub-review pair is no longer *dropped*
(today's ``separate``) — it is kept as a latent link the analyst can see but is not pestered by.
It is Partition/in-memory only (never drawn), so nothing here touches the wire view.
"""

from __future__ import annotations

from chanakya.resolve import resolve
from chanakya.schemas import Partition, pair_key
from tests.resolve._helpers import entity, mk_config, triple


def _as_pairs(pairs: list[tuple[str, str]]) -> set[frozenset[str]]:
    return {frozenset(p) for p in pairs}


# ── the retained ``possible`` tier ───────────────────────────────────────────────────────────────

def test_sub_hitl_scored_pair_is_retained_in_possible_with_its_score() -> None:
    """A pair scored in ``[possible_floor, hitl_low)`` is retained in ``possible`` — not dropped.

    Two units share TWO of three (support_k=3) neighbours ⇒ relational 0.667 ⇒ total ≈ 0.317,
    below hitl_low (0.45) but above the possible floor (0.25). Today that pair vanishes; Stage 2
    keeps it on the watch-list carrying its identity score/breakdown.
    """
    cfg = mk_config(possible_floor=0.25, relational_support_k=3)
    claims = [
        entity("unit_a", "unit", "Zulu"),   # single-token, mutually dissimilar names ⇒ attribute ≈ 0,
        entity("unit_b", "unit", "Kappa"),  # so the pair is a pure shared-neighbourhood link
        entity("comp_x", "component", "CX"),
        entity("comp_y", "component", "CY"),
        triple("unit_a", "fields", "comp_x"),
        triple("unit_a", "fields", "comp_y"),
        triple("unit_b", "fields", "comp_x"),
        triple("unit_b", "fields", "comp_y"),
    ]
    part = resolve(claims, cfg)
    key = pair_key("unit_a", "unit_b")
    assert frozenset({"unit_a", "unit_b"}) in _as_pairs(part.possible)
    assert frozenset({"unit_a", "unit_b"}) not in _as_pairs(part.candidates)
    assert part.same_as == []
    total = part.merge_breakdown[key]["total"]
    assert 0.25 <= total < 0.45  # possible_floor .. hitl_low


def test_pair_below_possible_floor_is_not_retained() -> None:
    """A scored pair BELOW the floor is genuinely dropped — the watch-list is not a dumping ground.

    Two units share ONE of three (support_k=3) neighbours ⇒ relational 0.333 ⇒ total ≈ 0.183,
    under the 0.25 floor. It is neither a candidate nor a ``possible`` link.
    """
    cfg = mk_config(possible_floor=0.25, relational_support_k=3)
    claims = [
        entity("unit_c", "unit", "Ravi"),   # one shared neighbour only ⇒ relational 0.333 ⇒ total ≈ 0.183
        entity("unit_d", "unit", "Mox"),
        entity("comp_z", "component", "CZ"),
        triple("unit_c", "fields", "comp_z"),
        triple("unit_d", "fields", "comp_z"),
    ]
    part = resolve(claims, cfg)
    key = pair_key("unit_c", "unit_d")
    assert frozenset({"unit_c", "unit_d"}) not in _as_pairs(part.possible)
    assert frozenset({"unit_c", "unit_d"}) not in _as_pairs(part.candidates)
    # if it was scored at all, its total sits below the floor (proves the floor gated it, not candidacy)
    if key in part.merge_breakdown:
        assert part.merge_breakdown[key]["total"] < 0.25


def test_possible_tier_off_when_no_floor_configured() -> None:
    """Absent ``possible_floor`` ⇒ tier off ⇒ ``possible`` empty (byte-unchanged from pre-Stage-2)."""
    cfg = mk_config(relational_support_k=3)  # no possible_floor
    claims = [
        entity("unit_a", "unit", "Zulu"),
        entity("unit_b", "unit", "Kappa"),
        entity("comp_x", "component", "CX"),
        entity("comp_y", "component", "CY"),
        triple("unit_a", "fields", "comp_x"),
        triple("unit_a", "fields", "comp_y"),
        triple("unit_b", "fields", "comp_x"),
        triple("unit_b", "fields", "comp_y"),
    ]
    part = resolve(claims, cfg)
    assert part.possible == []


# ── the three-status label helper ─────────────────────────────────────────────────────────────────

def test_identity_status_labels_the_three_lists() -> None:
    """The derived helper maps a link to confirmed / probable / possible / None (order-independent)."""
    part = Partition(
        same_as=[("a", "b")],
        candidates=[("c", "d")],
        possible=[("e", "f")],
    )
    assert part.identity_status("a", "b") == "confirmed"
    assert part.identity_status("b", "a") == "confirmed"  # order-independent
    assert part.identity_status("c", "d") == "probable"
    assert part.identity_status("d", "c") == "probable"
    assert part.identity_status("e", "f") == "possible"
    assert part.identity_status("f", "e") == "possible"
    assert part.identity_status("x", "y") is None  # an unrelated pair carries no identity status


# ── the name-alone policy dial (banked D4 correction) ───────────────────────────────────────────────

def _name_alone_claims() -> list:
    # Two variants that share ONLY a name signal: an identity attr agrees (export_designator) so the
    # attribute score reaches 1.0, but there is NO shared neighbourhood and NO source assertion. They
    # share the "HQ-9" token (so they are compared) but do not normalise-equal / alias (so no bootstrap).
    return [
        entity("var_a", "variant", "HQ-9 Alpha", export_designator="HQ-9/P"),
        entity("var_b", "variant", "HQ-9 Beta", export_designator="HQ-9/P"),
    ]


_NAME_ALONE_RULES = {"variant": {"identity": ["export_designator"]}}


def test_name_alone_dial_off_keeps_the_pair_a_candidate() -> None:
    """Default OFF preserves current banding — a name-only pair still reaches the analyst (probable)."""
    cfg = mk_config(attribute_rules=_NAME_ALONE_RULES, possible_floor=0.25)  # dial defaults off
    part = resolve(_name_alone_claims(), cfg)
    assert frozenset({"var_a", "var_b"}) in _as_pairs(part.candidates)
    assert frozenset({"var_a", "var_b"}) not in _as_pairs(part.possible)
    key = pair_key("var_a", "var_b")
    # sanity: it IS name-alone (only the attribute signal fired)
    bd = part.merge_breakdown[key]
    assert bd["attribute"] > 0 and bd["relational"] == 0 and bd["source_asserted"] == 0


def test_name_alone_dial_on_caps_the_pair_at_possible() -> None:
    """ON: a pair whose only nonzero identity signal is ``attribute`` cannot reach probable/HITL."""
    cfg = mk_config(
        attribute_rules=_NAME_ALONE_RULES,
        possible_floor=0.25,
        name_alone_caps_at_possible=True,
    )
    part = resolve(_name_alone_claims(), cfg)
    assert frozenset({"var_a", "var_b"}) in _as_pairs(part.possible)
    assert frozenset({"var_a", "var_b"}) not in _as_pairs(part.candidates)
