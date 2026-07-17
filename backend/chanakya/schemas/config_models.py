"""The seven config surfaces + the ``ConfigBundle`` (master §4.4).

F0 freezes the *shapes* and the **load-bearing typed fields** (weights, thresholds, half-lives) so
code can read them typed and gate G6 can assert "no magic numbers in code — all read from config".
DATA-C authors the *content*. Every model is a ``ConfigModel`` (``extra="allow"``) so DATA-C may add
knobs without an F0-amendment; only the typed fields below are a frozen contract.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import ConfigModel
from .claim import SourceRegistryEntry

# ── ontology.yaml ──────────────────────────────────────────────────────────────────────────────

class TypeDef(ConfigModel):
    """A node/edge/event type definition — schema designed, instances discovered (DECISIONS)."""

    name: str
    freshness_class: str | None = None  # → a half-life key in credibility.yaml
    attrs: list[str] = []


class OntologyConfig(ConfigModel):
    node_types: list[TypeDef] = []
    edge_types: list[TypeDef] = []
    event_types: list[TypeDef] = []


# ── sources.yaml ───────────────────────────────────────────────────────────────────────────────

class SourcesConfig(ConfigModel):
    """The source registry (independence + resolver inputs)."""

    sources: list[SourceRegistryEntry] = []

    def as_map(self) -> dict[str, SourceRegistryEntry]:
        return {s.source_id: s for s in self.sources}


# ── credibility.yaml ─────────────────────────────────────────────────────────────────────────

class CredibilityConfig(ConfigModel):
    """Resolver factor rubric + weights + gates + thresholds + half-lives (§3.4/§3.6).

    ``factor_weights`` (authority/process/directness/track_record) are analyst-set and normalised;
    ``R(source)`` is the rubric's *output*, never a hand-typed per-class constant (Module 1).
    """

    factor_weights: dict[str, float] = {}  # e.g. {"authority":0.35,"process":0.25,...}
    source_class_factors: dict[str, dict[str, float]] = {}  # class → per-factor 0–1 scores
    integrity_penalties: dict[str, float] = {}  # flag → multiplier (recycled, too-clean, …)
    thresholds: dict[str, float] = {}  # {"confirmed":0.80, "probable":0.50}
    half_lives_days: dict[str, float] = {}  # edge/event type → half-life in days (∞ = durable, omit)


# ── resolution.yaml ────────────────────────────────────────────────────────────────────────────

class ResolutionConfig(ConfigModel):
    """Merge scoring + bands + blocking + seeded alias table + transliteration (§3.9)."""

    merge_weights: dict[str, float] = {}  # {"attribute":0.30,"relational":0.40,"temporal":0.15,"source_asserted":0.15}
    bands: dict[str, float] = {}  # {"auto_merge":0.85, "hitl_low":0.55}
    blocking_keys: list[str] = []
    alias_table: dict[str, list[str]] = {}  # canonical → aliases (seeded; grows from HITL merges)
    transliteration: dict[str, str] = {}


# ── templates.yaml ─────────────────────────────────────────────────────────────────────────────

class EvidenceTemplate(ConfigModel):
    """An evidence-requirement template per assertion type (§3.7)."""

    assertion_type: str
    require: dict[str, Any] = {}  # e.g. {"any_of":[{"imagery_confirmation":{"within_days":365}}, …]}
    on_fail: str = "insufficient_evidence"
    refusal_template: str | None = None  # fill-in-the-blank; never regenerated prose (§3.11)


class TemplatesConfig(ConfigModel):
    templates: list[EvidenceTemplate] = []

    def as_map(self) -> dict[str, EvidenceTemplate]:
        return {t.assertion_type: t for t in self.templates}


# ── subjects.yaml ──────────────────────────────────────────────────────────────────────────────

class SubjectLens(ConfigModel):
    """A subject = a query-time lens (master §1 invariant #6; gate G10): anchors + hop/materiality rules."""

    subject_id: str
    anchors: list[str] = []  # anchor entity ids the lens centres on
    max_hops: int = 3
    materiality_filter: dict[str, Any] = {}  # e.g. {"min_chokepoint_count":1} or {} for no filter
    target_queries: list[str] = []


class SubjectsConfig(ConfigModel):
    subjects: list[SubjectLens] = []

    def as_map(self) -> dict[str, SubjectLens]:
        return {s.subject_id: s for s in self.subjects}


# ── observables.yaml ───────────────────────────────────────────────────────────────────────────

class ObservableDef(ConfigModel):
    """A declarative tripwire (§3.8) — a condition over existing attrs/precomputed metrics, no new code."""

    observable_id: str
    subject: str | None = None
    trigger: dict[str, Any] = {}  # {"on":…, "edge_type":…, "match_on":[…], "anchors_within_hops":…}
    severity: str = "notify"
    disposition: list[str] = Field(default_factory=lambda: ["real", "noise", "needs-more"])


class ObservablesConfig(ConfigModel):
    observables: list[ObservableDef] = []


# ── the bundle ─────────────────────────────────────────────────────────────────────────────────

class ConfigBundle(ConfigModel):
    """All seven surfaces + a monotonic ``version`` the config store bumps on every hot write."""

    version: int = 0
    ontology: OntologyConfig = OntologyConfig()
    sources: SourcesConfig = SourcesConfig()
    credibility: CredibilityConfig = CredibilityConfig()
    resolution: ResolutionConfig = ResolutionConfig()
    templates: TemplatesConfig = TemplatesConfig()
    subjects: SubjectsConfig = SubjectsConfig()
    observables: ObservablesConfig = ObservablesConfig()


# The seven surface filenames, in the fixed load order (config store reads these from config/).
CONFIG_SECTIONS: dict[str, type[ConfigModel]] = {
    "ontology": OntologyConfig,
    "sources": SourcesConfig,
    "credibility": CredibilityConfig,
    "resolution": ResolutionConfig,
    "templates": TemplatesConfig,
    "subjects": SubjectsConfig,
    "observables": ObservablesConfig,
}
