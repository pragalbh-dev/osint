"""Turn the claim list into the resolvable-entity view the resolver operates on.

An entity **profile** (type, name, merged attrs, claim ids) comes from entity-form claims; relationship
claims become **edges** (subject → object, with the edge-instance + a temporal upper-bound) that feed
the relational term and the relocation/supersede exclusion. Event claims stay per-claim (RESOLVE merges
entities, not events, in the core).

``base_ref`` reproduces F0's identity ``resolved_ref`` byte-for-byte, so a no-merge run is identical to
the stub (gate G2); merges are then expressed as an *overlay* (``same_as`` + ``entity_canonical``), never
by rewriting a claim's own ``resolved_ref``.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any

from chanakya.ontology import EdgeLaneIndex, build_edge_instance_key
from chanakya.schemas import ClaimRecord, DateValue, ResolvedRef, canonical_iso_bounds


def unordered_pairs[T](seq: list[T]) -> Iterator[tuple[T, T]]:
    """All i<j pairs of a sequence (a literal-free ``combinations(seq, 2)`` — keeps gate G6 happy)."""
    for i in range(len(seq)):
        for j in range(i + 1, len(seq)):
            yield seq[i], seq[j]


def as_pair(x: Iterable[str]) -> tuple[str, str]:
    """Normalise a 2-element pair/frozenset to a sorted ``(a, b)`` string tuple (typed for the schema)."""
    a, b = sorted(x)
    return (a, b)


def base_ref(claim: ClaimRecord, lane: EdgeLaneIndex | None = None) -> ResolvedRef:
    """The per-claim identity ref (extractor's if set, else synthesised) — matches F0's stub exactly.

    For a relationship claim the ``edge_instance`` is built through ``lane`` so a **functional** edge
    (``based-at``) keys on the subject alone and a unit's before/after basing sites share one instance
    (EVAL RCA §2.1). ``lane`` is passed by ``resolve()``; when absent (a caller with no ontology in hand),
    the default ``(from, to)`` key is used — byte-identical to the pre-fix ``edge:{s}:{p}:{o}`` for every
    edge, so nothing regresses. Both this and the ``view.pipeline`` fallback route through one builder.
    """
    if claim.resolved_ref is not None:
        return claim.resolved_ref
    p = claim.payload
    if p.form == "entity":
        return ResolvedRef(entity_id=f"ent:{p.entity_type}:{p.name}")
    if p.form == "triple":
        ei = (
            lane.edge_instance_key(p.subject, p.predicate, p.object)
            if lane is not None
            else build_edge_instance_key(p.subject, p.predicate, p.object)
        )
        return ResolvedRef(entity_id=f"ent:{p.subject}", edge_instance=ei)
    return ResolvedRef(entity_id=f"event:{p.event_type}:{claim.claim_id}")


@dataclass(frozen=True)
class AttrClaim:
    """One asserted value for an ``Entity`` attribute, + the claim/time axes that asserted it.

    Stage 3-prep: mirrors the view layer's ``AttrValueClaim`` (``schemas/view.py``, D7 §1B) one stage
    earlier in the pipeline. ``Entity.attrs[k]`` stays the first-claim-wins scalar every existing resolve
    reader depends on; ``Entity.attr_history[k]`` is the role-agnostic full time-ordered series of every
    value any claim asserted for that attribute, so a later — possibly conflicting — value is retained,
    not silently dropped. Pure data: no ordering/veto/scoring decision is taken here — that stays in
    ``resolve/scoring.py`` (3A's credibility-gated walls, 3B's update/stale, consume this; they do not
    populate it).
    """

    value: Any
    claim_id: str
    event_time: DateValue | None = None  # when true in the world (stated validity anchor)
    report_time: DateValue | None = None  # when the source published


def _attr_history_sort_key(entry: AttrClaim) -> tuple[bool, str, str, str]:
    """Deterministic oldest→newest order for a retained attribute series (mirrors ``view.pipeline``'s).

    Ordered by ``event_time`` lower bound, then ``report_time`` lower bound, then ``claim_id`` (unique →
    a total, hash-seed-independent order — G2). Undated entries sort last. Presentation/consumption
    ordering only; makes no supersede/contradiction/winner decision (that is 3A/3B).
    """
    ev_lo, _ = canonical_iso_bounds(entry.event_time)
    rep_lo, _ = canonical_iso_bounds(entry.report_time)
    return (ev_lo is None, ev_lo or "", rep_lo or "", entry.claim_id)


@dataclass
class Entity:
    eid: str
    etype: str
    name: str
    attrs: dict[str, Any] = field(default_factory=dict)
    claim_ids: list[str] = field(default_factory=list)
    source_ids: set[str] = field(default_factory=set)
    # True only for an entry seeded from the entity registry (``config/entities.yaml``, P3.0). It is a
    # *candidate* with a STABLE id, carrying no claims of its own: it never becomes a view node unless a
    # real claim resolves onto it, but when it does, its cluster adopts its id (see ``cluster._preferred``)
    # so the graph, the lenses and the oracle share one id namespace.
    registry: bool = False
    # ADDITIVE (Stage 3-prep, mirrors view's ``attr_history`` — §1B one stage earlier). Role-agnostic: every
    # claim-asserted value for an attribute is retained here, time-ordered, even one ``attrs[k]`` (first-
    # claim-wins) drops. Empty for entities carrying no claim of their own (registry seeds, T3b mints).
    attr_history: dict[str, list[AttrClaim]] = field(default_factory=dict)

    def namespace(self) -> str | None:
        """The 'country / domain namespace' blocking dimension, read from stated attrs (None ⇒ wildcard)."""
        for key in ("country", "operator_branch", "service_branch", "domain"):
            v = self.attrs.get(key)
            if v:
                return str(v)
        return None


def namespace_compatible(a: Entity, b: Entity) -> bool:
    """Same declared namespace, or at least one side unstated.

    Weaker than the exact-name bootstrap's ``==`` on purpose: an unstated namespace is a **wildcard**,
    not a conflict (most minted endpoint mentions carry no attrs at all), so a missing attribute never
    fabricates a difference. Two *stated* and different namespaces (China vs Pakistan) still block.
    """
    na, nb = a.namespace(), b.namespace()
    return na is None or nb is None or na == nb


@dataclass
class Edge:
    subject: str  # raw entity ref (an entity_id)
    predicate: str
    object: str
    edge_instance: str | None
    latest_iso: str | None  # event_time upper bound (for relocation/temporal reasoning)
    # The source that asserted this triple. Load-bearing for identity (D-2.5/D-P3.4): a ``same-as`` is an
    # ordinary evidence claim, so the weight its identity assertion carries in ``source_asserted_score``
    # is the *asserting source's* credibility grade — not a flat 1.0 for everyone.
    source_id: str | None = None
    # The claim this triple came from. An identity assertion ("A same-as B") is CONSUMED as a merge
    # signal rather than drawn as an edge (D-2.5), so without this the only trace of *who said* two
    # records are one was a number in ``merge_breakdown``: an analyst adjudicating the pair could read
    # the score but never the sentence. Carried here so the candidate ``same-as`` edge can cite its own
    # evidence (``resolve.identity_claim_ids`` → ``view/pipeline._resolution_edges`` → ``GET /evidence``).
    claim_id: str | None = None
    # The claim's tier-3 bag, carried through so a triple that says something *about how it was derived*
    # can be read here. Currently that is in-document coreference: its evidence category decides whether
    # the pair may bootstrap or only raise, and its licensing quote is the analyst's rationale. Carried
    # verbatim (never interpreted at build time) so a new signal needs no change to this layer.
    attributes: dict[str, Any] | None = None


@dataclass
class EntityGraph:
    entities: dict[str, Entity]
    edges: list[Edge]

    def incident(self, eid: str) -> list[Edge]:
        return [e for e in self.edges if e.subject == eid or e.object == eid]


def build(claims: list[ClaimRecord], lane: EdgeLaneIndex | None = None) -> EntityGraph:
    """Group entity claims into profiles + collect relationship edges (post-retraction claims in).

    ``lane`` (the ontology's edge index) is threaded so each edge's ``edge_instance`` honours the declared
    functional/multi-valued key — that is what revives the co-instance relocation exclusion in
    ``resolve.scoring`` (two based-at targets of one unit become co-objects of one instance again).
    """
    entities: dict[str, Entity] = {}
    edges: list[Edge] = []

    for c in claims:
        p = c.payload
        if p.form == "entity":
            eid = base_ref(c, lane).entity_id or f"ent:{p.entity_type}:{p.name}"
            ent = entities.get(eid)
            if ent is None:
                ent = Entity(eid=eid, etype=p.entity_type, name=p.name)
                entities[eid] = ent
            if c.claim_id not in ent.claim_ids:
                ent.claim_ids.append(c.claim_id)
            ent.source_ids.add(c.source_id)
            for k, v in p.attrs.items():
                ent.attrs.setdefault(k, v)  # scalar contract UNCHANGED: first claim wins (replay order)
                # ADDITIVE (Stage 3-prep): retain EVERY asserted value + its time axes, role-agnostic — a
                # later/conflicting value is just another entry, never a silently-dropped one.
                ent.attr_history.setdefault(k, []).append(
                    AttrClaim(value=v, claim_id=c.claim_id, event_time=c.event_time, report_time=c.report_time)
                )
        elif p.form == "triple":
            rr = base_ref(c, lane)
            edges.append(
                Edge(
                    subject=p.subject,
                    predicate=p.predicate,
                    object=p.object,
                    edge_instance=rr.edge_instance,
                    latest_iso=canonical_iso_bounds(c.event_time)[1],
                    source_id=c.source_id,
                    claim_id=c.claim_id,
                    attributes=c.attributes,
                )
            )

    # Time-order each retained attribute series (oldest→newest). Deterministic; carries no decision.
    for ent in entities.values():
        for series in ent.attr_history.values():
            series.sort(key=_attr_history_sort_key)

    return EntityGraph(entities=entities, edges=edges)
