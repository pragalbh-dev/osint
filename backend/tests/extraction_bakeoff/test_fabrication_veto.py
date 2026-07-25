"""RULING 2 — the fabrication line is a VETO, not a weight.

``trap_avoidance`` is the project's one non-negotiable expressed as a metric: did the candidate assert
something the document does not say, at the places the labeled slice knows the answer? This harness already
established the principle — *a non-negotiable is a veto, not a weight; inside a composite it is just a heavy
weight, and any weight is a price a good-enough model can pay*. These tests pin that trap_avoidance is
declared in ``gates.non_negotiable_floors`` (which reuses the margin rule, inventing no threshold) and
carries **no** weight, and that both halves of the veto hold:

* a candidate **materially worse** on it cannot be named winner however far ahead it is on score;
* a candidate whose trap line was **never measured** cannot be named winner either — otherwise the
  non-negotiable is traded away by absence rather than by arithmetic.
"""

from __future__ import annotations

from chanakya import settings
from eval.extraction.compare import composite_series, decide
from eval.extraction.gates import ImageryObservations, evaluate_gates
from eval.extraction.metrics import MetricValue
from eval.extraction.policy import load_bakeoff_config

from .fixtures import bakeoff_config
from .test_compare import _score, _series

TRAP = "trap_avoidance"


def _veto_config(**kw):
    """A bake-off whose only declared non-negotiable is the fabrication line."""
    gates = {"floating_alias_patterns": ["-latest"],
             "production_client_package": "chanakya.ingest",
             "non_negotiable_floors": {TRAP: None}}
    return bakeoff_config(gates=gates, **kw)


# ── the shipped declaration ────────────────────────────────────────────────────────────────────────

def test_the_shipped_config_declares_the_fabrication_line_a_veto_and_gives_it_no_weight() -> None:
    """The one assertion that would catch someone "simplifying" the veto back into a heavy weight."""
    cfg = load_bakeoff_config(settings.config_dir() / "bakeoff.yaml")
    assert TRAP in cfg.non_negotiable_metrics, "the fabrication line is not declared non-negotiable"
    assert cfg.weight_for(TRAP) == 0.0, (
        "trap_avoidance carries a composite weight — inside the composite it is just a heavy weight, and "
        "any weight is a price a model far enough ahead on recall can pay"
    )


def test_the_scorecard_marks_a_zero_weight_non_negotiable_as_a_veto() -> None:
    """The weight column is where a skimming reader decides what mattered, and the fabrication line's weight
    is deliberately 0.0. Unmarked, the most important criterion on the table reads as the least important."""
    from eval.extraction.render import render_markdown

    config = _veto_config(weights={"surface_f1": 3.0})
    scores = [
        _score("a", {"surface_f1": _series("surface_f1", (0.9, 0.9, 0.9)),
                     TRAP: _series(TRAP, (1.0, 1.0, 1.0))}),
        _score("b", {"surface_f1": _series("surface_f1", (0.5, 0.5, 0.5)),
                     TRAP: _series(TRAP, (1.0, 1.0, 1.0))}),
    ]
    verdict, composite = decide(scores, config)
    md = render_markdown(scores, verdict, {}, config, composite)
    trap_row = next(line for line in md.splitlines() if line.startswith(f"| `{TRAP}`"))
    assert "0 · **VETO**" in trap_row


def test_the_identity_over_read_count_can_never_enter_the_composite() -> None:
    """N=2. The gold's rule is "report the raw count, never a two-decimal rate, never rank on it", and the
    mechanism is the unit: ``composite_series`` admits only 0..1 rates."""
    config = bakeoff_config(weights={"surface_f1": 1.0, "identity_over_read": 4.0})
    a = _score("a", {"surface_f1": _series("surface_f1", (0.9, 0.9, 0.9)),
                     "identity_over_read": _series("identity_over_read", (0.0, 0.0, 0.0), unit="count",
                                                   direction="lower_is_better")})
    b = _score("b", {"surface_f1": _series("surface_f1", (0.5, 0.5, 0.5)),
                     "identity_over_read": _series("identity_over_read", (2.0, 2.0, 2.0), unit="count",
                                                   direction="lower_is_better")})
    _, used, excluded = composite_series([a, b], config)
    assert "identity_over_read" not in used
    assert "not a 0..1 rate" in excluded["identity_over_read"]


# ── the veto itself ────────────────────────────────────────────────────────────────────────────────

def test_a_candidate_that_wins_every_weighted_line_still_cannot_win_while_fabricating() -> None:
    """The proof Ruling 2 asks for.

    ``fluent`` leads *every* weighted line — F1, citations, structure — and leads the composite outright. It
    is refused solely because a rival is materially better on the fabrication line. If trap_avoidance were a
    weight instead, this candidate would win: it is ahead on 3 of 3 composited metrics.
    """
    config = _veto_config(weights={"surface_f1": 3.0, "citation_faithfulness": 4.5,
                                   "structured_output_reliability": 3.0})
    fluent = _score("fluent", {
        "surface_f1": _series("surface_f1", (0.90, 0.901, 0.899)),
        "citation_faithfulness": _series("citation_faithfulness", (0.95, 0.951, 0.949)),
        "structured_output_reliability": _series("structured_output_reliability", (1.0, 1.0, 1.0)),
        TRAP: _series(TRAP, (0.30, 0.31, 0.29)),
    })
    honest = _score("honest", {
        "surface_f1": _series("surface_f1", (0.70, 0.701, 0.699)),
        "citation_faithfulness": _series("citation_faithfulness", (0.80, 0.801, 0.799)),
        "structured_output_reliability": _series("structured_output_reliability", (0.90, 0.90, 0.90)),
        TRAP: _series(TRAP, (1.0, 1.0, 1.0)),
    })

    series, used, _ = composite_series([fluent, honest], config)
    assert TRAP not in used, "the fabrication line must not be inside the composite it is vetoing"
    assert series["fluent"].mean > series["honest"].mean, "the premise: the fabricator leads on score"

    verdict, _ = decide([fluent, honest], config)
    assert verdict.winner is None
    assert verdict.kind == "NON_NEGOTIABLE_REGRESSION"
    assert TRAP in verdict.statement


def test_the_veto_does_not_fire_on_a_within_noise_trap_difference() -> None:
    """Anti-vacuity. A veto that always fires moves the decision off the scorecard entirely, and the margin
    rule is what keeps it honest: only a difference already established as real may veto."""
    config = _veto_config(weights={"surface_f1": 3.0})
    ahead = _score("ahead", {"surface_f1": _series("surface_f1", (0.90, 0.901, 0.899)),
                             TRAP: _series(TRAP, (0.900, 0.901, 0.899))})
    behind = _score("behind", {"surface_f1": _series("surface_f1", (0.50, 0.501, 0.499)),
                               TRAP: _series(TRAP, (0.905, 0.906, 0.904))})
    verdict, _ = decide([ahead, behind], config)
    assert verdict.kind == "WINNER" and verdict.winner == "ahead", verdict.statement


def test_a_clean_leader_still_wins_so_the_veto_is_not_a_blanket_refusal() -> None:
    config = _veto_config(weights={"surface_f1": 3.0})
    clean = _score("clean", {"surface_f1": _series("surface_f1", (0.90, 0.901, 0.899)),
                             TRAP: _series(TRAP, (1.0, 1.0, 1.0))})
    sloppy = _score("sloppy", {"surface_f1": _series("surface_f1", (0.50, 0.501, 0.499)),
                               TRAP: _series(TRAP, (0.40, 0.41, 0.39))})
    verdict, _ = decide([clean, sloppy], config)
    assert verdict.kind == "WINNER" and verdict.winner == "clean", verdict.statement


# ── the other half: unmeasured is not a pass ──────────────────────────────────────────────────────

def test_an_unmeasured_fabrication_line_blocks_at_the_gate() -> None:
    """The loophole the relative veto cannot close on its own: with nothing to compare, ``compare_pair``
    returns NOT_RANKABLE and no veto fires. So the *gate* requires the metric to have been measured."""
    cand, cfg = bakeoff_config().candidates[0], _veto_config()
    unmeasured = {TRAP: MetricValue.unavailable(TRAP, "no negative-gold overlap")}
    report = evaluate_gates(cand, cfg, imagery=ImageryObservations(1, 1, ("probe",)),
                            non_negotiable_metrics=unmeasured, require_key=False)
    assert not report.eligible
    assert [g.name for g in report.blocking] == [f"non-negotiable:{TRAP}"]

    measured = {TRAP: MetricValue.measured(TRAP, 0.0)}
    fabricating = evaluate_gates(cand, cfg, imagery=ImageryObservations(1, 1, ("probe",)),
                                 non_negotiable_metrics=measured, require_key=False)
    # A measured zero passes the GATE (no absolute floor is configured — nobody has justified one); it is
    # the relative veto that stops it winning against a cleaner rival.
    assert fabricating.eligible


def test_a_gate_blocked_fabricator_cannot_be_selected_by_score() -> None:
    """End of the chain: gates dominate, so an unmeasured non-negotiable removes the candidate from winner
    consideration before any score is compared."""
    config = _veto_config(weights={"surface_f1": 3.0})
    blocked = _score("blocked", {"surface_f1": _series("surface_f1", (0.99, 0.99, 0.99))},
                     gates_pass=False)
    plain = _score("plain", {"surface_f1": _series("surface_f1", (0.50, 0.501, 0.499))})
    verdict, _ = decide([blocked, plain], config)
    assert verdict.winner is None
    assert verdict.kind == "SOLE_ELIGIBLE_CANDIDATE"
    assert "blocked" in verdict.disqualified
