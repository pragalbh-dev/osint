"""RESOLVE stage — iterative relational entity resolution (owned by session RESOLVE, spine/03).

C's marquee graded feature: confidently fuse "FD-2000" = "HQ-9/P" across transliterations + shell
aliases, *while keeping the traps apart* (FD-2000 ≠ FT-2000, HQ-9/P ≠ HQ-9BE, Karachi-Port ≠ Port-Qasim).

The whole stage is a **pure, deterministic** function of (claims, config, prev_view, decision log) —
no LLM / network / clock / RNG on this path (gate G1). The LLM is a *proposer* whose output is already
frozen in the decision log (``merge_proposal`` records) and consumed here as a **raise-only** signal;
the deterministic terms (``merge_score`` + bands + the fixpoint) always dispose. Merges are **reversible**
overlays (``same_as`` + ``entity_canonical``), never destructive node-collapse; a claim's own
``resolved_ref`` stays its per-claim identity so a no-merge run is byte-identical to F0's stub (gate G2).

Signature: ``resolve(claims, config, prev_view=None, decisions=None) -> Partition``.
"""

from __future__ import annotations

from itertools import product

from chanakya.schemas import ClaimRecord, ConfigBundle, DecisionRecord, GraphView, Partition

from . import aliases, entities, places
from .aliases import AliasIndex
from .cluster import Pair, ResolveResult, finalise, resolve_entities
from .entities import EntityGraph, base_ref
from .normalize import normalize
from .propose import propose_candidates
from .rconfig import ResolveConfig

__all__ = ["resolve", "propose_candidates"]


def resolve(
    claims: list[ClaimRecord],
    config: ConfigBundle,
    prev_view: GraphView | None = None,
    decisions: list[DecisionRecord] | None = None,
) -> Partition:
    """Resolve claims into entities/edges: candidate-gen → bootstrap → relational fixpoint → places."""
    cfg = ResolveConfig.from_bundle(config)
    graph = entities.build(claims)

    # Effective alias table = seeded config ∪ replayed merge_adjudication(accept)s (spine/03/06).
    alias_idx = aliases.build(cfg.alias_table, cfg.transliteration, decisions)

    # veto = configured distinct-from (by name) ∪ gazetteer-distinct place pairs (Karachi-Port ≠ Port-Qasim,
    # computed up front so it hard-vetoes an entity-level merge too, not just surfaces as an edge).
    veto = _veto_pairs(graph, cfg, alias_idx) | places.place_distinct_pairs(graph, cfg)
    llm = _llm_pairs(graph, cfg, alias_idx, decisions)

    result = resolve_entities(graph, cfg, alias_idx, veto, llm)
    places.augment(result, graph, cfg, alias_idx, veto)  # location resolution reuses the same bands + veto
    finalise(result, graph, cfg, veto, alias_idx)  # reconcile all merges into one flat, veto-guarded map

    return _to_partition(claims, result)


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

def _to_partition(claims: list[ClaimRecord], result: ResolveResult) -> Partition:
    """Per-claim identity resolved_ref (matches the stub) + the merge overlay from the resolver."""
    resolved_ref = {c.claim_id: base_ref(c) for c in claims}
    return Partition(
        resolved_ref=resolved_ref,
        same_as=result.same_as,
        candidates=result.candidates,
        distinct_from=result.distinct_from,
        merge_confidence=result.merge_confidence,
        merge_breakdown=result.merge_breakdown,
        entity_canonical=result.canonical,
    )
