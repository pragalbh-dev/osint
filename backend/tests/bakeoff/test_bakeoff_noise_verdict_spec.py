"""RK-BAKEOFF gate 1 — **a gap inside the noise is "no measured difference", never a ranking.**

Plan §8: "**Replication:** N repeated scoring runs per model with variance reported, a minimum margin
before a difference is 'material,' and within-noise gaps reported as **'no measured difference'** —
consistent with the no-winner posture, and necessary given confirmed run-to-run non-determinism on a small
slice."

Why this is the first gate. This bake-off is a **measuring instrument**, and the instrument's failure mode
is not "wrong number" — it is *manufacturing a ranking out of jitter*. Re-extraction is empirically
confirmed non-deterministic on this slice; two candidates two F1 points apart, each wobbling four points
run to run, are **not** distinguishable. A harness that prints "gemini wins, 0.835 vs 0.820" there has
fabricated an assessment out of noise — the same act the project's one non-negotiable forbids, applied to
its own oracle. It would hand the graded corpus to the wrong model, permanently.

**Non-vacuity.** A harness that simply never ranks anything would satisfy the clause above trivially and be
useless. So the gate is asserted *differentially*: the same scorecard call must refuse to rank a
within-noise gap **and** must be willing to rank a gap that is far outside both the minimum margin and the
pooled spread. Both directions are required; neither alone is a gate.
"""

from __future__ import annotations

from tests.bakeoff._bakeoff_contract_spec import (
    PRIMARY_METRIC,
    candidate,
    clean_runs,
    do_scorecard,
    ref_scorecard,
    why,
)

MIN_MARGIN = 0.03

# Two candidates ~1.5 F1 points apart, each wobbling ~±5 points run to run. Any honest rule — margin,
# pooled spread, or a t-test — calls this indistinguishable.
NOISY_A = candidate("alpha", model_id="alpha-1.0", runs=clean_runs([0.77, 0.87, 0.82]))
NOISY_B = candidate("beta", model_id="beta-1.0", runs=clean_runs([0.79, 0.88, 0.835]))

# A gap of 35 F1 points with the runs tight to a thousandth. Any honest rule calls this material.
TIGHT_LOW = candidate("alpha", model_id="alpha-1.0", runs=clean_runs([0.549, 0.551, 0.550]))
TIGHT_HIGH = candidate("beta", model_id="beta-1.0", runs=clean_runs([0.899, 0.901, 0.900]))


def _sc(cands, **kw):
    return do_scorecard(cands, min_margin=MIN_MARGIN, primary_metric=PRIMARY_METRIC, **kw)


# ── the gate ──────────────────────────────────────────────────────────────────────────────────────

def test_within_noise_gap_names_no_winner():
    sc = _sc([NOISY_A, NOISY_B])
    assert sc.winner is None, why(
        f"NOISE-RANKING: the harness named {sc.winner!r} the winner, but alpha (mean .820, runs "
        f"[.77,.87,.82]) and beta (mean .835, runs [.79,.88,.835]) differ by .015 — inside the "
        f"minimum margin ({MIN_MARGIN}) and far inside their own run-to-run spread (~.04 each). "
        "A gap within measured noise is not a difference; ranking it manufactures a result out of "
        "jitter and would hand the oracle to a model that never actually won."
    )


def test_within_noise_gap_is_reported_as_no_measured_difference():
    sc = _sc([NOISY_A, NOISY_B])
    assert "no measured difference" in sc.text(), why(
        "NOISE-VERDICT: a within-noise gap must be reported in words as 'no measured difference'. "
        "Silence, a blank winner field, or a bare 'inconclusive' leaves the next reader to fill the gap "
        f"with the higher mean. Verdict text was: {sc.text()[:400]!r}"
    )


def test_material_gap_is_still_callable():
    """Anti-vacuity: the noise rule must not degrade into 'never decide'."""
    sc = _sc([TIGHT_LOW, TIGHT_HIGH])
    assert sc.winner == "beta", why(
        f"NOISE-RULE-TOO-BLUNT: the harness returned winner={sc.winner!r} for a 35-point F1 gap "
        "(.550 vs .900) with run-to-run spread under .001. A harness that cannot call *that* difference "
        "is not conservative, it is inert — and an inert bake-off silently defaults to the incumbent "
        "while claiming to have measured. Verdict was: "
        f"{sc.text()[:400]!r}"
    )


def test_noise_verdict_is_symmetric_under_candidate_order():
    """The verdict must be a property of the measurements, not of the list order they arrived in."""
    forward, reverse = _sc([NOISY_A, NOISY_B]), _sc([NOISY_B, NOISY_A])
    assert forward.winner == reverse.winner, why(
        f"NOISE-ORDER-DEPENDENCE: winner was {forward.winner!r} with alpha listed first and "
        f"{reverse.winner!r} with beta listed first. A comparison whose outcome depends on argument "
        "order is not a measurement; it is a tie-break dressed as one."
    )


# ── positive controls: the same checks against a correct minimal harness must pass ────────────────

def test_positive_control_reference_refuses_the_noisy_gap():
    sc = ref_scorecard([NOISY_A, NOISY_B], min_margin=MIN_MARGIN)
    assert sc.winner is None
    assert "no measured difference" in sc.text()


def test_positive_control_reference_calls_the_material_gap():
    sc = ref_scorecard([TIGHT_LOW, TIGHT_HIGH], min_margin=MIN_MARGIN)
    assert sc.winner == "beta"
