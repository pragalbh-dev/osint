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
from .succession import ORDERED, classify_succession

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


def attribute_is_conflict(a: Entity, b: Entity, attr: str, cfg: ResolveConfig) -> bool:
    """Do ``a`` and ``b`` *conflict* on ``attr`` — a **time-aware** stated disagreement (Stage 3B-ii).

    A conflict requires both sides to STATE ``attr`` with DIFFERENT values (absence ≠ conflict; the same
    value on both sides ≠ conflict — exactly the old stated-different rule). The time-awareness is the one
    added waiver: when the two values differ, it is **still** a conflict *unless* the attribute is declared
    ``perishable`` for this type AND the two sides' retained value-series, taken together, form a clean
    ``ordered`` succession — a legitimate update over time (an old value cleanly superseded by a newer one),
    which is a state change, not a contradiction. A perishable attribute that changed once, cleanly, is not
    evidence that two profiles are different entities; it is one entity whose state moved.

    Everything else stays a conflict exactly as before: a ``contradiction`` (two values true over
    overlapping/equal time), an ``unorderable`` set (a distinct value with no usable date), and — crucially
    — **any** disagreement on an attribute not declared ``perishable is True`` (``None``/``False`` ⇒ a
    durable/undeclared attribute never earns the waiver; only an explicit ``True`` enables it). Pure and
    deterministic (reuses the offline :func:`classify_succession`; no clock/RNG/parse) — safe in the
    ``rebuild()`` path (gates G1/G2), and byte-inert wherever no attribute is declared perishable.
    """
    va, vb = a.attrs.get(attr), b.attrs.get(attr)
    if va is None or vb is None or va == vb:
        return False  # absence ≠ conflict; same value ≠ conflict
    if cfg.attribute_perishable(a.etype, attr) is True:
        series = a.attr_history.get(attr, []) + b.attr_history.get(attr, [])
        if classify_succession(series).status == ORDERED:
            return False  # a clean perishable update over time is not an identity conflict
    return True


def _stated_values_conflict(a: Entity, b: Entity, attrs: list[str], cfg: ResolveConfig) -> bool:
    """True if some attr in ``attrs`` is a **time-aware conflict** across ``a`` and ``b`` (absence ≠ conflict).

    The one shared detection ``has_hard_conflict``, ``critical_attribute_conflict`` and the scorer's soft
    penalty all read, so "what counts as a stated attribute disagreement" has exactly one definition — now
    routed, per attribute, through :func:`attribute_is_conflict` so a clean perishable succession no longer
    counts. A side that simply doesn't state the attribute is *unknown*, never *different*.
    """
    return any(attribute_is_conflict(a, b, k, cfg) for k in attrs)


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
    return _stated_values_conflict(a, b, cfg.critical_role_attrs(a.etype), cfg)


def _value_meets_grade_floor(ent: Entity, attr: str, value: object, cfg: ResolveConfig) -> bool:
    """Is ``ent``'s conflicting ``value`` for ``attr`` attested by ≥1 source at/above the credibility floor?

    Reads the per-value provenance retained in ``Entity.attr_history`` (Stage 3-prep): the sources that
    asserted exactly this value. A value with **no** source-attributed claim — a curated registry seed,
    say — is not a flaky source and counts as credible (the floor exists to neutralise identifiable
    low-grade *sources*, not analyst-curated facts). Otherwise the value is credible iff any asserting
    source clears :meth:`ResolveConfig.source_meets_critical_veto_floor` (floor OFF ⇒ always true).
    """
    source_ids = [ac.source_id for ac in ent.attr_history.get(attr, []) if ac.value == value and ac.source_id]
    if not source_ids:
        return True  # curated / not source-attributable ⇒ not a flaky source ⇒ credible
    return any(cfg.source_meets_critical_veto_floor(sid) for sid in source_ids)


def critical_conflict_disposition(a: Entity, b: Entity, cfg: ResolveConfig) -> tuple[str, tuple[str, ...]]:
    """Classify a same-type pair's critical-attribute situation for the D5 wall (Stage 3A credibility floor).

    Returns ``(disposition, conflicting_attrs)`` where disposition is one of:

    * ``"none"``  — no *stated* critical-attribute conflict (absence ≠ conflict);
    * ``"wall"``  — at least one conflicting critical attr is **credible on both sides** (each side's
      conflicting value is attested by a source at/above ``critical_veto_min_grade``) ⇒ a hard veto;
    * ``"raise"`` — a critical conflict exists but **none** is credible on both sides ⇒ below the floor,
      so the pair is raised to the analyst rather than walled (D5 take-care a).

    ``conflicting_attrs`` is the sorted tuple of the critical attributes actually in disagreement (the
    credible ones for a wall, all of them for a raise) — the material for a human-legible reason. Pure and
    deterministic (sorted, no clock/RNG); floor OFF ⇒ every conflict is credible ⇒ always ``"wall"``,
    byte-identical to the pre-Stage-3A unconditional veto.
    """
    if a.etype != b.etype:
        return ("none", ())
    conflicting = tuple(
        k for k in cfg.critical_role_attrs(a.etype) if attribute_is_conflict(a, b, k, cfg)
    )
    if not conflicting:
        return ("none", ())
    credible = tuple(
        k
        for k in conflicting
        if _value_meets_grade_floor(a, k, a.attrs[k], cfg) and _value_meets_grade_floor(b, k, b.attrs[k], cfg)
    )
    return ("wall", credible) if credible else ("raise", conflicting)


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
    if _stated_values_conflict(a, b, rules.get("conflict", []), cfg):
        return True
    for field_name, spec in rules.get("numeric_conflict", {}).items():
        if _numeric_conflict(a.attrs.get(field_name), b.attrs.get(field_name), spec.get("rel_tol")):
            return True
    return critical_attribute_conflict(a, b, cfg)  # D6: declared-critical roles are hard too


def _shared_unique_id(a: Entity, b: Entity, cfg: ResolveConfig) -> bool:
    """True if ``a`` and ``b`` state the SAME value of a declared **unique** hard identifier for their type.

    The strongest, most durable identity signal there is — a serial / registration / unique key two records
    share is one entity by construction. Reused verbatim by the Phase-1 bootstrap trigger
    (``cluster.resolve_entities``) and by :func:`has_durable_identity_support`; one definition so the two can
    never diverge on what "shared hard id" means.
    """
    for attr in cfg.hard_id_fields("unique").get(a.etype, []):
        va, vb = a.attrs.get(attr), b.attrs.get(attr)
        if va is not None and va == vb:
            return True
    return False


def has_durable_identity_support(a: Entity, b: Entity, cfg: ResolveConfig) -> bool:
    """True if ``a`` and ``b`` share a **durable** line of identity evidence (Stage 3B-iii).

    Durable = evidence that does not evaporate when a transient state changes. It is the counterpart to the
    perishable-only confirmation cap (``cluster.resolve_entities``): a pair may score into the auto-merge band
    purely on perishable/transient agreement (a shared location, status, posture — raised by
    :func:`attribute_score`'s agreement path), and a shared transient state can be one entity or two that
    merely passed through it. Durable support is what separates the two, so a confirm that has it (or still
    confirms without the perishable bonus) is trusted and one that rests solely on transient agreement is
    capped to ``probable``.

    Two durable sources, both **pair-intrinsic** (partition-independent — the answer never changes as
    clusters grow):

    * a shared **unique** hard identifier (:func:`_shared_unique_id`);
    * agreement on the SAME value of an identity-relevant attribute — the ``identity`` list ∪ the declared
      critical/supporting roles — that is **not** declared ``perishable`` (``attribute_perishable is not True``,
      so an undeclared or explicitly-durable attribute qualifies; a perishable one never does, because that is
      exactly the transient evidence the cap exists to distrust). Same-value only: the ``ordered``-succession
      waiver is a *perishable*-attribute allowance and is therefore not durable support.

    Deliberately does NOT consult the name / coreference bootstrap triggers (alias-equivalence, exact-name,
    containment, authoritative coref): those need the alias index / coref set the caller holds, so they are
    accounted for **at the cap site**, not here (hence the ``(a, b, cfg)`` signature). Pure and deterministic
    (no clock/RNG; no numeric literal — gate G6).
    """
    if _shared_unique_id(a, b, cfg):
        return True
    if a.etype != b.etype:
        return False  # role attrs + perishability are per-type; a cross-type pair has no durable attr agreement
    rules = cfg.attribute_rules(a.etype)
    id_attrs = list(rules.get("identity", [])) + cfg.critical_role_attrs(a.etype) + cfg.supporting_role_attrs(a.etype)
    for attr in id_attrs:
        va = a.attrs.get(attr)
        if va is not None and va == b.attrs.get(attr) and cfg.attribute_perishable(a.etype, attr) is not True:
            return True
    return False


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


def attribute_score(
    a: Entity, b: Entity, cfg: ResolveConfig, alias_idx: AliasIndex | None = None, durable_only: bool = False
) -> float:
    """Name similarity (or identity-attr agreement), knocked down by hard-conflict attributes.

    Alias-equivalent names (seed or learned) score a full 1.0 — FD-2000 ≡ HQ-9/P by the alias table,
    even though the surface strings barely resemble each other.

    ``durable_only`` (Stage 3B-iii): compute the score with **all perishable-attribute agreement removed** —
    a perishable attribute is a transient state, so its agreement in EITHER form (a same value, or a clean
    ``ordered`` succession of differing values) is dropped from the agreement ratio entirely and treated as
    *neutral* (neither raising nor lowering it). Everything durable is unchanged: base name similarity,
    alias-equivalence, the legacy ``identity`` list, and same-value agreement on a NON-perishable attribute
    still count; a genuine conflict still lowers the ratio and fires the soft penalty. This is the "would this
    pair still confirm on stable evidence alone?" score the perishable-only confirmation cap consults, and it
    is consistent with :func:`has_durable_identity_support` (which likewise treats a perishable same-value
    agreement as non-durable). ``False`` (the default) is the full Part-1 behaviour, byte-unchanged (gate G2).
    """
    if alias_idx is not None and alias_idx.equivalent(
        normalize(a.name, cfg.transliteration), normalize(b.name, cfg.transliteration)
    ):
        return 1.0
    sim = name_similarity(a.name, b.name, cfg.transliteration)
    rules = cfg.attribute_rules(a.etype) if a.etype == b.etype else {}

    # Identity-relevant attrs AGREEING can carry the pair even when the surface name drifts (Stage 3B-iii).
    # The agreeing set is the union of the legacy ``identity`` list and the declared identity-bearing roles
    # (critical ∪ supporting, D6) — every attribute whose agreement is positive identity evidence. An
    # attribute counts as AGREEING when both sides state the SAME value, OR (for a perishable attribute) when
    # their combined value-series is a clean ``ordered`` succession — a consistent trajectory over time reads
    # as consistency, not disagreement. That is exactly the negation of the time-aware
    # :func:`attribute_is_conflict` on an attribute both sides state, so it is routed through that one
    # detector rather than a second copy of the succession logic. ``sim`` is raised to
    # ``agreeing / present`` — the same formula and the same ``max`` the legacy identity path used (no new
    # weight — gate G6). Byte-inert where only a non-perishable ``identity`` list is declared (``agreeing``
    # collapses to the old strict ``equal``); it moves scores exactly where a role attr or a perishable
    # trajectory now counts as agreement, which is the point.
    id_attrs: list[str] = list(rules.get("identity", []))
    if a.etype == b.etype:
        id_attrs += cfg.critical_role_attrs(a.etype) + cfg.supporting_role_attrs(a.etype)
    seen_id: set[str] = set()
    present = 0
    agreeing = 0
    for k in id_attrs:
        if k in seen_id:
            continue
        seen_id.add(k)
        if a.attrs.get(k) is None or b.attrs.get(k) is None:
            continue  # not stated on both sides ⇒ not part of the agreement ratio (absence ≠ evidence)
        # ``durable_only``: a PERISHABLE attribute is a transient state, so its agreement — in EITHER form,
        # a same value ("both active now") or a clean ordered succession — is not durable identity evidence.
        # Drop it entirely (neutral), so it neither raises nor lowers the durable-only score. A non-perishable
        # attribute (undeclared or explicitly durable) is unaffected: same-value agreement still counts, a
        # genuine change still counts against it.
        if durable_only and cfg.attribute_perishable(a.etype, k) is True:
            continue
        present += 1
        if not attribute_is_conflict(a, b, k, cfg):
            agreeing += 1
    if present:
        sim = max(sim, agreeing / present)

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
            if attribute_is_conflict(a, b, k, cfg):  # time-aware: a clean perishable update is no penalty
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
    durable_only: bool = False,
) -> dict[str, float]:
    """Full weighted merge_score + the stored per-signal breakdown (explainability).

    ``durable_only`` is threaded only to :func:`attribute_score` (the ATTRIBUTE term), dropping the
    perishable ordered-succession bonus so the cap can ask "does this pair still confirm on stable evidence
    alone?"; ``relational`` and ``temporal`` are left as-is (a purely-relational perishable case is out of
    scope for Stage 3B-iii). Default ``False`` ⇒ the full score, byte-unchanged (gate G2).
    """
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
        ATTRIBUTE: attribute_score(a, b, cfg, alias_idx, durable_only=durable_only),
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
