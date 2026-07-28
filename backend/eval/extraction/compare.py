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
    "INSUFFICIENT_CRITERIA",
    "NON_NEGOTIABLE_REGRESSION",
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


def _oriented(series: MetricSeries, i: int) -> float:
    """Run *i*'s value, flipped so that **larger is always better** before it enters the composite.

    The composite is ranked ``higher_is_better``, so a ``lower_is_better`` member has to be inverted on the
    way in. Without this a rate-valued "how often did it do the bad thing" metric contributes *positively*:
    with fabrication weighted at 4.5, a model fabricating 40% of the time scored a composite of 0.56
    against a clean model's 0.32 — the harness would have actively selected for the one behaviour this
    project calls disqualifying, and every per-metric line would still have read correctly.

    Only 0..1 rates reach the composite (``composite_series`` enforces the unit), so ``1 - v`` is the
    meaningful inversion rather than a negation.
    """
    v = series.values[i]
    return (1.0 - v) if series.direction == "lower_is_better" else v


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
        directions = {s.direction for s in per_candidate if s}
        if len(directions) > 1:
            excluded[name] = (
                f"candidates disagree on this metric's direction {sorted(directions)} — refusing to "
                "composite a metric whose polarity is ambiguous"
            )
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
            sum(config.weight_for(m) * _oriented(score.series[m], i) for m in used) / total_weight
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

    # RULING (integration triage): a metric the config declares REQUIRED blocks the verdict; a merely
    # weighted one is excluded and named. Plan §8 splits the bake-off into a Wave-0 screen and a
    # definitive pass precisely because the two top-weighted criteria cannot be measured yet — so a
    # Wave-0 winner asserts the missing half could not have mattered, which is what has not been shown.
    # This is the project's own "insufficient evidence to assess" rule turned on its own instrument.
    # It lifts automatically: measure the required metrics and the block disappears.
    unmeasured_required = {
        name: "; ".join(sorted({
            f"{s.candidate_id}: {s.series[name].not_rankable_because}" if name in s.series
            else f"{s.candidate_id}: metric absent"
            for s in eligible
            if name not in s.series or not s.series[name].rankable
        }))
        for name in config.required_metrics
    }
    unmeasured_required = {k: v for k, v in unmeasured_required.items() if v}
    if unmeasured_required:
        detail = "; ".join(f"{k} ({v})" for k, v in sorted(unmeasured_required.items()))
        return Verdict(
            "INSUFFICIENT_CRITERIA",
            "Ranking refused: required criteria are UNMEASURED, not zero — "
            f"{detail}. Naming a winner now would assert that the unmeasured criteria could not have "
            "changed the outcome. Re-run once they can be measured; nothing else about this scorecard "
            "changes.",
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
        # RULING (integration triage): a non-negotiable is not tradeable. Before the composite may name a
        # winner, that winner must not be MATERIALLY worse than any rival on a declared non-negotiable
        # metric. Inside the composite these are just heavy weights, and any weight is a price a
        # good-enough model can pay — so a model 10 F1 points ahead could buy its way past a worse
        # fabrication rate. That model would re-extract and re-freeze the graded oracle, writing
        # ungrounded claims into the evidence layer wearing valid citations, which nothing downstream
        # catches. The check needs no invented threshold: it reuses the same margin rule, so only a
        # difference already established as real (outside run-to-run noise) can veto.
        by_id = {s.candidate_id: s for s in eligible}
        winner = by_id[top[0]]
        vetoes: list[str] = []
        for metric in config.non_negotiable_metrics:
            for rival in eligible:
                if rival.candidate_id == winner.candidate_id:
                    continue
                result = compare_pair(metric, rival.candidate_id, rival.series.get(metric),
                                      winner.candidate_id, winner.series.get(metric), config.margin)
                if result.verdict == "A_BETTER":
                    vetoes.append(
                        f"{rival.candidate_id} is materially better than {winner.candidate_id} on "
                        f"{metric} ({result.note})"
                    )
        if vetoes:
            return Verdict(
                "NON_NEGOTIABLE_REGRESSION",
                f"No winner: {top[0]} leads the weighted composite but is materially worse on a "
                "non-negotiable criterion — " + "; ".join(vetoes) + ". Citation faithfulness and the "
                "extract-only-stated discipline are not score lines to be averaged against recall; a "
                "non-negotiable that can be outweighed is a price. Resolve this as a human judgement, "
                "not by arithmetic.",
                disqualified=disqualified, composite_weights=weights,
                composite_exclusions=exclusions,
            ), comparison
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
