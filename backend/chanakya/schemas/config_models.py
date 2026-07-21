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
    #: Source documents deliberately **held out of the boot seed** — the reviewer's live-ingest set.
    #: Their frozen claim bundles stay on disk and stay ingestable through the keyless ``POST /ingest``
    #: lane; this list only decides what is *already there* when the app boots, never what exists. It is
    #: declared here (not buried in code or an env var) so the withholding is auditable: a reviewer can
    #: read exactly which documents the "before" graph is missing. Holding a document back automatically
    #: holds back everything derived from it (``<doc>__basing.json`` / ``<doc>__attr.json``) — otherwise
    #: the before-graph would assert an inference whose premises had not arrived
    #: (``ingest.seed.bundle_belongs_to_doc``). ``CHANAKYA_SEED_WITHHOLD`` overrides at deploy time.
    withheld_from_seed: list[str] = []

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
    # Which assessed statuses an ANSWER may rest a link on — walk as the spine of a trace and name its
    # far end as a finding (ASK; spine/09). Strongest first; ties break in this order. Same shape and
    # doctrine as ``supersede_floor.newer_status_allow``: a list of status names the machine emits, never
    # a second copy of a threshold. **Not a filter** — a link outside the band is still traversed and is
    # reported as *weighed and not carried*, with its status and its citation, because a suppressed
    # low-credibility attribution is indistinguishable from one that was never seen. Empty ⇒ no band is
    # declared, so ASK asserts nothing on status grounds (fails closed).
    assertable_status: list[str] = []
    # ASK answer-integrity gate: the LLM entailment ("NLI") judge that runs ON TOP of the always-on
    # deterministic citation checks (cited / citation exists / hop-support / real counts). The
    # deterministic layer already guarantees no naked or fabricated sentence — every sentence is *built
    # from* the claim_ids the tools returned — so this extra NLI pass is a belt on braces whose only
    # marginal catch is analyst-authored edge phrasing that over-claims a relation. Because the judge
    # "defaults to no when unsure" and is blind to resolved identity on non-hop sentences, it is the sole
    # source of spurious whole-answer withholding on free-form queries. Default OFF: run on deterministic
    # grounding alone. Flip true (hot-config, no restart) to re-enable the judge.
    entailment_judge_enabled: bool = False


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
    # How much a frozen coordinate is worth, by how INGEST obtained it (``GeocodeCandidate.source`` →
    # ``confidence``). A parsed grid/DMS is the source's own statement; a Nominatim centroid for a vague
    # regional phrase ("central Punjab") is a guess — RESOLVE must be able to tell them apart, and an
    # analyst must be able to retune the gap without a code change. Empty → the INGEST defaults.
    geocode_confidence: dict[str, float] = {}  # "coord-parse" | "gazetteer" | "relative-offset" | "nominatim"

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
    # Optional PROSE name for answer text. ``canonical_name`` is an *identity* string — it carries
    # disambiguating annotations ("(relocation subject)", "(export designator; …; ~260 km)") that read
    # badly mid-sentence, and the surface form a document happened to use can be vaguer than the entity
    # the registry resolved it to ("Pakistan Air Force" for a specific fire unit). ``display_name`` lets
    # the registry declare the most specific *accurate* name to show, without inventing specificity the
    # sources do not support. Opt-in: absent → the node's own resolved name is shown unchanged.
    display_name: str | None = None
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
    """Analyst-authored ANSWER COPY: the evidence-requirement templates + their refusal strings, the
    no-coverage phrase, and how a relation reads out loud. Presentation, deliberately separate from
    ``ontology.yaml`` — the ontology is the *semantic* contract (types, domain/range, freshness_class,
    instance_key, supplier_end) that extraction, resolution, rebuild, scoring and materiality reason over,
    and wording churn does not belong in a file half the pipeline depends on. Answer prose is still
    resolved backend-side because it is cited and entailment-validated there (``agent/validate.py``)."""

    templates: list[EvidenceTemplate] = []
    # What ``{next_coverage_due}`` renders as when no revisit date is derivable (no providing source
    # declares a numeric cadence, or the gap was raised by a stage that schedules nothing). "unscheduled"
    # alone half-undercuts the promise to name *when next coverage is due*; the honest reading is that the
    # gap is an untasked collection requirement — itself a finding. Analyst-editable, never a date the
    # code invents (§3.7: next_coverage_due is generated from cadence or it does not exist).
    unscheduled_coverage_phrase: str = "unscheduled"
    # edge type → {forward, inverse, by_from_type?} — the natural clause an answer uses instead of the
    # machine identifier ("X is linked to Y via 'based-at'"). See :meth:`edge_clause`.
    edge_phrasing: dict[str, dict[str, Any]] = {}

    def as_map(self) -> dict[str, EvidenceTemplate]:
        return {t.assertion_type: t for t in self.templates}

    def edge_clause(
        self, edge_type: str, *, forward: bool = True, from_type: str | None = None
    ) -> str | None:
        """The human clause for reading an edge — ``"is based at"`` rather than ``"via 'based-at'"``.

        ``forward`` reads the edge in its declared ``from -> to`` direction; ``forward=False`` reads it the
        other way, which a multi-hop trace needs because it walks bidirectionally and often enters a hop at
        the object end. ``from_type`` is the *actual* subject node's type: a ``by_from_type`` override for
        it wins, since one lane can be entered by different kinds of subject (a ``unit`` on the ``equips``
        lane *fields* a variant; a ``component`` *is fitted to* one).

        Returns ``None`` when nothing is declared, so the caller falls back to the bare edge name and an
        analyst-added edge never breaks an answer. Rendering only — never changes the asserted fact, its
        status, or its citations.
        """
        block = self.edge_phrasing.get(edge_type)
        if not block:
            return None
        key = "forward" if forward else "inverse"
        overrides = block.get("by_from_type")
        if from_type and isinstance(overrides, dict):
            override = overrides.get(from_type)
            if isinstance(override, dict) and isinstance(override.get(key), str):
                return str(override[key])
        value = block.get(key)
        return str(value) if isinstance(value, str) else None


# ── subjects.yaml ──────────────────────────────────────────────────────────────────────────────

class SubjectLens(ConfigModel):
    """A subject = a query-time lens (master §1 invariant #6; gate G10): anchors + hop/materiality rules."""

    subject_id: str
    anchors: list[str] = []  # anchor entity ids the lens centres on
    max_hops: int = 3
    materiality_filter: dict[str, Any] = {}  # e.g. {"min_chokepoint_count":1} or {} for no filter
    target_queries: list[str] = []
    # The lens's TRAVERSAL PATTERN: the ordered lanes a subject trace may walk, handed to ``find_paths``
    # as its ``edge_whitelist``. This is the other half of "a subject is a query-time lens" — anchors say
    # where a trace starts, these say what counts as a step in it (e.g. an ORBAT→origin chain walks
    # basing/induction/supply lanes, not the sighting lane). Empty ⇒ fall back to the ontology's full
    # traversable set, so a lens that declares none still traces.
    trace_lanes: list[str] = []


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
