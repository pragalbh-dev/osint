"""RK-BAKEOFF gate 6 — **no winner while a required metric is UNMEASURABLE; say "unmeasured", never zero.**

Plan §8 makes this concrete and unavoidable, because the bake-off is deliberately split in two:

    "**Wave-0 substrate-INDEPENDENT screen** (before any code): surface-claim P/R/F1, citation
    faithfulness, extract-only-stated discipline, structured-output reliability, cost/latency, and the VLM
    gate … **Definitive pass** (after RK-ATOMS for discriminator capture; after RK-COREF for coref
    binding): **the two top-weighted criteria**, measured against the real extractor contract."

So the two *highest-weighted* criteria — coref-binding quality and discriminator capture — are literally
unmeasurable until those stages merge. That is the whole hazard: a Wave-0 scorecard that renders a winner
looks finished. It has measured the low-weight half of the criteria and is silent about the half that was
supposed to decide. Nobody re-runs a bake-off that already has a verdict.

Three distinct wrongs, in increasing subtlety:

* **Zeroing.** An unmeasured metric scored 0.0 is a *claim* — that the model scored nothing — and it is
  false. Worse, it is uniform across candidates, so it silently reweights the decision onto whatever
  happened to be measurable.
* **Omitting.** A metric quietly dropped from the row leaves no trace that it was ever required. The
  scorecard then looks complete, which is the same lie told more cleanly.
* **Deciding anyway.** Even correctly labelled "unmeasured", naming a winner asserts the unmeasured
  criteria could not have changed the outcome — which is exactly what has not been established. This is
  the project's own "insufficient evidence to assess" rule turned on the harness itself: name what is
  missing and when it can be measured, do not fill the hole with the numbers you happen to have.
"""

from __future__ import annotations

from tests.bakeoff._bakeoff_contract_spec import (
    REQUIRED_METRICS,
    candidate,
    do_scorecard,
    ref_scorecard,
    row_metric,
    stat_measured,
    stat_runs,
    why,
)

MIN_MARGIN = 0.03

# The definitive-pass criteria: unmeasurable until RK-COREF / RK-ATOMS merge.
PENDING = ("coref_binding", "discriminator_capture")
REQUIRED = (*REQUIRED_METRICS, *PENDING)


def _cand(name: str, f1: list[float], *, model_id: str) -> dict:
    n = len(f1)
    return candidate(name, model_id=model_id, runs={
        "claim_f1": list(f1),
        "citation_faithfulness": [1.0] * n,
        "fabrication_rate": [0.0] * n,
        "coref_binding": None,          # awaiting RK-COREF
        "discriminator_capture": None,  # awaiting RK-ATOMS
    })


AHEAD = _cand("ahead", [0.899, 0.900, 0.901], model_id="ahead-1.0")
BEHIND = _cand("behind", [0.549, 0.550, 0.551], model_id="behind-1.0")


def _sc():
    return do_scorecard([AHEAD, BEHIND], min_margin=MIN_MARGIN, required_metrics=REQUIRED)


# ── the gate ──────────────────────────────────────────────────────────────────────────────────────

def test_unmeasured_required_metric_blocks_a_winner():
    sc = _sc()
    assert sc.winner is None, why(
        f"WINNER-ON-PARTIAL-EVIDENCE: the harness named {sc.winner!r} while coref_binding and "
        "discriminator_capture — plan §8's two TOP-WEIGHTED criteria — are unmeasurable until RK-COREF "
        "and RK-ATOMS merge. Deciding now asserts the missing half could not have changed the outcome, "
        "which is precisely what has not been established. And a scorecard that already has a verdict "
        "does not get re-run after those stages land."
    )


def test_the_reason_is_named():
    sc = _sc()
    text = sc.text()
    assert "unmeasured" in text or "not measured" in text or "unmeasurable" in text, why(
        "UNMEASURED-UNNAMED: the scorecard withheld a verdict without saying that a required metric "
        "could not be measured. This system's one rule is that a gap is named — what is missing and when "
        f"next coverage is due — not left as an absence. Verdict text was: {text[:400]!r}"
    )
    assert any(m in text for m in PENDING), why(
        f"UNMEASURED-UNIDENTIFIED: the scorecard says something is missing but not *which* criterion. "
        f"Expected one of {PENDING} to be named so the reader knows the bake-off is pending RK-COREF / "
        f"RK-ATOMS rather than pending a bug. Verdict text was: {text[:400]!r}"
    )


def test_unmeasured_metric_is_present_in_the_row_not_omitted():
    sc = _sc()
    for metric in PENDING:
        stat = row_metric(sc.row("ahead"), metric)
        assert stat is not None, why(
            f"UNMEASURED-OMITTED [{metric}]: the metric is absent from the candidate's row entirely. A "
            "required criterion that vanishes leaves a scorecard that looks complete — the same lie as "
            "zeroing it, told more cleanly. It must appear, marked unmeasured."
        )


def test_unmeasured_metric_is_not_scored_as_zero():
    sc = _sc()
    for metric in PENDING:
        stat = row_metric(sc.row("ahead"), metric)
        measured = stat_measured(stat)
        runs = stat_runs(stat)
        looks_like_zero = (
            stat == 0 or stat == 0.0
            or (runs is not None and list(runs) == [0.0])
            or (measured is None and isinstance(stat, int | float) and float(stat) == 0.0)
        )
        assert not looks_like_zero, why(
            f"UNMEASURED-ZEROED [{metric}]: an unmeasurable criterion is carried as 0.0. That is not a "
            "missing value, it is a false claim — that the model scored nothing — and because it is "
            "identical across candidates it silently shifts the whole decision onto whichever criteria "
            "happened to be measurable in Wave-0."
        )
        assert measured is not True, why(
            f"UNMEASURED-MISLABELLED [{metric}]: the row marks an unmeasurable criterion as measured. "
            "A reader auditing the scorecard has no way left to tell a real score from a placeholder."
        )


def test_measuring_the_pending_metrics_unblocks_the_verdict():
    """Anti-vacuity: the block must lift once the definitive pass can actually run."""
    ahead = candidate("ahead", model_id="ahead-1.0", runs={
        "claim_f1": [0.899, 0.900, 0.901], "citation_faithfulness": [1.0] * 3,
        "fabrication_rate": [0.0] * 3,
        "coref_binding": [0.90, 0.901, 0.899], "discriminator_capture": [0.88, 0.881, 0.879],
    })
    behind = candidate("behind", model_id="behind-1.0", runs={
        "claim_f1": [0.549, 0.550, 0.551], "citation_faithfulness": [1.0] * 3,
        "fabrication_rate": [0.0] * 3,
        "coref_binding": [0.60, 0.601, 0.599], "discriminator_capture": [0.58, 0.581, 0.579],
    })
    sc = do_scorecard([ahead, behind], min_margin=MIN_MARGIN, required_metrics=REQUIRED)
    assert sc.winner == "ahead", why(
        f"UNMEASURED-BLOCK-STUCK: with every required criterion measured over 3 runs and a 35-point "
        f"material lead, the harness still returned winner={sc.winner!r}. A block that never lifts is "
        "not caution — it makes the definitive pass unable to conclude anything, so the primary would be "
        f"settled off-scorecard by whoever is in the room. Verdict was: {sc.text()[:400]!r}"
    )


# ── positive controls ─────────────────────────────────────────────────────────────────────────────

def test_positive_control_reference_withholds_and_names():
    sc = ref_scorecard([AHEAD, BEHIND], min_margin=MIN_MARGIN, required_metrics=REQUIRED)
    assert sc.winner is None
    assert "unmeasured" in sc.text()
    assert all(m in sc.text() for m in PENDING)
    for metric in PENDING:
        stat = row_metric(sc.row("ahead"), metric)
        assert stat_measured(stat) is False and stat_runs(stat) is None
