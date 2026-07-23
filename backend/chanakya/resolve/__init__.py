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
    pair_key,
)

from . import aliases, entities, places, scoring
from .aliases import AliasIndex
from .anchor import AnchorResolution, resolve_anchors
from .cluster import Pair, ResolveResult, finalise, resolve_entities
from .entities import Entity, EntityGraph, as_pair, base_ref, namespace_compatible, unordered_pairs
from .normalize import normalize
from .places import location_attr
from .propose import propose_candidates
from .rconfig import ResolveConfig
from .scoring import (
    COREF_EVIDENCE_ATTR,
    COREF_PREDICATE,
    DISTINCT_PREDICATES,
    IDENTITY_PREDICATES,
    critical_attribute_conflict,
    has_hard_conflict,
)

__all__ = [
    "resolve",
    "resolve_anchors",
    "AnchorResolution",
    "propose_candidates",
    "location_attr",
    "IDENTITY_PREDICATES",
    "DISTINCT_PREDICATES",
    "COREF_PREDICATE",
]


def resolve(
    claims: list[ClaimRecord],
    config: ConfigBundle,
    prev_view: GraphView | None = None,
    decisions: list[DecisionRecord] | None = None,
) -> Partition:
    """Resolve claims into entities/edges: candidate-gen → bootstrap → relational fixpoint → places."""
    cfg = ResolveConfig.from_bundle(config)
    lane = EdgeLaneIndex(config.ontology)  # the edge index: endpoint typing + the functional instance key
    graph = entities.build(claims, lane)

    # P3.0 — the entity registry is a *prior*, seeded as candidate entities carrying stable ids. It adds
    # merge TARGETS, never nodes: a seeded entry holds no claims, so it only reaches the view when a real
    # claim resolves onto it (traceability non-negotiable / gate G4).
    _seed_registry(graph, cfg)

    # T3b-A — stamp the ontology's node-type REFINEMENTS (``refines:`` in config/ontology.yaml) before
    # anything reads a type. An area of operations is not a basing site (md/13 §1), and the place layer
    # is the first consumer that has to know: ``place_allowed_precision_classes`` pins a basing_site to a
    # pad or a site, which is right for a battery and wrong for a province — an area belongs on a
    # district/city/province anchor, rendered as an uncertainty envelope rather than a sharp pin. Running
    # before ``place_matches`` is what lets the two types carry different precision gates.
    _refine_node_types(graph, {}, cfg)

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
    mention, minted, ambiguous = _link_endpoints(graph, cfg, alias_idx, lane, veto)

    # …and again for the endpoints minted a line above, which did not exist for the first pass.
    _refine_node_types(graph, minted, cfg)

    # Re-read the claim-asserted distinct-froms now that endpoints carry entity ids: a document may state a
    # do-not-merge about a mention that only *became* an entity in the line above. Idempotent (a set union).
    # T3b-C — and add the hard-identifier rail: two entities whose names state DIFFERENT bill-of-lading /
    # contract references are a veto, not a low score (config/ontology.yaml ``identifier_patterns``).
    # D5/D6 — and the declared-critical-attribute rail: two same-type entities STATING different values of
    # a critical attribute (a different country/branch, a unique serial) are a wall no score may cross.
    veto |= (
        _claim_distinct_pairs(graph, cfg, alias_idx)
        | _identifier_veto(graph, cfg)
        | _critical_attribute_veto(graph, cfg)
    )

    # The raise-only proposal channels: the offline LLM's frozen proposals and the corpus's own
    # ``same-as`` assertions (D-2.5). Neither can auto-merge; both can put a pair in front of an analyst.
    # In-document coreference is the one signal that may also *bootstrap* — and only for the evidence
    # categories an operator opted in, uncontradicted (see :func:`_coref_pairs`); everything it cannot
    # justify falls back into the same raise-only queue.
    coref_authoritative, coref_raise = _coref_pairs(graph, cfg, alias_idx, veto)
    raise_only = (
        _llm_pairs(graph, cfg, alias_idx, decisions)
        | _identity_pairs(graph, cfg, alias_idx, veto)
        | coref_raise
    )

    result = resolve_entities(graph, cfg, alias_idx, veto, raise_only, coref_authoritative)
    result.candidates.extend(ambiguous)  # an endpoint with >1 irreconcilable match is adjudicated, never guessed
    places.augment(result, graph, cfg, alias_idx, veto, place_of)  # reuses the same bands + veto
    finalise(result, graph, cfg, veto, alias_idx)  # reconcile all merges into one flat, veto-guarded map

    return _to_partition(claims, result, mention, minted, place_of, lane, graph)


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


def _edge_allowed_types(graph: EntityGraph, lane: EdgeLaneIndex) -> dict[str, set[str]]:
    """``endpoint surface form → {node types the ontology allows it to be}`` (T3b-B).

    The sibling of :func:`_edge_implied_types`, and deliberately weaker: that one only speaks when a
    single edge end names exactly one type (it has to, because it *invents* a type for an endpoint
    nothing else describes). This one collects the **full declared constraint** — including a
    polymorphic end such as ``observed-at``'s ``from: [variant, component]`` — and INTERSECTS it across
    every edge the form appears on. It never invents a type; it only says which types are admissible.

    That is exactly what is needed to adjudicate *contradictory* entity claims about one surface form.
    ``HT-233`` is declared a ``component`` by one document and a ``variant`` by another; the resolver
    rightly refuses to guess a winner, and the string was left an untyped mention — so an endpoint whose
    surface form is IDENTICAL to a registry component ended up as a nameless ``unknown`` node that could
    never resolve. The predicate settles it without a guess: the form is the subject of ``equips``,
    whose domain is ``component``, so ``variant`` is not admissible here. Where the ontology admits both
    (or neither), the refusal stands.
    """
    out: dict[str, set[str]] = {}
    for e in graph.edges:
        from_types, to_types = lane.endpoint_types(e.predicate)
        for form, declared in ((e.subject, from_types), (e.object, to_types)):
            if not declared:
                continue  # a symmetric/undeclared end constrains nothing
            current = out.get(form)
            out[form] = set(declared) if current is None else current & set(declared)
    return out


def _settle_contradiction(
    form: str, matches: list[str], node_type: str, graph: EntityGraph
) -> str | None:
    """Where a contradictorily-typed form resolves once the ontology has ruled out a type (T3b-B).

    Deliberately **attach-only, never mint**. The ordinary path mints ``ent:<type>:<form>`` for an
    endpoint nothing describes, which is the honest answer there — but here something *does* describe
    it (that is why the types contradicted), so minting a second node under the surviving type adds a
    new short designator to the graph's vocabulary that no document used. That is not cost-free: a fresh
    short name is exactly the kind of hook the containment bootstrap over-extends (minting
    ``ent:component:HQ-9/P TEL`` made "HQ-9/P TEL canister" read as the same part described more fully,
    and silently fused a canister into a chassis).

    So it attaches to something that already exists, preferring the analyst-curated registry entry —
    which is what the registry is *for*: the extractor emits a surface form, the registry says which
    stable id owns it. Failing that, the entity a claim already declared under the surviving type. If
    neither is unambiguous the original refusal stands and the mention stays an untyped tier-3 mention.
    """
    of_type = [m for m in matches if graph.entities[m].etype == node_type]
    registry = [m for m in of_type if graph.entities[m].registry]
    if len(registry) == 1:
        return registry[0]
    declared = f"ent:{node_type}:{form}"
    return declared if declared in graph.entities else None


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
    allowed_types = _edge_allowed_types(graph, lane)
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
            # The matches disagree on what this form IS. Do not invent a winner — but the ONTOLOGY may
            # already have ruled one out: a triple's subject is an instance of its edge's domain, so a
            # type the predicate does not admit is not a candidate reading of this endpoint (T3b-B).
            # If that narrows the disagreement to exactly one admissible type, the ambiguity is settled
            # by the designed schema rather than by a guess; otherwise the refusal stands.
            narrowed = types & allowed_types.get(form, set())
            if len(narrowed) != 1:
                continue
            settled = _settle_contradiction(form, matches, next(iter(narrowed)), graph)
            if settled is None:
                continue
            mention[form] = settled
            continue
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


# ── T3b-A: node-type refinement (areas of operation are not basing sites) ──────────────────────

def _refine_node_types(
    graph: EntityGraph, minted: dict[str, str], cfg: ResolveConfig
) -> dict[str, str]:
    """Stamp each entity's ontology **refinement** type in place; returns ``{eid: refined type}``.

    A refinement (``refines:`` in ``config/ontology.yaml``) is a narrower reading of a base type that an
    edge's declared range cannot express: ``based-at``/``observed-at`` range over ``basing_site``, so a
    province and an air-defence sector are minted as basing sites alongside a real pad. Re-typing them
    here is what stops the resolver offering an AD Centre, a sector and a coastal belt to the analyst as
    candidate duplicates of one another — they are three different kinds of thing, and no amount of
    scoring should have been asked to notice that.

    The entity **id** is deliberately left alone. Ids are opaque handles minted from the base type at
    claim time; rewriting them would orphan every claim's ``resolved_ref`` and every frozen bundle. What
    changes is the *type* the resolver blocks, scores and bands on — and ``minted`` is updated in step so
    the view materialises a refined endpoint under its refined type too.

    Pure and deterministic (sorted iteration, no clock/RNG/LLM — gates G1/G2). With no refinement
    declared in the ontology this is a no-op and the partition is byte-identical.
    """
    ntx = cfg.node_types
    refined: dict[str, str] = {}
    for eid, ent in sorted(graph.entities.items()):
        new_type = ntx.refine(ent.etype, ent.name)
        if new_type and new_type != ent.etype:
            ent.etype = new_type
            refined[eid] = new_type
            if eid in minted:
                minted[eid] = new_type
    return refined


# ── T3b-C: the hard-identifier rail (a bill of lading is an identity, not a name) ───────────────

def _identifier_veto(graph: EntityGraph, cfg: ResolveConfig) -> set[Pair]:
    """Two same-type entities stating **different** hard identifiers → a hard veto, drawn like any other.

    ``config/ontology.yaml`` declares, per node type, the patterns that make a name a hard identifier
    (a bill-of-lading or contract reference). Where both sides state one and the two differ, the pair is
    not a low-scoring candidate — it is a *stated contradiction*, and it is vetoed before any band is
    computed, exactly as a configured ``distinct-from`` is. This closes the case T1 measured as the
    sharpest unguarded pair in the corpus: three distinct bills in one customs manifest, proposed as
    mutual merges with no deterministic guard, where a wrong merge collapses three import events into
    one and silently corrupts the supply-chain count.

    Absence is not disagreement (the ``has_hard_conflict`` doctrine): a prose-named contract event
    states no reference and is never vetoed by this rail. A type declaring no patterns is unaffected.
    """
    ntx = cfg.node_types
    by_type: dict[str, list[tuple[str, str]]] = {}
    for eid, ent in sorted(graph.entities.items()):
        ident = ntx.identifier(ent.etype, ent.name)
        if ident is not None:
            by_type.setdefault(ent.etype, []).append((eid, ident))
    out: set[Pair] = set()
    for members in by_type.values():
        for (a, ident_a), (b, ident_b) in unordered_pairs(members):
            if ident_a != ident_b:
                out.add(frozenset((a, b)))
    return out


# ── D5/D6: the declared-critical-attribute rail (a country/branch/serial disagreement is a wall) ──

def _critical_attribute_veto(graph: EntityGraph, cfg: ResolveConfig) -> set[Pair]:
    """Two same-type entities STATING different values of a declared-**critical** attribute → a hard veto.

    The D5 wall, generalised from the geographic (``geo_conflict_km``) and hard-identifier
    (:func:`_identifier_veto`) rails to *any* attribute the ontology's ``attribute_roles`` declares
    ``critical`` for a type — a stated different country / operator branch / service branch / unique
    serial is a cannot-link no similarity score may cross. It joins the veto set beside the identifier
    rail, so transitive enforcement and the before-scoring guard are already handled by the existing
    machinery (``cluster.vetoed`` / ``violates_veto_transitively``), and — like the identifier veto — the
    refused pair stays **drawn** in the view so the analyst can see the wall.

    Reuses :func:`scoring.critical_attribute_conflict` (same-type, absence ≠ conflict), so "what counts as
    a critical disagreement" has one definition shared with ``has_hard_conflict``. A type that declares no
    critical attribute is unaffected; a pair where either side is silent is never walled.

    SEAM (Stage 3A): the veto is deliberately **unconditional** here. The credibility floor on the
    vetoing claim (D5 take-care (a) — one flaky low-grade source must not shatter a well-corroborated
    merge, only flag it) is a later stage; this rail wires the critical→veto plainly first.
    """
    by_type: dict[str, list[str]] = {}
    for eid, ent in sorted(graph.entities.items()):
        if cfg.critical_role_attrs(ent.etype):  # only types that declare a critical attribute
            by_type.setdefault(ent.etype, []).append(eid)
    out: set[Pair] = set()
    for eids in by_type.values():
        for a, b in unordered_pairs(eids):
            if critical_attribute_conflict(graph.entities[a], graph.entities[b], cfg):
                out.add(frozenset((a, b)))
    return out


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


# ── in-document coreference: authoritative-unless-contradicted (INGEST pass 2) ─────────────────

def _coref_pairs(
    graph: EntityGraph, cfg: ResolveConfig, alias_idx: AliasIndex, veto: set[Pair]
) -> tuple[set[Pair], set[Pair]]:
    """Split ``coref-same-as`` claims into ``(authoritative, raise_only)`` entity-id pairs.

    A coreference claim carries something no other identity signal does: the extractor read **this one
    document's discourse** and reported which mentions it treats as one entity, with a verbatim span that
    licenses the grouping. Re-deriving that from surface strings is exactly the information loss the
    design forbids — so a category the operator has opted into
    (:attr:`ResolveConfig.coref_authoritative_evidence`, empty by default) *bootstraps* rather than
    merely raising, and every other category joins the ordinary raise-only queue.

    "Authoritative" is never "unconditional". A pair is demoted to raise-only — an analyst decision, with
    the licensing quote attached — whenever the two ends disagree in a way the document's local reading
    cannot settle: a different entity **type**, an incompatible **namespace** (a China/Pakistan split), or
    a stated **hard-attribute contradiction** (:func:`scoring.has_hard_conflict`). A vetoed pair is
    dropped outright, exactly like a source-asserted ``same-as``: a stated do-not-merge outranks any
    reading of the prose. Demotion, not silent deletion, is the point — the evidence still reaches a human.
    """
    authoritative: set[Pair] = set()
    raise_only: set[Pair] = set()
    allowed = cfg.coref_authoritative_evidence

    for e in graph.edges:
        if e.predicate != COREF_PREDICATE:
            continue
        evidence = str((e.attributes or {}).get(COREF_EVIDENCE_ATTR) or "")
        left = _matching_eids(e.subject, graph, cfg, alias_idx)
        right = _matching_eids(e.object, graph, cfg, alias_idx)
        for a, b in product(left, right):
            if a == b or a not in graph.entities or b not in graph.entities:
                continue
            pair = frozenset((a, b))
            if pair in veto:
                continue  # a stated do-not-merge outranks the extractor's reading of the prose
            ea, eb = graph.entities[a], graph.entities[b]
            contradicted = (
                ea.etype != eb.etype
                or not namespace_compatible(ea, eb)
                or has_hard_conflict(ea, eb, cfg)
            )
            if evidence in allowed and not contradicted:
                authoritative.add(pair)
            else:
                raise_only.add(pair)
    return authoritative, raise_only


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
    lane: EdgeLaneIndex | None = None,
    graph: EntityGraph | None = None,
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
    resolved_ref = {c.claim_id: base_ref(c, lane) for c in claims}

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

    # Who *said* two records are one. The score already rides the pair (``merge_breakdown``); this is the
    # sentence underneath it, so an analyst adjudicating the pair can read the source rather than trust a
    # number. Only for pairs an analyst will actually see (candidates + accepted merges), and only for the
    # pairs a source really spoke about — a pair with no identity claim gets no key, not an empty promise.
    identity_claims: dict[str, list[str]] = {}
    if graph is not None:
        for a, b in sorted({as_pair(p) for p in [*result.candidates, *result.same_as]}):
            cids = scoring.identity_claim_ids(graph, a, b)
            if cids:
                identity_claims[pair_key(a, b)] = cids

    return Partition(
        resolved_ref=resolved_ref,
        same_as=result.same_as,
        candidates=result.candidates,
        distinct_from=result.distinct_from,
        merge_confidence=result.merge_confidence,
        merge_breakdown=result.merge_breakdown,
        identity_claims=identity_claims,
        entity_canonical=entity_canonical,
        endpoint_node_types=endpoint_node_types,
        place_refs=place_refs,
    )
