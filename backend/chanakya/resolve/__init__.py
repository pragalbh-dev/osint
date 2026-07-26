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
from typing import Any

from chanakya import coref_gate
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

from . import aliases, cluster, entities, places, scoring
from .aliases import AliasIndex
from .anchor import AnchorResolution, resolve_anchors
from .cluster import Pair, ResolveResult, finalise, resolve_entities
from .entities import (
    Edge,
    Entity,
    EntityGraph,
    as_pair,
    base_ref,
    namespace_compatible,
    unordered_pairs,
)
from .normalize import normalize
from .places import location_attr
from .propose import propose_candidates
from .rconfig import ResolveConfig, ceiling_withholds, grade_meets_floor
from .scoring import (
    COREF_CLUSTER_ATTR,
    COREF_CONTRAST_PREDICATE,
    COREF_EVIDENCE_ATTR,
    COREF_FORMS_ATTR,
    COREF_GATE_ATTR,
    COREF_GATE_DETAIL_ATTR,
    COREF_GATE_PASS,
    COREF_PREDICATE,
    COREF_QUOTE_ATTR,
    COREF_QUOTES_ATTR,
    COREF_REFERENT_ATTR,
    DISTINCT_PREDICATES,
    IDENTITY_PREDICATES,
    critical_conflict_disposition,
    has_hard_conflict,
    identity_ledger,
)

__all__ = [
    "resolve",
    "resolve_with_types",
    "ResolveConfig",
    "resolve_anchors",
    "AnchorResolution",
    "propose_candidates",
    "location_attr",
    "identity_ledger",
    "IDENTITY_PREDICATES",
    "DISTINCT_PREDICATES",
    "COREF_PREDICATE",
    "COREF_CONTRAST_PREDICATE",
    "coref_raise_reasons",
]


def resolve(
    claims: list[ClaimRecord],
    config: ConfigBundle,
    prev_view: GraphView | None = None,
    decisions: list[DecisionRecord] | None = None,
) -> Partition:
    """Resolve claims into entities/edges: candidate-gen → bootstrap → relational fixpoint → places."""
    partition, _types = _resolve(claims, config, prev_view, decisions)
    return partition


def resolve_with_types(
    claims: list[ClaimRecord],
    config: ConfigBundle,
    prev_view: GraphView | None = None,
    decisions: list[DecisionRecord] | None = None,
) -> tuple[Partition, dict[str, str]]:
    """:func:`resolve` + the resolver's entity→ontology-type map (Stage 4 identity coverage, D11).

    Identical computation to :func:`resolve`: the returned ``Partition`` is byte-for-byte the one
    :func:`resolve` returns (gate G2). It *additionally* returns ``{entity_id: type}`` for every entity
    the resolver knows — the complete id universe the partition's ``same_as`` / ``candidates`` /
    ``possible`` links can reference (claim-backed entities, registry-seeded priors, and minted
    triple-endpoints, after node-type refinement). It is a **read** of the resolver's own typing (never a
    second, divergent notion of an entity's type), and is the ``type_of`` source
    :func:`chanakya.view.coverage.identity_coverage` consumes.
    """
    return _resolve(claims, config, prev_view, decisions)


def _resolve(
    claims: list[ClaimRecord],
    config: ConfigBundle,
    prev_view: GraphView | None = None,
    decisions: list[DecisionRecord] | None = None,
) -> tuple[Partition, dict[str, str]]:
    """Shared body: the identity :class:`Partition` + the resolver's post-refinement entity→type map."""
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
    # G19's Phase-1 half rides ``AliasIndex``'s own default now: an alias equivalence must rest on a real LINK
    # between two DIFFERENT surface forms, never on a name being reflexively equal to itself.
    alias_idx = aliases.build(
        cfg.alias_table, cfg.transliteration, decisions, cfg.registry_alias_table,
    )

    # veto = configured distinct-from (by name) ∪ registry distinct-from (by entity id) ∪ gazetteer-distinct
    # place pairs (Karachi-Port ≠ Port-Qasim) ∪ source-asserted distinct-from claims — computed up front so
    # it hard-vetoes an entity-level merge too, not just surfaces as an edge.
    # G18, EVERY RAIL: each veto channel also states its GROUND, keyed by pair, and the grounds are collected
    # in one dict here rather than at each call site. A wall nobody can read is indistinguishable from a
    # missing edge, and — measured — nineteen of the thirty walls drawn on the booted corpus were DERIVED
    # findings (gazetteer, hard identifier) rendering the string "explicit do-not-merge (hard veto)": the
    # identical text used for a genuinely curated analyst veto, so three distinct grounds collapsed into one
    # and the word "explicit" misattributed machine inference to a person.
    wall_grounds: dict[Pair, str] = {}
    curated_veto = _veto_pairs(graph, cfg, alias_idx) | _registry_veto(graph, cfg)
    place_walls, place_wall_reasons = places.place_distinct_pairs(graph, cfg, place_of)
    stated_walls = _claim_distinct_pairs(graph, cfg, alias_idx)
    # Least specific first: a later rail's more specific finding wins the same pair (the same precedence
    # rule the critical/relationship rails already used between themselves).
    wall_grounds.update({p: _curated_wall_reason() for p in curated_veto})
    wall_grounds.update({p: _stated_wall_reason() for p in stated_walls})
    wall_grounds.update(place_wall_reasons)
    veto = curated_veto | place_walls | stated_walls

    # P3.1 (RES-1) — endpoint-as-mention. Runs BEFORE the fixpoint so ``graph.edges`` already carry entity
    # ids when ``merge_score`` runs; that is what revives the relational + source-asserted terms.
    mention, minted, ambiguous = _link_endpoints(graph, cfg, alias_idx, lane, veto)

    # …and again for the endpoints minted a line above, which did not exist for the first pass.
    _refine_node_types(graph, minted, cfg)

    # Re-read the claim-asserted distinct-froms now that endpoints carry entity ids: a document may state a
    # do-not-merge about a mention that only *became* an entity in the line above. Idempotent (a set union).
    # T3b-C — and add the hard-identifier rail: two entities whose names state DIFFERENT bill-of-lading /
    # contract references are a veto, not a low score (config/ontology.yaml ``identifier_patterns``).
    # D5/D6/3A — and the declared-critical-attribute rail, now credibility-gated: two same-type entities
    # STATING different values of a critical attribute (a different country/branch, a unique serial) WALL
    # only when the conflict is trustworthy on both sides (each conflicting value attested by a source
    # at/above ``critical_veto_min_grade``). Below the floor the pair is not walled — it is RAISED to the
    # analyst (``crit_raises``, threaded into the resolver as a block-merge-and-review set), so one flaky
    # low-grade source cannot silently shatter a well-corroborated merge (D5 take-care a).
    crit_walls, crit_wall_reasons, crit_raises = _critical_attribute_walls(graph, cfg)
    # D-13.8/G18 (S3, NEW code) — the RELATIONSHIP rail the judge never had. A stated `based-at`/`operated-by`
    # conflict at overlapping times within one site class is a hard wall; an unreadable class or an undated
    # statement takes C7's third state (no wall, no fusion, a named reason). The walls join `veto` on purpose:
    # that channel is hard AND transitive, re-applied in `finalise`, visible to the D9 bridge alarm and DRAWN,
    # whereas the geo veto's channel is pairwise and invisible — and G18 would pass over either.
    rel_walls, rel_wall_reasons, rel_raises = _relationship_walls(graph, cfg, lane, alias_idx, place_of)
    stated_walls_2 = _claim_distinct_pairs(graph, cfg, alias_idx)
    ident_walls, ident_wall_reasons = _identifier_veto(graph, cfg)
    veto |= stated_walls_2 | ident_walls | crit_walls | rel_walls
    crit_raises = {**crit_raises, **rel_raises}
    # …and the grounds for the four rails resolved after the endpoint pass, least-specific first. The two
    # that had a producer (critical attribute, relationship) keep their existing precedence — relationship
    # last, as the more specific finding — and the two that had none (hard identifier, and the second read of
    # the stated do-not-merges) now have one.
    wall_grounds.update({p: _stated_wall_reason() for p in stated_walls_2 if p not in wall_grounds})
    wall_grounds.update(ident_wall_reasons)
    wall_grounds.update(crit_wall_reasons)
    wall_grounds.update(rel_wall_reasons)
    # The most specific ground there is: a HUMAN decided this pair apart (a `merge_adjudication` reject/split
    # replayed from the decision log). It outranks every derived rail — an override is not a finding (G12).
    wall_grounds.update(
        {
            frozenset(pair): _analyst_wall_reason()
            for pair in cluster.learned_distinct_eid_pairs(alias_idx, graph, cfg.transliteration)
        }
    )

    # The raise-only proposal channels: the offline LLM's frozen proposals and the corpus's own
    # ``same-as`` assertions (D-2.5). Neither can auto-merge; both can put a pair in front of an analyst.
    # In-document coreference is the one signal that may also *bootstrap* — and only for the evidence
    # categories an operator opted in, uncontradicted (see :func:`_coref_pairs`); everything it cannot
    # justify falls back into the same raise-only queue.
    coref_authoritative, coref_raise, coref_declined, coref_walled = _coref_pairs(
        graph, cfg, alias_idx, veto, lane, place_of
    )
    asserted_raise, asserted_walled = _identity_pairs(graph, cfg, alias_idx, veto)
    raise_only = (
        _llm_pairs(graph, cfg, alias_idx, decisions)
        | asserted_raise
        | coref_raise
    )
    # Both channels that can state an identity a hard wall refuses. Merged here so the escalate half has one
    # definition: an assertion the resolver overrode may not vanish, whichever pass produced it.
    walled_assertions = {**asserted_walled, **coref_walled}
    # D-13.19's contrastive channel: a same-document STATED contrast caps the pair at its DECLARED band — it
    # reaches the analyst with its licensing quote and can never auto-merge. Routed through the same
    # block-merge-and-review channel as every other cap, so "not automatically" is expressed once. ABSENCE of
    # a contrast stays NEUTRAL: it is never a prior *for* merging either.
    #
    # The declared band travels WITH the pairs (``raise_ceilings``), because this is the one rail on that
    # channel whose ceiling is a config value rather than a fixed one. The channel was band-blind, so
    # ``contrast_ceiling: possible`` and ``: probable`` produced identical behaviour while the reason prose
    # dutifully quoted whichever was configured — the config file describing a control the system did not
    # have, and the analyst reading a band nobody computed. Shipped value is ``probable``, so this is
    # byte-unchanged on the shipped configuration; what changes is that the other legal value now works.
    contrast_caps = _contrast_ceilings(graph, cfg, alias_idx)
    crit_raises = {**crit_raises, **coref_declined, **contrast_caps}
    raise_ceilings = {p: cfg.earned_identity.contrast_ceiling for p in contrast_caps}
    # D-13.17/C4: the licensing evidence, finally SURFACED. It was stamped on the claim and read nowhere, so
    # every justification of raise-only ("the analyst is handed the exact sentence") described a screen nobody
    # could see — and with the gates in place this queue is load-bearing, not a fallback.
    coref_reasons = coref_raise_reasons(graph, cfg, coref_authoritative, coref_raise, alias_idx)

    # RK-COREF item 11 — THE ORDERING FIX. Place identity is decided BEFORE the fixpoint and joins the
    # bootstrap, so a place merge is visible to ``relational_score``: two units based at
    # differently-named-but-identical sites now genuinely share a neighbour key. Ran afterwards (as it did),
    # a place merge could never scaffold anything, so spine/13 §6's "clean anchor the instance layer
    # crystallizes onto" was mechanically not one. This is also what makes the name cap survivable rather
    # than merely strict — a pair can now EARN the one extra signal the cap asks for.
    place_auto, place_hitl = places.place_merge_pairs(graph, cfg, alias_idx, veto, place_of)
    place_authoritative: set[Pair] = {frozenset(p) for p in place_auto}
    raise_only |= {frozenset(p) for p in place_hitl}

    result = resolve_entities(
        graph, cfg, alias_idx, veto, raise_only, coref_authoritative,
        raise_walls=crit_raises, raise_ceilings=raise_ceilings,
        place_identity=place_authoritative,
    )
    result.candidates.extend(ambiguous)  # an endpoint with >1 irreconcilable match is adjudicated, never guessed
    # G18: the wall must be READABLE. A wall nobody can read is indistinguishable from a missing edge, so the
    # reason rides the drawn do-not-merge edge (``view/pipeline._resolution_edges``).
    #
    # EVERY DERIVED RAIL, not just the relationship one. G18 landed with the relationship wall and wired only
    # that rail's reasons, so the attribute rail — the one that walls two same-named organisations stating
    # China and Pakistan, the costliest over-merge in an operator-scoped ORBAT — drew its do-not-merge edge
    # with the generic fallback and no ground named. Two refusals with two different causes read identically
    # to the analyst, which is the "fixed default wearing a rationale's clothes" failure: every "a reason
    # exists" check passes and the reason instructs nobody. The rails are merged in a fixed order so a pair
    # walled by both gets a stable reason (the relationship rail last, as the more specific finding) — that
    # ordering is now applied once, when ``wall_grounds`` is built above, and every rail that can draw a wall
    # is in it: curated config/registry, source-stated, gazetteer place, hard identifier, critical attribute,
    # relationship conflict, and the analyst's own replayed reject/split.
    result.wall_reasons.update(
        {pair_key(*sorted(p)): why for p, why in wall_grounds.items()}
    )
    # …and the ESCALATE half for the same collision. A wall that outranked a source's stated identity owes each
    # endpoint a named Known Gap, or the assertion the resolver overrode reached nobody. ``setdefault``, not
    # ``update``: ``fusion_blocked``'s own type/namespace refusal is the more specific finding where both fire,
    # and ``finalise`` prunes any entry whose endpoints ended up in one cluster along some other chain.
    for pair, what_missing in sorted(walled_assertions.items(), key=lambda kv: sorted(kv[0])):
        result.identity_refusals.setdefault(pair_key(*sorted(pair)), what_missing)
    # A raised coreference link keeps its licensing evidence on the queue item — BESIDE any reason the
    # resolver already recorded, never instead of it. The two answer different questions and the analyst needs
    # both: the resolver's reason says why the merge was WITHHELD (a critical conflict, a cap), the coref
    # reason says why it was PROPOSED and quotes the sentence that proposed it. `setdefault` looked safe and
    # silently dropped the quote the moment any cap fired on the same pair — which, with the name cap
    # unconditional, is the common case for a coreference link between two similar names. Losing the sentence
    # is what makes raise-only fictional (D-13.17).
    for pair, why in sorted(coref_reasons.items(), key=lambda kv: sorted(kv[0])):
        a, b = sorted(pair)
        existing = result.candidate_reasons.get(pair_key(a, b))
        result.candidate_reasons[pair_key(a, b)] = f"{existing}\n\nALSO: {why}" if existing else why
    finalise(result, graph, cfg, veto, alias_idx)  # reconcile all merges into one flat, veto-guarded map

    partition = _to_partition(claims, result, mention, minted, place_of, lane, graph)
    # The resolver's own typing, for Stage-4 coverage (D11): every entity id the partition can reference
    # — claim-backed, registry-seeded, or minted endpoint — mapped to its refined ontology type. A read,
    # not a re-derivation: ``graph.entities`` is the exact universe the merge decisions scored over.
    type_map = {eid: ent.etype for eid, ent in graph.entities.items()}
    return partition, type_map


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

# ── G18/B4: one truthful text per rail that can draw a wall ─────────────────────────────────────
#
# Three distinct grounds used to render one string — "explicit do-not-merge (hard veto)" — and only one of
# them was explicit. The word matters: it tells an analyst a *person* already ruled on this pair, so applying
# it to a machine inference both misattributes the decision and removes the analyst's reason to check it. Each
# rail now says what it is and, where it is derived, says so and names what would correct it.

def _curated_wall_reason() -> str:
    """The one rail where "explicit" is TRUE: a curated do-not-merge in config/entities.yaml or the
    ``distinct_from`` alias block. A human wrote this pair down; the resolver only instantiated it."""
    return (
        "explicit curated do-not-merge — this pair is written down as two different things in the curated "
        "reference data (the entity registry / the distinct-from table), so no amount of resemblance may fuse "
        "it. These are the flagship traps of the subject (an export designator that is NOT the design it is "
        "usually printed beside, two commands of different services). To overturn it, change the curated "
        "entry: the resolver will not, and an analyst merge is the only override."
    )


def _stated_wall_reason() -> str:
    """A SOURCE went out of its way to say "this is not that" — the cheapest high-value evidence there is.

    Distinct from the curated rail because the authority is different: a document, quotable, and the claim is
    on the drawn edge's ``claim_ids`` — so unlike the derived rails, this one's ground is one click from the
    sentence. Deliberately ungraded (see :func:`_claim_distinct_pairs`): the cost of honouring a wrong one is
    two nodes an analyst can still merge.
    """
    return (
        "a SOURCE states these are different — a document in evidence asserts a do-not-merge between these "
        "two mentions (the cited claim is the sentence). Not a curated rule and not a machine inference: an "
        "author disambiguating their own subject. Honoured ungraded, because the cost of honouring a wrong one "
        "is two nodes an analyst can merge, while the cost of ignoring a right one is a fused distinction "
        "nobody can recover."
    )


def _analyst_wall_reason() -> str:
    """An ANALYST decided this pair apart — a ``merge_adjudication`` reject/split replayed from the log.

    The most specific ground there is, and it outranks every derived rail: an override is a decision, not a
    finding (G12). It also explains a wall that no config file mentions, which is otherwise the most
    confusing wall an analyst can meet.
    """
    return (
        "an ANALYST adjudicated these apart — a proposed merge was rejected (or an existing one split) in the "
        "decision log, and that decision is replayed on every rebuild, so the wall holds without anyone "
        "having to edit config. This is a human judgement about these two mentions, not a machine finding; "
        "the audit trail is the adjudication record itself."
    )


def _identifier_wall_reason(ident_a: str, ident_b: str) -> str:
    """Analyst-facing ground for the hard-identifier wall (T3b-C) — a DERIVED finding, and it says so.

    Deliberately never the word *explicit*: nobody curated this pair. The resolver read a bill-of-lading /
    contract reference out of each name and found two different ones. Naming the two references is most of
    the value — an analyst who thinks the wall is wrong needs to know *which* identifiers were compared,
    because the usual cause of a wrong one is an extraction that swept a reference off the wrong line.
    """
    return (
        f"held apart by two DIFFERENT stated hard identifiers ({ident_a} ≠ {ident_b}). A bill-of-lading or "
        f"contract reference is an identity, not a description, so two different ones are two different "
        f"things — fusing them would collapse two import events into one and silently corrupt the "
        f"supply-chain count. This wall is DERIVED by the resolver from the two names; it is not a curated "
        f"do-not-merge. If the two references belong to one shipment, the extraction is what is wrong, and an "
        f"analyst merge overrides this (T3b-C)."
    )


def _identifier_veto(graph: EntityGraph, cfg: ResolveConfig) -> tuple[set[Pair], dict[Pair, str]]:
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

    Returns ``(walls, reasons)``. The reasons are what G18 asks of *every* rail that can draw a wall, and
    this one had none: its drawn edge carried the generic "explicit do-not-merge" label, which is false twice
    over — the finding is derived rather than explicit, and it named neither of the two identifiers it
    compared. Six of the thirty drawn walls on the booted corpus came from here.
    """
    ntx = cfg.node_types
    by_type: dict[str, list[tuple[str, str]]] = {}
    for eid, ent in sorted(graph.entities.items()):
        ident = ntx.identifier(ent.etype, ent.name)
        if ident is not None:
            by_type.setdefault(ent.etype, []).append((eid, ident))
    out: set[Pair] = set()
    reasons: dict[Pair, str] = {}
    for members in by_type.values():
        for (a, ident_a), (b, ident_b) in unordered_pairs(members):
            if ident_a != ident_b:
                pair = frozenset((a, b))
                out.add(pair)
                reasons[pair] = _identifier_wall_reason(*sorted((ident_a, ident_b)))
    return out, reasons


# ── D5/D6/3A: the declared-critical-attribute rail, credibility-gated (a serial/branch clash walls) ──

def _critical_attribute_walls(
    graph: EntityGraph, cfg: ResolveConfig
) -> tuple[set[Pair], dict[Pair, str], dict[Pair, str]]:
    """Split same-type declared-critical conflicts into hard **walls** and analyst **raises** (D5 + 3A).

    Returns ``(walls, wall_reasons, raises)``. ``wall_reasons`` used not to exist here, and its absence was
    the sharpest surviving hole in the escalate half of the non-negotiable — see the ``disposition == "wall"``
    branch below.

    The D5 wall, generalised from the geographic (``geo_conflict_km``) and hard-identifier
    (:func:`_identifier_veto`) rails to *any* attribute the ontology's ``attribute_roles`` declares
    ``critical`` for a type. Stage 3A adds the credibility floor of D5 take-care (a): a stated critical
    disagreement is a hard **wall** only when it is *trustworthy on both sides* — each side's conflicting
    value attested by a source graded at/above ``critical_veto_min_grade``. Below the floor the pair is a
    **raise** (returned separately, mapped to a human-legible reason): one flaky low-grade source must not
    silently shatter a well-corroborated merge, so the pair goes to the analyst as a ``probable`` candidate
    rather than being walled — or silently merged.

    * ``walls`` join the veto set beside the identifier rail, so transitive enforcement, the before-scoring
      guard and the drawn do-not-merge edge are all handled by the existing machinery
      (``cluster.vetoed`` / ``violates_veto_transitively``).
    * ``raises`` are threaded to the resolver as its ``raise_walls`` set: blocked from bootstrap/auto-merge
      *and* forced into the HITL candidate queue (never dropped).

    Reuses :func:`scoring.critical_conflict_disposition` (same-type, absence ≠ conflict), so "what counts
    as a critical disagreement" keeps one definition. A type that declares no critical attribute is
    unaffected; a pair where either side is silent is never walled. Floor OFF ⇒ every conflict is credible
    ⇒ ``raises`` is empty and ``walls`` is exactly the pre-Stage-3A unconditional veto (byte-unchanged).
    """
    floor = cfg.critical_veto_min_grade
    by_type: dict[str, list[str]] = {}
    for eid, ent in sorted(graph.entities.items()):
        # The enumeration is wider than the ``critical`` rows: a type that declares no critical attribute may
        # still declare a ``constitutive`` one (C6) or hold an unreadable wall-eligible slot (C7), and both
        # must bind the fusion path.
        interesting = bool(cfg.critical_role_attrs(ent.etype)) or bool(cfg.constitutive_attrs(ent.etype))
        if interesting or cfg.earned_identity.normalization_required_attrs:
            by_type.setdefault(ent.etype, []).append(eid)
    walls: set[Pair] = set()
    wall_reasons: dict[Pair, str] = {}
    raises: dict[Pair, str] = {}
    for eids in by_type.values():
        for a, b in unordered_pairs(eids):
            ea, eb = graph.entities[a], graph.entities[b]
            disposition, attrs = critical_conflict_disposition(ea, eb, cfg)
            if disposition == "wall":
                walls.add(frozenset((a, b)))
                # THE REASON SURVIVES THE WALL. ``critical_conflict_disposition`` computes exactly which
                # critical attributes are in credible disagreement and hands them back; this branch used to
                # drop them on the floor while the *raise* branch two lines below kept them. So the softer
                # outcome explained itself and the harder one did not, and the hardest refusal in the system
                # reached the analyst as ``view/pipeline``'s fallback string: "explicit do-not-merge (hard
                # veto)". No attribute named, no values quoted, identical on every rail — a curated veto an
                # analyst wrote and a derived one the system computed read the same, which is precisely the
                # distinction ``wall_reasons`` was introduced to draw (G18: "a wall the system *derived* does
                # [need explanation]: a stated relationship conflict … is a finding, and a finding with no
                # stated grounds is indistinguishable from a missing edge").
                #
                # The cost was not cosmetic. This is the rail that walls two same-named trading orgs stating
                # China and Pakistan — the costliest over-merge for an operator-scoped ORBAT, and the one the
                # analyst most needs to adjudicate. It fired correctly and told nobody why, so the analyst
                # could not tell it from a pair that never resembled each other. Refusing to assert is half
                # the non-negotiable; this is the other half.
                wall_reasons[frozenset((a, b))] = _critical_wall_reason(attrs, ea, eb, floor)
                continue
            if disposition == "raise":
                raises[frozenset((a, b))] = _critical_raise_reason(attrs, floor)
                continue
            # C7's THIRD STATE, on the attribute rail. An unreadable stated value on a slot we intend to wall
            # on is neither a conflict nor an agreement — so it may not wall (that would shatter a legitimate
            # merge) and it may not FUSE (that would assert an identity the evidence does not support). It
            # joins the block-merge-and-review channel, which is what makes the gap *bind* rather than merely
            # annotate — the rk-14 probe bug generalised: the prototype named the missing operator gap and
            # then drew the cross-army relocation anyway.
            unreadable = scoring.unnormalizable_critical_values(ea, eb, cfg)
            if unreadable:
                raises[frozenset((a, b))] = _unnormalizable_reason(unreadable)
                continue
            # C6's negative half: a difference on a ``constitutive`` attribute is DISTINCTNESS. Raised rather
            # than walled, because the strength of a constitutive difference depends on the attribute being
            # read correctly and a stated value we have not grade-checked should not shatter a cluster.
            differing = scoring.constitutive_difference(ea, eb, cfg)
            if differing:
                raises[frozenset((a, b))] = _constitutive_difference_reason(differing)
    return walls, wall_reasons, raises


def _critical_wall_reason(
    attrs: tuple[str, ...], a: Entity, b: Entity, floor: str | None
) -> str:
    """Why a credible critical-attribute disagreement holds this pair apart, in words an analyst can act on.

    Quotes the **stated values on both sides**, because the attribute name alone is not the analyst's
    instruction — "these disagree on origin_country" and "one source says China, the other Pakistan" ask for
    different next actions, and only the second says which document to go and read. The values come off the
    entities, never from a table, so a rail added later cannot get a stale copy (gate G6: prose only, no
    thresholds, no code literals).

    Deliberately different prose from :func:`_critical_raise_reason`: a wall and a raise are two different
    verdicts about the same disagreement (credible on both sides vs. not), and if they read alike the analyst
    cannot tell which one the system reached.
    """
    which = ", ".join(attrs) if attrs else "a critical attribute"
    at = f" at/above the credibility floor ({floor})" if floor else ""
    stated = "; ".join(
        f"{k}: {a.attrs.get(k)!r} vs {b.attrs.get(k)!r}"
        for k in (attrs or ())
        if a.attrs.get(k) is not None or b.attrs.get(k) is not None
    )
    detail = f" Stated values — {stated}." if stated else ""
    return (
        f"held apart by a stated critical-attribute contradiction on {which}: both sides state the attribute, "
        f"the values disagree, and each side's value is attested{at}, so this is a contradiction between two "
        f"credible sources rather than one flaky reading.{detail} These are therefore not one entity however "
        f"alike their names look — for an operator-scoped order of battle a wrong fusion here silently moves "
        f"an asset from one army to another and every downstream count inherits it. The resemblance is real "
        f"and is recorded: adjudicate which value is right, or have a source state one value for both "
        f"mentions, and the pair resolves on its merits (D5/D6)."
    )


def _unnormalizable_reason(attrs: tuple[str, ...]) -> str:
    """C7's third state on the attribute rail: no wall, no fusion, a named gap. Prose only (gate G6)."""
    which = ", ".join(attrs)
    return (
        f"unreadable critical value on {which} — both sides state it, the values differ, and at least one is "
        f"not a member of any declared equivalence class, so the system cannot tell a genuine disagreement "
        f"from a spelling. Walling on it would shatter a legitimate merge ('PAF' vs 'Pakistan Air Force'); "
        f"letting the pair confirm would assert an identity the evidence does not support. So it does "
        f"NEITHER: the merge is withheld and the pair is raised with the missing normalisation named. Add the "
        f"stated form to that attribute's equivalence classes and the pair resolves on its merits (C7)."
    )


def _constitutive_difference_reason(attrs: tuple[str, ...]) -> str:
    """C6's negative half: a difference on a CONSTITUTIVE attribute is distinctness. Prose only (G6)."""
    which = ", ".join(attrs)
    return (
        f"constitutive difference on {which} — this attribute is part of what the instance IS (a presence "
        f"*is* its operator, its design, its site and its window), so it cannot change without the thing "
        f"being a DIFFERENT instance. A difference here is therefore evidence of distinctness, not of a "
        f"stale reading, and it is not something a later report can 'update'. The merge is withheld and the "
        f"pair is raised: if these really are one instance, one of the two stated constitutive values is "
        f"wrong, and that is the question to adjudicate (C6)."
    )


def _critical_raise_reason(attrs: tuple[str, ...], floor: str | None) -> str:
    """The analyst-facing rationale for a below-floor critical-conflict raise (D5 take-care a)."""
    which = ", ".join(attrs) if attrs else "a critical attribute"
    at = f" (grade < {floor})" if floor else ""
    return (
        f"critical-attribute conflict on {which} below the source-credibility floor{at}: the conflicting "
        f"value is asserted only by below-floor sources on at least one side, so the difference is not "
        f"trustworthy enough to wall — raised for analyst adjudication (D5)."
    )


# ── D-13.8 / G18: the relationship-conflict WALL (NEW code — the judge had no relationship rail) ─

#: The type stamped on a mention nothing in the document declared — a bare relation endpoint. It COUNTS as
#: type-compatible in the anaphor gate, which is the clause that makes an under-reach fail the gate.
_UNKNOWN_ETYPE = "unknown"
#: "Exactly one type-compatible antecedent" — the cardinality the positive gate demands, named so the test
#: reads as the rule rather than as an integer (gate G6 bans numeric literals in scoring code).
_ONE_ANTECEDENT = 1

#: The predicate whose claim was *stated by a source* rather than derived by the rebuild or a proposer.
#: A derived basing is not a source saying "this unit is there", so it may never wall a merge on its own.
_STATED_KIND = "observation"


def _intervals_overlap(a: tuple[str | None, str | None], b: tuple[str | None, str | None]) -> bool:
    """Do two ISO validity intervals overlap? An UNKNOWN bound fails **safe** — it counts as overlapping.

    The wall exists to keep two units that are in different places *at the same time* apart. If we cannot
    read when one of the statements held, we do not get to conclude they were at different times: the honest
    reading is "possibly concurrent", and the fail-safe direction here is towards *not fusing*. (The caller
    then softens an unknown-time conflict from a hard wall to a raise — the same asymmetry C1 gives an
    unknown ``site_type``: never de-conflicted, but not silently walled either.)
    """
    lo_a, hi_a = a
    lo_b, hi_b = b
    if hi_a is not None and lo_b is not None and hi_a < lo_b:
        return False
    if hi_b is not None and lo_a is not None and hi_b < lo_a:
        return False
    return True


def _same_place(a: str, b: str, graph: EntityGraph, cfg: ResolveConfig, alias_idx: AliasIndex,
                place_of: dict[str, places.PlaceMatch]) -> bool:
    """Are two relationship OBJECTS the same thing, before resolution has run?

    The wall is computed up front (it has to be — it joins ``veto``, which is consulted before any band), so
    it cannot ask the partition. Three cheap, evidence-backed tests instead: the same id; the same curated
    gazetteer anchor (the place layer's own answer to "same place", already computed in this pass); or two
    names in one alias class. Anything else counts as *different*, which is the direction that walls — so
    this predicate is deliberately generous, because a wrong "different" costs a legitimate merge.
    """
    if a == b:
        return True
    ma, mb = place_of.get(a), place_of.get(b)
    if ma is not None and mb is not None and ma.place_id is not None and ma.place_id == mb.place_id:
        return True
    ea, eb = graph.entities.get(a), graph.entities.get(b)
    if ea is None or eb is None:
        return False
    return alias_idx.equivalent(
        normalize(ea.name, cfg.transliteration), normalize(eb.name, cfg.transliteration)
    )


def _stated_relations(
    graph: EntityGraph, cfg: ResolveConfig, lane: EdgeLaneIndex
) -> dict[tuple[str, str], list[tuple[str, str | None, str | None, str, bool]]]:
    """``(subject, predicate) → [(object, lo_iso, hi_iso, scope_bucket, scope_known)]`` for wall predicates.

    **C1 as amended by S2 — the scope decision is per ``(subject, predicate)``, over EVERY relationship of
    that subject, and it is a post-pass, never a key input.** A ``based-at`` conflict is only a conflict
    *within one kind of site*: a unit at its garrison and concurrently at a forward site is one unit with two
    valid basings. Scoping by class is therefore *de-confliction* — and separation IS de-confliction, so a
    **partial** tag is worse than none. S2 measured this the hard way: a per-edge tag put the flagship
    relocation's two ends in different buckets (one describes a revetment complex, the other an airfield) and
    the supersede silently never fired, with nothing anywhere to say so.

    So: all of a subject's classes readable ⇒ scope by class; **any** unreadable ⇒ the whole subject collapses
    to one shared bucket with ``scope_known=False``, which the caller turns into "no wall, no fusion, a named
    reason" rather than a silent de-confliction in either direction.
    """
    earned = cfg.earned_identity
    layers = cfg.layer_routing
    scope_attr = earned.wall_scope_attr
    out: dict[tuple[str, str], list[tuple[str, str | None, str | None, str, bool]]] = {}
    raw: dict[tuple[str, str], list[tuple[str, str | None, str | None, str, bool]]] = {}
    for e in graph.edges:
        if e.predicate not in earned.wall_predicates or e.kind != _STATED_KIND:
            continue
        # The scope attribute lives on the endpoint the functional key DROPS (for ``based-at``, the site,
        # whose class says what kind of basing this is) — the same endpoint S2's ``_tag_of`` reads. A
        # predicate the ontology gives no ``instance_key_tag`` (``operated-by``) is unscoped: a change of
        # operator is never de-conflicted by anything, so every such relation shares one bucket.
        tagged = lane.instance_key_tag(e.predicate) == scope_attr and bool(scope_attr)
        if tagged:
            obj = graph.entities.get(e.object)
            bucket, mapped = layers.normalise_tag(obj.attrs.get(scope_attr) if obj is not None else None)
        else:
            bucket, mapped = "", True
        raw.setdefault((e.subject, e.predicate), []).append(
            (e.object, e.earliest_iso, e.latest_iso, bucket, mapped)
        )
    for key, rows in raw.items():
        if all(mapped for *_rest, mapped in rows):
            out[key] = rows
        else:  # any unreadable class ⇒ ONE bucket for the whole subject, flagged unknown (C1 ⊂ C7)
            out[key] = [(obj, lo, hi, "", False) for obj, lo, hi, _bucket, _mapped in rows]
    return out


def _relationship_walls(
    graph: EntityGraph,
    cfg: ResolveConfig,
    lane: EdgeLaneIndex,
    alias_idx: AliasIndex,
    place_of: dict[str, places.PlaceMatch],
) -> tuple[set[Pair], dict[Pair, str], dict[Pair, str]]:
    """G18: a STATED ``based-at``/``operated-by`` conflict at overlapping times → ``(walls, reasons, raises)``.

    **The judge had no relationship discriminator at all.** ``relational_score`` is a Jaccard over *shared*
    neighbour keys, so it can only ever say "these two look alike because they touch the same things"; there
    was no comparison of two candidates' basing or operator *values*, and therefore no way for the system to
    notice that two profiles are in different places at the same time. Two units at different sites at
    overlapping times are **different units**, and that is a cannot-link no similarity score may cross —
    a wall, not a term.

    **The channel is named deliberately.** ``walls`` join the ``veto`` set, which is hard **and transitive**,
    re-applied in ``finalise``, visible to the D9 bridge alarm, and **drawn** as a do-not-merge edge. Built
    the way the geographic veto is built — consulted only inside ``cluster.vetoed`` — the wall would be
    pairwise, non-transitive **and invisible**, and G18 would still pass. ``reasons`` is what makes it
    analyst-visible: a wall nobody can read is indistinguishable from a missing edge.

    ``raises`` is C7's third state, reached when the ``site_type`` scope is unreadable on either side: **no
    wall** (an unreadable class must not shatter a legitimate merge) **and no fusion** (it must not confirm
    either) **plus a named reason**. All three or none.
    """
    walls: set[Pair] = set()
    reasons: dict[Pair, str] = {}
    raises: dict[Pair, str] = {}
    if not cfg.earned_identity.wall_predicates:
        return walls, reasons, raises

    relations = _stated_relations(graph, cfg, lane)
    subjects_by_pred: dict[str, list[str]] = {}
    for subject, predicate in relations:
        subjects_by_pred.setdefault(predicate, []).append(subject)

    for predicate, subjects in sorted(subjects_by_pred.items()):
        for a, b in unordered_pairs(sorted(set(subjects))):
            ea, eb = graph.entities.get(a), graph.entities.get(b)
            if ea is None or eb is None or ea.etype != eb.etype:
                continue  # a cross-type pair is not fusable anyway (G19) — nothing for the wall to add
            for oa, lo_a, hi_a, bucket_a, known_a in relations[(a, predicate)]:
                for ob, lo_b, hi_b, bucket_b, known_b in relations[(b, predicate)]:
                    # C1, and the trap inside it: a differing class de-conflicts ONLY when BOTH classes are
                    # readable. Where either side's class is unknown the buckets must not be compared at all —
                    # because separation IS de-confliction, and letting an unknown bucket differ from a known
                    # one is precisely the silent failure S2 measured across *edges*, reproduced here across
                    # *subjects*: the conflict quietly stops being detected while the code still looks
                    # deterministic, with no gap and no flag. Unknown ⇒ fall through to the conflict test, and
                    # (below) raise rather than wall.
                    if known_a and known_b and bucket_a != bucket_b:
                        continue  # a DIFFERING KNOWN class is not a conflict — garrison + forward site is fine
                    if _same_place(oa, ob, graph, cfg, alias_idx, place_of):
                        continue  # both stated the same thing — agreement, not conflict
                    if not _intervals_overlap((lo_a, hi_a), (lo_b, hi_b)):
                        continue  # sequential, not concurrent — that is a relocation, not two entities
                    pair = frozenset((a, b))
                    timed = lo_a is not None and hi_a is not None and lo_b is not None and hi_b is not None
                    if known_a and known_b and timed:
                        walls.add(pair)
                        reasons[pair] = _wall_reason(predicate, bucket_a)
                        raises.pop(pair, None)
                    elif pair not in walls:
                        raises[pair] = _wall_third_state_reason(predicate, known_a and known_b, timed)
    return walls, reasons, raises


def _wall_reason(predicate: str, bucket: str) -> str:
    """The analyst-facing reason a relationship wall holds this pair apart (G18). Prose only (gate G6)."""
    scope = f" within one '{bucket}' site class" if bucket else ""
    return (
        f"stated '{predicate}' conflict at overlapping times{scope} — two sources place these two profiles "
        f"in different, concurrently-valid relationships that one entity cannot hold at once. Two units at "
        f"different sites at the same time are different units, so this is a cannot-link no similarity score "
        f"may cross: it holds transitively (no chain of merges may fuse them either) and it is not a low "
        f"score to be argued up. If the two really are one unit, the fault is in one of the two stated "
        f"relationships or in their dates — adjudicate those, not this wall (D-13.8/G18)."
    )


def _wall_third_state_reason(predicate: str, scope_known: bool, timed: bool) -> str:
    """C7's third state on the relationship rail: no wall, no fusion, a named reason. Prose only (G6)."""
    missing = []
    if not scope_known:
        missing.append("the kind of site is not stated, or is stated in words the closed vocabulary "
                       "cannot read, on at least one of this subject's relationships")
    if not timed:
        missing.append("at least one of the two statements carries no readable validity interval")
    why = "; and ".join(missing)
    return (
        f"unreadable '{predicate}' conflict — these two profiles state different, apparently concurrent "
        f"relationships, but {why}. So the disagreement can be neither trusted as a wall nor waved away: "
        f"walling on an unreadable value would shatter a legitimate merge, and letting the pair confirm "
        f"would assert an identity the evidence does not support. The merge is withheld and the pair is "
        f"raised with this gap named — a gap that does not bind the fusion path is decoration (C7)."
    )


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
) -> tuple[set[Pair], dict[Pair, str]]:
    """A source-stated ``same-as`` → a **raise-only** merge signal (never an auto-merge).

    The asymmetry with :func:`_claim_distinct_pairs` is the whole of D-2.5: a "these are the same" is the
    assertion an adversary plants (the corpus cross-wires an Army variant onto the PAF one), so it only ever
    *proposes*, and a vetoed pair is dropped outright — a stated do-not-merge outranks a stated same-as. The
    asserting source's grade rides separately, in ``source_asserted_score``: a curated register's identity
    claim scores higher than an anonymous repost's, but neither can merge on its own.

    **A cross-type or cross-namespace assertion is KEPT, not dropped.** It used to be skipped here, which made
    the escape hatch the candidate-collection loop documents ("if a source explicitly asserts the identity the
    pair is in ``raise_only`` and still reaches the analyst — a cross-type assertion is exactly the kind of
    thing a human should see") fictional for the source-asserted channel, while the LLM-proposal channel beside
    it kept such pairs. A source stating that a *component* and a *variant* are one thing is either an
    extraction error, a typing error, or deception, and all three are findings. Keeping it costs nothing in
    safety: the pair cannot fuse — ``cluster.fusion_blocked`` refuses cross-type and cross-namespace fusion in
    both phases unconditionally — so what the assertion buys is a queue place and a named gap, not a merge.

    Returns ``(raise_only, walled)``. ``walled`` is the same channel :func:`_coref_pairs` returns and for the
    same reason: the verdict "a stated do-not-merge outranks a stated same-as" is right, and it was being
    reached *silently*. This function's own paragraph above argues that a contradicted assertion "is either an
    extraction error, a typing error, or deception, and all three are findings", and buys the pair "a queue
    place and a named gap" — while the wall case two lines below dropped the assertion outright and bought it
    neither. Two channels can assert an identity a wall refuses; both now name it.
    """
    out: set[Pair] = set()
    walled: dict[Pair, str] = {}
    for pair in _asserted_pairs(graph, cfg, alias_idx, IDENTITY_PREDICATES):
        a, b = sorted(pair)
        if pair in veto:
            walled[pair] = _walled_assertion_gap(
                graph.entities[a], graph.entities[b],
                "a source-stated same-as", _asserted_identity_quote(graph, a, b),
            )
            continue
        if _best_identity_weight(graph, cfg, a, b) < cfg.identity_raise_min_weight:
            continue
        out.add(pair)
    return out, walled


def _asserted_identity_quote(graph: EntityGraph, a: str, b: str) -> Any:
    """The licensing span from the best-placed source asserting ``a ≡ b``, or ``None`` if none carried one.

    Read off the claim rather than paraphrased: the escalation is only adjudicable in one read if it carries
    the document's own sentence, and an audit already found that promise fictional once.
    """
    for e in graph.edges:
        if e.predicate in IDENTITY_PREDICATES and {e.subject, e.object} == {a, b}:
            quote = (e.attributes or {}).get(COREF_QUOTE_ATTR)
            if isinstance(quote, str) and quote.strip():
                return quote
    return None


def _best_identity_weight(graph: EntityGraph, cfg: ResolveConfig, a: str, b: str) -> float:
    """The grade of the best source asserting a≡b — the triage gate's input (0.0 ⇒ nothing asserts it)."""
    weights = [
        cfg.identity_source_weight(e.source_id)
        for e in graph.edges
        if e.predicate in IDENTITY_PREDICATES and {e.subject, e.object} == {a, b}
    ]
    return max(weights) if weights else 0.0


# ── in-document coreference: authoritative-unless-contradicted (INGEST pass 2) ─────────────────

def _endpoint_eids(ref: str, graph: EntityGraph, cfg: ResolveConfig, alias_idx: AliasIndex) -> list[str]:
    """Every entity the endpoint's surface form denotes — the id it was rewritten to **and its name-class**.

    ``_link_endpoints`` rewrites a triple's endpoints onto entity ids before any of this runs, and for a form
    no entity id matched it **mints** ``ent:<type>:<form>`` rather than attaching to the claim-backed entity
    of the same name. So a coreference link about "8th AD Battalion" arrives pointing at a *minted twin* of the
    profile the document meant, and ``_matching_eids`` on an id short-circuits to that twin alone.

    For a channel that only ever *added* merges (which coreference used to be) that was harmless — the twin and
    the profile merge on their exact name anyway. For a **ceiling** it is fatal: the cap lands on the twin's
    pair while the claim-backed pair fuses beside it, i.e. a cap keyed to the wrong id form does nothing at
    all. Expanding through the endpoint's *name* puts the whole surface-form class in scope, which is what the
    document's mention actually denotes.
    """
    out = list(_matching_eids(ref, graph, cfg, alias_idx))
    ent = graph.entities.get(ref)
    if ent is not None and ent.name:
        for eid in _matching_eids(ent.name, graph, cfg, alias_idx):
            if eid not in out:
                out.append(eid)
    return sorted(out)


def _licensing_spans(e: Edge) -> list[str]:
    """The link's licensing spans, from either carrier. Verbatim-checked at ingest, where the document is."""
    raw = (e.attributes or {}).get(COREF_QUOTES_ATTR)
    if isinstance(raw, (list, tuple)):
        return [str(q) for q in raw if q]
    quote = (e.attributes or {}).get(COREF_QUOTE_ATTR)
    if isinstance(quote, (list, tuple)):
        return [str(q) for q in quote if q]
    return [str(quote)] if quote else []


def _link_forms(e: Edge, graph: EntityGraph) -> tuple[str, str]:
    """The two members' surface forms — the stamped pair, else the endpoint entities' own names.

    ``_link_endpoints`` rewrites a triple's endpoints onto entity ids before this runs, so the raw forms the
    document used are no longer on the edge. The producer stamps them; where it did not (a hand-built claim,
    a fixture, an older bundle) the endpoint entities' names are the same strings by construction, because
    that is what the mint used.
    """
    stamped = (e.attributes or {}).get(COREF_FORMS_ATTR)
    if isinstance(stamped, (list, tuple)):
        try:
            anchor, member = stamped  # a PAIR, read by unpacking — no length literal (gate G6)
        except ValueError:
            anchor, member = None, None
        if anchor and member:
            return str(anchor), str(member)
    sub, obj = graph.entities.get(e.subject), graph.entities.get(e.object)
    return (sub.name if sub else e.subject), (obj.name if obj else e.object)


def _anaphor_gate_from_graph(e: Edge, graph: EntityGraph) -> tuple[bool, str]:
    """The POSITIVE anaphor gate, recomputed from the graph — so the category is bindable from a bundle.

    I first made this producer-only, on the grounds that the gate needs "the document's whole mention
    inventory". That was half true and wholly wrong in effect: the graph carries a *document axis*
    (``Entity.doc_ids``, added for C9) and it carries the minted endpoints too, so the inventory the gate needs
    is right here. Requiring a stamp instead left the shipped config claiming a category binds while the
    resolver could never bind it — and D-13.17's conditional is precisely that *"the gate IS the decision:
    either the positive gate is built and the category binds, or the category is raise-only — never a config
    that claims one and does the other."*

    Positive, so every clause demands something be PRESENT (the original absence test failed **open** under
    extractor under-reach, which made its failure mode anti-correlated with safety):

    1. the antecedent is **named**;
    2. the antecedent is **declared** — it carries claims of its own, so something in the document asserted it
       rather than it arriving as a bare endpoint;
    3. the antecedent is **ontology-typed**;
    4. **exactly one** type-compatible mention is in scope, with an ``unknown``-typed endpoint **counting as
       compatible**. That last clause is what makes the test bite in the right direction: a second undeclared
       endpoint is exactly what an under-reach would hide, so it must FAIL the gate rather than pass it.

    Scope is the contributing document, plus entities carrying no document at all (a minted endpoint, a
    registry seed) — the same rule C9 uses, and for the same reason: a mention with no document cannot
    contradict the document scope, and excluding it would hide the undeclared endpoints clause 4 exists to
    count.
    """
    antecedent, anaphor = graph.entities.get(e.subject), graph.entities.get(e.object)
    if antecedent is None or anaphor is None:
        return False, "one end of the link is not an instantiated entity"
    if not antecedent.name.strip():
        return False, "the antecedent has no surface form (an anaphor needs a NAMED antecedent)"
    if not antecedent.claim_ids:
        return False, (
            "the antecedent is undeclared — no entity claim asserts it, so nothing states what the anaphor "
            "is being resolved TO"
        )
    if antecedent.etype == _UNKNOWN_ETYPE:
        return False, "the antecedent is not ontology-typed (an untyped antecedent cannot be type-unique)"
    docs = set(e.doc_ids)
    compatible = sorted(
        eid for eid, ent in graph.entities.items()
        if eid != anaphor.eid
        and (not ent.doc_ids or not docs or (ent.doc_ids & docs))
        and ent.etype in (antecedent.etype, _UNKNOWN_ETYPE)
    )
    if len(compatible) != _ONE_ANTECEDENT:
        return False, (
            f"the anaphor has {len(compatible)} type-compatible antecedents in scope, not exactly one — an "
            f"'unknown'-typed endpoint counts as compatible on purpose, because a second undeclared mention "
            f"is precisely what an extractor under-reach would hide"
        )
    if compatible[0] != antecedent.eid:
        return False, "the single type-compatible antecedent is not the one this link binds to"
    return True, (
        f"exactly one type-compatible antecedent ('{antecedent.etype}'), named and declared by its own claims"
    )


def _link_gate_verdict(
    e: Edge, evidence: str, graph: EntityGraph, cfg: ResolveConfig
) -> tuple[bool, str]:
    """Does this coreference link clear D-13.17's deterministic gate? — **recomputed here, not trusted.**

    The first cut of this stage read a verdict the producer had stamped on the claim. The independent suite
    killed that in one line: a holder of a config bundle and a claim log — a fixture, an operator, an auditor —
    **could not turn the policy on**, because the deciding input was an artifact only the producer knew how to
    write. And a gate whose verdict cannot be recomputed from the evidence is not a structural check; it is a
    second self-report one layer down, which is exactly what D-13.17 refuses.

    So the split is by *what is knowable here*:

    * ``EXPLICIT_EQUIVALENCE`` — **fully recomputed** from the licensing spans and the two surface forms, both
      of which ride the claim, against the configured marker vocabulary and the shipped mark-vs-word knob.
      Any reader can re-derive it. A stamped ``FAIL`` still loses: the producer saw the document and this side
      did not, so it may veto but never license.
    * ``UNAMBIGUOUS_ANAPHOR`` — the positive gate needs the document's whole mention inventory, which is not
      in the graph. So it is honoured **only** on a stamped pass, and an unstamped anaphor link falls back to
      raise-only. That is D-13.17's own conditional, not an improvisation: *"if the positive gate is not
      built, ``UNAMBIGUOUS_ANAPHOR`` reverts to raise-only."*
    * anything else, ``NAME_VARIANT`` included — never gated, therefore never bound.

    Per **M12** a failing conjunct **demotes to raise-only and never vetoes**, which is the whole reason a
    fallible structural test is admissible in this position: a false fire costs one analyst glance, with the
    licensing spans attached, rather than a lost merge.
    """
    stamped = (e.attributes or {}).get(COREF_GATE_ATTR)
    if stamped is not None and str(stamped) != COREF_GATE_PASS:
        return False, "the producer's own gate failed on evidence only it could see (the document text)"
    if evidence == coref_gate.EXPLICIT_EQUIVALENCE:
        anchor, member = _link_forms(e, graph)
        return coref_gate.explicit_equivalence(
            _licensing_spans(e), anchor, member,
            cfg.earned_identity.equivalence_markers, cfg.earned_identity.min_descriptor_len,
            documents=len(e.doc_ids) or 1,
        )
    if evidence == coref_gate.UNAMBIGUOUS_ANAPHOR:
        if coref_gate.differs_only_by_a_mark(
            *_link_forms(e, graph), cfg.earned_identity.min_descriptor_len
        ):
            return False, (
                "the two forms differ by a MARK, not a word — a mark distinguishes a variant rather than "
                "naming the same thing, so no anaphoric reading licenses the bind (M1)"
            )
        return _anaphor_gate_from_graph(e, graph)
    return False, (
        f"'{evidence}' has no deterministic gate and is raise-only by policy: an authoritative bind bypasses "
        f"banding, so authorising a bare name variant would rebuild the exact-name auto-merge lane on another "
        f"predicate, immune to the very cap that replaced it"
    )


def _coref_doc_scoped_eids(
    ref: str, doc_ids: set[str], graph: EntityGraph, cfg: ResolveConfig, alias_idx: AliasIndex
) -> list[str]:
    """``_matching_eids``, restricted to entities **attested in the contributing document** (C9).

    D-13.17 gates an authoritative bind on a *document-scoped* precondition — the extractor read *this one
    document's* discourse — but the bind then instantiates through ``_matching_eids``' **global** name/alias
    expansion, so the precondition did not bound the effect: a bind licensed by one document could fuse a
    same-named profile built entirely from other documents. Intersecting on :attr:`Entity.doc_ids` is what
    makes the effect as document-scoped as the licence.

    An entity with no ``doc_ids`` at all — a registry seed, a minted endpoint — is **not** excluded: it
    carries no document to contradict the scope, and excluding it would refuse the registry the very
    canonical-id adoption it exists for.
    """
    out = []
    for eid in _endpoint_eids(ref, graph, cfg, alias_idx):
        ent = graph.entities.get(eid)
        if ent is None:
            continue
        if not ent.doc_ids or (ent.doc_ids & doc_ids):
            out.append(eid)
    return out


def _referent_conflict(
    members: list[str], graph: EntityGraph, cfg: ResolveConfig, lane: EdgeLaneIndex,
    place_of: dict[str, places.PlaceMatch], alias_idx: AliasIndex,
) -> str | None:
    """D-13.18: does this referent grouping contain a conflicting critical discriminator? Names it, or ``None``.

    **The reversibility gap this closes, and it was disqualifying as the docs were written.** §4 promises a
    coref cluster stays "a challengeable proposal"; D-13.11 says atoms never split; and no document stated the
    mechanism by which a wrong grouping is undone. The resolution:

    > The referent atom is **evidence about a grouping, never the address** of the provisional instance.
    > Rebuild groups *claim* atoms; the referent is a strong grouping *signal* the grouping step consults. An
    > intra-referent critical-discriminator conflict makes the rebuild **DECLINE** the grouping — de-grouping
    > to claim-atom granularity and raising for an analyst. **No atom splits; the grouping declines.**

    Two kinds of conflict, per **C3**, because D-13.8 declares discriminators to be attributes *and*
    relationships and the decline mechanics as first written were attribute-only:

    * **attributes** — read the full member value set (``attr_history``), **never** the first-wins scalar.
      This is the part that is not obvious: ``Entity.attrs`` is first-claim-wins, so the losing value only
      ever reaches ``attr_history`` and an intra-referent conflict is otherwise **invisible**;
    * **relationships** — the *same* overlapping-time test G18 uses, under C1's site-class rule, so the
      decline and the cross-document wall share one predicate rather than drifting apart. A coref cluster
      that binds two mentions the relationships say are different things must decline, for the same reason
      and by the same test.
    """
    for a, b in unordered_pairs(sorted(set(members))):
        ea, eb = graph.entities.get(a), graph.entities.get(b)
        if ea is None or eb is None:
            continue
        disposition, attrs = critical_conflict_disposition(ea, eb, cfg)
        if disposition in ("wall", "raise") and attrs:
            return f"a conflicting critical attribute ({', '.join(attrs)})"
        # ``critical_conflict_disposition`` compares the first-wins scalar, so it cannot see a value that
        # only ever reached history. Read the retained series directly — this is the check D-13.18 names.
        hist = _history_conflict(ea, eb, cfg)
        if hist:
            return f"conflicting retained values of {hist} across the grouped mentions"
        unreadable = scoring.unnormalizable_critical_values(ea, eb, cfg)
        if unreadable:
            return f"an unreadable critical value ({', '.join(unreadable)})"
        differing = scoring.constitutive_difference(ea, eb, cfg)
        if differing:
            return f"a constitutive difference ({', '.join(differing)})"
    # C3: "the check is **the same overlapping-time conflict test G18 uses**, under C1's site_type rule" — so
    # the WALLS only. G18's third state (an unreadable site class, an undated statement) is explicitly *not* a
    # conflict: it is "we cannot read this". Declining a grouping on it would turn every undated basing into a
    # refusal to group, which is over-raising — the operational face of the thing the non-negotiable forbids —
    # and it would eat the legitimate cases the same ruling protects (non-overlapping times are a relocation,
    # and a differing site class is two valid basings). The third state already blocks fusion on its own rail.
    walls, _reasons, _raises = _relationship_walls(graph, cfg, lane, alias_idx, place_of)
    for a, b in unordered_pairs(sorted(set(members))):
        if frozenset((a, b)) in walls:
            return "a stated relationship conflict at overlapping times (the same test G18 walls on)"
    return None


def _history_conflict(a: Entity, b: Entity, cfg: ResolveConfig) -> str | None:
    """A critical attribute on which the two RETAINED value series disagree — the check ``attrs`` hides.

    ``Entity.attrs`` is first-claim-wins (``setdefault``), so where one mention asserted two values only the
    first survives into the scalar and every conflict detector that reads it is blind to the second. The
    decline must read **history**: it is comparing what a *grouping* of claim atoms collectively asserts, and
    that is exactly the set the scalar throws away. Values compared through the C7 normaliser, so a spelling
    is never a conflict.
    """
    if a.etype != b.etype:
        return None
    earned = cfg.earned_identity
    # The identity-BEARING slots, which is more than the ``critical`` ones: a component of a declared
    # composite unique key is identifying **by that declaration** — ``(service_branch, designator)`` says a
    # designation individuates a formation within its service, so one member asserting two different
    # designations cannot be one referent, whatever role the attribute carries for scoring.
    key_components = sorted({attr for key in cfg.unique_id_keys(a.etype) for attr in key})
    checked = cfg.critical_role_attrs(a.etype) + cfg.constitutive_attrs(a.etype) + key_components
    seen: set[str] = set()
    ordered: list[str] = []
    for attr in checked:  # de-duplicated, declaration order preserved (deterministic — gate G2)
        if attr not in seen:
            seen.add(attr)
            ordered.append(attr)
    for attr in ordered:
        values: set[str] = set()
        unreadable = False
        for ac in a.attr_history.get(attr, []) + b.attr_history.get(attr, []):
            canonical, mapped = earned.normalise_value(attr, ac.value)
            values.add(canonical)
            unreadable = unreadable or not mapped
        if len(values) > 1 and not unreadable:
            return attr
    return None


def _coref_pairs(
    graph: EntityGraph, cfg: ResolveConfig, alias_idx: AliasIndex, veto: set[Pair],
    lane: EdgeLaneIndex | None = None,
    place_of: dict[str, places.PlaceMatch] | None = None,
) -> tuple[set[Pair], set[Pair], dict[Pair, str], dict[Pair, str]]:
    """Split ``coref-same-as`` claims into ``(authoritative, raise_only, declined, walled)`` entity-id pairs.

    A coreference claim carries something no other identity signal does: the extractor read **this one
    document's discourse** and reported which mentions it treats as one entity, with a verbatim span that
    licenses the grouping. Re-deriving that from surface strings is exactly the information loss the
    design forbids — so a category the operator has opted into
    (:attr:`ResolveConfig.coref_authoritative_evidence`, empty by default) *bootstraps* rather than
    merely raising, and every other category joins the ordinary raise-only queue.

    "Authoritative" is never "unconditional". A pair is demoted to raise-only — an analyst decision, with
    the licensing quote attached — whenever the two ends disagree in a way the document's local reading
    cannot settle: a different entity **type**, an incompatible **namespace** (a China/Pakistan split), or
    a stated **hard-attribute contradiction** (:func:`scoring.has_hard_conflict`). A vetoed pair does not
    bind and does not merge — a stated do-not-merge outranks any reading of the prose — but it is **named**,
    in ``walled``: demotion, not silent deletion, is the point, and the wall case was the one place the
    sentence "the evidence still reaches a human" was not true. See the ``pair in veto`` branch.
    """
    authoritative: set[Pair] = set()
    raise_only: set[Pair] = set()
    #: Pairs a source ASSERTED are one entity and a hard wall holds apart — the escalate half of that
    #: collision. Routed to ``Partition.identity_refusals``, which ``rebuild()`` renders as one Known Gap per
    #: endpoint, so each mention states in its own drawer what could not be decided about it.
    walled_pairs: dict[Pair, str] = {}
    #: Pairs whose GROUPING the rebuild declined (D-13.18). Returned separately because a decline has to
    #: **bind the fusion path**, not merely withhold the coreference bind: if the pair can still fuse on the
    #: name/containment path beside it, the decline is decoration — the same lesson C7 states for a gap.
    declined_pairs: dict[Pair, str] = {}
    allowed = cfg.coref_authoritative_evidence
    nsn = cfg.namespace_normaliser
    grade_floor = cfg.earned_identity.bind_min_grade

    # Group the links by their REFERENT so the grouping — not merely the pair — can be adjudicated (A1).
    by_referent: dict[str, list[Edge]] = {}
    for e in graph.edges:
        if e.predicate != COREF_PREDICATE:
            continue
        # The GRAIN is the document-local coreference cluster; the referent atom is that grain's *name*. So
        # group on the referent where the producer minted one and on ``(document, cluster id)`` where it did
        # not — a hand-built claim, a fixture, a bundle recorded before the mint existed. Keying only on the
        # referent made the decline unreachable for every one of those, i.e. D-13.18 was inert wherever the
        # grouping was expressed the older way.
        attrs = e.attributes or {}
        referent = str(attrs.get(COREF_REFERENT_ATTR) or "")
        cluster = str(attrs.get(COREF_CLUSTER_ATTR) or "")
        doc_key = "|".join(sorted(e.doc_ids))
        grain = referent or (f"cluster:{doc_key}:{cluster}" if cluster else f"link:{id(e)}")
        by_referent.setdefault(grain, []).append(e)

    for referent, links in sorted(by_referent.items(), key=lambda kv: kv[0]):
        pairs_of: list[tuple[Edge, list[Pair]]] = []  # Edge is a mutable dataclass ⇒ unhashable; keep a list
        members: list[str] = []
        for e in links:
            docs = set(e.doc_ids)
            # C9: an authoritative bind may instantiate ONLY over entity ids attested in the contributing
            # document. Without this the document-scoped LICENCE does not bound the global EFFECT. A link
            # carrying no document at all cannot be doc-scoped, so it falls back to the endpoint expansion.
            if docs:
                left = _coref_doc_scoped_eids(e.subject, docs, graph, cfg, alias_idx)
                right = _coref_doc_scoped_eids(e.object, docs, graph, cfg, alias_idx)
            else:
                left = _endpoint_eids(e.subject, graph, cfg, alias_idx)
                right = _endpoint_eids(e.object, graph, cfg, alias_idx)
            found = [
                frozenset((a, b))
                for a, b in product(left, right)
                if a != b and a in graph.entities and b in graph.entities
            ]
            pairs_of.append((e, found))
            for pair in found:
                members.extend(sorted(pair))

        # D-13.18: the rebuild may DECLINE the whole grouping. Checked once per referent, before any link is
        # promoted, because the question is about the grouping rather than about a pair.
        declined = (
            _referent_conflict(members, graph, cfg, lane, place_of or {}, alias_idx)
            if not referent.startswith("link:") and lane is not None
            else None
        )

        for e, found in pairs_of:
            attrs = e.attributes or {}
            evidence = str(attrs.get(COREF_EVIDENCE_ATTR) or "")
            # Unconditional, both of them. A bind fuses at 1.0 past every band, so "is this licensed?" can
            # never depend on which stage is switched on — only on the evidence the pair carries.
            gate_ok, _why = _link_gate_verdict(e, evidence, graph, cfg)
            grade_ok = grade_floor is None or grade_meets_floor(cfg.source_grade(e.source_id), grade_floor)
            for pair in found:
                if pair in veto:
                    # A stated do-not-merge outranks the extractor's reading of the prose — the VERDICT is
                    # right and unchanged. What was wrong was that the assertion then vanished. A document
                    # said "these two are the same thing", a wall said they are not, and the collision of
                    # those two statements is a finding in its own right: either the extraction is wrong, or
                    # one of the walling values is wrong, or a source is deliberately conflating two
                    # organisations — and every one of those is the analyst's call, not the resolver's.
                    #
                    # Dropped outright, the pair became indistinguishable from two mentions that never
                    # resembled each other: no bind, no queue item, no gap, both halves orphaned. That is the
                    # non-negotiable's escalate half missing on the sharpest pair in the system — a
                    # same-named look-alike straddling two operators, coref-linked, which is the costliest
                    # over-merge in an operator-scoped ORBAT and the single most useful thing to hand a human.
                    # Refusing to assert was never the hard part; being told is.
                    walled_pairs[pair] = _walled_assertion_gap(
                        graph.entities[sorted(pair)[0]], graph.entities[sorted(pair)[1]],
                        evidence, attrs.get(COREF_QUOTE_ATTR),
                    )
                    continue
                a, b = sorted(pair)
                ea, eb = graph.entities[a], graph.entities[b]
                contradicted = (
                    ea.etype != eb.etype
                    or not namespace_compatible(ea, eb, nsn)
                    or has_hard_conflict(ea, eb, cfg)
                )
                may_bind = (
                    evidence in allowed
                    and not contradicted
                    and gate_ok
                    and grade_ok
                    and declined is None
                )
                if may_bind:
                    authoritative.add(pair)
                elif declined is not None:
                    # A DECLINED grouping is not merely un-bound: the conflict that declined it is anti-identity
                    # evidence about the pair itself, so the pair may not fuse by any other route either. It
                    # joins the block-merge-and-review channel with the reason — de-grouped to claim-atom
                    # granularity and raised, which is exactly what D-13.18 specifies. No atom splits.
                    declined_pairs[pair] = _decline_reason(declined)
                else:
                    # C5's partial bind: a failing link is not discarded, it becomes an injected Tier-1
                    # candidate pair — so a cluster binds over the links that pass and each link that does
                    # not still reaches the analyst, with its licensing evidence attached.
                    raise_only.add(pair)
    return authoritative, raise_only, declined_pairs, walled_pairs


def _walled_assertion_gap(a: Entity, b: Entity, evidence: str, quote: Any) -> str:
    """What is missing when a source ASSERTS an identity a hard wall refuses — the analyst's open question.

    Written as a ``what_missing`` (``Partition.identity_refusals`` ⇒ one Known Gap per endpoint) rather than a
    candidate reason, deliberately: a candidate invites "accept this merge", and this pair must never be
    offered that button — the wall is a credible stated contradiction, not a low score. What the analyst is
    owed is the *open question on each mention*: whose profile is this, given that one document says it is the
    same as another and the attributes say it cannot be.

    **Carries the document's own words where it supplied them.** The licensing quote is the only thing that
    lets the proposal be adjudicated in one read, and an audit already found that justification fictional once
    — the quote was stamped on the claim and read nowhere. A gap that says "a source disagreed" without the
    sentence is an unfalsifiable assertion that two mentions might be one thing.
    """
    cited = f' The document\'s own words: "{quote}".' if isinstance(quote, str) and quote.strip() else ""
    how = f" ({evidence})" if evidence else ""
    # Names BOTH mentions rather than "the same as <the other one>": ``rebuild()`` renders one gap per
    # ENDPOINT from this one pair-keyed string, so a text that points at a specific side reads correctly on one
    # endpoint's drawer and wrongly on the other's.
    pair = " and ".join(sorted((a.eid, b.eid)))
    return (
        f"the IDENTITY of this mention is contested and unresolved: a source read this document as stating "
        f"that {pair} are one entity{how}, while a hard do-not-merge holds "
        f"the two apart on stated, credibly-attested grounds — so the system asserts NEITHER the merge nor "
        f"that the mentions are unrelated.{cited} Both readings cannot be right, and which one is wrong is "
        f"not something the resolver can settle: it is an extraction error, a wrong attribute value, or a "
        f"source conflating two organisations. Needed: an analyst adjudication of the do-not-merge, or a "
        f"source that settles the conflicting attribute. Until then this mention's identity is an open "
        f"question and nothing downstream may treat it as closed."
    )


def _decline_reason(what: str) -> str:
    """Analyst-facing reason a referent GROUPING was declined (D-13.18). Prose only (gate G6)."""
    return (
        f"the coreference grouping was DECLINED — the extractor read this document as treating these mentions "
        f"as one entity, but the grouped mentions carry {what}. The referent atom is evidence ABOUT a grouping, "
        f"never an address, so the rebuild is free to refuse it: the grouping de-groups to per-mention "
        f"granularity and the pair is raised rather than fused. No claim atom was split — nothing was "
        f"rewritten, and re-running the rebuild after the conflict is resolved will re-form the grouping. If "
        f"these really are one entity then one of the conflicting values is wrong, and that is the question "
        f"to adjudicate (D-13.18)."
    )


def _contrast_ceilings(
    graph: EntityGraph, cfg: ResolveConfig, alias_idx: AliasIndex
) -> dict[Pair, str]:
    """A same-document **stated contrast** caps the pair at its declared band — D-13.19 decision (b).

    **Why a band ceiling and not a score penalty.** With ``auto_merge: 0.85`` / ``hitl_low: 0.45``, a ×0.5
    penalty moves a 0.85 pair to 0.425 — *below* ``hitl_low``, i.e. **two** bands, silently dropping the pair
    out of the analyst's queue entirely. Any coefficient carries that hazard and its safe value depends on
    thresholds that will move. A band name is threshold-independent and states the intent directly: contrast
    means "not automatically", never "not at all".

    **Why ungraded.** A grade gate would defend against a planted document — *"the 8th AD Bn and the separate
    12th AD Bn"* — shattering a well-corroborated cluster. That risk is specific to a **veto**, and it is why
    this is not one: a ceiling withholds one *new* fusion, cannot retract an existing merge, and a cluster can
    still form transitively through its other pairs. Choosing the non-shattering mechanism removes the harm
    the gate was defending against, so the gate would be a knob buying no risk reduction.

    **Doc-scoped in effect, not just in licence** (the same reasoning as C9): the contrast is a fact about one
    document's syntax, so it may not leak onto a cross-document pair through the global name expansion.
    """
    out: dict[Pair, str] = {}
    if not ceiling_withholds(cfg.earned_identity.contrast_ceiling):
        return out  # `confirmed` (or undeclared) ⇒ a stated contrast withholds nothing
    for e in graph.edges:
        if e.predicate != COREF_CONTRAST_PREDICATE:
            continue
        docs = set(e.doc_ids)
        spans = [str(q) for q in ((e.attributes or {}).get(COREF_QUOTES_ATTR) or []) if q]
        quote = (e.attributes or {}).get(COREF_QUOTE_ATTR)
        cited = "; ".join(f'"{s}"' for s in spans) or (f'"{quote}"' if quote else "its own wording")
        left = _coref_doc_scoped_eids(e.subject, docs, graph, cfg, alias_idx) if docs else []
        right = _coref_doc_scoped_eids(e.object, docs, graph, cfg, alias_idx) if docs else []
        for a, b in product(left, right):
            if a == b or a not in graph.entities or b not in graph.entities:
                continue
            out[frozenset((a, b))] = (
                f"the source document DISTINGUISHES these two mentions in its own words — {cited}. Capped at "
                f"'{cfg.earned_identity.contrast_ceiling}': the pair may never auto-merge, and it reaches you "
                f"with the quote so you can judge whether the document is separating two things or merely "
                f"listing one thing twice. Deliberately a ceiling rather than a do-not-merge: EVERY order of "
                f"battle contains an enumeration, so treating an enumeration as a hard, transitive veto would "
                f"let one planted list shatter a well-corroborated cluster. A ceiling withholds a new fusion "
                f"and can retract nothing (D-13.19)."
            )
    return out


def coref_raise_reasons(
    graph: EntityGraph, cfg: ResolveConfig, authoritative: set[Pair], raise_only: set[Pair],
    alias_idx: AliasIndex,
) -> dict[Pair, str]:
    """Analyst-facing reasons for every coreference link that did **not** bind — **with its licensing spans**.

    This is the mitigation that makes raise-only acceptable at all, and an audit found it fictional: the
    licensing quote is stamped on the claim and **read nowhere**, so every justification of raise-only
    ("the analyst is handed the exact sentence") was describing a screen nobody could see. Both decision (a)
    and decision (b) lean on it, and D-13.17 makes it load-bearing.

    So the reason names three things the analyst actually needs: *what the document said* (the verbatim
    spans), *what kind of reading it was* (the category), and *why the system would not act on it alone*.

    **That third thing is the COMPUTED ground, per pair, not a fixed sentence.** It used to fall back to
    "the category is raise-only by policy" whenever the producer had stamped no detail — asserting a reason
    the code had not used, while :func:`_coref_pairs` had just computed the real one (a missing equivalence
    marker, a cross-type impossibility, a source-grade floor) and thrown it away. The reason then invited the
    analyst to "accept the merge if you read it the same way" on a ground that was not the actual one, which
    is a provenance over-claim about the system's own decision. :func:`_raise_ground` recomputes the same
    tests in the same order ``may_bind`` evaluates them, so what the analyst reads is why the merge was
    actually withheld.
    """
    out: dict[Pair, str] = {}
    allowed = cfg.coref_authoritative_evidence
    grade_floor = cfg.earned_identity.bind_min_grade
    nsn = cfg.namespace_normaliser
    for e in graph.edges:
        if e.predicate != COREF_PREDICATE:
            continue
        attrs = e.attributes or {}
        evidence = str(attrs.get(COREF_EVIDENCE_ATTR) or "unstated category")
        spans = [str(q) for q in (attrs.get(COREF_QUOTES_ATTR) or []) if q]
        if not spans:
            quote = attrs.get(COREF_QUOTE_ATTR)
            spans = [str(quote)] if quote else []
        grade = cfg.source_grade(e.source_id)
        cited = "; ".join(f'"{s}"' for s in spans) if spans else "no licensing span survived validation"
        for a in _endpoint_eids(e.subject, graph, cfg, alias_idx):
            for b in _endpoint_eids(e.object, graph, cfg, alias_idx):
                pair = frozenset((a, b))
                if a == b or pair in authoritative or pair not in raise_only or pair in out:
                    continue
                out[pair] = (
                    f"in-document coreference, raised not bound — the extractor read this document's own "
                    f"discourse as treating these two mentions as one entity, category '{evidence}', "
                    f"licensed by {cited} (source grade {grade or 'unknown'}). It is not acted on "
                    f"automatically because: "
                    f"{_raise_ground(e, evidence, a, b, graph, cfg, allowed, grade_floor, nsn)}. An "
                    f"authoritative bind fuses at full confidence and bypasses every band and cap, so it "
                    f"must clear a deterministic structural gate AND a source-grade floor; this link did "
                    f"not. The evidence above is the whole of what the document says — judge it against the "
                    f"ground stated here (D-13.17)."
                )
    return out


def _raise_ground(
    e: Edge, evidence: str, a: str, b: str, graph: EntityGraph, cfg: ResolveConfig,
    allowed: set[str], grade_floor: str | None, nsn: Any,
) -> str:
    """WHY this coreference link did not bind — the ground the resolver actually used, in its own words.

    The same four tests :func:`_coref_pairs` conjoins in ``may_bind``, in that order, so the first one that
    fails is the one reported. A stamped ``gate_detail`` is used only to *extend* the recomputed gate reason,
    never to replace it: the stamp is the producer's self-report and the recomputation is the check.
    """
    if evidence not in allowed:
        return (
            f"the category '{evidence}' is not authorised to bootstrap on this deployment "
            f"(resolution.yaml earned_identity.authoritative_categories), so a link of this kind is "
            f"raise-only however well it reads"
        )
    ea, eb = graph.entities[a], graph.entities[b]
    if ea.etype != eb.etype:
        return (
            f"the two mentions are typed '{ea.etype}' and '{eb.etype}' — one document's reading of its own "
            f"discourse cannot settle a disagreement about what kind of thing this is"
        )
    if not namespace_compatible(ea, eb, nsn):
        return (
            f"the two mentions are scoped to different operators ('{ea.namespace(nsn)}' vs "
            f"'{eb.namespace(nsn)}'), and a cross-operator fusion is the costliest over-merge there is"
        )
    if has_hard_conflict(ea, eb, cfg):
        return "the two mentions STATE contradictory hard attributes, which no reading of the prose overrides"
    gate_ok, why = _link_gate_verdict(e, evidence, graph, cfg)
    if not gate_ok:
        detail = str((e.attributes or {}).get(COREF_GATE_DETAIL_ATTR) or "")
        return f"{why}{f' (producer detail: {detail})' if detail else ''}"
    if grade_floor is not None and not grade_meets_floor(cfg.source_grade(e.source_id), grade_floor):
        return (
            f"the asserting document's source is graded '{cfg.source_grade(e.source_id) or 'unknown'}', "
            f"below the '{grade_floor}' floor an identity-moving assertion has to clear"
        )
    return (
        "the coreference grouping it belongs to was declined, or the pair is held apart by a rail recorded "
        "elsewhere on this queue item — see the other reason on this pair"
    )


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
        candidate_reasons=result.candidate_reasons,
        identity_refusals=result.identity_refusals,
        possible=result.possible,
        distinct_from=result.distinct_from,
        wall_reasons={k: v for k, v in result.wall_reasons.items()},
        merge_confidence=result.merge_confidence,
        merge_breakdown=result.merge_breakdown,
        identity_claims=identity_claims,
        entity_canonical=entity_canonical,
        endpoint_node_types=endpoint_node_types,
        place_refs=place_refs,
    )
