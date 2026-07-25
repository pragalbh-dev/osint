"""Aggregation across runs, and the rendered scorecard's ordering discipline.

Layout is an argument: a reader who skims to the biggest number must hit the gate block first. And a
metric nobody could measure must print its reason where its number would have been — a dash reads like a
zero, and a zero reads like a finding.
"""

from __future__ import annotations

import json

import pytest

from eval.extraction.compare import decide, per_metric_comparisons
from eval.extraction.gates import GateReport, GateResult
from eval.extraction.metrics import NO_CLUSTERING, MetricValue
from eval.extraction.render import render_markdown, to_json
from eval.extraction.scorecard import (
    RunScore,
    aggregate_runs,
    build_series,
    claim_signature,
    determinism_values,
    series_table,
    unexercised,
)

from .fixtures import bakeoff_config, entity, triple


def _gates(status: str = "PASS") -> GateReport:
    return GateReport("x", (GateResult("vlm_imagery_path", status, "fixture"),))


def _run(cid: str, i: int, f1: float, *, claims=()) -> RunScore:
    return RunScore(cid, i, {"surface_f1": MetricValue.measured("surface_f1", f1)}, claims=claims)


# ── series aggregation ────────────────────────────────────────────────────────────────────────────

def test_a_series_records_mean_and_sample_spread() -> None:
    values = [MetricValue.measured("m", v) for v in (0.8, 0.9, 1.0)]
    series = build_series("m", values, 3, 3)
    assert series.mean == pytest.approx(0.9)
    assert series.stdev == pytest.approx(0.1)
    assert series.rankable


def test_a_series_measured_in_some_runs_is_partial_and_not_rankable() -> None:
    values = [MetricValue.measured("m", 0.8), MetricValue.unavailable("m", "no substrate"),
              MetricValue.measured("m", 0.9)]
    series = build_series("m", values, 3, 3)
    assert series.status == "partial" and not series.rankable
    assert series.mean is not None            # still reported, with the gap named
    assert "2/3" in series.not_rankable_because


def test_a_fully_unavailable_series_keeps_the_reason_and_reports_no_value() -> None:
    values = [MetricValue.unavailable("coref_binding", NO_CLUSTERING) for _ in range(3)]
    series = build_series("coref_binding", values, 3, 3)
    assert series.status == "unavailable" and series.values == () and series.mean is None
    assert series.reasons == (NO_CLUSTERING,)


def test_two_runs_are_below_the_ranking_floor_of_three() -> None:
    values = [MetricValue.measured("m", 0.8), MetricValue.measured("m", 0.9)]
    assert build_series("m", values, 2, 3).rankable is False


# ── determinism ───────────────────────────────────────────────────────────────────────────────────

def test_identical_runs_score_determinism_one() -> None:
    claims = (triple("c1", "A Foundry", "B Coupler"),)
    runs = [_run("a", i, 1.0, claims=claims) for i in range(1, 4)]
    values = determinism_values(runs)
    assert all(v.value == pytest.approx(1.0) for v in values)


def test_diverging_runs_score_below_one() -> None:
    runs = [
        _run("a", 1, 1.0, claims=(triple("c1", "A Foundry", "B Coupler"),)),
        _run("a", 2, 1.0, claims=(triple("c1", "C Works", "D Valve"),)),
        _run("a", 3, 1.0, claims=(triple("c1", "A Foundry", "B Coupler"),)),
    ]
    values = determinism_values(runs)
    assert all(v.value is not None and v.value < 1.0 for v in values)


def test_determinism_needs_two_runs_to_exist_at_all() -> None:
    values = determinism_values([_run("a", 1, 1.0)])
    assert values[0].status == "unavailable" and "at least 2 runs" in values[0].reason


def test_claim_signature_ignores_ids_and_provenance() -> None:
    a = triple("c1", "North Ridge Foundry", "Type-7 Coupler", span=(0, 10))
    b = triple("different-id", "north-ridge foundry", "type 7 coupler", span=(900, 950))
    assert claim_signature(a) == claim_signature(b)


def test_claim_signature_separates_a_negation() -> None:
    a = triple("c1", "A Foundry", "B Coupler")
    b = triple("c1", "A Foundry", "B Coupler", polarity="negative")
    assert claim_signature(a) != claim_signature(b)


def test_aggregate_runs_adds_the_determinism_series() -> None:
    cfg = bakeoff_config()
    runs = [_run("alpha", i, 0.9, claims=(entity("e", "North Ridge Foundry"),)) for i in range(1, 4)]
    score = aggregate_runs("alpha", "Alpha", "alpha-1", _gates(), runs, cfg.replication)
    assert "determinism" in score.series
    assert score.series["surface_f1"].mean == pytest.approx(0.9)
    assert [row["metric"] for row in series_table(score)] == ["determinism", "surface_f1"]


def test_an_unexercised_candidate_is_never_eligible() -> None:
    score = unexercised("beta", "Beta", "beta-1", _gates(), "no key")
    assert score.eligible_to_win is False and score.series == {}


# ── rendering ─────────────────────────────────────────────────────────────────────────────────────

def _two_candidate_render(f1_a: tuple[float, ...], f1_b: tuple[float, ...], *, gates_b: str = "PASS"):
    cfg = bakeoff_config()
    scores = [
        aggregate_runs("alpha", "Alpha", "alpha-2026-01-01", _gates(),
                       [_run("alpha", i + 1, v) for i, v in enumerate(f1_a)], cfg.replication),
        aggregate_runs("beta", "Beta", "beta-2026-01-01", _gates(gates_b),
                       [_run("beta", i + 1, v) for i, v in enumerate(f1_b)], cfg.replication),
    ]
    verdict, composite = decide(scores, cfg)
    return scores, verdict, per_metric_comparisons(scores, cfg), cfg, composite


def test_gates_are_printed_above_every_score() -> None:
    scores, verdict, comparisons, cfg, composite = _two_candidate_render(
        (0.9, 0.91, 0.92), (0.4, 0.41, 0.42))
    md = render_markdown(scores, verdict, comparisons, cfg, composite)
    assert md.index("Gating preconditions") < md.index("Measured criteria")
    assert "PASS/FAIL to win (never weighted)" in md


def test_a_within_noise_result_renders_the_exact_phrase_and_no_winner() -> None:
    scores, verdict, comparisons, cfg, composite = _two_candidate_render(
        (0.80, 0.84, 0.88), (0.79, 0.83, 0.87))
    md = render_markdown(scores, verdict, comparisons, cfg, composite)
    assert "NO MEASURED DIFFERENCE" in md
    assert "**Winner:" not in md


def test_a_disqualified_candidate_is_shown_as_such() -> None:
    scores, verdict, comparisons, cfg, composite = _two_candidate_render(
        (0.9, 0.91, 0.92), (0.4, 0.41, 0.42), gates_b="FAIL")
    md = render_markdown(scores, verdict, comparisons, cfg, composite)
    assert "NO — disqualified" in md
    assert verdict.kind == "SOLE_ELIGIBLE_CANDIDATE"


def test_the_match_policy_is_printed_under_the_numbers_it_produced() -> None:
    scores, verdict, comparisons, cfg, composite = _two_candidate_render(
        (0.9, 0.91, 0.92), (0.4, 0.41, 0.42))
    md = render_markdown(scores, verdict, comparisons, cfg, composite)
    assert "The match policy that produced these numbers" in md
    assert "token_sort_ratio" in md


def test_every_score_cell_carries_its_spread() -> None:
    scores, verdict, comparisons, cfg, composite = _two_candidate_render(
        (0.9, 0.91, 0.92), (0.4, 0.41, 0.42))
    md = render_markdown(scores, verdict, comparisons, cfg, composite)
    assert "±" in md and "n=3" in md


def test_json_output_round_trips_and_keeps_the_refusals() -> None:
    scores, verdict, comparisons, cfg, _ = _two_candidate_render(
        (0.80, 0.84, 0.88), (0.79, 0.83, 0.87))
    payload = json.loads(to_json(scores, verdict, comparisons, cfg))
    assert payload["verdict"]["kind"] == "NO_MEASURED_DIFFERENCE"
    assert payload["verdict"]["winner"] is None
    assert payload["match_policy"]["similarity"] == "token_sort_ratio"
    assert payload["replication"]["min_runs_for_ranking"] == 3
