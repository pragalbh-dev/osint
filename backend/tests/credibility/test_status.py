"""Noisy-OR pooling + the status machine — confirmed/probable/possible/insufficient/contradicted/stale."""

from __future__ import annotations

from pytest import approx

from chanakya.credibility.status import assign_status, noisy_or
from tests.credibility.builders import assertion, bundle, group

CFG = bundle()


def _status(a) -> tuple[str, float]:
    out = assign_status([a], CFG)[a.element_id]
    return out.status, out.assertion_confidence


# ── noisy-OR ─────────────────────────────────────────────────────────────────────────────────────

def test_two_independent_06_pool_to_084() -> None:
    conf = noisy_or([group("g1", ["a"]), group("g2", ["b"])], {"a": 0.6, "b": 0.6})
    assert conf == approx(0.84)  # 1 − 0.4·0.4


def test_echo_of_one_origin_adds_nothing() -> None:
    conf = noisy_or([group("g1", ["a", "b"])], {"a": 0.6, "b": 0.6})
    assert conf == approx(0.6)  # one group, c_g = max = 0.6


def test_same_class_half_weight_pools_lower() -> None:
    conf = noisy_or([group("g1", ["a"]), group("g2", ["b"], weight=0.5)], {"a": 0.6, "b": 0.6})
    assert conf == approx(1 - 0.4 * (1 - 0.3))  # second look at half weight → 0.72


# ── status bands ──────────────────────────────────────────────────────────────────────────────────

def test_confirmed_when_all_gates_met() -> None:
    a = assertion(per_claim={"a": 0.9, "b": 0.9}, groups=[group("g1", ["a"]), group("g2", ["b"])])
    status, conf = _status(a)
    assert status == "confirmed" and conf == approx(0.99)


def test_single_group_caps_at_probable() -> None:
    a = assertion(per_claim={"a": 0.9}, groups=[group("g1", ["a"])])
    assert _status(a)[0] == "probable"  # one independent look can't confirm


def test_probable_band() -> None:
    a = assertion(per_claim={"a": 0.6}, groups=[group("g1", ["a"])])
    assert _status(a) == ("probable", approx(0.6))


def test_possible_below_floor() -> None:
    a = assertion(per_claim={"a": 0.4}, groups=[group("g1", ["a"])])
    assert _status(a) == ("possible", approx(0.4))


def test_insufficient_dominates() -> None:
    # A required KIND missing → insufficient, even with strong magnitude (assessability ⊥ magnitude).
    a = assertion(per_claim={"a": 0.9, "b": 0.9}, groups=[group("g1", ["a"]), group("g2", ["b"])],
                  satisfied=False)
    assert _status(a)[0] == "insufficient"


def test_contradicted() -> None:
    a = assertion(per_claim={"a": 0.9, "b": 0.9}, groups=[group("g1", ["a"]), group("g2", ["b"])],
                  contradiction=True)
    assert _status(a)[0] == "contradicted"


def test_adversary_denial_caps_even_over_threshold() -> None:
    a = assertion(per_claim={"a": 0.9, "b": 0.9}, groups=[group("g1", ["a"]), group("g2", ["b"])],
                  gate_flags=["adversary-denial"])
    assert _status(a)[0] == "probable"  # gate, not multiplier — never counts as confirmation


def test_decoy_risk_caps_at_probable() -> None:
    a = assertion(per_claim={"a": 0.9, "b": 0.9}, groups=[group("g1", ["a"]), group("g2", ["b"])],
                  gate_flags=["decoy-risk"])
    assert _status(a)[0] == "probable"


def test_gated_attr_unknown_blocks_confirmed() -> None:
    a = assertion(per_claim={"a": 0.9, "b": 0.9}, groups=[group("g1", ["a"]), group("g2", ["b"])],
                  gate_flags=["gated-attr-unknown"])
    assert _status(a)[0] == "probable"


def test_stale_demotes_a_would_be_confirmed() -> None:
    a = assertion(per_claim={"a": 0.9, "b": 0.9}, groups=[group("g1", ["a"]), group("g2", ["b"])],
                  gate_flags=["aging", "stale"])
    assert _status(a)[0] == "stale"  # freshest look aged past one half-life → demoted from confirmed


def test_aging_but_not_stale_is_probable() -> None:
    a = assertion(per_claim={"a": 0.9, "b": 0.9}, groups=[group("g1", ["a"]), group("g2", ["b"])],
                  gate_flags=["aging"])
    assert _status(a)[0] == "probable"


# ── the confirmed-gate property (mirrors G7 at the machine level) ──────────────────────────────────

def test_confirmed_gate_requires_every_condition() -> None:
    """Break each confirmed condition one at a time — none may reach confirmed alone."""
    ok = assertion(per_claim={"a": 0.9, "b": 0.9}, groups=[group("g1", ["a"]), group("g2", ["b"])])
    assert _status(ok)[0] == "confirmed"

    broken = [
        assertion(per_claim={"a": 0.6, "b": 0.6}, groups=[group("g1", ["a"]), group("g2", ["b"])]),  # 0.84 ok...
        assertion(per_claim={"a": 0.9}, groups=[group("g1", ["a"])]),                                 # single group
        assertion(per_claim={"a": 0.9, "b": 0.9}, groups=[group("g1", ["a"]), group("g2", ["b"])],
                  satisfied=False),                                                                    # insufficient
        assertion(per_claim={"a": 0.9, "b": 0.9}, groups=[group("g1", ["a"]), group("g2", ["b"])],
                  gate_flags=["adversary-denial"]),                                                    # capped
        assertion(per_claim={"a": 0.9, "b": 0.9}, groups=[group("g1", ["a"]), group("g2", ["b"])],
                  contradiction=True),                                                                 # contradicted
    ]
    # 0.84 with two clean independent looks IS confirmable; the rest are not.
    statuses = [_status(a)[0] for a in broken]
    assert statuses[0] == "confirmed"  # 0.84 ≥ 0.80, two clean looks
    assert all(s != "confirmed" for s in statuses[1:])
