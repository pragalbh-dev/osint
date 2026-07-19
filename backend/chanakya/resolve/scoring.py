"""``merge_score`` — the four signals, weighted, with a stored breakdown (spine/03, spine/08 §3.9).

``merge_score = w_a·attribute + w_r·relational + w_t·temporal_consistency + w_s·source_asserted``.
The weights are config (gate G6). Each signal is a pure function of the entity graph + the *current*
partition (relational is collective — it reads resolved neighbours), so it is recomputed as clusters grow.

The **relocation exclusion** is load-bearing: two entities that are co-endpoints of one edge-instance
(a unit relocated between two sites — the same supersede instance F0 detects) are *anti-identity*
evidence, so that shared neighbour is dropped from the relational term and temporal consistency is 0.
This is what keeps a relocation from masquerading as a shared-neighbourhood merge.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from .aliases import AliasIndex
from .entities import Entity, EntityGraph
from .normalize import name_similarity, normalize
from .rconfig import ATTRIBUTE, RELATIONAL, SOURCE_ASSERTED, TEMPORAL, ResolveConfig

# predicates by which a *source* directly asserts an identity (feeds source_asserted — an identity
# signal, never claim credibility, gate G5). Strings, not numbers — G6 bans only numeric literals.
_IDENTITY_PREDICATES = {"same-as", "same_as", "aka", "also-known-as", "marketed-as", "is"}

Canonical = Callable[[str], str]


def co_instances(graph: EntityGraph, a: str, b: str) -> set[str]:
    """Edge-instances where a and b are co-objects or co-subjects — i.e. a relocation/contradiction pair."""
    subj: dict[str, set[str]] = defaultdict(set)
    obj: dict[str, set[str]] = defaultdict(set)
    for e in graph.edges:
        if e.edge_instance is None:
            continue
        subj[e.edge_instance].add(e.subject)
        obj[e.edge_instance].add(e.object)
    out: set[str] = set()
    for inst in set(subj) | set(obj):
        if {a, b} <= obj[inst] or {a, b} <= subj[inst]:
            out.add(inst)
    return out


def _neighbours(graph: EntityGraph, eid: str, canonical: Canonical, exclude: set[str]) -> set[tuple[str, str, str]]:
    """Resolved neighbourhood: {(predicate, direction, canonical(other))}, minus excluded instances."""
    nbrs: set[tuple[str, str, str]] = set()
    for e in graph.incident(eid):
        if e.edge_instance in exclude:
            continue
        if e.subject == eid:
            nbrs.add((e.predicate, "out", canonical(e.object)))
        if e.object == eid:
            nbrs.add((e.predicate, "in", canonical(e.subject)))
    return nbrs


def attribute_score(a: Entity, b: Entity, cfg: ResolveConfig, alias_idx: AliasIndex | None = None) -> float:
    """Name similarity (or identity-attr agreement), knocked down by hard-conflict attributes.

    Alias-equivalent names (seed or learned) score a full 1.0 — FD-2000 ≡ HQ-9/P by the alias table,
    even though the surface strings barely resemble each other.
    """
    if alias_idx is not None and alias_idx.equivalent(
        normalize(a.name, cfg.transliteration), normalize(b.name, cfg.transliteration)
    ):
        return 1.0
    sim = name_similarity(a.name, b.name, cfg.transliteration)
    rules = cfg.attribute_rules(a.etype) if a.etype == b.etype else {}

    # Identity attrs agreeing can carry the pair even when the surface name drifts.
    id_attrs = rules.get("identity", [])
    present = [k for k in id_attrs if a.attrs.get(k) is not None and b.attrs.get(k) is not None]
    if present:
        equal = sum(1 for k in present if a.attrs[k] == b.attrs[k])
        sim = max(sim, equal / len(present))

    # Hard-conflict attrs pull the score down (the false-merge guard).
    penalty = 1.0
    cpen = cfg.attribute_scoring("conflict_penalty")
    if cpen is not None:
        for k in rules.get("conflict", []):
            va, vb = a.attrs.get(k), b.attrs.get(k)
            if va is not None and vb is not None and va != vb:
                penalty *= cpen
    npen = cfg.attribute_scoring("numeric_conflict_penalty")
    if npen is not None:
        for field_name, spec in rules.get("numeric_conflict", {}).items():
            if _numeric_conflict(a.attrs.get(field_name), b.attrs.get(field_name), spec.get("rel_tol")):
                penalty *= npen

    return _clamp(sim * penalty)


def _numeric_conflict(va: object, vb: object, rel_tol: object) -> bool:
    """True if two numeric attrs differ by more than the configured relative tolerance."""
    if rel_tol is None:
        return False
    try:
        fa, fb, tol = float(va), float(vb), float(rel_tol)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return False
    scale = max(abs(fa), abs(fb))
    if scale == 0.0:
        return False
    return abs(fa - fb) / scale > tol


def relational_score(graph: EntityGraph, a: str, b: str, canonical: Canonical, exclude: set[str]) -> float:
    """Jaccard overlap of the two resolved neighbourhoods (excluding relocation instances)."""
    na = _neighbours(graph, a, canonical, exclude)
    nb = _neighbours(graph, b, canonical, exclude)
    union = na | nb
    if not union:
        return 0.0
    return len(na & nb) / len(union)


def temporal_score(reloc: bool) -> float:
    """Coherent unless we detect a conflict: a relocation/contradiction pair scores 0 (anti-identity)."""
    return 0.0 if reloc else 1.0


def source_asserted_score(graph: EntityGraph, a: str, b: str) -> float:
    """1.0 iff a source directly asserts the identity a≡b (an identity signal, never truth — G5)."""
    for e in graph.edges:
        if e.predicate in _IDENTITY_PREDICATES and {e.subject, e.object} == {a, b}:
            return 1.0
    return 0.0


def merge_score(
    a: Entity,
    b: Entity,
    graph: EntityGraph,
    canonical: Canonical,
    cfg: ResolveConfig,
    alias_idx: AliasIndex | None = None,
) -> dict[str, float]:
    """Full weighted merge_score + the stored per-signal breakdown (explainability)."""
    exclude = co_instances(graph, a.eid, b.eid)
    reloc = bool(exclude)
    parts = {
        ATTRIBUTE: attribute_score(a, b, cfg, alias_idx),
        RELATIONAL: relational_score(graph, a.eid, b.eid, canonical, exclude),
        TEMPORAL: temporal_score(reloc),
        SOURCE_ASSERTED: source_asserted_score(graph, a.eid, b.eid),
    }
    total = sum(cfg.weight(sig) * parts[sig] for sig in parts)
    return {**parts, "total": _clamp(total)}


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))
