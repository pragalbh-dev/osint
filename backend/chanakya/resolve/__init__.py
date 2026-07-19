"""RESOLVE stage — iterative relational entity resolution (owned by session RESOLVE, spine/03).

C's marquee graded feature: confidently fuse "FD-2000" = "HQ-9/P" across transliterations + shell
aliases, *while keeping the traps apart* (FD-2000 ≠ FT-2000, HQ-9/P ≠ HQ-9BE, Karachi-Port ≠ Port-Qasim).

The whole stage is a **pure, deterministic** function of (claims, config, prev_view, decision log) —
no LLM / network / clock / RNG on this path (gate G1). There are two *proposers* and both are
**raise-only**: the LLM, whose output is already frozen in the decision log (``merge_proposal`` records),
and the corpus itself, whose ``same-as`` claims are read from the claim stream weighted by the asserting
source's credibility grade (D-2.5). Neither can auto-merge; the deterministic terms (``merge_score`` +
bands + the fixpoint) always dispose. A ``distinct-from`` claim is the mirror image — an immediate hard
veto, and it stays **drawn** so the trap is visible. Merges are **reversible**
overlays (``same_as`` + ``entity_canonical``), never destructive node-collapse; a claim's own
``resolved_ref`` stays its per-claim identity so a no-merge run is byte-identical to F0's stub (gate G2).

Signature: ``resolve(claims, config, prev_view=None, decisions=None) -> Partition``.
"""

from __future__ import annotations

from itertools import product

from chanakya.ontology import EdgeLaneIndex
from chanakya.schemas import (
    ClaimRecord,
    ConfigBundle,
    DecisionRecord,
    GraphView,
    Partition,
    PlaceRef,
)

from . import aliases, entities, places
from .aliases import AliasIndex
from .cluster import Pair, ResolveResult, finalise, resolve_entities
from .entities import Entity, EntityGraph, base_ref, namespace_compatible, unordered_pairs
from .normalize import normalize
from .places import location_attr
from .propose import propose_candidates
from .rconfig import ResolveConfig
from .scoring import DISTINCT_PREDICATES, IDENTITY_PREDICATES

__all__ = [
    "resolve",
    "propose_candidates",
    "location_attr",
    "IDENTITY_PREDICATES",
    "DISTINCT_PREDICATES",
]


def resolve(
    claims: list[ClaimRecord],
    config: ConfigBundle,
    prev_view: GraphView | None = None,
    decisions: list[DecisionRecord] | None = None,
) -> Partition:
    """Resolve claims into entities/edges: candidate-gen → bootstrap → relational fixpoint → places."""
    cfg = ResolveConfig.from_bundle(config)
    graph = entities.build(claims)

    # P3.0 — the entity registry is a *prior*, seeded as candidate entities carrying stable ids. It adds
    # merge TARGETS, never nodes: a seeded entry holds no claims, so it only reaches the view when a real
    # claim resolves onto it (traceability non-negotiable / gate G4).
    _seed_registry(graph, cfg)

    # P3.4 — the ONE place-resolution pass. Every consumer (the distinct-from veto, the place-merge
    # augment, and the ``place_refs`` write-back) reads this same map, so they agree by construction.
    # Computed here because only claim-backed entities carry a frozen location: registry seeds hold no
    # attrs and minted endpoints hold none either, so nothing below this line can add a place mention.
    place_of = places.place_matches(graph, cfg)

    # Effective alias table = seeded config ∪ registry classes ∪ replayed merge_adjudication(accept)s.
    alias_idx = aliases.build(cfg.alias_table, cfg.transliteration, decisions, cfg.registry_alias_table)

    # veto = configured distinct-from (by name) ∪ registry distinct-from (by entity id) ∪ gazetteer-distinct
    # place pairs (Karachi-Port ≠ Port-Qasim) ∪ source-asserted distinct-from claims — computed up front so
    # it hard-vetoes an entity-level merge too, not just surfaces as an edge.
    veto = (
        _veto_pairs(graph, cfg, alias_idx)
        | _registry_veto(graph, cfg)
        | places.place_distinct_pairs(graph, cfg, place_of)
        | _claim_distinct_pairs(graph, cfg, alias_idx)
    )

    # P3.1 (RES-1) — endpoint-as-mention. Runs BEFORE the fixpoint so ``graph.edges`` already carry entity
    # ids when ``merge_score`` runs; that is what revives the relational + source-asserted terms.
    mention, minted, ambiguous = _link_endpoints(graph, cfg, alias_idx, EdgeLaneIndex(config.ontology), veto)

    # Re-read the claim-asserted distinct-froms now that endpoints carry entity ids: a document may state a
    # do-not-merge about a mention that only *became* an entity in the line above. Idempotent (a set union).
    veto |= _claim_distinct_pairs(graph, cfg, alias_idx)

    # The two raise-only proposal channels: the offline LLM's frozen proposals and the corpus's own
    # ``same-as`` assertions (D-2.5). Neither can auto-merge; both can put a pair in front of an analyst.
    raise_only = _llm_pairs(graph, cfg, alias_idx, decisions) | _identity_pairs(graph, cfg, alias_idx, veto)

    result = resolve_entities(graph, cfg, alias_idx, veto, raise_only)
    result.candidates.extend(ambiguous)  # an endpoint with >1 irreconcilable match is adjudicated, never guessed
    places.augment(result, graph, cfg, alias_idx, veto, place_of)  # reuses the same bands + veto
    finalise(result, graph, cfg, veto, alias_idx)  # reconcile all merges into one flat, veto-guarded map

    return _to_partition(claims, result, mention, minted, place_of)


# ── the entity registry as a resolution prior (P3.0) ───────────────────────────────────────────

def _seed_registry(graph: EntityGraph, cfg: ResolveConfig) -> None:
    """Seed ``config/entities.yaml`` entries into the candidate space as claim-less stable-id entities.

    Mirrors how the place gazetteer seeds place identity, one level up the stack. A seeded entry is a
    merge **target**: it carries ``entity_id``/``type``/``canonical_name`` (its aliases ride the
    ``AliasIndex``, its ``distinct_from`` the veto). It deliberately holds **no claim_ids**, so it can
    never fabricate a view node — only a real claim resolving onto it puts it on the graph, and that
    claim supplies the provenance. An id already present in the graph is left alone (claims win).
    """
    for entry in cfg.entities.entities:
        if entry.entity_id in graph.entities:
            continue
        graph.entities[entry.entity_id] = Entity(
            eid=entry.entity_id,
            etype=entry.type,
            name=entry.canonical_name,
            attrs=dict(entry.attrs),
            registry=True,
        )


def _registry_veto(graph: EntityGraph, cfg: ResolveConfig) -> set[Pair]:
    """Registry ``distinct_from`` → hard-veto pairs, already expressed as entity ids (no name matching).

    These are the flagship do-not-merge traps stated at the identity level rather than the string level
    (``var_hq9p`` ≠ ``var_hq9be`` ≠ ``alias_ft2000``; ``unit_paad`` ≠ ``unit_hq9b``), so they hold however
    a document happens to spell either side.
    """
    return {
        frozenset((a, b))
        for a, b in cfg.registry_distinct_from
        if a != b and a in graph.entities and b in graph.entities
    }


# ── veto + LLM-proposal pair construction (name/id → entity id) ────────────────────────────────

def _matching_eids(ref: str, graph: EntityGraph, cfg: ResolveConfig, alias_idx: AliasIndex) -> list[str]:
    """Entities whose id equals ``ref`` or whose (normalised) name matches / is alias-equivalent to it."""
    if ref in graph.entities:
        return [ref]
    target = normalize(ref, cfg.transliteration)
    out = []
    for eid, ent in graph.entities.items():
        nn = normalize(ent.name, cfg.transliteration)
        if nn == target or alias_idx.equivalent(nn, target):
            out.append(eid)
    return sorted(out)


def _veto_pairs(graph: EntityGraph, cfg: ResolveConfig, alias_idx: AliasIndex) -> set[Pair]:
    """Instantiate the configured distinct-from names into entity-id pairs (the hard veto)."""
    veto: set[Pair] = set()
    for canonical, others in cfg.distinct_from.items():
        left = _matching_eids(canonical, graph, cfg, alias_idx)
        for other in others:
            right = _matching_eids(other, graph, cfg, alias_idx)
            for a, b in product(left, right):
                if a != b:
                    veto.add(frozenset((a, b)))
    return veto


# ── RES-1: endpoint-as-mention (P3.1, the master fix) ──────────────────────────────────────────

def _edge_implied_types(graph: EntityGraph, lane: EdgeLaneIndex) -> dict[str, set[str]]:
    """``endpoint surface form → {node types the ontology's domain/range implies for it}``.

    A triple's subject is an instance of its edge's **domain** and its object an instance of the
    **range**, so the predicate types an endpoint that no entity claim ever declared. Only an
    unambiguously-declared end contributes (a polymorphic or undeclared end is skipped, and a symmetric
    edge such as ``same-as`` declares neither) — so an endpoint the ontology cannot type in either order
    simply never appears here, and stays an untyped tier-3 mention rather than being given an invented type.
    """
    out: dict[str, set[str]] = {}
    for e in graph.edges:
        from_types, to_types = lane.endpoint_types(e.predicate)
        if len(from_types) == 1:
            out.setdefault(e.subject, set()).add(from_types[0])
        if len(to_types) == 1:
            out.setdefault(e.object, set()).add(to_types[0])
    return out


def _spans_veto(matches: list[str], veto: set[Pair]) -> bool:
    """True if two of an endpoint's candidate matches are explicitly do-not-merge (a trap straddle)."""
    return any(frozenset((a, b)) in veto for a, b in unordered_pairs(sorted(set(matches))))


def _link_endpoints(
    graph: EntityGraph,
    cfg: ResolveConfig,
    alias_idx: AliasIndex,
    lane: EdgeLaneIndex,
    veto: set[Pair],
) -> tuple[dict[str, str], dict[str, str], list[tuple[str, str]]]:
    """Induct every triple endpoint as a **mention** and rewrite the edge onto the resolved entity id.

    Entity-form claims always went through resolution; triple endpoints never did — they stayed raw LLM
    designator strings in a second, disconnected id space. That single gap is what minted the ``unknown``
    twin nodes and left ``relational``/``source_asserted`` dead for every candidate pair. Here each
    endpoint is resolved by the *same* machinery (normalize + ``AliasIndex`` + the registry), then
    ``Edge.subject``/``Edge.object`` are rewritten **in the graph** — before the fixpoint — so
    ``merge_score`` sees real neighbourhoods and real source-asserted identities.

    One attach-or-mint process, resolved per distinct surface form (never per occurrence, so one form
    always lands on one id):

    * an endpoint that is **already an entity id** is left exactly as-is (the extractor pre-resolved it);
    * its **type** comes from the entities it matches — an entity-form claim or a registry entry is
      authoritative about what a surface form *is* — and only failing that from the edge's domain/range;
    * with a type in hand it resolves to ``ent:<type>:<name>``, **minting** that typed entity when no
      claim declared it. Minting, not linking, is the honest answer to "we have no entity for this": the
      endpoint gets its own typed node and the fixpoint may still merge it on the evidence.
    * matches straddling a **do-not-merge veto**, disagreeing on type, or an un-typable endpoint are
      **never guessed**: the mention is left raw (an untyped tier-3 mention) and a straddle is returned
      as an adjudication candidate.

    Pure and deterministic — sorted iteration, no clock/RNG/LLM (gates G1/G2). A no-op wherever the
    ontology declares no domain/range and endpoints are already ids, which is exactly the golden fixture.
    """
    edge_types = _edge_implied_types(graph, lane)
    surface_forms = sorted({e.subject for e in graph.edges} | {e.object for e in graph.edges})

    mention: dict[str, str] = {}   # surface form → entity id it resolves to
    minted: dict[str, str] = {}    # newly minted entity id → its ontology node type
    ambiguous: list[tuple[str, str]] = []

    for form in surface_forms:
        if form in graph.entities:
            continue  # already an entity id — nothing to resolve (and the golden fixtures' whole story)

        matches = _matching_eids(form, graph, cfg, alias_idx)
        if _spans_veto(matches, veto):
            # The form is alias-equivalent to two entities we are told are NOT the same thing. Picking one
            # would silently collapse a trap; leave the mention unresolved and hand the pair to an analyst.
            ambiguous.extend(
                (a, b) for a, b in unordered_pairs(sorted(set(matches))) if frozenset((a, b)) in veto
            )
            continue

        types = {graph.entities[m].etype for m in matches}
        if len(types) > 1:
            continue  # matches disagree on what this form IS → ambiguous, do not invent a winner
        if not types:
            types = edge_types.get(form, set())  # nothing knows this form — fall back to the edge's own range
        if len(types) != 1:
            continue  # un-typable (or contradictorily typed) → stays an untyped tier-3 mention

        node_type = next(iter(types))
        eid = f"ent:{node_type}:{form}"
        if eid not in graph.entities:
            graph.entities[eid] = Entity(eid=eid, etype=node_type, name=form)
            minted[eid] = node_type
        mention[form] = eid

    for e in graph.edges:  # rewrite in place: the fixpoint scores over entity ids from here on
        e.subject = mention.get(e.subject, e.subject)
        e.object = mention.get(e.object, e.object)

    return mention, minted, ambiguous


# ── RES-4: identity read from the claim stream, source-weighted (P3.2, D-2.5 / D-P3.4) ─────────

def _asserted_pairs(
    graph: EntityGraph, cfg: ResolveConfig, alias_idx: AliasIndex, predicates: set[str]
) -> set[Pair]:
    """Entity-id pairs named by claims whose predicate is in ``predicates`` (identity or its negation).

    Each endpoint goes through the *same* ``_matching_eids`` resolution the configured distinct-from names
    use, so a claim about "FD-2000" reaches ``var_hq9p`` however the registry spells it. A pair whose ends
    do not both instantiate is silently dropped — a claim about something we have no entity for is not a
    merge signal, and inventing one would be fabrication.
    """
    out: set[Pair] = set()
    for e in graph.edges:
        if e.predicate not in predicates:
            continue
        left = _matching_eids(e.subject, graph, cfg, alias_idx)
        right = _matching_eids(e.object, graph, cfg, alias_idx)
        for a, b in product(left, right):
            if a != b and a in graph.entities and b in graph.entities:
                out.add(frozenset((a, b)))
    return out


def _claim_distinct_pairs(graph: EntityGraph, cfg: ResolveConfig, alias_idx: AliasIndex) -> set[Pair]:
    """A source-stated ``distinct-from`` → a **hard veto**, on the same footing as the configured traps.

    Deliberately *not* graded or type-gated: a document going out of its way to say "this is not that"
    is the cheapest, highest-value evidence in the corpus (the spares tender disambiguating its own
    subject), and the cost of honouring a wrong one is two nodes an analyst can still merge — versus a
    false merge that silently destroys the distinction. The trap also stays **drawn** in the view.
    """
    return _asserted_pairs(graph, cfg, alias_idx, DISTINCT_PREDICATES)


def _identity_pairs(
    graph: EntityGraph, cfg: ResolveConfig, alias_idx: AliasIndex, veto: set[Pair]
) -> set[Pair]:
    """A source-stated ``same-as`` → a **raise-only** merge signal (never an auto-merge).

    The asymmetry with :func:`_claim_distinct_pairs` is the whole of D-2.5: a "these are the same" is the
    assertion an adversary plants (the corpus cross-wires an Army variant onto the PAF one), so it is
    gated — the two ends must agree on **type** and be namespace-compatible, and a vetoed pair is dropped
    outright — and even then it only *proposes*. The asserting source's grade rides separately, in
    ``source_asserted_score``: a curated register's identity claim scores higher than an anonymous
    repost's, but neither can merge on its own.
    """
    out: set[Pair] = set()
    for pair in _asserted_pairs(graph, cfg, alias_idx, IDENTITY_PREDICATES):
        if pair in veto:
            continue
        a, b = sorted(pair)
        ea, eb = graph.entities[a], graph.entities[b]
        if ea.etype != eb.etype or not namespace_compatible(ea, eb):
            continue
        if _best_identity_weight(graph, cfg, a, b) < cfg.identity_raise_min_weight:
            continue
        out.add(pair)
    return out


def _best_identity_weight(graph: EntityGraph, cfg: ResolveConfig, a: str, b: str) -> float:
    """The grade of the best source asserting a≡b — the triage gate's input (0.0 ⇒ nothing asserts it)."""
    weights = [
        cfg.identity_source_weight(e.source_id)
        for e in graph.edges
        if e.predicate in IDENTITY_PREDICATES and {e.subject, e.object} == {a, b}
    ]
    return max(weights) if weights else 0.0


def _llm_pairs(
    graph: EntityGraph, cfg: ResolveConfig, alias_idx: AliasIndex, decisions: list[DecisionRecord] | None
) -> set[Pair]:
    """Frozen ``merge_proposal`` records → raise-only candidate pairs (never an auto-merge, gate §3.11)."""
    out: set[Pair] = set()
    for d in decisions or []:
        if d.type != "merge_proposal":
            continue
        pair = aliases._pair(d)
        if pair is None:
            continue
        left = _matching_eids(pair[0], graph, cfg, alias_idx)
        right = _matching_eids(pair[1], graph, cfg, alias_idx)
        for a, b in product(left, right):
            if a != b:
                out.add(frozenset((a, b)))
    return out


# ── Partition assembly ─────────────────────────────────────────────────────────────────────────

#: How two competing place matches on ONE post-merge node are ranked (lower wins). Ordering, not
#: scoring — the sequences ARE the preference, so there are no numbers to tune: a decided band beats a
#: queued one, stated identity (a hard ID, then a name) beats an inference from distance, and only then
#: does the shorter distance decide, with the place_id as a final tiebreak. Deterministic (gate G2).
_BAND_ORDER = ("auto", "hitl")
_VIA_ORDER = ("hard-id", "toponym", "proximity")


def _rank_in(order: tuple[str, ...], value: str) -> int:
    """Position of ``value`` in a preference sequence; anything unlisted sorts after all of it."""
    return order.index(value) if value in order else len(order)


def _ref_rank(ref: PlaceRef) -> tuple[int, int, float, str]:
    return (
        _rank_in(_BAND_ORDER, ref.band),
        _rank_in(_VIA_ORDER, ref.via),
        ref.distance_m if ref.distance_m is not None else 0.0,
        ref.place_id,
    )


def _to_partition(
    claims: list[ClaimRecord],
    result: ResolveResult,
    mention: dict[str, str] | None = None,
    minted: dict[str, str] | None = None,
    place_of: dict[str, places.PlaceMatch] | None = None,
) -> Partition:
    """Per-claim identity resolved_ref (matches the stub) + the merge overlay from the resolver.

    ``entity_canonical`` is widened here from "merged cluster members" to "**any** ref the view may meet"
    (P3.1): each triple-endpoint mention is composed through the merge map, so the raw designator a
    document used lands directly on the post-merge node id. ``endpoint_node_types`` carries the ontology
    type of each endpoint the resolver had to mint, so ``_assemble`` can materialise it as a TYPED node
    instead of the ``unknown`` fallback. ``place_refs`` (P3.4) carries each entity's curated-gazetteer
    anchor *with the distance and band that earned it*. All three collapse to the plain merge map when
    nothing was linked, minted, or matched.
    """
    resolved_ref = {c.claim_id: base_ref(c) for c in claims}

    def canonical_of(eid: str) -> str:
        return result.canonical.get(eid, eid)

    entity_canonical = dict(result.canonical)
    for form, eid in sorted((mention or {}).items()):
        target = canonical_of(eid)
        if form != target:  # an identity mapping would be a no-op — keep the map minimal (gate G2)
            entity_canonical[form] = target

    endpoint_node_types: dict[str, str] = {}
    for eid, node_type in sorted((minted or {}).items()):
        endpoint_node_types.setdefault(canonical_of(eid), node_type)

    # Keyed by the POST-merge id, so the view can stamp it straight onto the node. A merge that fused two
    # mentions carrying different matches keeps the better-evidenced one rather than "last write wins".
    place_refs: dict[str, PlaceRef] = {}
    for eid, match in sorted((place_of or {}).items()):
        if match.place_id is None:
            continue
        ref = PlaceRef(
            place_id=match.place_id, band=match.band, distance_m=match.distance_m, via=match.via
        )
        target = canonical_of(eid)
        current = place_refs.get(target)
        if current is None or _ref_rank(ref) < _ref_rank(current):
            place_refs[target] = ref

    return Partition(
        resolved_ref=resolved_ref,
        same_as=result.same_as,
        candidates=result.candidates,
        distinct_from=result.distinct_from,
        merge_confidence=result.merge_confidence,
        merge_breakdown=result.merge_breakdown,
        entity_canonical=entity_canonical,
        endpoint_node_types=endpoint_node_types,
        place_refs=place_refs,
    )
