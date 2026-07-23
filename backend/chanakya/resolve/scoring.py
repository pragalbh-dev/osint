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
from collections.abc import Callable, Mapping

from .aliases import AliasIndex
from .entities import Entity, EntityGraph
from .geo import separation_km
from .normalize import name_similarity, normalize
from .rconfig import ATTRIBUTE, RELATIONAL, SIGNALS, SOURCE_ASSERTED, TEMPORAL, ResolveConfig

# Predicates by which a *source* directly asserts an identity (feeds source_asserted — an identity
# signal, never claim credibility, gate G5). Strings, not numbers — G6 bans only numeric literals.
# These claims are CONSUMED as merge signals rather than drawn as relationships (D-2.5): the view
# suppresses them (``view/pipeline._assemble``) because a "same-as" is a statement *about identity*,
# which the knowledge layer expresses by merging, not by an edge.
IDENTITY_PREDICATES = {"same-as", "same_as", "aka", "also-known-as", "marketed-as", "is"}
# …and the negative form. Unlike the positive, a distinct-from is a **hard veto AND stays drawn**: the
# trap has to remain visible to the analyst (an invisible veto is indistinguishable from a missing edge).
DISTINCT_PREDICATES = {"distinct-from", "distinct_from", "not-same-as"}

# ── in-document coreference (produced by INGEST extraction pass 2, ``ingest/coref.py``) ─────────
# The strings are duplicated rather than imported: ``rebuild()`` imports this package, and ``ingest``
# reaches the LLM client, so resolve must never import it (the same reason IDENTITY_PREDICATES are
# strings). A coreference claim is NOT an ordinary identity assertion — it is the extractor reporting
# what THIS document's own discourse treats as one entity, with a verbatim span that licenses it. That
# is strictly more information than a bare ``same-as``, which is why one category of it may bootstrap
# (see ``ResolveConfig.coref_authoritative_evidence``) instead of merely raising.
COREF_PREDICATE = "coref-same-as"
#: Tier-3 keys the producer stamps on each coreference claim.
COREF_EVIDENCE_ATTR = "_coref_evidence"
COREF_QUOTE_ATTR = "source_quote"


def geo_conflict_km(a: Entity, b: Entity, cfg: ResolveConfig) -> float | None:
    """How far apart two entities state they are, **when that is too far to be one entity** — else ``None``.

    The missing rail behind the "Karachi drawn in Gujranwala" class of bug. Every other guard in this
    module compares *names, attributes and neighbourhoods*; none of them knows that Karachi and Sargodha
    are 1,100 km apart. So a pair could be scored into the merge queue (or, at a high enough score,
    merged outright) on name/neighbourhood alone, and the surviving node then keeps whichever of the two
    coordinates its first claim happened to carry — i.e. one of the two places is silently redrawn at the
    other. A map that lies about *where* something is is worse than a map that omits it.

    So: an entity is in ONE place. If both sides carry their own frozen WGS84 coordinate and the geodesic
    separation exceeds the configured per-type tolerance, they are not the same entity — no matter what
    the score says. Deliberately narrow, because a wrong veto costs recall:

    * only **stated** coordinates count. A side with no coordinate is *unknown*, never "somewhere else"
      — absence is not disagreement, the same rule :func:`has_hard_conflict` follows;
    * no gazetteer lookup, no geocoding, no inference from a toponym — that is the place layer's job
      (``resolve.places``) and its own gates;
    * the tolerance is config (``entity_geo_conflict_max_km``), per type, and **unset ⇒ off**.

    Returns the separation in km when it is a conflict (so the caller can log/explain it), else ``None``.
    """
    tolerances = [cfg.geo_conflict_max_km(a.etype), cfg.geo_conflict_max_km(b.etype)]
    stated = [t for t in tolerances if t is not None]
    if not stated:
        return None  # gate not configured for either type ⇒ off
    km = separation_km(a, b)
    if km is None:
        return None  # at least one side states no coordinate ⇒ unknown, not incompatible
    return km if km > min(stated) else None  # the stricter of the two types governs


def _stated_values_conflict(a: Entity, b: Entity, attrs: list[str]) -> bool:
    """True if some attr in ``attrs`` is **stated on both sides and different** (absence ≠ conflict).

    The one shared detection ``has_hard_conflict``, ``critical_attribute_conflict`` and the scorer's soft
    penalty all read, so "what counts as a stated attribute disagreement" has exactly one definition. A
    side that simply doesn't state the attribute is *unknown*, never *different* — the geo veto's rule too.
    """
    for k in attrs:
        va, vb = a.attrs.get(k), b.attrs.get(k)
        if va is not None and vb is not None and va != vb:
            return True
    return False


def critical_attribute_conflict(a: Entity, b: Entity, cfg: ResolveConfig) -> bool:
    """A STATED disagreement on a declared-**critical** attribute (D5/D6) — the attribute wall only.

    The detection the critical→veto contributor (``resolve._critical_attribute_veto``) rides: a stated,
    different value on an attribute the config declares ``critical`` for this type is a cannot-link no
    similarity score may cross. Same-type only (a cross-type pair is handled by its own type gate, not by
    THIS attribute rail), and absence is never disagreement. Type/geo walls stay separate rails — see
    :func:`has_hard_conflict`, which composes this with them.
    """
    if a.etype != b.etype:
        return False
    return _stated_values_conflict(a, b, cfg.critical_role_attrs(a.etype))


def has_hard_conflict(a: Entity, b: Entity, cfg: ResolveConfig) -> bool:
    """True if a configured hard-conflict attribute is **stated on both sides and different**.

    The over-merge rail for an *authoritative* coreference merge (proposal §4): a cluster that looks
    coreferent but whose entities disagree on a hard attribute (origin country, designator, a numeric
    spec beyond tolerance) must go to an analyst rather than merge. It composes three hard rails: a type
    mismatch, a geographic impossibility, the legacy overloaded ``attribute_rules.conflict`` list (kept
    for backward compatibility), and the declared-**critical** roles (D6) via
    :func:`critical_attribute_conflict`. An attribute stated on only one side is **not** a conflict —
    absence is not disagreement.
    """
    if a.etype != b.etype:
        return True
    # Two stated positions too far apart to be one thing is a contradiction of exactly this kind, and
    # the rail has to read it too — otherwise an authoritative coreference could bootstrap the very
    # merge the cluster-level veto exists to refuse.
    if geo_conflict_km(a, b, cfg) is not None:
        return True
    rules = cfg.attribute_rules(a.etype)  # LEGACY overloaded conflict list (backward compat; inert on C)
    if _stated_values_conflict(a, b, rules.get("conflict", [])):
        return True
    for field_name, spec in rules.get("numeric_conflict", {}).items():
        if _numeric_conflict(a.attrs.get(field_name), b.attrs.get(field_name), spec.get("rel_tol")):
            return True
    return critical_attribute_conflict(a, b, cfg)  # D6: declared-critical roles are hard too

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

    # A disagreement on a SOFT identity attribute pulls the score down (the false-merge guard). Two
    # sources feed it, deduplicated: the legacy overloaded ``attribute_rules.conflict`` list (unchanged),
    # and the declared-**supporting** roles (D6) — for which a stated disagreement is soft negative
    # evidence, never a wall (that is the critical role's job). Gated on ``conflict_penalty`` being
    # configured, so it stays inert wherever the penalty is unset (no code literal, gate G6).
    penalty = 1.0
    cpen = cfg.attribute_scoring("conflict_penalty")
    if cpen is not None:
        soft_attrs: list[str] = list(rules.get("conflict", []))
        if a.etype == b.etype:
            soft_attrs += cfg.supporting_role_attrs(a.etype)
        seen: set[str] = set()
        for k in soft_attrs:
            if k in seen:
                continue
            seen.add(k)
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


def relational_score(
    graph: EntityGraph,
    a: str,
    b: str,
    canonical: Canonical,
    exclude: set[str],
    support_k: int | None = None,
) -> float:
    """Jaccard overlap of the two resolved neighbourhoods, discounted by how much it rests on (T3b-F).

    A raw Jaccard **saturates at a perfect 1.0 on a one-element neighbourhood**: two basing sites whose
    only edge is a ``based-at`` from the same unit overlap totally, so the collective-ER signal — the
    strongest term in ``merge_score`` — reads "identical neighbourhood" from a single shared link. On
    this corpus that artefact alone was what lifted eighteen cross-country site pairs to exactly
    ``hitl_low`` and filled most of the analyst's merge queue; nothing else about those pairs agreed.

    ``support_k`` is the number of *distinct shared neighbours* at which the signal reaches full
    strength; below it the overlap is scaled by ``shared / support_k``. The invariant it buys, in the
    same form ``resolution.yaml`` already states its others: **a perfect shared neighbourhood must rest
    on at least ``support_k`` shared neighbours to reach the analyst on its own.** Two entities that
    both connect to one hub are not thereby the same entity — the hub is the evidence that they are two
    things attached to the same third thing.

    Unset (or ``<= 1``) ⇒ the raw Jaccard, byte-identical to the pre-fix behaviour (gates G2/G6).
    """
    na = _neighbours(graph, a, canonical, exclude)
    nb = _neighbours(graph, b, canonical, exclude)
    union = na | nb
    if not union:
        return 0.0
    shared = na & nb
    overlap = len(shared) / len(union)
    if support_k is None or support_k <= 1:
        return overlap
    return overlap * min(1.0, len(shared) / support_k)


def temporal_score(reloc: bool) -> float:
    """Coherent unless we detect a conflict: a relocation/contradiction pair scores 0 (anti-identity)."""
    return 0.0 if reloc else 1.0


def source_asserted_score(
    graph: EntityGraph, a: str, b: str, weight_of: Callable[[str | None], float] | None = None
) -> float:
    """How strongly a *source* asserts the identity a≡b — the best asserting source's grade (D-2.5).

    Identity assertions are ordinary evidence claims and therefore carry their source's credibility:
    a curated register saying "FD-2000 is HQ-9/P" is not the same evidence as an anonymous repost saying
    it. So this returns the **maximum** source weight over the asserting claims rather than a flat 1.0
    (best-source semantics, matching how corroboration treats the strongest look). Still an *identity*
    signal, never claim truth (gate G5), and still structurally incapable of reaching auto-merge on its
    own (``cluster._band``). ``weight_of`` absent ⇒ the old binary behaviour.
    """
    best = 0.0
    for e in graph.edges:
        if e.predicate in IDENTITY_PREDICATES and {e.subject, e.object} == {a, b}:
            best = max(best, weight_of(e.source_id) if weight_of is not None else 1.0)
    return best


def identity_claim_ids(graph: EntityGraph, a: str, b: str) -> list[str]:
    """The claims in which a **source** asserts a≡b — the evidence *behind* ``source_asserted_score``.

    Same pair/predicate test as the score itself, so the list and the number can never disagree: if the
    signal is above zero these claims are why, and if it is zero this is empty. Returned in replay order
    (deterministic, gate G2) and de-duplicated. Identity assertions are consumed rather than drawn
    (``view/pipeline._assemble``), so this is the ONLY route from a candidate ``same-as`` edge back to the
    sentence a source actually wrote — the one-click-to-source non-negotiable, on the one screen where an
    analyst is asked to make an identity call.

    Coreference (``COREF_PREDICATE``) is deliberately excluded: it is a different lane that does not feed
    ``source_asserted``, so including it here would make the citation over-claim what the signal counted.
    """
    out: list[str] = []
    for e in graph.edges:
        if e.predicate not in IDENTITY_PREDICATES or e.claim_id is None:
            continue
        if {e.subject, e.object} == {a, b} and e.claim_id not in out:
            out.append(e.claim_id)
    return out


def _relational_counts(a: Entity, b: Entity, cfg: ResolveConfig) -> bool:
    """May the shared-neighbourhood term contribute for this pair? (Both types must allow it.)"""
    ntx = cfg.node_types
    return ntx.relational_identity(a.etype) and ntx.relational_identity(b.etype)


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
    # T3b-A: for some node types a shared neighbourhood is not identity evidence at all. Two AREAS of
    # responsibility that both contain sightings of the same equipment share a neighbourhood **by
    # construction** — that is a fact about where the equipment is dispersed, not a reason to think the
    # two areas are one area. The ontology declares which types those are (`identity.relational: false`);
    # every other type keeps the collective-ER signal untouched, and an area can still merge or queue on
    # name/alias evidence, which is the only honest identity signal it has.
    relational = (
        relational_score(graph, a.eid, b.eid, canonical, exclude, cfg.relational_support_k)
        if _relational_counts(a, b, cfg)
        else 0.0
    )
    parts = {
        ATTRIBUTE: attribute_score(a, b, cfg, alias_idx),
        RELATIONAL: relational,
        TEMPORAL: temporal_score(reloc),
        SOURCE_ASSERTED: source_asserted_score(graph, a.eid, b.eid, cfg.identity_source_weight),
    }
    total = sum(cfg.weight(sig) * parts[sig] for sig in parts)
    return {**parts, "total": _clamp(total)}


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def identity_ledger(breakdown: Mapping[str, float]) -> list[dict[str, float | str]]:
    """The merge's own corroboration ledger, derived purely from a stored ``merge_breakdown`` (D4).

    "Merge corroboration, not assertion corroboration": one entry per independent identity signal
    (:data:`SIGNALS` — ``attribute`` / ``relational`` / ``temporal_consistency`` / ``source_asserted``)
    whose raw value is **> 0**, in signal order (deterministic — gate G2). It records *which* independent
    lines of evidence say two profiles co-refer, with their values — the merge's own accounting, separate
    from whether any fact about the entity is true (gate G5).

    Empty for a degenerate breakdown carrying only ``total`` (nothing corroborated), so a caller records it
    only when there is something to record — keeping the pre-Stage-2 provenance shape byte-identical where
    no signal fired. Pure function of the breakdown ⇒ callable on any stored breakdown, incl. a confirmed
    merge's ``resolved_from`` entry.
    """
    return [
        {"signal": sig, "value": float(breakdown[sig])}
        for sig in SIGNALS
        if breakdown.get(sig, 0.0) > 0
    ]
