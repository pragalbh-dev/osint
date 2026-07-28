"""The measurement discipline — the tests that matter most.

The bake-off decides which model re-freezes the graded oracle. A scorer that manufactures a ranking out
of run-to-run jitter hands that job to whichever candidate got lucky. These tests pin the four structural
refusals: under-replication, un-rankable series, gate dominance, and tie-means-no-winner — and the
``Verdict`` invariant that makes the last one impossible to bypass in code.
"""

from __future__ import annotations

import pytest

from eval.extraction.compare import (
    COMPOSITE,
    NO_DIFFERENCE_PHRASE,
    Verdict,
    compare_metric,
    compare_pair,
    decide,
    pooled_sd,
    required_margin,
)
from eval.extraction.gates import GateReport, GateResult
from eval.extraction.scorecard import CandidateScore, MetricSeries

from .fixtures import bakeoff_config


def _series(name: str, values: tuple[float, ...], *, unit: str = "rate",
            direction: str = "higher_is_better", n_runs: int | None = None) -> MetricSeries:
    return MetricSeries(
        name=name, unit=unit, direction=direction, values=values,  # type: ignore[arg-type]
        n_runs=n_runs if n_runs is not None else len(values), status="measured",
        min_runs_for_ranking=3,
    )


def _gates(passing: bool = True) -> GateReport:
    status = "PASS" if passing else "FAIL"
    return GateReport("x", (GateResult("vlm_imagery_path", status, "fixture"),))


def _score(cid: str, series: dict[str, MetricSeries], *, gates_pass: bool = True,
           runs: int = 3) -> CandidateScore:
    from eval.extraction.scorecard import RunScore

    return CandidateScore(
        candidate_id=cid, label=cid.title(), model_id=f"{cid}-2026-01-01",
        gates=GateReport(cid, (GateResult("vlm_imagery_path", "PASS" if gates_pass else "FAIL", "fx"),)),
        series=series,
        runs=tuple(RunScore(cid, i + 1, {}) for i in range(runs)),
    )


# ── the arithmetic of the margin rule ─────────────────────────────────────────────────────────────

def test_pooled_sd_and_required_margin() -> None:
    assert pooled_sd(0.02, 0.02) == pytest.approx(0.02)
    assert pooled_sd(None, 0.02) is None
    cfg = bakeoff_config()
    # the floor dominates when noise is tiny
    assert required_margin("surface_f1", 0.001, cfg.margin) == pytest.approx(0.03)
    # noise dominates when it is large
    assert required_margin("surface_f1", 0.05, cfg.margin) == pytest.approx(0.10)
    assert required_margin("surface_f1", None, cfg.margin) is None


def test_a_gap_inside_the_noise_is_no_measured_difference() -> None:
    cfg = bakeoff_config()
    a = _series("surface_f1", (0.80, 0.84, 0.88))   # mean 0.84, sd ≈ 0.04
    b = _series("surface_f1", (0.78, 0.82, 0.86))   # mean 0.82, sd ≈ 0.04
    result = compare_pair("surface_f1", "a", a, "b", b, cfg.margin)
    assert result.verdict == "NO_MEASURED_DIFFERENCE"
    assert not result.material


def test_a_gap_clearing_both_floor_and_noise_is_material() -> None:
    cfg = bakeoff_config()
    a = _series("surface_f1", (0.90, 0.91, 0.92))
    b = _series("surface_f1", (0.50, 0.51, 0.52))
    result = compare_pair("surface_f1", "a", a, "b", b, cfg.margin)
    assert result.verdict == "A_BETTER" and result.material


def test_a_tiny_but_stable_gap_is_still_not_material_because_of_the_floor() -> None:
    """Low variance must not let a 0.005 difference be called a result."""
    cfg = bakeoff_config()
    a = _series("surface_f1", (0.900, 0.900, 0.901))
    b = _series("surface_f1", (0.895, 0.895, 0.896))
    assert compare_pair("surface_f1", "a", a, "b", b, cfg.margin).verdict == "NO_MEASURED_DIFFERENCE"


def test_lower_is_better_direction_is_respected() -> None:
    cfg = bakeoff_config()
    fast = _series("latency_s", (1.0, 1.1, 1.2), unit="seconds", direction="lower_is_better")
    slow = _series("latency_s", (9.0, 9.1, 9.2), unit="seconds", direction="lower_is_better")
    assert compare_pair("latency_s", "fast", fast, "slow", slow, cfg.margin).verdict == "A_BETTER"


def test_a_single_run_cannot_be_ranked() -> None:
    cfg = bakeoff_config()
    a = _series("surface_f1", (0.9,))
    b = _series("surface_f1", (0.2,))
    result = compare_pair("surface_f1", "a", a, "b", b, cfg.margin)
    assert result.verdict == "NOT_RANKABLE"


def test_partially_measured_series_is_not_rankable() -> None:
    partial = MetricSeries("surface_f1", "rate", "higher_is_better", (0.9, 0.9), 3, "partial",
                           min_runs_for_ranking=3)
    assert partial.rankable is False
    assert "2/3" in partial.not_rankable_because


def test_tiers_group_candidates_that_are_not_separable() -> None:
    cfg = bakeoff_config()
    series = {
        "a": _series("surface_f1", (0.90, 0.91, 0.92)),
        "b": _series("surface_f1", (0.89, 0.90, 0.91)),
        "c": _series("surface_f1", (0.30, 0.31, 0.32)),
    }
    comparison = compare_metric("surface_f1", series, cfg.margin)
    assert comparison.tiers[0] == ("a", "b")   # within noise of each other
    assert comparison.tiers[1] == ("c",)


# ── the four structural refusals ──────────────────────────────────────────────────────────────────

def test_verdict_refuses_to_carry_a_winner_outside_the_winner_kind() -> None:
    """The invariant that makes a fabricated ranking impossible rather than merely discouraged."""
    with pytest.raises(ValueError, match="winner"):
        Verdict("NO_MEASURED_DIFFERENCE", "tied", winner="a")
    with pytest.raises(ValueError, match="winner"):
        Verdict("WINNER", "won")


def test_under_replication_refuses_to_rank_at_all() -> None:
    cfg = bakeoff_config()
    scores = [
        _score("alpha", {"surface_f1": _series("surface_f1", (0.9, 0.9), n_runs=2)}, runs=2),
        _score("beta", {"surface_f1": _series("surface_f1", (0.1, 0.1), n_runs=2)}, runs=2),
    ]
    verdict, comparison = decide(scores, cfg)
    assert verdict.kind == "INSUFFICIENT_REPLICATION"
    assert verdict.winner is None and comparison is None


def test_a_within_noise_composite_yields_no_measured_difference_not_a_winner() -> None:
    cfg = bakeoff_config()
    scores = [
        _score("alpha", {"surface_f1": _series("surface_f1", (0.80, 0.84, 0.88))}),
        _score("beta", {"surface_f1": _series("surface_f1", (0.79, 0.83, 0.87))}),
    ]
    verdict, _ = decide(scores, cfg)
    assert verdict.kind == "NO_MEASURED_DIFFERENCE"
    assert verdict.winner is None
    assert set(verdict.tied) == {"alpha", "beta"}
    assert NO_DIFFERENCE_PHRASE in verdict.statement


def test_a_real_separation_does_produce_a_winner() -> None:
    """The instrument must still be able to say something — a scorer that never decides is useless."""
    cfg = bakeoff_config()
    scores = [
        _score("alpha", {"surface_f1": _series("surface_f1", (0.90, 0.91, 0.92))}),
        _score("beta", {"surface_f1": _series("surface_f1", (0.40, 0.41, 0.42))}),
    ]
    verdict, comparison = decide(scores, cfg)
    assert verdict.kind == "WINNER" and verdict.winner == "alpha"
    assert comparison is not None and comparison.metric == COMPOSITE


def test_a_gate_failure_dominates_any_score() -> None:
    """A disqualified candidate cannot win no matter how far ahead it is."""
    cfg = bakeoff_config()
    scores = [
        _score("alpha", {"surface_f1": _series("surface_f1", (0.99, 0.99, 0.99))}, gates_pass=False),
        _score("beta", {"surface_f1": _series("surface_f1", (0.40, 0.41, 0.42))}),
    ]
    verdict, _ = decide(scores, cfg)
    assert verdict.kind == "SOLE_ELIGIBLE_CANDIDATE"
    assert verdict.winner is None
    assert "alpha" in verdict.disqualified


def test_all_gates_failing_leaves_nothing_selectable() -> None:
    cfg = bakeoff_config()
    scores = [
        _score("alpha", {"surface_f1": _series("surface_f1", (0.9, 0.9, 0.9))}, gates_pass=False),
        _score("beta", {"surface_f1": _series("surface_f1", (0.8, 0.8, 0.8))}, gates_pass=False),
    ]
    verdict, _ = decide(scores, cfg)
    assert verdict.kind == "NO_ELIGIBLE_CANDIDATE" and verdict.winner is None


def test_a_metric_one_candidate_lacks_is_excluded_from_the_composite() -> None:
    cfg = bakeoff_config(weights={"surface_f1": 1.0, "coref_binding": 5.0})
    scores = [
        _score("alpha", {
            "surface_f1": _series("surface_f1", (0.90, 0.91, 0.92)),
            "coref_binding": MetricSeries("coref_binding", "rate", "higher_is_better", (), 3,
                                          "unavailable", ("AWAITING S3",), 3),
        }),
        _score("beta", {
            "surface_f1": _series("surface_f1", (0.40, 0.41, 0.42)),
            "coref_binding": MetricSeries("coref_binding", "rate", "higher_is_better", (), 3,
                                          "unavailable", ("AWAITING S3",), 3),
        }),
    ]
    verdict, _ = decide(scores, cfg)
    assert "coref_binding" in verdict.composite_exclusions
    assert "coref_binding" not in verdict.composite_weights
    assert verdict.kind == "WINNER"      # still decidable on what WAS measured


def test_no_comparable_metric_means_no_ranking() -> None:
    cfg = bakeoff_config(weights={"coref_binding": 5.0})
    unavailable = MetricSeries("coref_binding", "rate", "higher_is_better", (), 3, "unavailable",
                               ("AWAITING S3",), 3)
    scores = [_score("alpha", {"coref_binding": unavailable}),
              _score("beta", {"coref_binding": unavailable})]
    verdict, _ = decide(scores, cfg)
    assert verdict.kind == "NO_COMPARABLE_METRICS" and verdict.winner is None


def test_non_rate_metrics_never_enter_the_composite() -> None:
    """Seconds and dollars need a normalising constant nobody justified — so they stay out."""
    cfg = bakeoff_config(weights={"latency_s": 5.0, "surface_f1": 1.0})
    scores = [
        _score("alpha", {
            "surface_f1": _series("surface_f1", (0.90, 0.91, 0.92)),
            "latency_s": _series("latency_s", (1.0, 1.1, 1.2), unit="seconds",
                                 direction="lower_is_better"),
        }),
        _score("beta", {
            "surface_f1": _series("surface_f1", (0.40, 0.41, 0.42)),
            "latency_s": _series("latency_s", (9.0, 9.1, 9.2), unit="seconds",
                                 direction="lower_is_better"),
        }),
    ]
    verdict, _ = decide(scores, cfg)
    assert verdict.composite_weights == {"surface_f1": 1.0}
    assert "not a 0..1 rate" in verdict.composite_exclusions["latency_s"]
