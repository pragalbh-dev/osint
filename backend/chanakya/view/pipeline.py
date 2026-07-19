"""``rebuild()`` — the pure, deterministic reduction of (evidence, decision, config) → view.

**The load-bearing invariant (master §1, gate G1):** no LLM, network, clock, or randomness runs
here. The LLM *proposed* upstream (its output is frozen in the logs); deterministic rules *dispose*
inside this function. Given the same logs + config, the emitted view is byte-identical (gate G2).

Stage call-order is fixed (master §4.3):
``resolve → score_claims → (group by independence) → assign_status → check → precompute``.
Around those five stages, F0 owns four *real* pieces: retraction handling, supersede/contradict
(``supersede.py``), rendering the resolver's decisions as edges (candidate ``same-as`` + ``distinct-from``,
G4-exempt / never scored), and HITL decision-effect application (gate G12). All numeric scoring lives
in the stages (which read config), never here.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any, cast

from chanakya.credibility import (
    assertion_freshness,
    assign_status,
    group_by_independence,
    score_claims,
)
from chanakya.materiality import precompute
from chanakya.resolve import resolve
from chanakya.schemas import (
    AssertionInput,
    ClaimRecord,
    ConfidenceBreakdown,
    ConfigBundle,
    DecisionRecord,
    EdgeView,
    EntityDescriptor,
    EventDescriptor,
    EventView,
    GraphView,
    KnownGap,
    NodeView,
    Partition,
    SourceRegistryEntry,
    pair_key,
)
from chanakya.sufficiency import check
from chanakya.timeref import effective_as_of, is_available_by

from .export import sorted_view
from .supersede import build_instance_edges

# ── log normalisation ────────────────────────────────────────────────────────────────────────

def _replay[T](source: object, item_type: type[T]) -> list[T]:
    """Accept a log object (``.replay()``) or a plain list of records — return the list."""
    if hasattr(source, "replay"):
        return cast("list[T]", source.replay())
    return cast("list[T]", list(cast("Iterable[T]", source)))


# ── retraction (real F0) ─────────────────────────────────────────────────────────────────────

def apply_retractions(claims: list[ClaimRecord]) -> list[ClaimRecord]:
    """Drop claims targeted by a retraction claim (and the retraction records themselves).

    Retraction is an *appended* claim, never a delete (append-only store, gate G3); the view simply
    excludes the retracted claim on rebuild.
    """
    retracted = {c.targets for c in claims if c.kind == "retraction" and c.targets}
    return [c for c in claims if c.kind != "retraction" and c.claim_id not in retracted]


def apply_claim_exclusions(
    claims: list[ClaimRecord], decisions: list[DecisionRecord]
) -> list[ClaimRecord]:
    """Drop claims a HITL decision rejected — sourced from the decision log, applied like a retraction.

    The richer *reject* beat (SCORE pickup #1): rejecting a look **excludes** it upstream of scoring so
    the status machine re-derives the verdict from fewer independent groups (confirmed→probable), instead
    of force-flipping the label post-machine. HITL emits an ``exclude_claims`` effect; rebuild applies it
    here — the claim is never mutated or deleted from the log (append-only, gate G3), just left out of the
    view on this rebuild. Empty when no decision excludes anything → view unchanged (gate G2).
    """
    excluded: set[str] = set()
    for d in decisions:
        effect = (d.effects or {}).get("exclude_claims")
        if isinstance(effect, str):
            excluded.add(effect)
        elif isinstance(effect, (list, tuple)):
            excluded.update(str(cid) for cid in effect)
    return [c for c in claims if c.claim_id not in excluded] if excluded else claims


def deception_gate_flags(
    element: NodeView | EdgeView | EventView,
    claims_by_id: dict[str, ClaimRecord],
    sources: dict[str, SourceRegistryEntry],
) -> list[str]:
    """The unconditional deception gate — ``adversary-denial`` (spine/04 §3.4) — computed where claims +
    the source registry are in scope, so ``assign_status`` can cap from the ``AssertionInput`` alone.

    Fires if any supporting claim's source carries ``adversary_denial_flag`` (a fake second-source / a
    denial of a known dependency). Empty on clean elements → golden view unchanged (gate G2). The
    *decoy* gate is separate (single-pass-conditional — see :func:`has_decoy_look`).
    """
    for cid in element.claim_ids:
        claim = claims_by_id.get(cid)
        if claim is None:
            continue
        src = sources.get(claim.source_id)
        if src is not None and src.adversary_denial_flag:
            return ["adversary-denial"]
    return []


def has_decoy_look(
    element: NodeView | EdgeView | EventView, claims_by_id: dict[str, ClaimRecord]
) -> bool:
    """True if a single-pass decoy signal rides this element — on the element itself, or on a supporting
    claim's ``attributes`` (e.g. INGEST's attribution ``inference`` claim D, which carries
    ``decoy_risk_flag`` on ``ClaimRecord.attributes``, never on the edge). The *cap* is applied only when
    the assertion is single-pass (< the min independent looks); a second independent look resolves it.
    """
    if getattr(element, "attrs", {}).get("decoy_risk_flag"):
        return True
    for cid in element.claim_ids:
        claim = claims_by_id.get(cid)
        attrs = (claim.attributes or {}) if claim is not None else {}
        if attrs.get("decoy_risk_flag") or attrs.get("decoy_risk"):
            return True
    return False


def gated_attr_flags(
    element: NodeView | EdgeView | EventView, config: ConfigBundle
) -> list[str]:
    """``gated-attr-unknown`` if a configured gated attr (foreign_control/readiness) is present-but-UNKNOWN.

    Such an element cannot reach *confirmed* (spine/04 §3.4: gated attrs not UNKNOWN; C/01 "never
    default-to-OEM"). An absent attr is not applicable → no flag. The gated-attr list is config-driven
    (default the two C/01 gated attrs). Empty on clean elements → golden view unchanged (gate G2).
    """
    gated = getattr(config.credibility, "gated_attrs", None) or ("foreign_control", "readiness")
    attrs = getattr(element, "attrs", {})
    for attr in gated:
        value = attrs.get(attr)
        if isinstance(value, str) and value.strip().upper() == "UNKNOWN":
            return ["gated-attr-unknown"]
    return []


# ── partition application ────────────────────────────────────────────────────────────────────

def _apply_partition(claims: list[ClaimRecord], partition: Partition) -> list[ClaimRecord]:
    """Stamp each claim with its resolved_ref from the partition (immutably — a copy)."""
    out = []
    for c in claims:
        rr = partition.resolved_ref.get(c.claim_id, c.resolved_ref)
        out.append(c.model_copy(update={"resolved_ref": rr}) if rr is not c.resolved_ref else c)
    return out


# ── resolution-decision rendering (real F0: merges + traps made inspectable) ───────────────────

def _merge_provenance(nodes: dict[str, NodeView], partition: Partition) -> None:
    """Stamp accepted-merge provenance on the surviving (canonical) node — the auto-merge audit trail.

    An accepted merge is *effected* by a shared ``resolved_ref`` (both members already collapsed to
    one node); this records the *why* (which ref, at what confidence, with the score breakdown) on
    that node so the merge stays one-click inspectable. ``merge_confidence`` is identity, never truth
    (gate G5). Iterated in sorted order for byte-determinism (gate G2).
    """
    for member, canonical in sorted(partition.same_as):
        node = nodes.get(canonical)
        if node is None:
            continue
        key = pair_key(member, canonical)
        entry: dict[str, Any] = {"merged_ref": member}
        conf = partition.merge_confidence.get(key)
        if conf is not None:
            entry["merge_confidence"] = conf
        breakdown = partition.merge_breakdown.get(key)
        if breakdown:
            entry["breakdown"] = breakdown
        node.attrs.setdefault("resolved_from", []).append(entry)


def _resolution_edges(node_ids: set[str], partition: Partition) -> list[EdgeView]:
    """Render the resolver's *undecided* + *veto* decisions: candidate ``same-as`` + ``distinct-from`` edges.

    These cite a merge decision, not a claim, so they are G4-exempt and are **never scored** (added
    after the status machine; they carry ``merge_confidence`` — identity — never
    ``assertion_confidence``, gate G5). Auto-merges do *not* appear here (they collapse to one node —
    see :func:`_merge_provenance`); only pairs an analyst still has to adjudicate, and explicit
    do-not-merge traps, surface as edges. An edge is emitted only when *both* endpoints exist as nodes.
    """
    out: list[EdgeView] = []
    for a, b in sorted(partition.candidates):
        if a in node_ids and b in node_ids:
            key = pair_key(a, b)
            out.append(
                EdgeView(
                    id=f"same-as:{key}",
                    type="same-as",
                    source=a,
                    target=b,
                    merge_confidence=partition.merge_confidence.get(key),
                    attrs={"merge_band": "candidate", "breakdown": partition.merge_breakdown.get(key, {})},
                )
            )
    for a, b in sorted(partition.distinct_from):
        if a in node_ids and b in node_ids:
            out.append(
                EdgeView(
                    id=f"distinct-from:{pair_key(a, b)}",
                    type="distinct-from",
                    source=a,
                    target=b,
                    attrs={"reason": "explicit do-not-merge (hard veto)"},
                )
            )
    return out


# ── graph assembly (+ supersede/contradict) ──────────────────────────────────────────────────

def _assemble(
    resolved: list[ClaimRecord], entity_canonical: dict[str, str] | None = None
) -> tuple[dict[str, NodeView], list[EdgeView], list[EventView]]:
    nodes: dict[str, NodeView] = {}
    events: list[EventView] = []
    edge_groups: dict[str, list[ClaimRecord]] = defaultdict(list)
    # A merge reconnects edges: a triple's raw subject/object (supersede.py reads these directly) is
    # remapped to the merged entity's canonical id. Empty map ⇒ identity ⇒ view unchanged (gate G2).
    canon = entity_canonical or {}

    def to_canonical(ref: str) -> str:
        return canon.get(ref, ref)

    for c in resolved:
        rr = c.resolved_ref
        payload = c.payload
        # Narrow on the payload type (isinstance) — the validator guarantees it matches `asserts`.
        if isinstance(payload, EntityDescriptor):
            raw = rr.entity_id if rr and rr.entity_id else f"ent:{payload.entity_type}:{payload.name}"
            nid = to_canonical(raw)
            node = nodes.get(nid)
            if node is None:
                node = NodeView(id=nid, type=payload.entity_type, name=payload.name)
                nodes[nid] = node
            if c.claim_id not in node.claim_ids:
                node.claim_ids.append(c.claim_id)
            for k, v in payload.attrs.items():
                node.attrs.setdefault(k, v)  # first claim wins; deterministic in replay order
        elif isinstance(payload, EventDescriptor):
            eid = rr.entity_id if rr and rr.entity_id else f"event:{c.claim_id}"
            events.append(
                EventView(
                    id=eid,
                    event_type=payload.event_type,
                    time_interval=payload.time_interval,
                    location=payload.location,
                    participants=[to_canonical(p) for p in payload.participants],
                    attrs=dict(payload.attrs),
                    claim_ids=[c.claim_id],
                )
            )
        else:  # Triple (relationship)
            # Remap endpoints through the merge map so build_instance_edges (which reads the raw
            # subject/object) attaches the edge to the canonical nodes. No-op when nothing merged.
            subj, obj = to_canonical(payload.subject), to_canonical(payload.object)
            if (subj, obj) != (payload.subject, payload.object):
                c = c.model_copy(update={"payload": payload.model_copy(update={"subject": subj, "object": obj})})
            ei = rr.edge_instance if rr and rr.edge_instance else f"edge:{subj}:{payload.predicate}:{obj}"
            edge_groups[ei].append(c)

    edges: list[EdgeView] = []
    for ei, cs in edge_groups.items():
        edges.extend(build_instance_edges(ei, cs))

    # Never leave an edge dangling: materialise a referenced-but-undeclared node, citing the edge's
    # claims as its (weak) provenance so gate G4 (every node carries ≥1 claim_id) still holds.
    for e in edges:
        for endpoint in (e.source, e.target):
            if endpoint not in nodes:
                nodes[endpoint] = NodeView(id=endpoint, type="unknown", claim_ids=list(e.claim_ids))

    return nodes, edges, events


# ── HITL decision effects (real F0, gate G12) ─────────────────────────────────────────────────

def apply_decision_effects(view: GraphView, decisions: Iterable[DecisionRecord]) -> GraphView:
    """Apply decision-log ``effects`` to the view — this is what makes HITL propagation structural.

    An analyst ``status_override`` sets the element's status (legitimately overriding the machine —
    the whole point of gate G12); an ``integrity_flag`` adds a flag to the confidence breakdown.
    """
    idx: dict[str, NodeView | EdgeView | EventView] = {}
    for n in view.nodes:
        idx[n.id] = n
    for e in view.edges:
        idx[e.id] = e
    for ev in view.events:
        idx[ev.id] = ev

    for d in decisions:
        effects = d.effects or {}
        set_status = effects.get("set_status")
        if isinstance(set_status, dict):
            for elid, status in set_status.items():
                el = idx.get(elid)
                if el is not None:
                    el.status = status
        add_flag = effects.get("add_integrity_flag")
        if isinstance(add_flag, dict):
            el = idx.get(add_flag.get("element_id", ""))
            if el is not None:
                if el.confidence is None:
                    el.confidence = ConfidenceBreakdown()
                flag = add_flag.get("flag")
                if flag:
                    el.confidence.integrity_flags = sorted(set(el.confidence.integrity_flags) | {flag})
    return view


# ── the orchestrator ─────────────────────────────────────────────────────────────────────────

def rebuild(evidence: object, decision: object, config: ConfigBundle, prev_view: GraphView | None = None) -> GraphView:
    """Reduce the two logs + config to the knowledge view — pure & deterministic (G1, G2)."""
    claims: list[ClaimRecord] = _replay(evidence, ClaimRecord)
    decisions: list[DecisionRecord] = _replay(decision, DecisionRecord)
    active = apply_retractions(claims)
    active = apply_claim_exclusions(active, decisions)  # HITL reject → drop the look upstream of scoring

    # Rewind: a *past* ``config.credibility.as_of`` hides claims not yet available then, so "as of DATE"
    # is an honest point-in-time view (is_available_by is clock-free — G1). Unset/future ⇒ no-op (G2).
    if config.credibility.as_of:
        active = [c for c in active if is_available_by(c, config.credibility.as_of)]

    # 1. resolution — resolve() is a pure function of (claims, config, prev_view, decision log): the
    #    decision log carries the offline LLM proposer's frozen merge_proposal records + the analyst's
    #    replayed merge_adjudication(accept)s that grow the alias table (spine/03; still no live LLM — G1).
    partition = resolve(active, config, prev_view, decisions)
    resolved = _apply_partition(active, partition)

    # 2. assemble nodes/edges/events (+ supersede/contradict — real F0); the merge map reconnects a
    #    merged-away entity's edges to its canonical node (no-op when nothing merged).
    nodes, edges, events = _assemble(resolved, partition.entity_canonical)
    _merge_provenance(nodes, partition)  # accepted-merge audit trail on the canonical node
    claims_by_id = {c.claim_id: c for c in resolved}
    sources = config.sources.as_map()

    # 3. credibility (per-claim) — decisions carry analyst integrity flags (origin-wide, incl. future claims)
    credibility = score_claims(resolved, sources, config, decisions)

    # 4. per-assertion inputs: independence groups attached to each element
    elements: dict[str, NodeView | EdgeView | EventView] = {}
    for n in nodes.values():
        elements[n.id] = n
    for e in edges:
        elements[e.id] = e
    for ev in events:
        elements[ev.id] = ev

    # The clock-free evaluation "now" for freshness/staleness (pinned as_of, else newest claim).
    as_of = effective_as_of(config, resolved)

    assertions: list[AssertionInput] = []
    for eid, el in elements.items():
        groups = group_by_independence(el.claim_ids, claims_by_id, sources, config)
        el.supporting_claims = groups
        per_claim = {cid: credibility[cid] for cid in el.claim_ids if cid in credibility}
        kind = "node" if isinstance(el, NodeView) else ("edge" if isinstance(el, EdgeView) else "event")
        contradiction = bool(getattr(el, "attrs", {}).get("contradiction"))
        # Gates computed where claims + sources are in scope, so assign_status can enforce the caps
        # from the AssertionInput alone (spine/04 §3.4): deception (adversary-denial/decoy-risk),
        # freshness (aging/stale), and gated-attr-unknown (foreign_control/readiness).
        fresh_summary, fresh_flags = assertion_freshness(el.claim_ids, claims_by_id, as_of, config)
        gate_flags = deception_gate_flags(el, claims_by_id, sources)
        # Single-pass decoy: caps at probable only when the assertion is a lone look; a second
        # independent, clean look resolves it (spine/04 "single-pass"; keeps gate G7 satisfiable).
        if has_decoy_look(el, claims_by_id):
            min_g = getattr(config.credibility, "min_independent_groups", None)
            effective_looks = sum(g.weight for g in groups)
            if min_g is None or effective_looks < min_g:
                gate_flags.append("decoy-risk")
        gate_flags.extend(fresh_flags)
        gate_flags.extend(gated_attr_flags(el, config))
        if contradiction:
            gate_flags.append("contradiction")
        a = AssertionInput(
            element_id=eid,
            element_kind=kind,
            per_claim_credibility=per_claim,
            groups=groups,
            opposing_claims=list(el.opposing_claims),
            has_unresolved_contradiction=contradiction,
            gate_flags=gate_flags,
            freshness=fresh_summary,
        )
        # Sufficiency runs BEFORE status so the confirmed gate can require it + the machine owns the
        # `insufficient` label (assessability ⊥ magnitude — spine/04 §3.7). AssertionInput.sufficiency
        # is the F0-frozen channel for exactly this (§4.3 "illustrative" order reconciled here).
        a.sufficiency = check(a, claims_by_id, config)
        assertions.append(a)

    # 5. status (batch) — reads a.sufficiency + a.gate_flags for the gate machine
    assessments = assign_status(assertions, config)

    # 6. attach status/confidence/freshness/sufficiency; emit a first-class Known Gap on a failed template
    known_gaps: list[KnownGap] = []
    for a in assertions:
        el = elements[a.element_id]
        suff = a.sufficiency
        el.sufficiency = suff
        el.freshness = a.freshness
        assess = assessments.get(a.element_id)
        if assess is not None:
            el.status = assess.status
            el.confidence = ConfidenceBreakdown(
                per_claim_credibility=a.per_claim_credibility,
                independence_groups=a.groups,
                integrity_flags=a.gate_flags,
                freshness_factor=a.freshness.decay_factor if a.freshness else None,
                assertion_confidence=assess.assertion_confidence,
            )
        if suff is not None and not suff.satisfied:
            known_gaps.append(
                KnownGap(
                    id=f"gap:{a.element_id}",
                    related_ref=a.element_id,
                    what_missing=(suff.missing_slots[0] if suff.missing_slots else "evidence requirement unmet"),
                    observability_ceiling=suff.ceiling or "confirmable",
                    next_coverage_due=suff.next_coverage_due,
                    missing_slots=list(suff.missing_slots),
                )
            )

    view = GraphView(
        nodes=list(nodes.values()),
        edges=edges,
        events=events,
        known_gaps=known_gaps,
    )

    # 7. materiality precompute — inside rebuild, tracks config automatically (spine/09)
    view = precompute(view, config)

    # 8. HITL decision effects last (an override wins over the machine — gate G12)
    view = apply_decision_effects(view, decisions)

    # 8b. render the resolver's decisions as edges — candidate same-as (HITL band) + distinct-from
    #     traps. Added AFTER scoring so they're never assigned a truth status (G5); G4-exempt.
    view.edges.extend(_resolution_edges({n.id for n in view.nodes}, partition))

    # 9. deterministic ordering + diagnostic meta (no clock, no RNG — G2)
    view = sorted_view(view)
    view.meta = {
        "config_version": config.version,
        "node_count": len(view.nodes),
        "edge_count": len(view.edges),
        "event_count": len(view.events),
        "known_gap_count": len(view.known_gaps),
    }
    return view
