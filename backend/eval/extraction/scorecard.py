"""Per-run scores, and their aggregation across the N repeated runs — where variance is recorded.

Re-extraction is **empirically non-deterministic on a small slice** (it has already broken a hero query
once), so a single run per candidate measures a sample, not a model. Everything here is built around
that fact:

* a :class:`RunScore` is one run — every metric, plus the raw evidence that produced it;
* a :class:`MetricSeries` is one metric across the N runs — its values, mean, sample standard deviation,
  and, crucially, whether it is **rankable at all**;
* a :class:`CandidateScore` is one candidate: its gate report plus one series per metric.

A series is rankable only when every run measured it *and* there are enough runs to estimate a spread.
A metric measured in 3 of 5 runs still gets a mean printed — with the gap named — but it is excluded from
ranking, because comparing a 3-run mean to a 5-run mean and calling the difference material is exactly
the kind of number this harness exists to refuse.

**Determinism** is itself scored here, as a per-run value so it has a spread like everything else: run
*i*'s determinism is the mean multiset Jaccard of its claim signatures against every *other* run of the
same candidate. One run → not measurable, and it says so.
"""

from __future__ import annotations

import statistics
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from .gates import GateReport
from .metrics import Direction, MetricValue
from .policy import Replication
from .surface import SurfaceClaim, normalize_surface

SeriesStatus = Literal["measured", "partial", "unavailable"]


# ── one run ───────────────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RunScore:
    """Every metric for one extraction run of one candidate, plus the evidence behind them."""

    candidate_id: str
    run_index: int
    metrics: dict[str, MetricValue]
    claims: tuple[SurfaceClaim, ...] = ()
    image_calls_ok: int = 0
    image_calls_total: int = 0
    #: Every billable call this run made — both lanes, both passes. Recorded so the driver can report the
    #: spend it ACTUALLY incurred, not just the range it projected: extraction pass 2 is conditional on
    #: what pass 1 found, so the projection is a floor and a ceiling and only a completed run knows where
    #: between them the truth fell.
    calls_total: int = 0
    notes: list[str] = field(default_factory=list)

    def metric(self, name: str) -> MetricValue | None:
        return self.metrics.get(name)


def claim_signature(claim: SurfaceClaim) -> str:
    """A content signature for a claim — what makes two runs' outputs "the same claim".

    Ids are excluded on purpose (they are re-minted every extraction), as is provenance: determinism here
    means *the model said the same things*, not *our id derivation is stable* (that is gate G1's job).
    """
    roles = "|".join(f"{k}={normalize_surface(v)}" for k, v in sorted(claim.roles.items()))
    return "::".join([
        claim.form, claim.polarity, normalize_surface(claim.predicate),
        normalize_surface(claim.entity_type), roles,
    ])


def _multiset_jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    ca, cb = Counter(a), Counter(b)
    keys = set(ca) | set(cb)
    if not keys:
        return 1.0
    inter = sum(min(ca[k], cb[k]) for k in keys)
    union = sum(max(ca[k], cb[k]) for k in keys)
    return inter / union if union else 1.0


def determinism_values(runs: Sequence[RunScore]) -> list[MetricValue]:
    """One determinism value per run: its mean claim-set agreement with every other run.

    Leave-one-out rather than a single cross-run number, so determinism carries a spread of its own and
    goes through the same margin rule as every other metric instead of being ranked on a point estimate.
    """
    if len(runs) < 2:
        reason = "determinism needs at least 2 runs of the same candidate to be measurable"
        return [MetricValue.unavailable("determinism", reason) for _ in runs]
    sigs = [[claim_signature(c) for c in run.claims] for run in runs]
    out: list[MetricValue] = []
    for i in range(len(runs)):
        others = [_multiset_jaccard(sigs[i], sigs[j]) for j in range(len(runs)) if j != i]
        out.append(MetricValue.measured(
            "determinism", sum(others) / len(others),
            detail={"claims": len(sigs[i]), "compared_against": len(others)},
        ))
    return out


# ── one metric across N runs ──────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MetricSeries:
    """One metric across the N runs of one candidate — the unit the margin rule operates on."""

    name: str
    unit: str
    direction: Direction
    values: tuple[float, ...]
    n_runs: int
    status: SeriesStatus
    reasons: tuple[str, ...] = ()
    min_runs_for_ranking: int = 2

    @property
    def mean(self) -> float | None:
        return statistics.fmean(self.values) if self.values else None

    @property
    def stdev(self) -> float | None:
        """Sample standard deviation — ``None`` below two values (a spread of one point is not a spread)."""
        return statistics.stdev(self.values) if len(self.values) >= 2 else None

    @property
    def rankable(self) -> bool:
        """May this series take part in a comparison at all?

        Requires: every run measured it, and there are at least ``min_runs_for_ranking`` of them. A
        partially-measured or under-replicated series can be *reported* but never *ranked* — the whole
        point of the margin rule is that it needs a real estimate of noise to subtract.
        """
        return (
            self.status == "measured"
            and len(self.values) == self.n_runs
            and len(self.values) >= self.min_runs_for_ranking
        )

    @property
    def not_rankable_because(self) -> str:
        if self.rankable:
            return ""
        if self.status == "unavailable":
            return self.reasons[0] if self.reasons else "not measured"
        if len(self.values) < self.n_runs:
            return f"measured in only {len(self.values)}/{self.n_runs} runs"
        return f"only {len(self.values)} run(s); ranking needs {self.min_runs_for_ranking}"


def build_series(
    name: str, values: Sequence[MetricValue], n_runs: int, min_runs_for_ranking: int
) -> MetricSeries:
    """Fold one metric's per-run values into a series, preserving *why* anything is missing."""
    measured = [v for v in values if v.status == "measured" and v.value is not None]
    reasons = tuple(dict.fromkeys(v.reason for v in values if v.status == "unavailable" and v.reason))
    unit = values[0].unit if values else "rate"
    direction = values[0].direction if values else "higher_is_better"
    if not measured:
        status: SeriesStatus = "unavailable"
    elif len(measured) < n_runs:
        status = "partial"
    else:
        status = "measured"
    return MetricSeries(
        name=name, unit=unit, direction=direction,
        values=tuple(float(v.value) for v in measured),  # type: ignore[arg-type]
        n_runs=n_runs, status=status, reasons=reasons,
        min_runs_for_ranking=min_runs_for_ranking,
    )


# ── one candidate ─────────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CandidateScore:
    """One candidate's whole result: its gates (which dominate) and its metric series."""

    candidate_id: str
    label: str
    model_id: str
    gates: GateReport
    series: dict[str, MetricSeries]
    runs: tuple[RunScore, ...] = ()
    exercised: bool = True
    not_exercised_reason: str = ""

    @property
    def eligible_to_win(self) -> bool:
        """Gates dominate: a candidate that failed any gate cannot win at any score."""
        return self.exercised and self.gates.eligible


def aggregate_runs(
    candidate_id: str, label: str, model_id: str, gates: GateReport, runs: Sequence[RunScore],
    replication: Replication,
) -> CandidateScore:
    """Fold N :class:`RunScore` into a :class:`CandidateScore`, adding the determinism series."""
    names: list[str] = []
    for run in runs:
        for name in run.metrics:
            if name not in names:
                names.append(name)

    n_runs = len(runs)
    series: dict[str, MetricSeries] = {}
    for name in names:
        per_run = [
            run.metrics.get(name)
            or MetricValue.unavailable(name, f"run {run.run_index} did not produce this metric")
            for run in runs
        ]
        series[name] = build_series(name, per_run, n_runs, replication.min_runs_for_ranking)

    det = determinism_values(runs)
    series["determinism"] = build_series("determinism", det, n_runs, replication.min_runs_for_ranking)

    return CandidateScore(
        candidate_id=candidate_id, label=label, model_id=model_id, gates=gates,
        series=series, runs=tuple(runs),
    )


def unexercised(candidate_id: str, label: str, model_id: str, gates: GateReport,
                reason: str) -> CandidateScore:
    """A candidate that could not be run at all — recorded, never silently dropped.

    Dropping it would let the report read like a three-way comparison that only ever ran two ways.
    """
    return CandidateScore(
        candidate_id=candidate_id, label=label, model_id=model_id, gates=gates, series={},
        runs=(), exercised=False, not_exercised_reason=reason,
    )


def series_table(score: CandidateScore) -> list[dict[str, Any]]:
    """The candidate's series as printable rows (mean ± sd, n, rankable)."""
    rows: list[dict[str, Any]] = []
    for name in sorted(score.series):
        s = score.series[name]
        rows.append({
            "metric": name,
            "mean": s.mean,
            "stdev": s.stdev,
            "n": len(s.values),
            "n_runs": s.n_runs,
            "unit": s.unit,
            "direction": s.direction,
            "status": s.status,
            "rankable": s.rankable,
            "note": s.not_rankable_because,
        })
    return rows


__all__ = [
    "CandidateScore",
    "MetricSeries",
    "RunScore",
    "SeriesStatus",
    "aggregate_runs",
    "build_series",
    "claim_signature",
    "determinism_values",
    "series_table",
    "unexercised",
]
