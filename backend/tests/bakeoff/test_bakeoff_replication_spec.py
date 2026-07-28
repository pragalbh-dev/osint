"""RK-BAKEOFF gate 2 — **the harness must not manufacture determinism.**

Plan §8: "N repeated scoring runs per model with **variance reported** … necessary given confirmed
run-to-run non-determinism on a small slice", and among the scored criteria: "determinism/reproducibility
across the N runs (the live lane is *allowed* non-deterministic … re-extraction is *empirically confirmed
non-deterministic and has broken the hero query*)".

Two distinct lies this gate forbids:

1. **The single run reported as truth.** With N=1 the spread is not small — it is *unknown*. A harness that
   ranks off one run per candidate has not measured anything; it has sampled once and called it a fact.
   Because the spread of an unreplicated metric is undefined, no minimum-margin rule can protect against
   it — the refusal has to be structural.
2. **N runs silently collapsed to their mean.** If the report keeps only the mean, the reader cannot audit
   the margin call at all: the one number that decides "material vs jitter" has been thrown away before it
   reaches them. Reporting variance means *carrying the per-run values and a dispersion figure into the
   artifact*, not computing them and discarding them.

**Scope, stated honestly.** These assertions are on the scorecard/report contract, which is where the lie
becomes visible to a reader. Whether the orchestrator physically re-invokes the provider N times cannot be
pinned blind without coupling to an unseen orchestrator API; the last test here pins the observable half —
that N per-run values survive into the report, so a harness that fabricated them from one call would have
to fabricate N *distinct* values to pass.
"""

from __future__ import annotations

from tests.bakeoff._bakeoff_contract_spec import (
    candidate,
    clean_runs,
    do_scorecard,
    ref_scorecard,
    row_metric,
    stat_runs,
    stat_spread,
    why,
)

MIN_MARGIN = 0.03

# One run each, and a big apparent gap — exactly the shape that seduces a harness into declaring a winner.
ONE_RUN_LOW = candidate("alpha", model_id="alpha-1.0", runs=clean_runs([0.55]))
ONE_RUN_HIGH = candidate("beta", model_id="beta-1.0", runs=clean_runs([0.90]))

THREE_RUN_A = candidate("alpha", model_id="alpha-1.0", runs=clean_runs([0.77, 0.87, 0.82]))
THREE_RUN_B = candidate("beta", model_id="beta-1.0", runs=clean_runs([0.79, 0.88, 0.835]))


# ── the gate ──────────────────────────────────────────────────────────────────────────────────────

def test_single_run_cannot_produce_a_winner():
    sc = do_scorecard([ONE_RUN_LOW, ONE_RUN_HIGH], min_margin=MIN_MARGIN)
    assert sc.winner is None, why(
        f"UNREPLICATED-WINNER: the harness named {sc.winner!r} from ONE run per candidate. With N=1 the "
        "run-to-run spread is not small, it is unknown — so the .35 gap cannot be distinguished from the "
        "jitter that has already been confirmed on this slice (and has broken the hero query before). "
        "A single sample is not a measurement, and the refusal must be structural, not a margin call."
    )


def test_single_run_is_named_as_unreplicated():
    sc = do_scorecard([ONE_RUN_LOW, ONE_RUN_HIGH], min_margin=MIN_MARGIN)
    text = sc.text()
    assert any(k in text for k in ("unreplicated", "single run", "n=1", "one run", "replication")), why(
        "UNREPLICATED-UNNAMED: the scorecard must say *why* it withheld a verdict — that the candidates "
        "were run once and the spread is unknown. An unexplained empty winner reads as 'they tied', "
        f"which is a different and false claim. Verdict text was: {text[:400]!r}"
    )


def test_per_run_values_survive_into_the_report():
    sc = do_scorecard([THREE_RUN_A, THREE_RUN_B], min_margin=MIN_MARGIN)
    row = sc.row("alpha")
    runs = stat_runs(row_metric(row, "claim_f1"))
    assert runs is not None and len(list(runs)) == 3, why(
        f"COLLAPSED-TO-MEAN: alpha was scored over 3 runs ([.77,.87,.82]) but the report carries "
        f"{runs!r}. Collapsing N runs to a point before they reach the reader destroys the only evidence "
        "that would let anyone check the margin call — the report then asserts a precision it cannot "
        "support."
    )


def test_spread_is_reported_alongside_the_mean():
    sc = do_scorecard([THREE_RUN_A, THREE_RUN_B], min_margin=MIN_MARGIN)
    for name in ("alpha", "beta"):
        spread = stat_spread(row_metric(sc.row(name), "claim_f1"))
        assert spread is not None, why(
            f"VARIANCE-UNREPORTED: {name}'s claim_f1 row carries no dispersion figure. Plan §8 requires "
            "variance *reported*, not merely computed: without it the difference between 'ahead' and "
            "'noisier' is invisible, and the reader has no way to audit whether the winner was real."
        )


def test_reported_spread_tracks_the_actual_variation():
    """A constant or zero 'spread' would satisfy the previous test while reporting nothing."""
    steady = candidate("steady", model_id="steady-1.0", runs=clean_runs([0.820, 0.820, 0.820]))
    jumpy = candidate("jumpy", model_id="jumpy-1.0", runs=clean_runs([0.60, 0.82, 0.99]))
    sc = do_scorecard([steady, jumpy], min_margin=MIN_MARGIN)
    s_spread = stat_spread(row_metric(sc.row("steady"), "claim_f1"))
    j_spread = stat_spread(row_metric(sc.row("jumpy"), "claim_f1"))
    assert s_spread is not None and j_spread is not None and float(j_spread) > float(s_spread), why(
        f"SPREAD-IS-DECORATIVE: a model whose runs were [.60,.82,.99] reported spread {j_spread!r} while "
        f"a model whose runs never moved off .820 reported {s_spread!r}. A dispersion figure that does "
        "not respond to dispersion is a field, not a measurement — and the whole noise rule is built on "
        "top of it."
    )


# ── positive controls ─────────────────────────────────────────────────────────────────────────────

def test_positive_control_reference_refuses_a_single_run():
    sc = ref_scorecard([ONE_RUN_LOW, ONE_RUN_HIGH], min_margin=MIN_MARGIN)
    assert sc.winner is None
    assert "unreplicated" in sc.text()


def test_positive_control_reference_reports_runs_and_spread():
    sc = ref_scorecard([THREE_RUN_A, THREE_RUN_B], min_margin=MIN_MARGIN)
    stat = row_metric(sc.row("alpha"), "claim_f1")
    assert len(list(stat_runs(stat))) == 3
    assert stat_spread(stat) is not None and float(stat_spread(stat)) > 0.0
