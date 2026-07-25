"""The gating preconditions — PASS / FAIL to WIN, never weighted.

A gate is not a heavy score line. A candidate that would drop the locked VLM imagery path is
**disqualified**, not marked down; a candidate that cannot be the producer freezing the seed bundles
cannot restore KEYLESS==LIVE no matter how well it extracts; a floating ``-latest`` model id breaks
reproducibility whatever it scores today. Weighing those against accuracy would let a high score buy its
way past a locked decision, which is precisely the trade this project has already refused.

So gates live in their own type, are evaluated separately, and the comparative verdict removes any
candidate that is not ``PASS`` on every gate from winner consideration **before** any score is compared.
A gate that could not be checked is ``UNKNOWN``, and UNKNOWN also blocks: "we did not verify the VLM path
survived" is not the same as "it did", and only one of those is allowed to win.
"""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from typing import Literal

from .metrics import MetricValue
from .policy import BakeoffConfig, Candidate

GateStatus = Literal["PASS", "FAIL", "UNKNOWN"]


@dataclass(frozen=True)
class GateResult:
    """One precondition on one candidate."""

    name: str
    status: GateStatus
    detail: str

    @property
    def blocks_winning(self) -> bool:
        return self.status != "PASS"


@dataclass(frozen=True)
class GateReport:
    """Every gate for one candidate. ``eligible`` is the single thing the verdict consults."""

    candidate_id: str
    gates: tuple[GateResult, ...]

    @property
    def eligible(self) -> bool:
        return all(g.status == "PASS" for g in self.gates)

    @property
    def blocking(self) -> tuple[GateResult, ...]:
        return tuple(g for g in self.gates if g.blocks_winning)


# ── individual gates ──────────────────────────────────────────────────────────────────────────────

def gate_vlm_imagery(candidate: Candidate, *, image_calls_ok: int, image_calls_total: int) -> GateResult:
    """The locked in-scope VLM imagery path must survive — evidenced, not asserted.

    A declaration of ``multimodal: none`` fails outright. Anything else must be *demonstrated*: the run
    has to have made at least one standalone-image call that came back. No image call attempted →
    UNKNOWN, because a gate nobody exercised is not a gate anybody passed.
    """
    if candidate.multimodal == "none":
        return GateResult("vlm_imagery_path", "FAIL",
                          "declared text-only — would drop the locked VLM imagery path (disqualifier)")
    if image_calls_total == 0:
        return GateResult("vlm_imagery_path", "UNKNOWN",
                          f"declared multimodal={candidate.multimodal} but no standalone-image call was "
                          "exercised in this run — include an image document in the slice")
    if image_calls_ok < image_calls_total:
        return GateResult("vlm_imagery_path", "FAIL",
                          f"{image_calls_total - image_calls_ok}/{image_calls_total} standalone-image "
                          "calls failed")
    return GateResult("vlm_imagery_path", "PASS",
                      f"{image_calls_ok}/{image_calls_total} standalone-image calls returned "
                      f"(multimodal={candidate.multimodal})")


def gate_keyless_equals_live(candidate: Candidate, config: BakeoffConfig) -> GateResult:
    """The winner must run live in the shipped image AND be the producer that freezes the seed bundles.

    Three conditions, all necessary: the client must live on the shipped ingest path (a client under
    ``backend/eval`` is a measuring instrument, not a production extractor); its SDK must actually
    import (Gemini's live 500s today are exactly this failure); and it must be declared as the seed
    producer, because KEYLESS==LIVE holds *by construction* only when the same model produces both.
    """
    required_pkg = config.gates.production_client_package
    problems: list[str] = []
    if not candidate.client_module.startswith(required_pkg):
        problems.append(
            f"client lives in {candidate.client_module!r}, not under {required_pkg!r} — it cannot be the "
            "producer that freezes the seed bundles"
        )
    try:
        importlib.import_module(candidate.sdk_module)
    except Exception as exc:
        problems.append(f"SDK {candidate.sdk_module!r} does not import here ({type(exc).__name__}) — "
                        "it would 500 live in the shipped image")
    if not candidate.freezes_seed:
        problems.append("not declared as the seed-bundle producer (freezes_seed: false), so keyless "
                        "would not equal live by construction")
    if problems:
        return GateResult("keyless_equals_live", "FAIL", "; ".join(problems))
    return GateResult("keyless_equals_live", "PASS",
                      f"{candidate.client_module} is on the shipped ingest path, {candidate.sdk_module} "
                      "imports, and it is declared the seed producer")


def gate_pinned_model_id(candidate: Candidate, config: BakeoffConfig) -> GateResult:
    """The evaluated model id must be a concrete pinned version, never a floating alias.

    A floating alias silently changes what produced the frozen seed, which breaks reproducibility and
    KEYLESS==LIVE at once. The alias is a live-resilience fallback only — never a seed producer.
    """
    model_id = candidate.model_id.strip()
    if not model_id:
        return GateResult("pinned_model_id", "FAIL", "no model_id declared")
    lowered = model_id.casefold()
    for pattern in config.gates.floating_alias_patterns:
        if lowered.endswith(pattern.casefold()):
            return GateResult("pinned_model_id", "FAIL",
                              f"{model_id!r} matches the floating-alias pattern {pattern!r}")
    if model_id.upper().startswith("REPLACE-"):
        return GateResult("pinned_model_id", "UNKNOWN",
                          f"{model_id!r} is a config placeholder — pin a concrete version before running")
    return GateResult("pinned_model_id", "PASS", f"{model_id!r} is a concrete pinned id")


def gate_key_present(candidate: Candidate) -> GateResult:
    """Can this candidate be exercised at all? An unprovisioned key is a measurement fact, not a score.

    Reported as a gate so the scorecard cannot imply a three-way comparison that never ran.
    """
    if os.environ.get(candidate.key_env):
        return GateResult("exercisable", "PASS", f"{candidate.key_env} is set")
    return GateResult("exercisable", "FAIL",
                      f"{candidate.key_env} is not set — this candidate could not be exercised, so any "
                      "comparison excluding it is not the three-way measurement it might look like")


def gate_non_negotiable_floor(metric: MetricValue, floor: float | None) -> GateResult | None:
    """An optional hard floor on a non-negotiable metric. ``None`` floor → no gate at all.

    Deliberately unset by default: picking the number is a human judgement about how much fabrication is
    tolerable, and a scorer that invents that threshold has decided the question it was built to measure.
    """
    if floor is None:
        return None
    name = f"floor:{metric.name}"
    if metric.status != "measured":
        return GateResult(name, "UNKNOWN", f"{metric.name} was not measured ({metric.reason})")
    assert metric.value is not None
    if metric.value < floor:
        return GateResult(name, "FAIL", f"{metric.name}={metric.value:.3f} is below the floor {floor:.3f}")
    return GateResult(name, "PASS", f"{metric.name}={metric.value:.3f} clears the floor {floor:.3f}")


def evaluate_gates(
    candidate: Candidate,
    config: BakeoffConfig,
    *,
    image_calls_ok: int,
    image_calls_total: int,
    non_negotiable_metrics: dict[str, MetricValue] | None = None,
    require_key: bool = True,
) -> GateReport:
    """All gates for one candidate, in report order (the blocking ones first)."""
    gates: list[GateResult] = [
        gate_vlm_imagery(candidate, image_calls_ok=image_calls_ok, image_calls_total=image_calls_total),
        gate_keyless_equals_live(candidate, config),
        gate_pinned_model_id(candidate, config),
    ]
    if require_key:
        gates.append(gate_key_present(candidate))
    for name, floor in (config.gates.non_negotiable_floors or {}).items():
        metric = (non_negotiable_metrics or {}).get(name)
        if metric is None:
            if floor is not None:
                gates.append(GateResult(f"floor:{name}", "UNKNOWN",
                                        f"a floor is configured for {name!r} but it was not scored"))
            continue
        result = gate_non_negotiable_floor(metric, floor)
        if result is not None:
            gates.append(result)
    return GateReport(candidate_id=candidate.id, gates=tuple(gates))


__all__ = [
    "GateReport",
    "GateResult",
    "GateStatus",
    "evaluate_gates",
    "gate_key_present",
    "gate_keyless_equals_live",
    "gate_non_negotiable_floor",
    "gate_pinned_model_id",
    "gate_vlm_imagery",
]
