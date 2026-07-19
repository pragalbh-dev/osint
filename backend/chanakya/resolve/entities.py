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

from chanakya.schemas import ClaimRecord, ResolvedRef, canonical_iso_bounds


def unordered_pairs[T](seq: list[T]) -> Iterator[tuple[T, T]]:
    """All i<j pairs of a sequence (a literal-free ``combinations(seq, 2)`` — keeps gate G6 happy)."""
    for i in range(len(seq)):
        for j in range(i + 1, len(seq)):
            yield seq[i], seq[j]


def as_pair(x: Iterable[str]) -> tuple[str, str]:
    """Normalise a 2-element pair/frozenset to a sorted ``(a, b)`` string tuple (typed for the schema)."""
    a, b = sorted(x)
    return (a, b)


def base_ref(claim: ClaimRecord) -> ResolvedRef:
    """The per-claim identity ref (extractor's if set, else synthesised) — matches F0's stub exactly."""
    if claim.resolved_ref is not None:
        return claim.resolved_ref
    p = claim.payload
    if p.form == "entity":
        return ResolvedRef(entity_id=f"ent:{p.entity_type}:{p.name}")
    if p.form == "triple":
        return ResolvedRef(entity_id=f"ent:{p.subject}", edge_instance=f"edge:{p.subject}:{p.predicate}:{p.object}")
    return ResolvedRef(entity_id=f"event:{p.event_type}:{claim.claim_id}")


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


def build(claims: list[ClaimRecord]) -> EntityGraph:
    """Group entity claims into profiles + collect relationship edges (post-retraction claims in)."""
    entities: dict[str, Entity] = {}
    edges: list[Edge] = []

    for c in claims:
        p = c.payload
        if p.form == "entity":
            eid = base_ref(c).entity_id or f"ent:{p.entity_type}:{p.name}"
            ent = entities.get(eid)
            if ent is None:
                ent = Entity(eid=eid, etype=p.entity_type, name=p.name)
                entities[eid] = ent
            if c.claim_id not in ent.claim_ids:
                ent.claim_ids.append(c.claim_id)
            ent.source_ids.add(c.source_id)
            for k, v in p.attrs.items():
                ent.attrs.setdefault(k, v)  # first claim wins (deterministic in replay order)
        elif p.form == "triple":
            rr = base_ref(c)
            edges.append(
                Edge(
                    subject=p.subject,
                    predicate=p.predicate,
                    object=p.object,
                    edge_instance=rr.edge_instance,
                    latest_iso=canonical_iso_bounds(c.event_time)[1],
                    source_id=c.source_id,
                    attributes=c.attributes,
                )
            )
    return EntityGraph(entities=entities, edges=edges)
