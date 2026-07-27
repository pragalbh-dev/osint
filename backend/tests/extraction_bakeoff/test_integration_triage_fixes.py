"""Regressions for the four defects found when the three blind hands' work was merged (RK-BAKEOFF triage).

Each test here pins a defect that was live on the merged branch and is now fixed. They are grouped in one
file because they share a provenance, not a module: all four are integration failures — things that could
only be seen once the impl, the spec gates and the labeled gold were in the same tree.

1. ``composite_series`` ignored ``MetricSeries.direction`` — a lower-is-better rate contributed
   *positively*, so the harness preferred the model that did the bad thing more often.
2. No relative veto on the non-negotiables — a big enough score lead could buy past a materially worse
   fabrication/citation record, which makes a "non-negotiable" a price.
3. No notion of a REQUIRED metric — a Wave-0 run could render a finished-looking winner while the two
   top-weighted criteria were unmeasurable.
4. The gold loader read the sentinel string ``"unknown"`` as a STATED discriminator, inverting both A7
   metrics at once.
"""

from __future__ import annotations

import json
from pathlib import Path

from eval.extraction.compare import COMPOSITE, composite_series, decide
from eval.extraction.gold import load_claim_gold

from .fixtures import bakeoff_config
from .test_compare import _score, _series

# ── 1. the composite must respect metric direction ────────────────────────────────────────────────

def test_composite_inverts_a_lower_is_better_metric():
    """A rate of *doing the bad thing* must lower the composite, not raise it.

    Before the fix, with fabrication weighted 4.5 against F1's 3.0, a model fabricating 40% of the time
    scored a composite of 0.56 against a clean model's 0.32 — the harness actively selected for the one
    behaviour this project calls disqualifying, while every per-metric line still read correctly.
    """
    config = bakeoff_config(weights={"surface_f1": 3.0, "fabrication_rate": 4.5})
    clean = _score("clean", {
        "surface_f1": _series("surface_f1", (0.80, 0.801, 0.799)),
        "fabrication_rate": _series("fabrication_rate", (0.0, 0.0, 0.0), direction="lower_is_better"),
    })
    inventor = _score("inventor", {
        "surface_f1": _series("surface_f1", (0.80, 0.801, 0.799)),
        "fabrication_rate": _series("fabrication_rate", (0.40, 0.41, 0.39), direction="lower_is_better"),
    })

    series, used, _ = composite_series([clean, inventor], config)
    assert "fabrication_rate" in used, "the metric must actually be in the composite for this to mean anything"
    assert series["clean"].mean > series["inventor"].mean, (
        f"the fabricating candidate scored {series['inventor'].mean} against the clean candidate's "
        f"{series['clean'].mean} — the composite is still treating lower-is-better as higher-is-better"
    )

    verdict, _ = decide([clean, inventor], config)
    assert verdict.winner != "inventor"


def test_composite_refuses_a_metric_whose_direction_is_ambiguous():
    """If two candidates disagree on a metric's polarity, it is excluded rather than guessed."""
    config = bakeoff_config(weights={"surface_f1": 1.0, "odd": 1.0})
    a = _score("a", {"surface_f1": _series("surface_f1", (0.9, 0.9, 0.9)),
                     "odd": _series("odd", (0.5, 0.5, 0.5), direction="higher_is_better")})
    b = _score("b", {"surface_f1": _series("surface_f1", (0.5, 0.5, 0.5)),
                     "odd": _series("odd", (0.5, 0.5, 0.5), direction="lower_is_better")})
    _, used, excluded = composite_series([a, b], config)
    assert "odd" not in used
    assert "direction" in excluded["odd"]


# ── 2. the non-negotiables are vetoes, not weights ────────────────────────────────────────────────

def _non_negotiable_config(**kw):
    gates = {"floating_alias_patterns": ["-latest"],
             "production_client_package": "chanakya.ingest",
             "non_negotiable_floors": {"citation_faithfulness": None}}
    return bakeoff_config(gates=gates, **kw)


def test_a_score_lead_cannot_buy_past_a_worse_citation_record():
    """A non-negotiable that can be outweighed is a price, not a non-negotiable.

    The winner here leads the composite outright; it is refused because a rival is *materially* better on
    citation faithfulness. "Materially" reuses the same margin rule, so a within-noise difference cannot
    veto — no new threshold is invented to make this work.
    """
    config = _non_negotiable_config(weights={"surface_f1": 5.0, "citation_faithfulness": 1.0})
    fluent = _score("fluent", {
        "surface_f1": _series("surface_f1", (0.90, 0.901, 0.899)),
        "citation_faithfulness": _series("citation_faithfulness", (0.70, 0.71, 0.69)),
    })
    honest = _score("honest", {
        "surface_f1": _series("surface_f1", (0.80, 0.801, 0.799)),
        "citation_faithfulness": _series("citation_faithfulness", (1.0, 1.0, 1.0)),
    })
    verdict, _ = decide([fluent, honest], config)
    assert verdict.winner is None
    assert verdict.kind == "NON_NEGOTIABLE_REGRESSION"
    assert "citation_faithfulness" in verdict.statement


def test_the_veto_does_not_fire_on_a_within_noise_difference():
    """Anti-vacuity: a veto that always fires would push the decision off-scorecard entirely."""
    config = _non_negotiable_config(weights={"surface_f1": 5.0, "citation_faithfulness": 1.0})
    ahead = _score("ahead", {
        "surface_f1": _series("surface_f1", (0.90, 0.901, 0.899)),
        "citation_faithfulness": _series("citation_faithfulness", (0.980, 0.981, 0.979)),
    })
    behind = _score("behind", {
        "surface_f1": _series("surface_f1", (0.50, 0.501, 0.499)),
        "citation_faithfulness": _series("citation_faithfulness", (0.985, 0.986, 0.984)),
    })
    verdict, _ = decide([ahead, behind], config)
    assert verdict.kind == "WINNER" and verdict.winner == "ahead", verdict.statement


# ── 3. a REQUIRED metric blocks the verdict; a merely weighted one does not ────────────────────────

def test_an_unmeasured_required_metric_blocks_the_winner_and_names_itself():
    config = bakeoff_config(weights={"surface_f1": 1.0}, required_metrics=["coref_binding"])
    pending = _series("coref_binding", (), n_runs=3)
    pending = pending.__class__(name="coref_binding", unit="rate", direction="higher_is_better",
                                values=(), n_runs=3, status="unavailable",
                                reasons=("AWAITING S3 (RK-COREF)",), min_runs_for_ranking=3)
    ahead = _score("ahead", {"surface_f1": _series("surface_f1", (0.90, 0.901, 0.899)),
                             "coref_binding": pending})
    behind = _score("behind", {"surface_f1": _series("surface_f1", (0.55, 0.551, 0.549)),
                               "coref_binding": pending})
    verdict, _ = decide([ahead, behind], config)
    assert verdict.winner is None
    assert verdict.kind == "INSUFFICIENT_CRITERIA"
    assert "coref_binding" in verdict.statement
    assert "UNMEASURED" in verdict.statement


def test_the_block_lifts_once_the_required_metric_is_measured():
    """A caution rule that never lifts is as bad as one that never fires: the call just moves off-record."""
    config = bakeoff_config(weights={"surface_f1": 1.0}, required_metrics=["coref_binding"])
    ahead = _score("ahead", {"surface_f1": _series("surface_f1", (0.90, 0.901, 0.899)),
                             "coref_binding": _series("coref_binding", (0.90, 0.90, 0.90))})
    behind = _score("behind", {"surface_f1": _series("surface_f1", (0.55, 0.551, 0.549)),
                               "coref_binding": _series("coref_binding", (0.55, 0.55, 0.55))})
    verdict, _ = decide([ahead, behind], config)
    assert verdict.kind == "WINNER" and verdict.winner == "ahead", verdict.statement


def test_a_weighted_but_not_required_metric_is_excluded_not_blocking():
    """The distinction is the whole point: weight ⇒ exclude-and-name; required ⇒ refuse to rank."""
    config = bakeoff_config(weights={"surface_f1": 1.0, "coref_binding": 5.0}, required_metrics=[])
    pending = _series("coref_binding", (), n_runs=3).__class__(
        name="coref_binding", unit="rate", direction="higher_is_better", values=(), n_runs=3,
        status="unavailable", reasons=("AWAITING S3",), min_runs_for_ranking=3)
    ahead = _score("ahead", {"surface_f1": _series("surface_f1", (0.90, 0.901, 0.899)),
                             "coref_binding": pending})
    behind = _score("behind", {"surface_f1": _series("surface_f1", (0.55, 0.551, 0.549)),
                               "coref_binding": pending})
    verdict, comparison = decide([ahead, behind], config)
    assert verdict.kind == "WINNER"
    assert "coref_binding" in verdict.composite_exclusions
    assert comparison is not None and comparison.metric == COMPOSITE


# ── 4. the gold loader must read "unknown" as NOT STATED ──────────────────────────────────────────

def _gold_file(tmp_path: Path, discriminators: dict) -> Path:
    p = tmp_path / "gold.json"
    p.write_text(json.dumps({
        "schema_version": "rk-bakeoff-claim-gold/1.0",
        "claims": [{
            "gold_id": "g1", "source_id": "doc1", "form": "entity", "name": "North Ridge Foundry",
            "entity_type": "manufacturer", "doc_ref": {"file": "doc1.txt", "span": [0, 19]},
            "discriminators": discriminators,
        }],
    }), encoding="utf-8")
    return p


def test_unknown_sentinel_is_read_as_not_stated(tmp_path):
    """"unknown" is the labeled slice's way of writing null; reading it as a value inverts both A7 metrics.

    Left unfixed, ``discriminator_capture``'s denominator swells to every slot of every row (a perfect
    model scores ~0.30) and ``discriminator_fabrication_avoidance`` loses its denominator entirely — and a
    model that literally emits the word "unknown" outscores one that correctly abstains.
    """
    claims = load_claim_gold(_gold_file(tmp_path, {
        "operator": "the PAF", "geography": "unknown", "designation": "  UNKNOWN  ", "time": None,
    }))
    assert claims[0].discriminators == {
        "operator": "the PAF", "geography": None, "designation": None, "time": None,
    }


def test_a_real_discriminator_value_is_still_preserved(tmp_path):
    """Anti-vacuity: the sentinel rule must not swallow genuine values."""
    claims = load_claim_gold(_gold_file(tmp_path, {
        "operator": "Pakistan Army Air Defence", "geography": "Rahwali",
        "designation": "8 AD Bn", "time": "2025-06-11",
    }))
    assert all(v is not None for v in claims[0].discriminators.values())
