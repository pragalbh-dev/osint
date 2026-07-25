"""The orchestration: N repeated extractions per candidate → a bundle per run → a rebuild → a scorecard.

The loop itself is small; the discipline around it is the point.

* **N runs, always.** ``replication.runs_per_candidate`` extractions per candidate, each recorded to its
  own bundle directory, each rebuilt and scored independently. One run is a sample; the spread across
  runs is what the margin rule subtracts before calling any gap real.
* **Every run leaves an artefact.** ``<out_dir>/<candidate>/run-NN/<source_id>.json``, byte-stable, so
  any figure on the scorecard can be traced back to the claims that produced it and a disputed run can be
  re-scored without re-spending the API call.
* **Real code, real path.** Each run drives ``chanakya.ingest.lane.extract_many`` and
  ``chanakya.view.rebuild`` — the shipped extraction and rebuild, not a scorer-local imitation. A
  bake-off measured on a parallel implementation would measure the imitation.
* **No network in tests.** The client is injected. Pass a factory returning ``ScriptedExtractionClient``
  and the whole orchestrator runs offline; the default factory builds live clients and is never reached
  from a test.
* **Unexercisable candidates are recorded, not dropped.** A missing key or a missing SDK produces a
  candidate row saying so. If only one candidate can run, the verdict says "the incumbent stays by
  default" rather than implying a comparison happened.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from chanakya.ingest.lane import DocInput, extract_many
from chanakya.schemas import ClaimRecord, ConfigBundle, GraphView
from chanakya.store import EvidenceLog
from chanakya.view import rebuild

from . import metrics as M
from .compare import MetricComparison, Verdict, composite_series, decide, per_metric_comparisons
from .gates import GateReport, evaluate_gates
from .gold import SubOracle, load_claim_gold, load_sub_oracle
from .matcher import match_claims
from .policy import BakeoffConfig, Candidate
from .recording import RecordingExtractionClient
from .scorecard import CandidateScore, RunScore, aggregate_runs, unexercised
from .surface import SurfaceClaim, from_claim_record

#: ``(candidate, run_index) -> client``. Returning ``None`` marks the candidate unexercisable.
ClientFactory = Callable[[Candidate, int], Any | None]


@dataclass(frozen=True)
class BakeoffInputs:
    """Everything the bake-off reads. The two labeled files are **paths**, never opened by the scorer's
    author: a matcher tuned by someone who has read the answers measures the tuning, not the models."""

    docs: Sequence[DocInput]
    config: ConfigBundle
    gold_path: Path
    sub_oracle_path: Path
    out_dir: Path
    #: Optional ``file -> text`` overrides for documents whose ``raw`` is not plain text (PDFs). Files
    #: absent from both this map and ``docs`` are simply not gradable for grounding, and say so.
    doc_texts: Mapping[str, str] = field(default_factory=dict)
    concurrency: int = 8

    def texts(self) -> dict[str, str]:
        texts = {doc.file: doc.raw for doc in self.docs if isinstance(doc.raw, str)}
        texts.update(self.doc_texts)
        return texts


@dataclass(frozen=True)
class BakeoffResult:
    """The whole bake-off: per-candidate scores, per-metric comparisons, and the verdict."""

    scores: list[CandidateScore]
    verdict: Verdict
    comparisons: dict[str, MetricComparison]
    composite: MetricComparison | None
    config: BakeoffConfig


# ── the live client factory (never called from a test) ────────────────────────────────────────────

def live_client_factory(candidate: Candidate, run_index: int) -> Any | None:
    """Build the declared client for a candidate, or ``None`` when it cannot be exercised here.

    Resolves ``client_module``/``client_class`` by import, so adding a candidate stays a config edit plus
    one client class. The pinned ``model_id`` from config is passed through and ends up stamped on every
    claim's ``Extraction.version``.
    """
    del run_index  # the same client serves every run; runs differ only by the model's own variance
    if not os.environ.get(candidate.key_env):
        return None
    try:
        module = importlib.import_module(candidate.client_module)
        cls = getattr(module, candidate.client_class)
    except Exception:
        return None
    return cls(model_id=candidate.model_id)


# ── one run ───────────────────────────────────────────────────────────────────────────────────────

def write_bundles(claims_per_doc: Sequence[list[ClaimRecord]], docs: Sequence[DocInput],
                  run_dir: Path) -> list[Path]:
    """Write one byte-stable bundle per document (same shape ``ingest.seed`` freezes)."""
    run_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for doc, claims in zip(docs, claims_per_doc, strict=True):
        path = run_dir / f"{doc.source_id}.json"
        rows = [c.model_dump(mode="json") for c in claims]
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
        written.append(path)
    return written


def rebuild_from_claims(claims: Sequence[ClaimRecord], config: ConfigBundle) -> GraphView:
    """Append this run's claims to a fresh in-memory log and reduce them with the shipped ``rebuild()``."""
    log = EvidenceLog(":memory:")
    log.append_many(list(claims))
    return rebuild(log, [], config)


def score_run(
    *,
    candidate: Candidate,
    run_index: int,
    claims: Sequence[ClaimRecord],
    raw_payloads: Sequence[Mapping[str, Any]],
    recorder: RecordingExtractionClient,
    gold: Sequence[SurfaceClaim],
    oracle: SubOracle,
    doc_texts: Mapping[str, str],
    config: BakeoffConfig,
    view: GraphView,
) -> RunScore:
    """Every metric for one run. Pure given its inputs — no I/O, no clock, no network."""
    surfaces = [from_claim_record(c) for c in claims]
    match = match_claims(list(gold), surfaces, config.match_policy)

    values: dict[str, M.MetricValue] = {}
    values.update(M.surface_metrics(match))
    values["citation_faithfulness"] = M.citation_faithfulness(surfaces, doc_texts, config.match_policy)
    values["extract_only_stated"] = M.extract_only_stated(surfaces, doc_texts, config.match_policy)
    values["structured_output_reliability"] = M.structured_output_reliability(recorder.calls)
    values.update(M.discriminator_metrics(
        M.tally_discriminators(raw_payloads, gold, config.match_policy)))
    values["coref_binding"] = M.coref_binding(match)
    values["kind_tagging"] = M.kind_tagging(match)
    values.update(M.graph_recall(view, oracle, config.match_policy))
    values["latency_s"] = M.latency_metric(recorder.total_latency_s(), len(recorder.calls))
    values["cost_usd"] = M.cost_metric(recorder.total_usage(), candidate.pricing)

    image_calls = recorder.image_calls()
    return RunScore(
        candidate_id=candidate.id,
        run_index=run_index,
        metrics=values,
        claims=tuple(surfaces),
        image_calls_ok=sum(1 for c in image_calls if c.ok),
        image_calls_total=len(image_calls),
    )


def run_candidate(
    candidate: Candidate,
    inputs: BakeoffInputs,
    config: BakeoffConfig,
    client_factory: ClientFactory,
    *,
    gold: Sequence[SurfaceClaim],
    oracle: SubOracle,
    require_key: bool = True,
) -> CandidateScore:
    """Run one candidate N times, score each run, and fold them into a :class:`CandidateScore`."""
    doc_texts = inputs.texts()
    runs: list[RunScore] = []
    image_ok = image_total = 0

    for run_index in range(1, config.replication.runs_per_candidate + 1):
        client = client_factory(candidate, run_index)
        if client is None:
            gates = evaluate_gates(candidate, config, image_calls_ok=0, image_calls_total=0,
                                   require_key=require_key)
            return unexercised(
                candidate.id, candidate.label, candidate.model_id, gates,
                f"no client could be built (key env {candidate.key_env}, client "
                f"{candidate.client_module}.{candidate.client_class}) — this candidate was NOT measured",
            )
        recorder = RecordingExtractionClient(client)
        claims_per_doc = asyncio.run(extract_many(
            inputs.docs, concurrency=inputs.concurrency, client=recorder, config=inputs.config))
        write_bundles(claims_per_doc, inputs.docs,
                      inputs.out_dir / candidate.id / f"run-{run_index:02d}")

        flat = [c for chunk in claims_per_doc for c in chunk]
        view = rebuild_from_claims(flat, inputs.config)
        payloads = [c.payload for c in recorder.calls if c.ok and c.payload is not None]
        runs.append(score_run(
            candidate=candidate, run_index=run_index, claims=flat, raw_payloads=payloads,
            recorder=recorder, gold=gold, oracle=oracle, doc_texts=doc_texts, config=config, view=view,
        ))
        image_ok += runs[-1].image_calls_ok
        image_total += runs[-1].image_calls_total

    gates = _gates_for(candidate, config, runs, image_ok, image_total, require_key)
    return aggregate_runs(candidate.id, candidate.label, candidate.model_id, gates, runs,
                          config.replication)


def _gates_for(candidate: Candidate, config: BakeoffConfig, runs: Sequence[RunScore],
               image_ok: int, image_total: int, require_key: bool) -> GateReport:
    """Gates, with the optional non-negotiable floors judged on the mean over the runs."""
    floors: dict[str, M.MetricValue] = {}
    for name in (config.gates.non_negotiable_floors or {}):
        vals = [
            r.metrics[name].value for r in runs
            if name in r.metrics and r.metrics[name].status == "measured"
            and r.metrics[name].value is not None
        ]
        if vals:
            mean = sum(float(v) for v in vals if v is not None) / len(vals)
            floors[name] = M.MetricValue.measured(name, mean, detail={"runs": len(vals)})
        else:
            floors[name] = M.MetricValue.unavailable(name, "not measured in any run")
    return evaluate_gates(candidate, config, image_calls_ok=image_ok, image_calls_total=image_total,
                          non_negotiable_metrics=floors, require_key=require_key)


# ── the whole bake-off ────────────────────────────────────────────────────────────────────────────

def run_bakeoff(
    inputs: BakeoffInputs,
    config: BakeoffConfig,
    client_factory: ClientFactory = live_client_factory,
    *,
    candidates: Sequence[str] | None = None,
    require_key: bool = True,
) -> BakeoffResult:
    """Run every declared candidate N times and produce the comparative verdict.

    ``candidates`` optionally restricts the run to some ids — but note that a *narrowed* bake-off is
    still reported as what it is: candidates that were not run appear nowhere, and if only one candidate
    survives the gates the verdict is ``SOLE_ELIGIBLE_CANDIDATE``, never ``WINNER``.
    """
    gold = load_claim_gold(inputs.gold_path)
    oracle = load_sub_oracle(inputs.sub_oracle_path)

    wanted = set(candidates) if candidates else None
    scores = [
        run_candidate(cand, inputs, config, client_factory, gold=gold, oracle=oracle,
                      require_key=require_key)
        for cand in config.candidates
        if wanted is None or cand.id in wanted
    ]

    verdict, composite = decide(scores, config)
    comparisons = per_metric_comparisons(scores, config)
    return BakeoffResult(scores=scores, verdict=verdict, comparisons=comparisons, composite=composite,
                         config=config)


def preflight(config: BakeoffConfig, *, require_key: bool = True) -> list[GateReport]:
    """Evaluate every gate that can be judged **without spending a single API call**.

    The VLM gate necessarily comes back UNKNOWN here (nothing was exercised), which is the honest answer:
    a gate nobody ran is not a gate anybody passed. Everything else — pinned id, production client path,
    SDK import, key presence — is checkable dry, and checking it first is how a bake-off avoids paying
    for runs on a candidate that is already disqualified.
    """
    return [
        evaluate_gates(cand, config, image_calls_ok=0, image_calls_total=0, require_key=require_key)
        for cand in config.candidates
    ]


__all__ = [
    "BakeoffInputs",
    "BakeoffResult",
    "ClientFactory",
    "composite_series",
    "live_client_factory",
    "preflight",
    "rebuild_from_claims",
    "run_bakeoff",
    "run_candidate",
    "score_run",
    "write_bundles",
]
