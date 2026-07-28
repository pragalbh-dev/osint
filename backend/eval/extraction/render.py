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
from .metrics import NO_CLUSTERING
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

    # ── run provenance: printed BEFORE the numbers, because it qualifies one of them ──────────────
    add(_provenance_section(scores))

    # ── scores ────────────────────────────────────────────────────────────────────────────────────
    add("\n## 2. Measured criteria (mean ± sample SD over the runs)\n")
    metric_names = sorted({n for s in scores for n in s.series})
    exercised = [s for s in scores if s.exercised]
    if exercised:
        header = "| metric | weight | " + " | ".join(s.candidate_id for s in exercised) + " | verdict |"
        add(header)
        add("|---|---|" + "---|" * (len(exercised) + 1))
        for name in metric_names:
            # A non-negotiable is marked in the weight column, because that column is where a skimming
            # reader decides what mattered — and the fabrication line's weight is deliberately ZERO. Left
            # unmarked, the single most important criterion reads as the least important one.
            weight_cell = f"{config.weight_for(name):g}"
            if name in config.non_negotiable_metrics:
                weight_cell += " · **VETO**"
            score_cells: list[str] = []
            for s in exercised:
                series = s.series.get(name)
                score_cells.append(summarize_spread(series) if series else "not produced")
            verdict_cell = _metric_verdict_cell(comparisons.get(name))
            # `determinism` is the one line whose meaning depends on HOW the runs were obtained, so the
            # caveat is stamped on the row itself and not left to a section a skimming reader may pass.
            name_cell = f"`{name}`"
            if name == "determinism" and any(not s.provenance.single_invocation for s in exercised):
                name_cell += " ⚠︎ **cross-invocation**"
            add(f"| {name_cell} | {weight_cell} | " + " | ".join(score_cells) + f" | {verdict_cell} |")

    awaiting = [
        n for n in metric_names
        if all(NO_CLUSTERING in (s.series[n].reasons or ()) for s in exercised if n in s.series)
        and exercised
    ]
    if awaiting:
        add("\n> **No clustering to score.** " + ", ".join(f"`{n}`" for n in awaiting) +
            " — the metric is implemented and its substrate has shipped (S3 / RK-COREF), but not one "
            "claim in this run carried a referent id, so no number is reported for anyone. Either the "
            "coreference channel was unavailable on this run's config (preflight names the cause) or "
            "every candidate declined to bind any mention. It is not zero and it is not a tie; it is not "
            "measured.")

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

    # ── what precision excludes, and why the fabrication line is not on the weighted table ────────
    # The gold types its negative rows into four classes and declares only ONE of them (not_a_claim) a
    # genuine false positive. The other three are declared *neutral*, and they are neutral only because
    # the harness calls eval.gold.adapter.precision_exclusions — which it now does, per emitted claim,
    # inside score_run. This section states the resulting semantics so a reader knows what the precision
    # denominator is, rather than assuming it is "everything emitted".
    add("\n## 5. What `surface_precision` excludes, and what vetoes a winner\n")
    add("Precision above is **matched / emitted-minus-neutral**. The labeled slice types its negative rows "
        "into four classes and declares only `not_a_claim` a true false positive; `unmodelled`, "
        "`anti_coref` and non-identity claims over an `ambiguous` pair are **neutral** — a candidate "
        "reading an off-ontology sentence correctly is not wrong, and charging it would penalise a model "
        "in proportion to how much of the document it read, which does not cancel between candidates and "
        "favours the terser extractor. Those exclusions come from `eval.gold.adapter.precision_exclusions` "
        "— the gold owner's own definition, consumed rather than re-derived — and every excluded claim key "
        "is listed in the metric detail of the JSON output.\n")
    add("A `not_a_claim` span is never excused. An emission there costs precision **and** is scored by "
        "`trap_avoidance`, and where a neutral span overlaps a trap the trap wins. A trap hit also "
        "requires the emission to be **unpaired** against positive gold: one trap span overlaps a positive "
        "claim's span, so a bare-overlap test would charge an honest model.\n")
    add("`trap_avoidance` is a **veto, not a weighted line** — it carries no weight and appears in "
        "`gates.non_negotiable_floors`. A non-negotiable inside a composite is only a heavy weight, and "
        "any weight is a price a good-enough model can pay. A candidate materially worse on it than a "
        "rival cannot be named winner at any score, and a candidate whose trap line was never measured is "
        "gate-UNKNOWN, which blocks just as hard. `identity_over_read` is reported as a raw count (N=2) "
        "and never ranked on.\n")
    return "\n".join(out) + "\n"


def _provenance_section(scores: list[CandidateScore]) -> str:
    """Where each candidate's runs came from — above every number, because it qualifies one of them.

    A resumed run reuses documents a previous invocation paid for. That is sound: a cached document is
    refused unless the pinned model id, the document set and the prompt/schema version all still match, so
    the *inputs* are identical by construction. What is NOT identical is the sitting, and ``determinism``
    is a measured, weighted criterion whose whole content is run-to-run agreement. Stitching runs from
    different sessions and printing that number as if it had been sampled in one would be a corrupted
    measurement wearing a clean one's clothes — the exact failure this harness exists to refuse.
    """
    exercised = [s for s in scores if s.exercised]
    if not exercised:
        return ""
    out = ["\n## 1b. Where these runs came from\n"]
    stitched = [s for s in exercised if not s.provenance.single_invocation]
    if stitched:
        out.append("> **⚠︎ RESUMED — this scorecard is not one sitting.** " +
                   ", ".join(f"`{s.candidate_id}`" for s in stitched) +
                   " had runs assembled across more than one invocation. Inputs are pinned identical "
                   "(model id, document set, prompt/schema version — a cached bundle is refused "
                   "otherwise), so every *content* metric is unaffected. `determinism` is not: it "
                   "measures run-to-run agreement, and these runs were sampled across provider-side "
                   "change as well as model variance. Re-run with `--no-resume` for a single-sitting "
                   "number.\n")
    replayed = [s for s in exercised
                if s.provenance.single_invocation and s.provenance.documents_reused
                and s.provenance.invocations[:1] != (s.provenance.current,)]
    if replayed and not stitched:
        out.append("> **Replayed, not re-run.** " + ", ".join(f"`{s.candidate_id}`" for s in replayed) +
                   " was scored entirely from artefacts an earlier invocation paid for. Those runs *were* "
                   "sampled in a single sitting, so `determinism` means what it normally means — but the "
                   "numbers describe that session, not this one.\n")
    out.append("| candidate | invocations | documents reused | documents bought |")
    out.append("|---|---|---|---|")
    for s in exercised:
        prov = s.provenance
        invocations = "<br>".join(f"`{i}`" for i in prov.invocations) or "—"
        out.append(f"| `{s.candidate_id}` | {invocations} | {prov.documents_reused} | "
                   f"{prov.documents_bought} |")
    return "\n".join(out)


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
                "provenance": {
                    "invocations": list(s.provenance.invocations),
                    "current_invocation": s.provenance.current,
                    "single_invocation": s.provenance.single_invocation,
                    "documents_reused": s.provenance.documents_reused,
                    "documents_bought": s.provenance.documents_bought,
                    "statement": s.provenance.statement(),
                },
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
