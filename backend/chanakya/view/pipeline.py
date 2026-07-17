"""``rebuild()`` — the pure, deterministic reduction of (evidence, decision, config) → view.

**The load-bearing invariant (master §1, gate G1):** no LLM, network, clock, or randomness runs
here. The LLM *proposed* upstream (its output is frozen in the logs); deterministic rules *dispose*
inside this function. Given the same logs + config, the emitted view is byte-identical (gate G2).

Stage call-order is fixed (master §4.3):
``resolve → score_claims → (group by independence) → assign_status → check → precompute``.
Around those five stages, F0 owns three *real* pieces: retraction handling, supersede/contradict
(``supersede.py``), and HITL decision-effect application (gate G12). All numeric scoring lives in the
stages (which read config), never here.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import cast

from chanakya.credibility import assign_status, group_by_independence, score_claims
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
)
from chanakya.sufficiency import check

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


# ── partition application ────────────────────────────────────────────────────────────────────

def _apply_partition(claims: list[ClaimRecord], partition: Partition) -> list[ClaimRecord]:
    """Stamp each claim with its resolved_ref from the partition (immutably — a copy)."""
    out = []
    for c in claims:
        rr = partition.resolved_ref.get(c.claim_id, c.resolved_ref)
        out.append(c.model_copy(update={"resolved_ref": rr}) if rr is not c.resolved_ref else c)
    return out


# ── graph assembly (+ supersede/contradict) ──────────────────────────────────────────────────

def _assemble(resolved: list[ClaimRecord]) -> tuple[dict[str, NodeView], list[EdgeView], list[EventView]]:
    nodes: dict[str, NodeView] = {}
    events: list[EventView] = []
    edge_groups: dict[str, list[ClaimRecord]] = defaultdict(list)

    for c in resolved:
        rr = c.resolved_ref
        payload = c.payload
        # Narrow on the payload type (isinstance) — the validator guarantees it matches `asserts`.
        if isinstance(payload, EntityDescriptor):
            nid = rr.entity_id if rr and rr.entity_id else f"ent:{payload.entity_type}:{payload.name}"
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
                    participants=list(payload.participants),
                    attrs=dict(payload.attrs),
                    claim_ids=[c.claim_id],
                )
            )
        else:  # Triple (relationship)
            ei = rr.edge_instance if rr and rr.edge_instance else (
                f"edge:{payload.subject}:{payload.predicate}:{payload.object}"
            )
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

    # 1. resolution
    partition = resolve(active, config, prev_view)
    resolved = _apply_partition(active, partition)

    # 2. assemble nodes/edges/events (+ supersede/contradict — real F0)
    nodes, edges, events = _assemble(resolved)
    claims_by_id = {c.claim_id: c for c in resolved}
    sources = config.sources.as_map()

    # 3. credibility (per-claim)
    credibility = score_claims(resolved, sources, config)

    # 4. per-assertion inputs: independence groups attached to each element
    elements: dict[str, NodeView | EdgeView | EventView] = {}
    for n in nodes.values():
        elements[n.id] = n
    for e in edges:
        elements[e.id] = e
    for ev in events:
        elements[ev.id] = ev

    assertions: list[AssertionInput] = []
    for eid, el in elements.items():
        groups = group_by_independence(el.claim_ids, claims_by_id, sources, config)
        el.supporting_claims = groups
        per_claim = {cid: credibility[cid] for cid in el.claim_ids if cid in credibility}
        kind = "node" if isinstance(el, NodeView) else ("edge" if isinstance(el, EdgeView) else "event")
        contradiction = bool(getattr(el, "attrs", {}).get("contradiction"))
        assertions.append(
            AssertionInput(
                element_id=eid,
                element_kind=kind,
                per_claim_credibility=per_claim,
                groups=groups,
                opposing_claims=list(el.opposing_claims),
                has_unresolved_contradiction=contradiction,
                gate_flags=["contradiction"] if contradiction else [],
            )
        )

    # 5. status (batch) — fixed order: assign_status precedes check (master §4.3)
    assessments = assign_status(assertions, config)

    # 6. sufficiency (per-assertion) + attach status/confidence; emit Known Gaps on failure
    known_gaps: list[KnownGap] = []
    for a in assertions:
        el = elements[a.element_id]
        suff = check(a, claims_by_id, config)
        el.sufficiency = suff
        assess = assessments.get(a.element_id)
        if assess is not None:
            el.status = assess.status
            el.confidence = ConfidenceBreakdown(
                per_claim_credibility=a.per_claim_credibility,
                independence_groups=a.groups,
                integrity_flags=a.gate_flags,
                assertion_confidence=assess.assertion_confidence,
            )
        if not suff.satisfied:
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
