"""The bake-off's declared knobs — replication, margin, gates, weights, match policy, candidates.

Everything the *verdict* depends on is loaded from ``config/bakeoff.yaml`` and nothing is a literal in
scorer code. That is not decoration: the matcher's leniency **is** the measurement, and the margin rule
is what stops the harness manufacturing a ranking out of run-to-run jitter, so both have to sit where a
reader of the scorecard can see and change them.

The models here are plain pydantic records with ``extra="forbid"`` — a typo'd knob is an error, never a
silently-ignored default, because a silently-ignored margin is a fabricated ranking waiting to happen.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

SCHEMA_PREFIX = "rk-bakeoff/"

#: The similarity functions a match policy may name (all from ``rapidfuzz.fuzz``, all deterministic).
SimilarityName = Literal["token_set_ratio", "token_sort_ratio", "partial_ratio", "ratio"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Replication(_Strict):
    """How many runs per candidate, and the floor below which ranking is structurally refused."""

    runs_per_candidate: int = Field(ge=1)
    #: Below this many runs the comparative report returns INSUFFICIENT_REPLICATION and names no winner —
    #: with one or two samples the run-to-run spread is not estimable, so *every* gap is within unmeasured
    #: noise. This is the anti-fabrication rule applied to our own benchmark.
    min_runs_for_ranking: int = Field(ge=2)


class Margin(_Strict):
    """The minimum-margin rule: ``|Δmean| >= max(min_absolute, noise_multiplier * pooled_sd)``."""

    min_absolute: float = Field(ge=0.0)
    noise_multiplier: float = Field(ge=0.0)
    per_metric_min_absolute: dict[str, float] = {}

    def floor_for(self, metric: str) -> float:
        return self.per_metric_min_absolute.get(metric, self.min_absolute)


class GateConfig(_Strict):
    """Gate parameters — the patterns and package name the PASS/FAIL preconditions are checked against."""

    floating_alias_patterns: list[str]
    production_client_package: str
    non_negotiable_floors: dict[str, float | None] = {}


class MatchPolicy(_Strict):
    """What counts as "the same claim". The documented, configurable leniency of the whole measurement."""

    #: Default is ``token_sort_ratio``, not the more usual ``token_set_ratio``: the latter compares only
    #: the shared-token intersection and so scores an invented name that shares one token with the truth
    #: as a near-match, which would report fabrication as recall. See ``config/bakeoff.yaml`` for the
    #: full trade-off note.
    similarity: SimilarityName = "token_sort_ratio"
    require_same_form: bool = True
    require_same_polarity: bool = True
    predicate_policy: Literal["exact", "normalized", "ignore"] = "normalized"
    entity_type_policy: Literal["exact", "normalized", "ignore"] = "normalized"
    role_min_similarity: float = Field(ge=0.0, le=1.0)
    pair_min_similarity: float = Field(ge=0.0, le=1.0)
    span_policy: Literal["ignore", "bonus", "require"] = "bonus"
    span_iou_floor: float = Field(ge=0.0, le=1.0)
    span_bonus_weight: float = Field(ge=0.0, le=1.0)
    grounding_similarity: float = Field(ge=0.0, le=1.0)

    def describe(self) -> list[str]:
        """The policy as human-readable lines, printed *above* every number it produced."""
        lines = [
            f"similarity        : {self.similarity} (rapidfuzz, scaled 0..1)",
            f"same form/polarity: form={self.require_same_form}  polarity={self.require_same_polarity}",
            f"predicate         : {self.predicate_policy}      entity_type: {self.entity_type_policy}",
            f"thresholds        : per-role >= {self.role_min_similarity}, pair mean >= {self.pair_min_similarity}",
            f"spans             : {self.span_policy} (IoU floor {self.span_iou_floor}, bonus weight {self.span_bonus_weight})",
            f"grounding         : surface must reach {self.grounding_similarity} against the cited text",
        ]
        return lines


class Pricing(_Strict):
    """Per-million-token prices. Absent (``None`` on the candidate) means cost is reported UNPRICED."""

    input_per_mtok: float = Field(ge=0.0)
    output_per_mtok: float = Field(ge=0.0)


class Candidate(_Strict):
    """One model under test — a *declaration*, checked at run time, never assumed to be exercisable."""

    id: str
    label: str
    provider: str
    model_id: str
    client_module: str
    client_class: str
    sdk_module: str
    key_env: str
    #: ``native`` = the model itself reads images; ``tiered`` = a declared multimodal tier retains the
    #: locked VLM path; ``none`` = text-only, which is a DISQUALIFIER (plan §8), not a score deduction.
    multimodal: Literal["native", "tiered", "none"] = "none"
    #: Would this candidate be the producer that freezes the seed bundles? KEYLESS==LIVE holds only by
    #: construction, i.e. only when the live extractor and the seed producer are the same model.
    freezes_seed: bool = False
    pricing: Pricing | None = None


class BakeoffConfig(_Strict):
    """The whole declared bake-off: replication, margin, gates, weights, match policy, candidates."""

    schema_version: str
    replication: Replication
    margin: Margin
    gates: GateConfig
    weights: dict[str, float]
    match_policy: MatchPolicy
    candidates: list[Candidate]

    def weight_for(self, metric: str) -> float:
        return self.weights.get(metric, 0.0)

    def candidate(self, candidate_id: str) -> Candidate:
        for cand in self.candidates:
            if cand.id == candidate_id:
                return cand
        raise KeyError(f"no candidate {candidate_id!r} declared in bakeoff config")


def load_bakeoff_config(path: str | Path | None = None) -> BakeoffConfig:
    """Load ``config/bakeoff.yaml`` (or an explicit path). Raises loudly on an unrecognised schema.

    A wrong-shaped config must fail here rather than fall back to defaults: a default margin silently
    substituted for a missing one is exactly how a within-noise gap gets reported as a ranking.
    """
    if path is None:
        from chanakya import settings

        path = settings.config_dir() / "bakeoff.yaml"
    raw: Any = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    version = str(raw.get("schema_version", ""))
    if not version.startswith(SCHEMA_PREFIX):
        raise ValueError(
            f"{path}: expected schema_version starting {SCHEMA_PREFIX!r}, got {version!r} — refusing to "
            "guess the shape of a config the verdict depends on"
        )
    return BakeoffConfig.model_validate(raw)


__all__ = [
    "BakeoffConfig",
    "Candidate",
    "GateConfig",
    "Margin",
    "MatchPolicy",
    "Pricing",
    "Replication",
    "SimilarityName",
    "load_bakeoff_config",
]
