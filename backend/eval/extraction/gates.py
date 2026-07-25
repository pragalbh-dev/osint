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

ONE GATE, ONE DECIDER
─────────────────────
Every caller — the dry ``preflight`` and the real run alike — reaches the imagery gate through
:func:`gate_vlm_imagery` with an :class:`ImageryObservations`, and builds that through the single function
:func:`eval.extraction.vlm_probe.observations_for`. The alternative, which this harness shipped and has
now fixed, was two callers reading two different sources: preflight judged the gate on the *recorded*
probe evidence while the run judged it on the calls that run happened to make, so preflight could show
PASS on all three candidates and the run could then return ``NO_ELIGIBLE_CANDIDATE``. Green light followed
by silent disqualification is the exact trap this project keeps getting bitten by, and the fix is
structural: there is no code path that reaches the gate with only half the observations.
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


# ── the imagery observations: the one input the imagery gate is judged on ──────────────────────────

@dataclass(frozen=True)
class ImageryObservations:
    """Every standalone-image call known about one candidate, from every source that saw one.

    Two sources exist and both are first-hand: the recorded ``vlm-probe`` evidence (a real image through
    the real imagery lane, pinned to the model id it was recorded against) and the standalone-image calls a
    bake-off run made itself. They are *summed*, not chosen between — a candidate that failed the probe and
    succeeded in the run has one failure and one success, and the gate should see both.

    ``sources`` exists so the gate's own detail line can say where its evidence came from. A reader who
    sees PASS is entitled to know whether anything was exercised today or the verdict rests on a record.
    """

    calls_ok: int = 0
    calls_total: int = 0
    sources: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.calls_ok < 0 or self.calls_total < 0 or self.calls_ok > self.calls_total:
            raise ValueError(
                f"ImageryObservations({self.calls_ok}/{self.calls_total}) is not a possible observation — "
                "more successful calls than calls would let a failure be washed out by arithmetic"
            )

    def plus(self, other: ImageryObservations) -> ImageryObservations:
        return ImageryObservations(
            calls_ok=self.calls_ok + other.calls_ok,
            calls_total=self.calls_total + other.calls_total,
            sources=self.sources + other.sources,
        )

    @property
    def described(self) -> str:
        return ", ".join(self.sources) if self.sources else "nothing exercised"


# ── individual gates ──────────────────────────────────────────────────────────────────────────────

def gate_vlm_imagery(candidate: Candidate, imagery: ImageryObservations) -> GateResult:
    """The locked in-scope VLM imagery path must survive — evidenced, not asserted.

    A declaration of ``multimodal: none`` fails outright. Anything else must be *demonstrated*: some
    standalone-image call, in the recorded probe or in this run, has to have come back. No image call
    attempted anywhere → UNKNOWN, because a gate nobody exercised is not a gate anybody passed.

    This is the **only** function that turns imagery observations into a gate status, and it takes them as
    one object so no caller can supply half of them. Preflight and the run therefore cannot disagree.
    """
    if candidate.multimodal == "none":
        return GateResult("vlm_imagery_path", "FAIL",
                          "declared text-only — would drop the locked VLM imagery path (disqualifier)")
    if imagery.calls_total == 0:
        return GateResult("vlm_imagery_path", "UNKNOWN",
                          f"declared multimodal={candidate.multimodal} but no standalone-image call has "
                          "been exercised — run `vlm-probe`, or include an image document in the slice "
                          f"({imagery.described})")
    if imagery.calls_ok < imagery.calls_total:
        return GateResult("vlm_imagery_path", "FAIL",
                          f"{imagery.calls_total - imagery.calls_ok}/{imagery.calls_total} standalone-image "
                          f"calls failed ({imagery.described})")
    return GateResult("vlm_imagery_path", "PASS",
                      f"{imagery.calls_ok}/{imagery.calls_total} standalone-image calls returned "
                      f"(multimodal={candidate.multimodal}; {imagery.described})")


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


def gate_non_negotiable(name: str, metric: MetricValue | None, floor: float | None) -> GateResult:
    """A metric named in ``gates.non_negotiable_floors`` must be **measured**, and must clear any floor.

    Two distinct disciplines, one gate, because both are ways of trading a non-negotiable away:

    * **Measured.** A declared non-negotiable that nobody scored is ``UNKNOWN``, and UNKNOWN blocks — even
      with no floor configured. Without this, the relative veto in :func:`eval.extraction.compare.decide`
      has nothing to compare, so a candidate whose fabrication line simply failed to measure could win on
      the strength of the lines that did. "We did not check whether it fabricates" is not a pass.
    * **Above the floor.** ``None`` means no absolute threshold is enforced, and the report says so:
      picking the number is a human judgement about how much fabrication is tolerable, and a scorer that
      invents that threshold has decided the question it was built to measure. The *relative* veto still
      applies, and it needs no invented number because it reuses the margin rule.
    """
    gate_name = f"non-negotiable:{name}"
    if metric is None:
        return GateResult(gate_name, "UNKNOWN",
                          f"{name} is declared non-negotiable but was not scored in this run — an "
                          "unmeasured non-negotiable cannot be traded away by absence")
    if metric.status != "measured":
        return GateResult(gate_name, "UNKNOWN",
                          f"{name} is declared non-negotiable but was not measured ({metric.reason})")
    assert metric.value is not None
    if floor is None:
        return GateResult(gate_name, "PASS",
                          f"{name}={metric.value:.3f} measured; no absolute floor is configured, so only "
                          "the relative veto (materially worse than a rival) applies")
    if metric.value < floor:
        return GateResult(gate_name, "FAIL", f"{name}={metric.value:.3f} is below the floor {floor:.3f}")
    return GateResult(gate_name, "PASS", f"{name}={metric.value:.3f} clears the floor {floor:.3f}")


def non_negotiable_gate_names(config: BakeoffConfig) -> tuple[str, ...]:
    """The gate names that can only be judged once a run has produced numbers.

    Named so ``preflight`` can *say* what it deferred instead of either inventing a verdict or quietly
    omitting a blocking precondition. A reader of a green preflight is entitled to know which gates are
    still ahead of the candidate.
    """
    return tuple(f"non-negotiable:{name}" for name in (config.gates.non_negotiable_floors or {}))


def dry_gates(
    candidate: Candidate,
    config: BakeoffConfig,
    *,
    imagery: ImageryObservations,
    require_key: bool = True,
) -> GateReport:
    """The preconditions judgeable **without a run**: imagery, KEYLESS==LIVE, the pin, the key.

    The imagery gate belongs here even though it is about model behaviour, because it is judged on
    *recorded* evidence — a real image through the real lane, already paid for — rather than on this run.
    That is exactly what makes the preflight/run symmetry possible.
    """
    gates: list[GateResult] = [
        gate_vlm_imagery(candidate, imagery),
        gate_keyless_equals_live(candidate, config),
        gate_pinned_model_id(candidate, config),
    ]
    if require_key:
        gates.append(gate_key_present(candidate))
    return GateReport(candidate_id=candidate.id, gates=tuple(gates))


def evaluate_gates(
    candidate: Candidate,
    config: BakeoffConfig,
    *,
    imagery: ImageryObservations,
    non_negotiable_metrics: dict[str, MetricValue] | None = None,
    require_key: bool = True,
) -> GateReport:
    """Every gate for one candidate after a run: the dry preconditions plus the non-negotiable metrics.

    ``imagery`` is required and is the *whole* observation set — build it with
    :func:`eval.extraction.vlm_probe.observations_for` so the recorded evidence is never left behind. That
    is the single decider Ruling 3 asked for: preflight and the run reach :func:`gate_vlm_imagery` with the
    same evidence, and the run merely adds the calls it made itself.

    The non-negotiable gates are appended here and **not** in :func:`dry_gates` because they need measured
    numbers. Their absence in preflight is stated by :func:`non_negotiable_gate_names`, never implied to be
    a pass: this is the run knowing *more* than preflight, which is the safe direction, unlike the defect
    Ruling 3 closed where the run knew *less*.
    """
    gates = list(dry_gates(candidate, config, imagery=imagery, require_key=require_key).gates)
    for name, floor in (config.gates.non_negotiable_floors or {}).items():
        gates.append(gate_non_negotiable(name, (non_negotiable_metrics or {}).get(name), floor))
    return GateReport(candidate_id=candidate.id, gates=tuple(gates))


__all__ = [
    "GateReport",
    "GateResult",
    "GateStatus",
    "ImageryObservations",
    "dry_gates",
    "evaluate_gates",
    "gate_key_present",
    "gate_keyless_equals_live",
    "gate_non_negotiable",
    "gate_pinned_model_id",
    "gate_vlm_imagery",
    "non_negotiable_gate_names",
]
