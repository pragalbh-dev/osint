"""The comparative verdict — the minimum-margin rule, and the reason this harness cannot invent a winner.

This is the most important module in the bake-off, and it is deliberately the most conservative. The
instrument it implements is not "rank the candidates"; it is "say whether the evidence supports a
ranking at all, and refuse otherwise". Manufacturing an ordering out of run-to-run jitter would be the
same failure as fabricating an assessment from thin evidence — the one thing this project treats as
disqualifying — applied to our own benchmark.

THE RULE
────────
For a metric measured over N runs per candidate, the gap between candidates *a* and *b* is **material**
only when::

    |mean_a - mean_b|  >=  max( margin.min_absolute_for(metric),
                                margin.noise_multiplier * sqrt((sd_a^2 + sd_b^2) / 2) )

Anything below that is **NO MEASURED DIFFERENCE**. Not "a slight edge", not "marginally better" — no
difference was measured, and the report says so in those words.

FOUR STRUCTURAL REFUSALS
────────────────────────
1. **Under-replication.** Fewer runs than ``replication.min_runs_for_ranking`` and the verdict is
   ``INSUFFICIENT_REPLICATION``, full stop. With one or two samples the spread is not estimable, so
   *every* gap is within unmeasured noise.
2. **Un-rankable series.** A metric that some run failed to measure, or that only one candidate has,
   is excluded from the composite and named in the exclusions. It is never imputed and never zero-filled.
3. **Gate dominance.** Candidates failing any gate are removed *before* scores are compared. No score
   buys past a locked precondition.
4. **Tie ⇒ no winner.** ``Verdict`` enforces in its constructor that ``winner`` is set if and only if the
   verdict is literally ``WINNER``, and ``WINNER`` is only ever constructed from a top tier of size one.
   There is no code path that can name a winner on a within-noise gap.

The composite is computed **per run**, not by propagating standard deviations: run *i*'s composite is the
weighted mean of that run's metric values, so the composite carries a real, observed spread and goes
through exactly the same margin rule as any single metric. Only rate-valued metrics (0..1) enter it —
seconds and dollars would need a normalising constant nobody has justified, so cost and latency are
reported with their own per-metric verdicts and left as human tie-breakers.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from .policy import BakeoffConfig, Margin
from .scorecard import CandidateScore, MetricSeries

PairVerdict = Literal["A_BETTER", "B_BETTER", "NO_MEASURED_DIFFERENCE", "NOT_RANKABLE"]
VerdictKind = Literal[
    "WINNER",
    "NO_MEASURED_DIFFERENCE",
    "INSUFFICIENT_REPLICATION",
    "SOLE_ELIGIBLE_CANDIDATE",
    "NO_ELIGIBLE_CANDIDATE",
    "NO_COMPARABLE_METRICS",
]

#: The one phrase the report is allowed to use for a within-noise gap.
NO_DIFFERENCE_PHRASE = "NO MEASURED DIFFERENCE"


def pooled_sd(sd_a: float | None, sd_b: float | None) -> float | None:
    """Pooled standard deviation of two run-samples; ``None`` if either spread is unknown."""
    if sd_a is None or sd_b is None:
        return None
    return math.sqrt((sd_a**2 + sd_b**2) / 2.0)


def required_margin(metric: str, sd: float | None, margin: Margin) -> float | None:
    """The gap a difference must clear on this metric: the configured floor, or N pooled SDs, whichever
    is larger. ``None`` when the noise is unknown — in which case nothing may be called material."""
    if sd is None:
        return None
    return max(margin.floor_for(metric), margin.noise_multiplier * sd)


@dataclass(frozen=True)
class PairwiseResult:
    """One head-to-head on one metric, with the arithmetic left visible."""

    metric: str
    a: str
    b: str
    mean_a: float | None
    mean_b: float | None
    #: How much better *a* is than *b*, already oriented by the metric's direction (positive ⇒ a better).
    advantage_a: float | None
    pooled_sd: float | None
    margin: float | None
    verdict: PairVerdict
    note: str = ""

    @property
    def material(self) -> bool:
        return self.verdict in ("A_BETTER", "B_BETTER")


def _advantage(mean_a: float, mean_b: float, direction: str) -> float:
    return (mean_b - mean_a) if direction == "lower_is_better" else (mean_a - mean_b)


def compare_pair(metric: str, a: str, sa: MetricSeries | None, b: str, sb: MetricSeries | None,
                 margin: Margin) -> PairwiseResult:
    """Apply the minimum-margin rule to one metric for one pair of candidates."""
    if sa is None or sb is None or not sa.rankable or not sb.rankable:
        why = []
        if sa is None:
            why.append(f"{a}: metric absent")
        elif not sa.rankable:
            why.append(f"{a}: {sa.not_rankable_because}")
        if sb is None:
            why.append(f"{b}: metric absent")
        elif not sb.rankable:
            why.append(f"{b}: {sb.not_rankable_because}")
        return PairwiseResult(metric, a, b, sa.mean if sa else None, sb.mean if sb else None,
                              None, None, None, "NOT_RANKABLE", "; ".join(why))

    mean_a, mean_b = sa.mean, sb.mean
    assert mean_a is not None and mean_b is not None
    sd = pooled_sd(sa.stdev, sb.stdev)
    need = required_margin(metric, sd, margin)
    adv = _advantage(mean_a, mean_b, sa.direction)
    if need is None:
        return PairwiseResult(metric, a, b, mean_a, mean_b, adv, sd, need, "NOT_RANKABLE",
                              "run-to-run spread is unknown, so no gap can be called material")
    if abs(adv) < need:
        return PairwiseResult(metric, a, b, mean_a, mean_b, adv, sd, need, "NO_MEASURED_DIFFERENCE",
                              f"|Δ|={abs(adv):.4f} < required margin {need:.4f}")
    return PairwiseResult(metric, a, b, mean_a, mean_b, adv, sd, need,
                          "A_BETTER" if adv > 0 else "B_BETTER",
                          f"|Δ|={abs(adv):.4f} >= required margin {need:.4f}")


@dataclass(frozen=True)
class MetricComparison:
    """One metric across all candidates: ordered tiers plus every head-to-head."""

    metric: str
    tiers: tuple[tuple[str, ...], ...]
    pairwise: tuple[PairwiseResult, ...]
    excluded: dict[str, str] = field(default_factory=dict)

    @property
    def top_tier(self) -> tuple[str, ...]:
        return self.tiers[0] if self.tiers else ()

    @property
    def has_separation(self) -> bool:
        return len(self.tiers) > 1 or (len(self.tiers) == 1 and len(self.tiers[0]) == 1
                                       and not self.excluded)


def compare_metric(metric: str, series: Mapping[str, MetricSeries | None], margin: Margin) -> MetricComparison:
    """Tier the candidates on one metric under the margin rule.

    Tiering rule, stated because it is a judgement call: candidates are ordered best-mean-first, and each
    is placed in the current tier unless it is *materially* worse than that tier's **leader**, in which
    case it opens a new tier. Comparing to the leader (rather than to the tier's weakest member) keeps
    tiers from chaining indefinitely through a series of individually-within-noise gaps; it is the
    stricter of the two readings, i.e. the one less likely to hide a real difference — while a
    within-noise gap still cannot separate anyone.
    """
    excluded = {
        cid: (s.not_rankable_because if s is not None else "metric absent")
        for cid, s in series.items()
        if s is None or not s.rankable
    }
    usable = {cid: s for cid, s in series.items() if s is not None and s.rankable}

    pairwise: list[PairwiseResult] = []
    ids = sorted(series)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            pairwise.append(compare_pair(metric, a, series.get(a), b, series.get(b), margin))

    if not usable:
        return MetricComparison(metric, (), tuple(pairwise), excluded)

    direction = next(iter(usable.values())).direction
    ordered = sorted(
        usable,
        key=lambda cid: (usable[cid].mean if direction == "lower_is_better"
                         else -usable[cid].mean, cid),  # type: ignore[operator]
    )

    tiers: list[list[str]] = []
    leader: str | None = None
    for cid in ordered:
        if leader is None:
            tiers.append([cid])
            leader = cid
            continue
        result = compare_pair(metric, leader, usable[leader], cid, usable[cid], margin)
        if result.verdict == "A_BETTER":  # the leader is materially better → new tier
            tiers.append([cid])
            leader = cid
        else:
            tiers[-1].append(cid)
    return MetricComparison(metric, tuple(tuple(t) for t in tiers), tuple(pairwise), excluded)


# ── the composite ─────────────────────────────────────────────────────────────────────────────────

COMPOSITE = "composite"


def composite_series(
    scores: Sequence[CandidateScore], config: BakeoffConfig
) -> tuple[dict[str, MetricSeries], dict[str, float], dict[str, str]]:
    """Build a per-run weighted composite for each candidate.

    Returns ``(series by candidate, weights actually used, excluded metrics → why)``. A metric enters the
    composite only if it is weighted, rate-valued, and **rankable for every candidate being compared** —
    a metric one candidate lacks cannot separate anyone, and imputing it would invent the separation.
    """
    considered = [s for s in scores if s.exercised]
    metric_names = sorted({name for s in considered for name in s.series})
    used: dict[str, float] = {}
    excluded: dict[str, str] = {}

    for name in metric_names:
        weight = config.weight_for(name)
        if weight <= 0:
            excluded[name] = "weight 0 (reported, not composited)"
            continue
        per_candidate = [s.series.get(name) for s in considered]
        if any(s is None for s in per_candidate):
            missing = [c.candidate_id for c, s in zip(considered, per_candidate, strict=True) if s is None]
            excluded[name] = f"not produced by {', '.join(missing)}"
            continue
        units = {s.unit for s in per_candidate if s}
        if units != {"rate"}:
            excluded[name] = f"unit {sorted(units)} is not a 0..1 rate — reported, not composited"
            continue
        unrankable = [
            f"{c.candidate_id} ({s.not_rankable_because})"
            for c, s in zip(considered, per_candidate, strict=True) if s and not s.rankable
        ]
        if unrankable:
            excluded[name] = "not rankable for " + "; ".join(unrankable)
            continue
        used[name] = weight

    out: dict[str, MetricSeries] = {}
    total_weight = sum(used.values())
    for score in considered:
        if not used or total_weight <= 0:
            out[score.candidate_id] = MetricSeries(
                COMPOSITE, "rate", "higher_is_better", (), len(score.runs), "unavailable",
                ("no metric is rankable across every candidate, so no composite exists",),
                config.replication.min_runs_for_ranking,
            )
            continue
        n_runs = min(len(score.series[m].values) for m in used)
        values = tuple(
            sum(config.weight_for(m) * score.series[m].values[i] for m in used) / total_weight
            for i in range(n_runs)
        )
        out[score.candidate_id] = MetricSeries(
            COMPOSITE, "rate", "higher_is_better", values, len(score.runs), "measured", (),
            config.replication.min_runs_for_ranking,
        )
    return out, used, excluded


# ── the verdict ───────────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Verdict:
    """The bake-off's answer. ``winner`` exists **only** in the ``WINNER`` case, enforced here."""

    kind: VerdictKind
    statement: str
    winner: str | None = None
    tied: tuple[str, ...] = ()
    disqualified: dict[str, str] = field(default_factory=dict)
    composite_weights: dict[str, float] = field(default_factory=dict)
    composite_exclusions: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if (self.kind == "WINNER") != (self.winner is not None):
            raise ValueError(
                "Verdict invariant violated: `winner` may be set if and only if kind == 'WINNER'. "
                "A winner named under any other verdict is a ranking manufactured from noise."
            )


def decide(scores: Sequence[CandidateScore], config: BakeoffConfig) -> tuple[Verdict, MetricComparison | None]:
    """Gates first, replication second, margin third — then, and only then, a winner may exist."""
    disqualified = {
        s.candidate_id: (
            s.not_exercised_reason if not s.exercised
            else "; ".join(f"{g.name}={g.status} ({g.detail})" for g in s.gates.blocking)
        )
        for s in scores if not s.eligible_to_win
    }
    eligible = [s for s in scores if s.eligible_to_win]

    if not eligible:
        return Verdict(
            "NO_ELIGIBLE_CANDIDATE",
            "No candidate satisfied every gating precondition. Nothing may be selected on score: the "
            "gates are pass/fail to win, not weighted lines.",
            disqualified=disqualified,
        ), None

    under = [s for s in eligible if len(s.runs) < config.replication.min_runs_for_ranking]
    if under:
        names = ", ".join(f"{s.candidate_id} ({len(s.runs)} run(s))" for s in under)
        return Verdict(
            "INSUFFICIENT_REPLICATION",
            f"Ranking refused: {names} — fewer than the configured minimum of "
            f"{config.replication.min_runs_for_ranking} runs. Re-extraction is non-deterministic, so "
            "below that the run-to-run spread cannot be estimated and every gap sits inside unmeasured "
            "noise.",
            disqualified=disqualified,
        ), None

    if len(eligible) == 1:
        only = eligible[0]
        return Verdict(
            "SOLE_ELIGIBLE_CANDIDATE",
            f"{only.candidate_id} is the only candidate that passed every gate, so it is what remains — "
            "this is a default, not a measured win. No comparison took place; do not read this scorecard "
            "as a multi-way result.",
            disqualified=disqualified,
        ), None

    comp_series, weights, exclusions = composite_series(eligible, config)
    if not weights:
        return Verdict(
            "NO_COMPARABLE_METRICS",
            "No metric is rankable across every eligible candidate, so no composite exists and no "
            "ranking is possible. " + NO_DIFFERENCE_PHRASE + ".",
            disqualified=disqualified, composite_exclusions=exclusions,
        ), None

    comparison = compare_metric(COMPOSITE, dict(comp_series), config.margin)
    top = comparison.top_tier
    if len(top) == 1:
        return Verdict(
            "WINNER", f"{top[0]} wins on the weighted composite by a margin exceeding run-to-run noise.",
            winner=top[0], disqualified=disqualified, composite_weights=weights,
            composite_exclusions=exclusions,
        ), comparison
    return Verdict(
        "NO_MEASURED_DIFFERENCE",
        f"{NO_DIFFERENCE_PHRASE} between {', '.join(top)}: every gap between them sits inside the "
        "run-to-run noise at the configured margin. Naming one of them would be a ranking invented from "
        "jitter.",
        tied=tuple(top), disqualified=disqualified, composite_weights=weights,
        composite_exclusions=exclusions,
    ), comparison


def per_metric_comparisons(
    scores: Sequence[CandidateScore], config: BakeoffConfig
) -> dict[str, MetricComparison]:
    """Every metric compared across the exercised candidates — reported even when it cannot rank."""
    considered = [s for s in scores if s.exercised]
    names = sorted({n for s in considered for n in s.series})
    return {
        name: compare_metric(name, {s.candidate_id: s.series.get(name) for s in considered}, config.margin)
        for name in names
    }


def summarize_spread(series: MetricSeries) -> str:
    """``mean ± sd (n=…)`` or an explicit refusal — the string every report row prints."""
    if not series.values:
        return f"not measured — {series.reasons[0] if series.reasons else 'no reason recorded'}"
    mean = statistics.fmean(series.values)
    if len(series.values) < 2:
        return f"{mean:.4f} (n=1; spread unmeasurable)"
    return f"{mean:.4f} ± {statistics.stdev(series.values):.4f} (n={len(series.values)})"


__all__ = [
    "COMPOSITE",
    "NO_DIFFERENCE_PHRASE",
    "MetricComparison",
    "PairwiseResult",
    "Verdict",
    "compare_metric",
    "compare_pair",
    "composite_series",
    "decide",
    "per_metric_comparisons",
    "pooled_sd",
    "required_margin",
    "summarize_spread",
]
