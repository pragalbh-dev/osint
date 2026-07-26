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
    recording.py  the instrumented client wrapper: raw payloads, latency, usage, call reliability
    surface.py    the comparison unit — a claim reduced to what is comparable across extractors
    gold.py       loaders + declared schemas for the labeled claim gold and the per-slice sub-oracle
    negative_gold.py  the gold's typed NEGATIVE rows: precision exclusions + the fabrication line
    matcher.py    the alignment rule (its leniency IS the measurement) → precision / recall / F1
    metrics.py    every scored line; MetricValue makes "unavailable" un-fakeable as a number
    scorecard.py  per-run scores and their aggregation into series with mean / sd / rankability
    compare.py    the minimum-margin rule, tiering, the composite, and the Verdict invariant
    gates.py      the pass/fail preconditions
    runner.py     N runs per candidate → bundles → rebuild → comparative scorecard
    secrets.py    .env key loading — names only; a value never leaves the module
    coref_channel.py  is there a model-facing coref output channel, and is it switched on?
    vlm_probe.py  the deliberate imagery experiment that turns the VLM gate from UNKNOWN into evidence
    render.py     markdown + JSON output, gates printed above every score

**No candidate's extraction client lives here, and that is a rule rather than an accident.** All three
sit beside each other in :mod:`chanakya.ingest.client`, on the shipped ingest path, because the
KEYLESS==LIVE gate asks whether the *same code* that freezes the seed bundles is the code the live system
runs. A client parked in this tree could be measured but could never be the seed producer, so its
candidate was structurally unable to win — the harness would have been running a two-horse race wearing
three declarations. This package measures models; it does not host them.
"""

from __future__ import annotations

from .compare import NO_DIFFERENCE_PHRASE, Verdict, compare_metric, decide
from .coref_channel import CorefChannel, CorefChannelDormant, with_channel_on
from .gates import GateReport, GateResult, ImageryObservations, dry_gates, evaluate_gates
from .gold import load_claim_gold, load_sub_oracle
from .matcher import MatchResult, match_claims
from .metrics import NO_CLUSTERING, MetricValue
from .negative_gold import NegativeGold, emitted_spans, load_negative_gold
from .policy import BakeoffConfig, Candidate, MatchPolicy, load_bakeoff_config
from .recording import RecordingExtractionClient
from .render import render_markdown, to_json
from .runner import BakeoffInputs, BakeoffResult, preflight, run_bakeoff
from .scorecard import CandidateScore, MetricSeries, RunScore
from .secrets import key_names_present, load_env_file
from .surface import SurfaceClaim, from_claim_record
from .vlm_probe import ImageryEvidence, gate_from_evidence, observations_for, probe_candidate

__all__ = [
    "NO_CLUSTERING",
    "NO_DIFFERENCE_PHRASE",
    "BakeoffConfig",
    "BakeoffInputs",
    "BakeoffResult",
    "Candidate",
    "CorefChannel",
    "CorefChannelDormant",
    "CandidateScore",
    "GateReport",
    "GateResult",
    "ImageryEvidence",
    "ImageryObservations",
    "MatchPolicy",
    "MatchResult",
    "MetricSeries",
    "MetricValue",
    "NegativeGold",
    "RecordingExtractionClient",
    "RunScore",
    "SurfaceClaim",
    "Verdict",
    "compare_metric",
    "decide",
    "dry_gates",
    "emitted_spans",
    "evaluate_gates",
    "from_claim_record",
    "gate_from_evidence",
    "key_names_present",
    "load_bakeoff_config",
    "load_env_file",
    "load_claim_gold",
    "load_negative_gold",
    "load_sub_oracle",
    "match_claims",
    "observations_for",
    "preflight",
    "probe_candidate",
    "render_markdown",
    "run_bakeoff",
    "to_json",
    "with_channel_on",
]
