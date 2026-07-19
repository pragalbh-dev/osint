"""The nine config surfaces + the ``ConfigBundle`` (master §4.4).

F0 freezes the *shapes* and the **load-bearing typed fields** (weights, thresholds, half-lives) so
code can read them typed and gate G6 can assert "no magic numbers in code — all read from config".
DATA-C authors the *content*. Every model is a ``ConfigModel`` (``extra="allow"``) so DATA-C may add
knobs without an F0-amendment; only the typed fields below are a frozen contract.

F0-amendment (EVAL RCA, DECISIONS §6 "EVAL" D-A/D-B): edge types carry ``from``/``to``/``symmetric``/
``extractor`` (domain/range for the write-time re-lane + the extraction enum), and a 9th surface —
``entities.yaml`` (the entity canonical-id registry) — mirrors ``places.yaml``.
"""

from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import ConfigModel
from .claim import SourceRegistryEntry
from .values import PrecisionClass

# ── ontology.yaml ──────────────────────────────────────────────────────────────────────────────

def _as_list(v: str | list[str] | None) -> list[str]:
    """Normalise a scalar/list/None domain-or-range spec to a list of node-type names."""
    if v is None:
        return []
    return [v] if isinstance(v, str) else list(v)


class TypeDef(ConfigModel):
    """A node/edge/event type definition — schema designed, instances discovered (DECISIONS).

    Edge types additionally declare a **domain/range** — ``from``/``to`` node types — plus ``symmetric``
    and ``extractor`` flags (D-A, the edge-vocabulary collision fix). Endpoint types make each *extractor*
    edge uniquely determinable, so a write-time re-lane can put a fact on the edge its endpoints imply
    regardless of the verb the model chose (``manufactures``↔``supplies-component``, ``equips``'s
    direction), and ``extractor: true`` marks the relationship edges the LLM is allowed to assert (the
    extraction enum). These fields are inert on node/event types. Read via :mod:`chanakya.ontology`.
    """

    name: str
    freshness_class: str | None = None  # → a half-life key in credibility.yaml
    attrs: list[str] = []
    # edge-only (ignored on node/event types) — D-A:
    from_type: str | list[str] | None = Field(default=None, alias="from")  # domain: subject node type(s)
    to_type: str | list[str] | None = Field(default=None, alias="to")      # range:  object  node type(s)
    symmetric: bool = False   # same-as / distinct-from / substitutable-by / corroborates / contradicts
    extractor: bool = False   # part of the extraction enum (a relationship edge the LLM may assert)

    def from_types(self) -> list[str]:
        return _as_list(self.from_type)

    def to_types(self) -> list[str]:
        return _as_list(self.to_type)


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
    # The evaluation "now" for freshness/staleness (age = as_of − event_time). rebuild() is clock-free
    # (G1/G2), so "now" is an explicit input, never a wall-clock read: an ISO ``YYYY-MM-DD`` pinned here
    # (retro-analysis / reproducible demo), stamped by the API at request time for a live "now", or —
    # left null — the newest available claim date is the fallback (see ``chanakya.timeref``). A *past*
    # ``as_of`` also rewinds the graph: rebuild hides claims not yet available then (point-in-time view).
    as_of: str | None = None


# ── resolution.yaml ────────────────────────────────────────────────────────────────────────────

class ResolutionConfig(ConfigModel):
    """Merge scoring + bands + blocking + seeded alias table + transliteration (§3.9)."""

    merge_weights: dict[str, float] = {}  # {"attribute":0.30,"relational":0.40,"temporal_consistency":0.15,"source_asserted":0.15}
    bands: dict[str, float] = {}  # {"auto_merge":0.85, "hitl_low":0.55}
    blocking_keys: list[str] = []
    alias_table: dict[str, list[str]] = {}  # canonical → aliases (seeded; grows from HITL merges)
    transliteration: dict[str, str] = {}


# ── places.yaml (the place gazetteer — 8th surface; RESOLVE consumes at rebuild) ─────────────────

class PlaceEntry(ConfigModel):
    """One canonical place node in the gazetteer (``config/places.yaml``; md/13).

    A curated *prior* for place resolution, **not a closed world**: at rebuild a frozen coord beyond
    the precision-class radius mints a *new* place node (open-world). Carries the exact WGS84 coord +
    the aliases/hard-IDs (ICAO/LOCODE) that customs & aviation sources actually use + the do-not-merge
    traps (Karachi-Port ≠ Port-Qasim). Coord canonicalisation/geocoding is INGEST's (frozen onto the
    claim); this is the identity target RESOLVE matches those frozen coords + toponyms against.
    """

    place_id: str
    canonical_name: str
    kind: str | None = None  # airbase | seaport | sam_site | facility | airfield …
    precision_class: PrecisionClass | None = None  # coarsest identity the node needs (md/13 §1)
    canonical_dd: tuple[float, float] | None = None  # (lat, lon) WGS84
    aliases: list[str] = []
    icao: str | None = None  # unique hard-ID (airbase)
    locode: str | None = None  # unique hard-ID (seaport, e.g. PKBQM)
    admin: str | None = None
    provenance: str | None = None  # real | synthetic | approximate
    distinct_from: list[str] = []  # explicit do-not-merge place_ids (hard veto, before banding)


class PlacesConfig(ConfigModel):
    """The seed place gazetteer + per-precision-class proximity radii (md/13; hot-config extensible).

    Loaded from ``config/places.yaml`` through the live store like every other surface, so an analyst
    can add a place or fix a coord with no restart. RESOLVE reuses the ``merge_score``/bands machinery
    over these entries (toponym/alias match + geodesic proximity by ``precision_class``).
    """

    crs: str = "EPSG:4326"  # canonical output frame (WGS84 decimal degrees)
    places: list[PlaceEntry] = []
    proximity_radius_m: dict[str, float] = {}  # precision_class → auto-resolve radius (1x–3x → HITL; beyond → new place)

    def as_map(self) -> dict[str, PlaceEntry]:
        return {p.place_id: p for p in self.places}


# ── entities.yaml (the entity canonical-id registry — 9th surface; RESOLVE consumes at rebuild) ──

class EntityEntry(ConfigModel):
    """One canonical entity in the registry (``config/entities.yaml``; mirrors :class:`PlaceEntry`, D-B).

    The stable semantic-id target RESOLVE resolves surface forms onto — via alias-equivalence (this
    table ∪ learned merges) + fuzzy/attribute scoring — so the graph, subject lenses, observables, and
    the oracle share ONE id space (closing the id-namespace split). A curated *prior*, not a closed
    world: an unknown entity still mints its own node. The extractor never emits these ids; it emits
    surface form + type, and RESOLVE maps surface→id. Consumed at rebuild like the place gazetteer.
    """

    entity_id: str                  # stable canonical id (== the oracle id, e.g. comp_ht233, unit_paad)
    type: str                       # ontology node type (component | variant | manufacturer | unit | …)
    canonical_name: str
    aliases: list[str] = []         # known surface forms that resolve to this entity
    distinct_from: list[str] = []   # explicit do-not-merge entity_ids (hard veto, before banding)
    attrs: dict[str, Any] = {}      # optional seeded node attrs (e.g. foreign_control) — DATA-C-authored


class EntitiesConfig(ConfigModel):
    """The seed entity registry (``config/entities.yaml``; hot-config extensible, mirrors PlacesConfig).

    Loaded through the live store like every other surface, so an analyst can add an entity or fix an
    alias with no restart. RESOLVE consumes it to (a) seed the alias index with each entry's
    canonical/alias equivalence class and (b) elect the ``entity_id`` as a cluster's canonical node id.
    Open-world: entries are a prior, never a closed vocabulary.
    """

    entities: list[EntityEntry] = []

    def as_map(self) -> dict[str, EntityEntry]:
        return {e.entity_id: e for e in self.entities}


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
    subject: str | None = None  # a lens id: broad graph-hop scope (anchors + anchors_within_hops)
    watch_instances: list[str] = []  # explicit resolved entity ids to watch; scope = lens ∪ this set.
    # Filled by explicit multi-select (UI sends resolved ids) or an upstream text→observable proposer
    # (ASK) that resolves named mentions to ids. Match is always on the RESOLVED instance, never a
    # designator string (§3.8). Empty + a subject = lens-only scope; empty + no subject = unscoped.
    trigger: dict[str, Any] = {}  # {"on":…, "edge_type":…, "match_on":[…], "anchors_within_hops":…}
    severity: str = "notify"
    disposition: list[str] = Field(default_factory=lambda: ["real", "noise", "needs-more"])


class ObservablesConfig(ConfigModel):
    observables: list[ObservableDef] = []


# ── the bundle ─────────────────────────────────────────────────────────────────────────────────

class ConfigBundle(ConfigModel):
    """All nine surfaces + a monotonic ``version`` the config store bumps on every hot write."""

    version: int = 0
    ontology: OntologyConfig = OntologyConfig()
    sources: SourcesConfig = SourcesConfig()
    credibility: CredibilityConfig = CredibilityConfig()
    resolution: ResolutionConfig = ResolutionConfig()
    templates: TemplatesConfig = TemplatesConfig()
    subjects: SubjectsConfig = SubjectsConfig()
    observables: ObservablesConfig = ObservablesConfig()
    places: PlacesConfig = PlacesConfig()
    entities: EntitiesConfig = EntitiesConfig()


# The nine surface filenames, in the fixed load order (config store reads these from config/).
CONFIG_SECTIONS: dict[str, type[ConfigModel]] = {
    "ontology": OntologyConfig,
    "sources": SourcesConfig,
    "credibility": CredibilityConfig,
    "resolution": ResolutionConfig,
    "templates": TemplatesConfig,
    "subjects": SubjectsConfig,
    "observables": ObservablesConfig,
    "places": PlacesConfig,
    "entities": EntitiesConfig,
}
