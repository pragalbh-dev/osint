"""The knowledge view — the derived layer ``rebuild()`` emits, and its JSON shape (master §4.8).

Everything here is **computed, never stored on a raw claim**: status/confidence/freshness are a
function of the supporting claims + config. Two structural rules the schema encodes:

* **Traceability (G4):** every ``NodeView``/``EdgeView`` carries ``claim_ids`` resolving to real
  claims → doc spans. A naked assertion cannot be represented.
* **Two scores, never averaged (G5):** ``merge_confidence`` (identity — lives *only* on a same-as
  edge) is a different field from ``ConfidenceBreakdown.assertion_confidence`` (truth). They are
  never blended, and ``status`` is set only by the status machine (SCORE), never hand-written.

Field names track product/03 (B: node/edge · C: provenance drawer · G: Known Gap · F: alert); a few
may still move — this is the shape-of-record F0 reconciles the API against.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from .base import Record
from .values import DateValue, Location, Period

# confirmed / probable / possible are a confidence *magnitude* axis; insufficient is *off* that
# axis (an assessability failure → Known Gap); contradicted/stale are overlays (spine/08 §3.4).
Status = Literal["confirmed", "probable", "possible", "contradicted", "stale", "insufficient"]
ObservabilityCeiling = Literal["confirmable", "probable-max", "never-observable"]


class IndependenceGroup(Record):
    """A cluster of supporting claims that are *not* independent of each other (§3.5).

    The centerpiece of the provenance drawer: render "5 sources · 2 independent looks", not a flat
    list. ``axis_key`` records the origin/discipline/interest keys the grouping collapsed on.
    """

    group_id: str
    claim_ids: list[str]
    axis_key: dict[str, str] = {}  # {"origin": …, "discipline": …, "interest": …}
    weight: float = 1.0  # 0.5 for same-class-but-passing pairs (§3.5)


class ConfidenceBreakdown(Record):
    """The persisted, replayable "why" behind a status (B pre-wiring #6; product/03 C).

    Decomposed so deception resistance is a query: "confidence is high *because* 3 sources corroborate
    — but they share one origin". ``assertion_confidence`` is the noisy-OR over independence groups.
    """

    per_claim_credibility: dict[str, float] = {}  # claim_id → claim_credibility (reliability×integrity×freshness)
    integrity_flags: list[str] = []  # recycled / too-clean / adversary-denial / decoy-risk …
    independence_groups: list[IndependenceGroup] = []
    freshness_factor: float | None = None
    assertion_confidence: float | None = None  # 1 − Π_g (1 − c_g); truth, never identity


class Freshness(Record):
    """Renderable freshness: last-support date · this fact-kind's half-life · current decay factor."""

    last_support_time: str | None = None  # ISO of the freshest supporting look
    half_life: str | None = None  # config key / label for this edge-type's half-life
    half_life_days: float | None = None  # resolved numeric half-life (from config), for display
    decay_factor: float | None = None  # 2^(−age / half_life), 1.0 = fresh


class SufficiencyEval(Record):
    """The latest evidence-requirement-template check for an assertion (§3.7; product/03 C/G)."""

    satisfied: bool
    missing_slots: list[str] = []
    next_coverage_due: str | None = None  # generated from the source cadence, never hand-written
    ceiling: ObservabilityCeiling | None = None
    template_id: str | None = None


class MaterialityAttrs(Record):
    """Precomputed-in-``rebuild()`` node attrs the retrieval tools filter on (spine/09; C/01)."""

    chokepoint_count: int | None = None
    chokepoint_status: Literal["confirmed", "candidate", "none"] | None = None
    substitutability_state: Literal["known-sole-source", "known-alternates", "UNKNOWN"] | None = None
    contributing_refs: list[str] = []  # claim/edge IDs so the attribute still cites its basis


class AttrValueClaim(Record):
    """One asserted value for a derived node attribute, with the time axes it was asserted over (D7, §1B).

    The **retained history** the assembler no longer drops. ``NodeView.attrs[k]`` still holds the single
    first-claim-wins scalar every existing consumer reads; ``NodeView.attr_history[k]`` keeps *every*
    value any claim asserted for that attribute, so a later — possibly conflicting — value is simply
    another entry and nothing is hidden. **Role-agnostic:** values are retained regardless of the
    attribute's critical/supporting/neutral role (that classification lives in RESOLVE / Stage 1A, never
    here). The time carrier mirrors ``EventView.time_interval`` (events already carry an interval
    end-to-end; nodes/edges did not).

    ``event_time`` is the stated validity anchor; ``report_time`` the publication date. ``valid_from`` /
    ``valid_until`` are the report-bounded validity window from :func:`values.report_bounded_validity`
    (report_time as the upper bound where no explicit validity interval was stated) — a pure record, no
    decision. Ordering / supersede / contradiction over these entries is deferred to Stage 3B.
    """

    value: Any = None
    claim_id: str
    event_time: DateValue | None = None  # when true in the world (stated validity anchor)
    report_time: DateValue | None = None  # when the source published (upper bound on validity)
    valid_from: str | None = None  # ISO lower bound of validity (from event_time), pure-derived
    valid_until: str | None = None  # ISO upper bound of validity (report_time, unless explicit interval)


class _Assessed(Record):
    """Fields shared by nodes and edges — the assessment attached to a derived element."""

    claim_ids: list[str] = []  # G4: ≥1, each resolving to a real claim → doc_ref
    status: Status | None = None  # set ONLY by the status machine (G5); None until SCORE runs
    confidence: ConfidenceBreakdown | None = None
    freshness: Freshness | None = None
    supporting_claims: list[IndependenceGroup] = []  # grouped by independence
    opposing_claims: list[str] = []
    sufficiency: SufficiencyEval | None = None


class NodeView(_Assessed):
    """A resolved entity on the graph/map (product/03 B)."""

    id: str
    type: str  # ontology node type (manufacturer, component, unit, basing_site, …)
    name: str | None = None
    attrs: dict[str, Any] = {}  # per-type attributes (functional_role, decoy_risk_flag, …)
    location: Location | None = None
    materiality: MaterialityAttrs | None = None  # precomputed (SCORE); None until it runs
    # Retained per-attribute value history (D7, §1B). ADDITIVE: ``attrs`` above is unchanged (first-claim
    # -wins scalar); this maps each claim-asserted attribute → the full time-ordered series of every value
    # asserted for it — the entity's timeline. SURFACED on the wire (a target output — "store previous
    # values, makes the KG more useful"); the frozen ``expected_view.json`` must be regenerated to match
    # (data-refresh ledger §A). Empty until the assembler folds attrs.
    attr_history: dict[str, list[AttrValueClaim]] = Field(default_factory=dict)


class EdgeView(_Assessed):
    """A resolved relationship between two nodes (product/03 B)."""

    id: str
    type: str  # ontology edge type (supplies-component, based-at, same-as, …)
    source: str  # source node id
    target: str  # target node id
    edge_instance: str | None = None  # the resolved instance id (supersede/contradict match key)
    attrs: dict[str, Any] = {}
    superseded_by: str | None = None  # a newer edge that supersedes this one (→ stale)
    supersedes: str | None = None  # the older edge this one retires
    # Identity confidence — lives ONLY on same-as edges, NEVER fed into assertion_confidence (G5).
    merge_confidence: float | None = None
    # Validity interval carried onto the edge (D7, §1B) — mirrors ``EventView.time_interval``, which
    # already carries an interval end-to-end. Populated from the edge's claim ``event_time``(s). SURFACED
    # on the wire (a target output; frozen ``expected_view.json`` regenerated to match — data-refresh
    # ledger §A). ``None`` when no supporting claim is dated.
    time_interval: Period | DateValue | None = Field(default=None)


class EventView(_Assessed):
    """A first-class event (TransferEvent, InductionEvent, SightingEvent, ExerciseEvent)."""

    id: str
    event_type: str
    time_interval: Period | DateValue | None = None
    location: Location | None = None
    participants: list[str] = []
    attrs: dict[str, Any] = {}


class KnownGap(Record):
    """A first-class known-*unknown* (C/01; product/03 G) — the node-level home of the non-negotiable.

    Off the confidence scale entirely (a refusal, not "confidence≈0"). Doubles as collection tasking.
    """

    id: str
    what_missing: str  # rendered from a template keyed off the unmet slot (never regenerated prose)
    observability_ceiling: ObservabilityCeiling
    next_coverage_due: str | None = None  # only meaningful for a *confirmable* ceiling
    related_ref: str | None = None  # the node/edge this gap hangs off
    missing_slots: list[str] = []


class AlertProvenance(Record):
    """The evidence behind a fired Alert (G4) — what the analyst clicks through to.

    An alert asserts something about the world ("this unit moved"), so it obeys the same rule as every
    other derived element: it names the claims it rests on. ``before_*`` are the claims that asserted
    the prior state, ``after_*`` the claims that assert the new one — the split is the point, because
    "what changed" is only auditable if both sides are separately traceable. ``status`` /
    ``assertion_confidence`` are **copied** off the after-element (SCORE computed them; MONITOR never
    derives a score — G5). All fields optional: an alert whose element carried no claims says so by
    being empty rather than by inventing a citation.
    """

    before_ref: str | None = None  # view element (edge/node id) that carried the prior state
    after_ref: str | None = None  # view element that carries the new state
    before_claim_ids: list[str] = []
    after_claim_ids: list[str] = []
    claim_ids: list[str] = []  # union (before-first, de-duplicated) — the provenance-drawer target
    status: Status | None = None  # the after-element's status, as SCORE set it
    assertion_confidence: float | None = None  # truth confidence, never identity (G5)


class Alert(Record):
    """A fired observable/tripwire (MONITOR; product/03 F)."""

    observable_id: str
    subject: str | None = None
    before: dict[str, Any] = {}
    after: dict[str, Any] = {}
    severity: str = "notify"
    fired_ts: str | None = None
    disposition: Literal["real", "noise", "needs-more"] | None = None
    provenance: AlertProvenance | None = None  # G4: the claims behind before→after (None = pre-MON-4 alert)


class GraphView(Record):
    """The whole rebuilt knowledge view — the ``GET /view`` payload and the SPA's binding target."""

    nodes: list[NodeView] = []
    edges: list[EdgeView] = []
    events: list[EventView] = []
    known_gaps: list[KnownGap] = []
    alerts: list[Alert] = []
    meta: dict[str, Any] = {}  # config_version, subject lens applied, counts — diagnostic only
