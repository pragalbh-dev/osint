"""Rendering the comparative scorecard — gates first and separate, then spreads, then the verdict.

Layout is an argument, not decoration. The gate block is printed **above** every score and every gate
failure is spelled out, because a reader who skims to the biggest number must not be able to reach it
before reading "this candidate is disqualified". Every score line carries its ``± sd (n=…)``; a metric
that could not be measured prints its reason where its number would have been, never a dash that reads
like a zero.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any

from .compare import COMPOSITE, MetricComparison, Verdict, summarize_spread
from .metrics import AWAITING_S3
from .policy import BakeoffConfig
from .scorecard import CandidateScore


def _fmt(value: float | None, unit: str) -> str:
    if value is None:
        return "—"
    if unit == "usd":
        return f"${value:,.4f}"
    if unit == "seconds":
        return f"{value:,.2f}s"
    return f"{value:.4f}"


def render_markdown(
    scores: list[CandidateScore], verdict: Verdict, comparisons: dict[str, MetricComparison],
    config: BakeoffConfig, composite: MetricComparison | None = None,
) -> str:
    """The whole scorecard as markdown."""
    out: list[str] = []
    add = out.append

    add("# RK-BAKEOFF — comparative extractor scorecard\n")
    add(f"Replication: **{config.replication.runs_per_candidate} runs/candidate** "
        f"(ranking refused below {config.replication.min_runs_for_ranking}). "
        f"Margin: **max({config.margin.min_absolute}, {config.margin.noise_multiplier}×pooled SD)**.\n")

    # ── gates: first, separate, dominating ────────────────────────────────────────────────────────
    add("\n## 1. Gating preconditions — PASS/FAIL to win (never weighted)\n")
    add("A candidate failing any gate **cannot win at any score**. UNKNOWN blocks too: an unverified "
        "precondition is not a satisfied one.\n")
    add("| candidate | model id | gates | eligible to win |")
    add("|---|---|---|---|")
    for score in scores:
        cells = "<br>".join(f"`{g.status}` **{g.name}** — {g.detail}" for g in score.gates.gates) or "—"
        eligible = "**YES**" if score.eligible_to_win else "**NO — disqualified**"
        add(f"| {score.label} (`{score.candidate_id}`) | `{score.model_id}` | {cells} | {eligible} |")

    not_run = [s for s in scores if not s.exercised]
    if not_run:
        add("\n**Not exercised** (recorded so this cannot read as a comparison that did not happen):\n")
        for s in not_run:
            add(f"- `{s.candidate_id}` — {s.not_exercised_reason}")

    # ── scores ────────────────────────────────────────────────────────────────────────────────────
    add("\n## 2. Measured criteria (mean ± sample SD over the runs)\n")
    metric_names = sorted({n for s in scores for n in s.series})
    exercised = [s for s in scores if s.exercised]
    if exercised:
        header = "| metric | weight | " + " | ".join(s.candidate_id for s in exercised) + " | verdict |"
        add(header)
        add("|---|---|" + "---|" * (len(exercised) + 1))
        for name in metric_names:
            weight = config.weight_for(name)
            score_cells: list[str] = []
            for s in exercised:
                series = s.series.get(name)
                score_cells.append(summarize_spread(series) if series else "not produced")
            verdict_cell = _metric_verdict_cell(comparisons.get(name))
            add(f"| `{name}` | {weight:g} | " + " | ".join(score_cells) + f" | {verdict_cell} |")

    awaiting = [
        n for n in metric_names
        if all(AWAITING_S3 in (s.series[n].reasons or ()) for s in exercised if n in s.series)
        and exercised
    ]
    if awaiting:
        add("\n> **Awaiting substrate.** " + ", ".join(f"`{n}`" for n in awaiting) +
            " — the metric is implemented and defined, but S3 (RK-COREF) has not landed, so no number is "
            "reported for anyone. It is not zero and it is not a tie; it is not measured.")

    # ── composite + verdict ───────────────────────────────────────────────────────────────────────
    add("\n## 3. Composite and verdict\n")
    if verdict.composite_weights:
        add("Composite = weighted mean **per run** of these rate metrics: " +
            ", ".join(f"`{k}`×{v:g}" for k, v in sorted(verdict.composite_weights.items())) + ".\n")
    if verdict.composite_exclusions:
        add("Excluded from the composite (reported above, not composited):\n")
        for name, why in sorted(verdict.composite_exclusions.items()):
            add(f"- `{name}` — {why}")
    if composite is not None and composite.tiers:
        add("\nComposite tiers (best first; candidates inside one tier are not separable at the "
            "configured margin):\n")
        for i, tier in enumerate(composite.tiers, 1):
            add(f"{i}. " + ", ".join(f"`{c}`" for c in tier))

    add(f"\n### VERDICT: `{verdict.kind}`\n")
    add(verdict.statement)
    if verdict.winner:
        add(f"\n**Winner: `{verdict.winner}`.**")
    if verdict.tied:
        add(f"\n**Tied within noise: {', '.join('`' + c + '`' for c in verdict.tied)}** — no winner.")
    if verdict.disqualified:
        add("\nDisqualified / not comparable:\n")
        for cid, why in sorted(verdict.disqualified.items()):
            add(f"- `{cid}` — {why}")

    # ── the match policy, printed under the numbers it produced ───────────────────────────────────
    add("\n## 4. The match policy that produced these numbers\n")
    add("The matcher's leniency **is** the measurement; read this before reading any figure above.\n")
    add("```")
    out.extend(config.match_policy.describe())
    add("```")
    return "\n".join(out) + "\n"


def _metric_verdict_cell(comparison: MetricComparison | None) -> str:
    if comparison is None or not comparison.tiers:
        return "not rankable"
    if len(comparison.tiers) == 1 and len(comparison.tiers[0]) > 1:
        return "NO MEASURED DIFFERENCE"
    return " > ".join("/".join(t) for t in comparison.tiers)


def to_json(
    scores: list[CandidateScore], verdict: Verdict, comparisons: dict[str, MetricComparison],
    config: BakeoffConfig,
) -> str:
    """The same result as machine-readable JSON (for diffing two bake-off runs)."""
    payload: dict[str, Any] = {
        "schema_version": "rk-bakeoff-scorecard/1.0",
        "replication": config.replication.model_dump(),
        "margin": config.margin.model_dump(),
        "match_policy": config.match_policy.model_dump(),
        "verdict": _dump(verdict),
        "candidates": [
            {
                "id": s.candidate_id,
                "label": s.label,
                "model_id": s.model_id,
                "exercised": s.exercised,
                "not_exercised_reason": s.not_exercised_reason,
                "eligible_to_win": s.eligible_to_win,
                "gates": [_dump(g) for g in s.gates.gates],
                "series": {
                    name: {
                        "values": list(series.values),
                        "mean": series.mean,
                        "stdev": series.stdev,
                        "n_runs": series.n_runs,
                        "unit": series.unit,
                        "direction": series.direction,
                        "status": series.status,
                        "rankable": series.rankable,
                        "reasons": list(series.reasons),
                    }
                    for name, series in sorted(s.series.items())
                },
            }
            for s in scores
        ],
        "comparisons": {
            name: {
                "tiers": [list(t) for t in comp.tiers],
                "excluded": comp.excluded,
                "pairwise": [_dump(p) for p in comp.pairwise],
            }
            for name, comp in sorted(comparisons.items())
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _dump(obj: Any) -> Any:
    return asdict(obj) if is_dataclass(obj) and not isinstance(obj, type) else obj


__all__ = ["COMPOSITE", "render_markdown", "to_json"]
