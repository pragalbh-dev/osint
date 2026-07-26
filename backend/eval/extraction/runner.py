"""The orchestration: N repeated extractions per candidate → a bundle per run → a rebuild → a scorecard.

The loop itself is small; the discipline around it is the point.

* **N runs, always.** ``replication.runs_per_candidate`` extractions per candidate, each recorded to its
  own bundle directory, each rebuilt and scored independently. One run is a sample; the spread across
  runs is what the margin rule subtracts before calling any gap real.
* **Every DOCUMENT leaves an artefact, the moment it lands.**
  ``<out_dir>/<candidate>/run-NN/<source_id>.json`` (byte-stable claims) plus a ``_resume/`` sidecar
  carrying that document's call records — written by :class:`eval.extraction.resume.ResumeStore` as each
  document completes, not batched at the end of a run. So any figure on the scorecard traces back to the
  claims that produced it, a disputed run is re-scored without re-spending anything, and — the reason it
  is per-document — an exception partway through a run no longer discards the calls already bought.
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
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from chanakya.ingest.lane import DocInput, extract_many
from chanakya.schemas import ClaimRecord, ConfigBundle, GraphView
from chanakya.store import EvidenceLog
from chanakya.view import rebuild

from . import coref_channel
from . import metrics as M
from . import resume as R
from .compare import MetricComparison, Verdict, composite_series, decide, per_metric_comparisons
from .gates import GateReport, dry_gates, evaluate_gates
from .gold import CorefRegistry, SubOracle, load_claim_gold, load_coref_registry, load_sub_oracle
from .matcher import match_claims
from .negative_gold import NegativeGold, emitted_spans, load_negative_gold
from .policy import BakeoffConfig, Candidate
from .recording import RecordingExtractionClient
from .resilience import RetryingExtractionClient
from .scorecard import CandidateScore, RunScore, aggregate_runs, unexercised
from .surface import SurfaceClaim, from_claim_record
from .throttle import RequestPacer, ThrottledExtractionClient, virtual_pacer
from .vlm_probe import ImageryEvidence, observations_for, resolve_evidence

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

    The client is wrapped in :class:`~eval.extraction.resilience.RetryingExtractionClient`, which retries
    **transport faults only** — a call that never received an HTTP response. On 2026-07-26 a single
    corrupted TLS record ended a run after the first candidate had been paid for in full. A response the
    provider actually returned is never retried, whatever its status: that is the candidate's own
    behaviour, and ``structured_output_reliability`` exists to score it. A 429 is a returned response, so
    it is handled by *pacing* (:mod:`.throttle`) and never by re-issuing.

    The run is no longer un-resumable, which changes what a raised exception costs: every document already
    recorded stays on disk and a later invocation reuses it (:mod:`.resume`). Retry is still the first line
    — a rescued blip beats a resumed run — but it is no longer the only one.
    """
    del run_index  # the same client serves every run; runs differ only by the model's own variance
    if not os.environ.get(candidate.key_env):
        return None
    try:
        module = importlib.import_module(candidate.client_module)
        cls = getattr(module, candidate.client_class)
    except Exception:
        return None
    return RetryingExtractionClient(cls(model_id=candidate.model_id))


# ── one run ───────────────────────────────────────────────────────────────────────────────────────

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
    negative: NegativeGold,
    oracle: SubOracle,
    doc_texts: Mapping[str, str],
    config: BakeoffConfig,
    view: GraphView,
    coref_registry: CorefRegistry | None = None,
    provenance: R.RunProvenance | None = None,
    calls_bought: int = 0,
) -> RunScore:
    """Every metric for one run. Pure given its inputs — no I/O, no clock, no network.

    The negative gold is consumed **after** the alignment and **before** the surface metrics, because both
    things it produces depend on the matcher's verdict: an emission that paired with positive gold can
    neither hit a trap nor earn a precision exclusion. See :mod:`.negative_gold`.
    """
    surfaces = [from_claim_record(c) for c in claims]
    match = match_claims(list(gold), surfaces, config.match_policy)
    emitted = emitted_spans(surfaces, match, negative)
    match = match.with_precision_exclusions(negative.excluded_keys(emitted))

    values: dict[str, M.MetricValue] = {}
    values.update(M.surface_metrics(match, doc_texts, config.match_policy))
    values["trap_avoidance"] = M.trap_avoidance(negative, emitted)
    values["identity_over_read"] = M.identity_over_read(negative, emitted)
    values["citation_faithfulness"] = M.citation_faithfulness(surfaces, doc_texts, config.match_policy)
    values["extract_only_stated"] = M.extract_only_stated(surfaces, doc_texts, config.match_policy)
    values["structured_output_reliability"] = M.structured_output_reliability(recorder.calls)
    values.update(M.discriminator_metrics(
        M.tally_discriminators(raw_payloads, gold, config.match_policy)))
    values["coref_binding"] = M.coref_binding(match, coref_registry)
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
        calls_total=len(recorder.calls),
        calls_bought=calls_bought,
        provenance=provenance or R.RunProvenance(),
    )


def run_candidate(
    candidate: Candidate,
    inputs: BakeoffInputs,
    config: BakeoffConfig,
    client_factory: ClientFactory,
    *,
    gold: Sequence[SurfaceClaim],
    negative: NegativeGold,
    oracle: SubOracle,
    evidence: Mapping[str, ImageryEvidence],
    coref_registry: CorefRegistry | None = None,
    require_key: bool = True,
    store: R.ResumeStore,
    pacer: RequestPacer,
    producer: str = R.LIVE,
) -> CandidateScore:
    """Run one candidate N times, score each run, and fold them into a :class:`CandidateScore`.

    Two things happen here that did not before, and both exist because a live run of this is ~195 billed
    calls in one process:

    * **every document is looked up on disk before it is bought.** ``store`` holds what previous
      invocations paid for, keyed by candidate, run index and document and validated against a
      fingerprint over the pinned model id, the document set and the prompt/schema version. A hit costs
      nothing and is recorded as reused; a miss is bought and written the moment it lands.
    * **calls are paced per provider.** ``pacer`` is this candidate's own limiter, so a lane capped at 3
      requests a minute slows itself and nothing else — the other candidates are separate loops holding
      separate pacers.
    """
    doc_texts = inputs.texts()
    runs: list[RunScore] = []
    image_ok = image_total = 0
    fingerprint = R.fingerprint(model_id=candidate.model_id, docs=inputs.docs,
                                producer=producer)

    for run_index in range(1, config.replication.runs_per_candidate + 1):
        cached = {
            doc.source_id: store.load(candidate.id, run_index, doc.source_id, fingerprint)
            for doc in inputs.docs
        }
        missing = [doc for doc in inputs.docs if cached[doc.source_id] is None]

        bought_ids = {doc.source_id for doc in missing}
        if missing:
            client = client_factory(candidate, run_index)
            if client is None:
                imagery, _ = observations_for(candidate, evidence=evidence)
                gates = evaluate_gates(candidate, config, imagery=imagery, require_key=require_key)
                return unexercised(
                    candidate.id, candidate.label, candidate.model_id, gates,
                    f"no client could be built (key env {candidate.key_env}, client "
                    f"{candidate.client_module}.{candidate.client_class}) — this candidate was NOT measured",
                )
            fresh = asyncio.run(_extract_and_persist(
                missing, client=ThrottledExtractionClient(client, pacer), config=inputs.config,
                concurrency=inputs.concurrency, store=store, candidate_id=candidate.id,
                run_index=run_index, fingerprint=fingerprint,
            ))
            for source_id, doc_claims, doc_calls in fresh:
                cached[source_id] = R.CachedDoc(source_id=source_id, claims=doc_claims, calls=doc_calls,
                                                invocation=store.invocation, recorded_at="")

        # Reassemble in `docs` order, whatever mixture of disk and network produced it. Every slot must
        # be filled by now: a document is either cached or was just bought, and a failure to buy raised.
        ordered: list[R.CachedDoc] = []
        for doc in inputs.docs:
            entry = cached[doc.source_id]
            if entry is None:                                    # pragma: no cover - defensive
                raise RuntimeError(
                    f"document {doc.source_id!r} of {candidate.id} run {run_index} is neither cached nor "
                    "freshly extracted; refusing to score a run with a hole in it"
                )
            ordered.append(entry)
        flat = [claim for entry in ordered for claim in entry.claims]
        recorder = RecordingExtractionClient.replay(
            [call for entry in ordered for call in entry.calls])
        provenance = R.summarize(
            reused=[(doc.source_id, entry.invocation)
                    for doc, entry in zip(inputs.docs, ordered, strict=True)
                    if doc.source_id not in bought_ids],
            bought=sorted(bought_ids),
            current=store.invocation,
        )

        view = rebuild_from_claims(flat, inputs.config)
        payloads = [c.payload for c in recorder.calls if c.ok and c.payload is not None]
        runs.append(score_run(
            candidate=candidate, run_index=run_index, claims=flat, raw_payloads=payloads,
            recorder=recorder, gold=gold, negative=negative, oracle=oracle, doc_texts=doc_texts,
            config=config, view=view, coref_registry=coref_registry, provenance=provenance,
            calls_bought=sum(len(entry.calls)
                             for doc, entry in zip(inputs.docs, ordered, strict=True)
                             if doc.source_id in bought_ids),
        ))
        image_ok += runs[-1].image_calls_ok
        image_total += runs[-1].image_calls_total

    gates = _gates_for(candidate, config, runs, image_ok, image_total, evidence, require_key)
    return aggregate_runs(candidate.id, candidate.label, candidate.model_id, gates, runs,
                          config.replication, provenance=R.merge([r.provenance for r in runs],
                                                                 store.invocation))


async def _extract_and_persist(
    docs: Sequence[DocInput], *, client: Any, config: ConfigBundle, concurrency: int,
    store: R.ResumeStore, candidate_id: str, run_index: int, fingerprint: str,
) -> list[tuple[str, tuple[ClaimRecord, ...], tuple[Any, ...]]]:
    """Extract each document and write it the instant it lands. Survives a sibling's failure.

    Two departures from the previous single ``extract_many(all_docs)`` call, both deliberate:

    * **one recorder per document**, so calls are attributed to the document that made them. Without
      that attribution a cached document could not carry its own call records, and the three
      measured-at-the-call criteria would silently go missing on any resumed run.
    * **failures do not cancel siblings' bookkeeping.** ``gather`` is told to return exceptions rather
      than propagate the first one, so every document that *did* complete is persisted before the error
      is re-raised. That is the whole point: on 2026-07-26 one exception discarded ~225 already-billed
      Opus calls, and the fix is not to swallow the exception but to stop it taking the receipts with it.

    ``concurrency`` now bounds **documents** in flight rather than raw calls; a document's own text ∥
    image calls still overlap. Per-provider pacing (:mod:`.throttle`) is what bounds request *rate*, and
    it is the knob that matters against an account cap — a global call count never was.
    """
    sem = asyncio.Semaphore(max(1, concurrency))

    async def one(doc: DocInput) -> tuple[str, tuple[ClaimRecord, ...], tuple[Any, ...]]:
        async with sem:
            recorder = RecordingExtractionClient(client)
            claims = (await extract_many(
                [doc], concurrency=1 + len(doc.images), client=recorder, config=config))[0]
            calls = tuple(recorder.calls)
            store.save(candidate_id, run_index, doc, claims, calls, fingerprint)
            return doc.source_id, tuple(claims), calls

    results = await asyncio.gather(*(one(doc) for doc in docs), return_exceptions=True)
    done: list[tuple[str, tuple[ClaimRecord, ...], tuple[Any, ...]]] = [
        r for r in results if not isinstance(r, BaseException)]
    for outcome in results:
        if isinstance(outcome, BaseException):
            raise outcome
    return done


def _gates_for(candidate: Candidate, config: BakeoffConfig, runs: Sequence[RunScore],
               image_ok: int, image_total: int, evidence: Mapping[str, ImageryEvidence],
               require_key: bool) -> GateReport:
    """Gates for a run: the non-negotiables judged on the mean over the runs, imagery on ALL the evidence.

    The imagery observations are the recorded probe **plus** this run's own image calls, built by the same
    :func:`~eval.extraction.vlm_probe.observations_for` ``preflight`` uses. That is why a green preflight can
    no longer be followed by a silent disqualification: with the same evidence and no image call of its own,
    a run reaches exactly the status preflight printed.
    """
    non_negotiables: dict[str, M.MetricValue] = {}
    for name in (config.gates.non_negotiable_floors or {}):
        vals = [
            r.metrics[name].value for r in runs
            if name in r.metrics and r.metrics[name].status == "measured"
            and r.metrics[name].value is not None
        ]
        if vals:
            mean = sum(float(v) for v in vals if v is not None) / len(vals)
            non_negotiables[name] = M.MetricValue.measured(name, mean, detail={"runs": len(vals)})
        else:
            reasons = sorted({
                r.metrics[name].reason for r in runs
                if name in r.metrics and r.metrics[name].status == "unavailable" and r.metrics[name].reason
            })
            non_negotiables[name] = M.MetricValue.unavailable(
                name, "; ".join(reasons) or "not measured in any run")
    imagery, _ = observations_for(candidate, evidence=evidence, run_calls_ok=image_ok,
                                 run_calls_total=image_total)
    return evaluate_gates(candidate, config, imagery=imagery,
                          non_negotiable_metrics=non_negotiables, require_key=require_key)


# ── the whole bake-off ────────────────────────────────────────────────────────────────────────────

def run_bakeoff(
    inputs: BakeoffInputs,
    config: BakeoffConfig,
    client_factory: ClientFactory = live_client_factory,
    *,
    candidates: Sequence[str] | None = None,
    require_key: bool = True,
    evidence: Mapping[str, ImageryEvidence] | None = None,
    resume_enabled: bool = True,
    invocation: str | None = None,
    pace: bool = True,
    producer: str = R.LIVE,
) -> BakeoffResult:
    """Run every declared candidate N times and produce the comparative verdict.

    ``candidates`` optionally restricts the run to some ids — but note that a *narrowed* bake-off is
    still reported as what it is: candidates that were not run appear nowhere, and if only one candidate
    survives the gates the verdict is ``SOLE_ELIGIBLE_CANDIDATE``, never ``WINNER``.

    Preconditions are checked **before the first API call**. ``coref_binding`` is the top-weighted
    criterion and is declared required, but it needs both halves of its substrate: extraction pass 2 live
    on this run's config, and cluster labels in the labeled slice (see :mod:`.coref_channel`). Either one
    missing raises here, rather than after N extractions per candidate have been paid for and the verdict
    comes back INSUFFICIENT_CRITERIA.

    ``evidence`` resolves through :func:`~eval.extraction.vlm_probe.resolve_evidence`, the same function
    ``preflight`` uses: ``None`` reads the recorded artefact, an explicit mapping is taken as given. The two
    entry points therefore judge the imagery gate on the same evidence by construction, which is what stops
    a green preflight from being followed by ``NO_ELIGIBLE_CANDIDATE``.

    ``resume_enabled`` decides whether documents already on disk under ``inputs.out_dir`` are **reused**.
    They are always *written* — that is what makes the next invocation cheap — but an operator who wants
    a clean single-invocation measurement passes ``False`` and pays for it, which is the honest way to get
    ``determinism`` sampled in one sitting rather than deleting a directory and hoping. Whatever the
    choice, the scorecard reports which invocations actually contributed.

    ``pace`` applies the per-provider rate limits declared in config. ``False`` swaps each limiter for a
    virtual-clock one that computes the wait a live run would incur without incurring it — that is how
    ``--dry-run`` exercises the throttle for real and reports its wall-clock floor instead of skipping the
    one mechanism added to stop a rate-limit killing a run.
    """
    coref_channel.require(inputs.config, config)
    gold = load_claim_gold(inputs.gold_path)
    coref_registry = load_coref_registry(inputs.gold_path)
    coref_channel.require_gold_labels(gold, config, registry=coref_registry)
    # The typed negative gold rides in the same adapted file as the positive claims, so this is the path
    # the caller already supplied — never a second input an operator has to remember.
    negative = load_negative_gold(inputs.gold_path)
    oracle = load_sub_oracle(inputs.sub_oracle_path)
    records = resolve_evidence(evidence)

    store = R.ResumeStore(root=Path(inputs.out_dir),
                          invocation=invocation or R.new_invocation_id(),
                          enabled=resume_enabled)

    wanted = set(candidates) if candidates else None
    scores = [
        run_candidate(cand, inputs, config, client_factory, gold=gold, negative=negative, oracle=oracle,
                      evidence=records, coref_registry=coref_registry, require_key=require_key, store=store,
                      pacer=_pacer_for(cand, config, pace=pace), producer=producer)
        for cand in config.candidates
        if wanted is None or cand.id in wanted
    ]

    verdict, composite = decide(scores, config)
    comparisons = per_metric_comparisons(scores, config)
    return BakeoffResult(scores=scores, verdict=verdict, comparisons=comparisons, composite=composite,
                         config=config)


def _pacer_for(candidate: Candidate, config: BakeoffConfig, *, pace: bool) -> RequestPacer:
    """This candidate's own limiter. One per candidate, never shared — that is what keeps a capped lane's
    slowness its own: the three candidates are three independent loops, so a 3-req/min pacer on one of
    them cannot make the other two wait."""
    limit = config.rate_limit(candidate.provider)
    return RequestPacer(limit=limit) if pace else virtual_pacer(limit)


def preflight(config: BakeoffConfig, *, require_key: bool = True,
              evidence: Mapping[str, ImageryEvidence] | None = None) -> list[GateReport]:
    """Evaluate every gate that can be judged **without spending a single API call**.

    Pinned id, production client path, SDK import and key presence are all checkable dry, and checking
    them first is how a bake-off avoids paying for runs on a candidate that is already disqualified.

    The VLM imagery gate is the exception: it cannot be judged by inspection, because "would this model
    read an image" is not a property of the config. It is judged on **recorded evidence** from
    :mod:`.vlm_probe` — a real standalone-image call through the real imagery lane, whose verdict is
    pinned to the model id it was recorded against. No record, or a record for a model id this candidate
    no longer names, reads UNKNOWN. That is the honest answer *and* a blocking one: a gate nobody ran is
    not a gate anybody passed, and UNKNOWN must never quietly become a pass.

    Judged through exactly the functions the real run uses —
    :func:`~eval.extraction.vlm_probe.resolve_evidence`, then
    :func:`~eval.extraction.vlm_probe.observations_for`, then :func:`~eval.extraction.gates.evaluate_gates`.
    Preflight is simply the run with zero image calls of its own, so a PASS printed here cannot turn into a
    disqualification later on the same evidence.
    """
    records = resolve_evidence(evidence)
    reports: list[GateReport] = []
    for cand in config.candidates:
        imagery, _ = observations_for(cand, evidence=records)
        reports.append(dry_gates(cand, config, imagery=imagery, require_key=require_key))
    return reports


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
]
