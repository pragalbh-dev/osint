"""RK-BAKEOFF — the extractor-model bake-off harness (plan §8).

A **measuring instrument**, not a leaderboard. It exists to settle which model re-extracts and re-freezes
the graded oracle, so a scorer that cannot discriminate honestly hands that job to the wrong model
permanently. Two disciplines are therefore built into the types rather than left to the operator:

1. **Gating preconditions are pass/fail to win, never weighted** (:mod:`gates`). A candidate that would
   drop the locked VLM imagery path, that cannot be the producer freezing the seed bundles, or that names
   a floating ``-latest`` model id is *disqualified* — no score buys past it.
2. **Measurement discipline** (:mod:`compare`). N repeated runs per candidate, variance reported, and a
   minimum margin before a difference is called material. A gap inside the noise is reported as
   "NO MEASURED DIFFERENCE" and the ``Verdict`` type refuses, in its constructor, to name a winner in any
   other case.

Module map::

    policy.py     the declared knobs (config/bakeoff.yaml): replication, margin, weights, match policy
    gpt_client.py the OpenAI ExtractionClient — text + PDF-page multimodal + standalone VLM imagery
    recording.py  the instrumented client wrapper: raw payloads, latency, usage, call reliability
    surface.py    the comparison unit — a claim reduced to what is comparable across extractors
    gold.py       loaders + declared schemas for the labeled claim gold and the per-slice sub-oracle
    matcher.py    the alignment rule (its leniency IS the measurement) → precision / recall / F1
    metrics.py    every scored line; MetricValue makes "unavailable" un-fakeable as a number
    scorecard.py  per-run scores and their aggregation into series with mean / sd / rankability
    compare.py    the minimum-margin rule, tiering, the composite, and the Verdict invariant
    gates.py      the pass/fail preconditions
    runner.py     N runs per candidate → bundles → rebuild → comparative scorecard
    render.py     markdown + JSON output, gates printed above every score
"""

from __future__ import annotations

from .compare import NO_DIFFERENCE_PHRASE, Verdict, compare_metric, decide
from .gates import GateReport, GateResult, evaluate_gates
from .gold import load_claim_gold, load_sub_oracle
from .gpt_client import OpenAIExtractionClient
from .matcher import MatchResult, match_claims
from .metrics import AWAITING_S3, MetricValue
from .policy import BakeoffConfig, Candidate, MatchPolicy, load_bakeoff_config
from .recording import RecordingExtractionClient
from .render import render_markdown, to_json
from .runner import BakeoffInputs, BakeoffResult, preflight, run_bakeoff
from .scorecard import CandidateScore, MetricSeries, RunScore
from .surface import SurfaceClaim, from_claim_record

__all__ = [
    "AWAITING_S3",
    "NO_DIFFERENCE_PHRASE",
    "BakeoffConfig",
    "BakeoffInputs",
    "BakeoffResult",
    "Candidate",
    "CandidateScore",
    "GateReport",
    "GateResult",
    "MatchPolicy",
    "MatchResult",
    "MetricSeries",
    "MetricValue",
    "OpenAIExtractionClient",
    "RecordingExtractionClient",
    "RunScore",
    "SurfaceClaim",
    "Verdict",
    "compare_metric",
    "decide",
    "evaluate_gates",
    "from_claim_record",
    "load_bakeoff_config",
    "load_claim_gold",
    "load_sub_oracle",
    "match_claims",
    "preflight",
    "render_markdown",
    "run_bakeoff",
    "to_json",
]
