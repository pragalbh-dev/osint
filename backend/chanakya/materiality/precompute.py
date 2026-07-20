"""Materiality precompute — chokepoints & substitutability as filterable node attrs (spine/09; C/01).

The fifth SCORE stage, run **last** inside ``rebuild()`` (after status, so it can read the scored view).
Pure, config-driven graph computation — no LLM (gate G1), no scoring literals (gate G6). It materialises
the attrs the retrieval tools filter on (``MaterialityAttrs``): ``chokepoint_count`` / ``chokepoint_status``
/ ``substitutability_state``, each carrying its ``contributing_refs`` so answers still cite the basis.

Criteria (C/01 §"topology nominates; evidence confirms"):

* **#1 sole-source in-degree, three-state gated** — a node reached by exactly one sustainment-function
  edge is nominated; then its ``substitutable-by`` three-state decides: known-sole-source → CONFIRMED,
  **UNKNOWN → CANDIDATE (+ Known Gap)**, known-alternates → not a chokepoint. ``sustained-by`` (a coarse
  rollup) is excluded from the computation.
* **#4 foreign-control severity** — evidence-backed OEM/adversary ``foreign_control`` → confirmed
  severity; UNKNOWN → candidate. #7 **confidence ceiling** — an all-inferred / analog-propagated
  nomination (every supporting edge merely ``possible``) is capped at CANDIDATE.
* **#10 confirmed-vs-candidate separation** — the two are never collapsed: ``chokepoint_count`` counts
  only *confirmed* chokepoints in the sustainment closure; candidates surface via ``chokepoint_status`` +
  a Known Gap. **UNKNOWN is not a chokepoint** — it renders candidate, never printed as sole-source
  (absence of evidence ≠ evidence of absence). A known-alternate carrying ``adversary_denial`` is
  discounted (a seeded fake second-source can't dissolve a real chokepoint).
"""

from __future__ import annotations

from chanakya.ontology import EdgeLaneIndex
from chanakya.schemas import ConfigBundle, EdgeView, GraphView, KnownGap, MaterialityAttrs, NodeView

# Ontology edge roles (names, not scoring numbers — G6). Overridable via config.materiality if present.
_SUSTAINMENT = (
    "supplies-component", "manufactures", "equips", "component-of",
    "exported-by", "design-authority-for",
)  # sustained-by deliberately EXCLUDED (coarse rollup, C/01:163)
_SUBSTITUTABLE_BY = "substitutable-by"
_TO_END = "to"                                  # supplier is the edge's target (e.g. exported-by)
_DEFAULT_FUNCTION_ATTR = "functional_role"      # component attr that partitions sole-source by function
_CONFIRMED, _CANDIDATE, _NONE = "confirmed", "candidate", "none"
_SOLE_SOURCE, _ALTERNATES, _UNKNOWN = "known-sole-source", "known-alternates", "UNKNOWN"
_POSSIBLE = "possible"  # an inferred/candidate edge status (never confirmed)


def _role_edges(config: ConfigBundle) -> tuple[tuple[str, ...], str]:
    materiality = getattr(config, "materiality", None)
    sustainment = getattr(materiality, "sustainment_edges", None) if materiality else None
    substitutable = getattr(materiality, "substitutable_edge", None) if materiality else None
    return tuple(sustainment) if sustainment else _SUSTAINMENT, substitutable or _SUBSTITUTABLE_BY


def _function_attr(config: ConfigBundle) -> str:
    """The node attr that partitions a dependent's sole-source count by *function* (C/01 #1/#9).

    Config-driven (``ontology.materiality.function_attr``); falls back to the declared component
    ``functional_role`` slot. So a variant equipped by one acquisition radar + one engagement radar + one
    launcher exposes three sole-source functions (each a SPOF), not in-degree 3 on one ``equips`` lane;
    a supplier with no such attr degrades gracefully to per-edge-type counting so nothing regresses.
    """
    materiality = getattr(config.ontology, "materiality", None)
    if isinstance(materiality, dict):
        attr = materiality.get("function_attr")
        if isinstance(attr, str) and attr:
            return attr
    return _DEFAULT_FUNCTION_ATTR


def _foreign_control_backed(node: NodeView) -> bool:
    """Evidence-backed foreign control (OEM/adversary) — a concrete value, never the UNKNOWN default."""
    value = node.attrs.get("foreign_control")
    return isinstance(value, str) and value.strip() != "" and value.upper() != _UNKNOWN


def _substitutability(
    node: NodeView, out_sub: list[EdgeView], nodes: dict[str, NodeView]
) -> tuple[str, list[str]]:
    """Three-state substitutability from the node's ``substitutable-by`` edges (+ adversary-denial discount)."""
    if not out_sub:
        return _UNKNOWN, []  # no evidence of an alternate → UNKNOWN (the default; NOT a SPOF finding)
    refs: list[str] = []
    has_real_alternate = False
    for edge in out_sub:
        state = edge.attrs.get("state") or edge.attrs.get("substitutability")
        if isinstance(state, str) and state in (_SOLE_SOURCE, _ALTERNATES, _UNKNOWN):
            refs.extend(edge.claim_ids)
            if state == _SOLE_SOURCE:
                return _SOLE_SOURCE, list(edge.claim_ids)
            if state == _ALTERNATES:
                has_real_alternate = True
            continue
        alt = nodes.get(edge.target)
        # An adversary-denial-flagged "alternate" is discounted — it can't dissolve a real chokepoint.
        if alt is not None and not alt.attrs.get("adversary_denial_flag"):
            has_real_alternate = True
            refs.extend(edge.claim_ids)
    return (_ALTERNATES, refs) if has_real_alternate else (_UNKNOWN, refs)


def _all_inferred(in_edges: list[EdgeView]) -> bool:
    """True if every supporting edge is merely a candidate (status ``possible``) → #7 ceiling → candidate."""
    return bool(in_edges) and all(e.status == _POSSIBLE for e in in_edges)


def precompute(view: GraphView, config: ConfigBundle) -> GraphView:
    """Materialise chokepoint/substitutability attrs on every node (config-driven, cite-preserving).

    Direction (D-P4.7): a sustainment edge has a *supplier* end and a *dependent* end, declared per-edge
    via ``supplier_end`` (``exported-by`` puts the supplier on ``to``, the rest on ``from``). The
    sole-source in-degree TEST is a fact about the **dependent** (does it have exactly one supplier on a
    given function?); the chokepoint FINDING attaches to the **supplier** — the node that fails the
    sustainment if it disappears. Both passes read one accessor (:meth:`EdgeLaneIndex.supplier_end`).
    """
    sustainment, substitutable_edge = _role_edges(config)
    lanes = EdgeLaneIndex(config.ontology)
    function_attr = _function_attr(config)
    nodes = {n.id: n for n in view.nodes}

    def ends(edge: EdgeView) -> tuple[str, str]:
        """``(supplier_id, dependent_id)`` for a sustainment edge — from the ontology, not orientation."""
        if lanes.supplier_end(edge.type) == _TO_END:
            return edge.target, edge.source
        return edge.source, edge.target

    def function_slot(edge: EdgeView, supplier_id: str) -> tuple[str, str | None]:
        """The dependent's supply is counted per ``(edge type, supplier's functional role)`` — 'one
        engagement radar' is a SPOF even when the variant has many other components; role absent →
        per-edge-type so a supplier tier that declares no role never regresses."""
        supplier = nodes.get(supplier_id)
        role = supplier.attrs.get(function_attr) if supplier else None
        return (edge.type, role if isinstance(role, str) and role else None)

    def supplier_type_ok(edge: EdgeView, supplier_id: str) -> bool:
        """The supplier-end node type must be a declared endpoint of this edge — the read-time mirror of
        the write-time re-lane's off-ontology rejection. A ``unit`` sitting in ``equips``'s component slot
        is a mis-lane that slipped past the extractor, not a supplier, and must not be nominated. When the
        edge declares no endpoints (empty) or the node is missing, don't over-reject — keep it."""
        frm, to = lanes.endpoint_types(edge.type)
        allowed = to if lanes.supplier_end(edge.type) == _TO_END else frm
        supplier = nodes.get(supplier_id)
        return not allowed or supplier is None or supplier.type in allowed

    # Index each dependent's sustainment edges by function slot; substitutable-by out-edges per node.
    dep_by_fn: dict[str, dict[tuple[str, str | None], list[EdgeView]]] = {n.id: {} for n in view.nodes}
    sub_out: dict[str, list[EdgeView]] = {n.id: [] for n in view.nodes}
    for edge in view.edges:
        if edge.type in sustainment:
            supplier, dependent = ends(edge)
            if dependent in dep_by_fn and supplier_type_ok(edge, supplier):
                dep_by_fn[dependent].setdefault(function_slot(edge, supplier), []).append(edge)
        elif edge.type == substitutable_edge and edge.source in sub_out:
            sub_out[edge.source].append(edge)

    # #1: a dependent with exactly one supplier on a function slot ⇒ that SUPPLIER is a sole-source SPOF.
    # The finding is collected on the supplier end (not the dependent that carried the in-degree fact).
    supplier_sole: dict[str, list[EdgeView]] = {n.id: [] for n in view.nodes}
    for by_fn in dep_by_fn.values():
        for edges in by_fn.values():
            if len(edges) == 1:
                supplier, _dependent = ends(edges[0])
                if supplier in supplier_sole:
                    supplier_sole[supplier].append(edges[0])

    # Pass 1: per-supplier substitutability + chokepoint classification.
    status_by_node: dict[str, str] = {}
    for node in view.nodes:
        sub_state, sub_refs = _substitutability(node, sub_out[node.id], nodes)
        sole_edges = supplier_sole[node.id]
        contributing: list[str] = list(sub_refs)

        if not sole_edges:
            choke = _NONE
        else:
            for e in sole_edges:
                contributing.extend(e.claim_ids)
                contributing.append(e.id)
            if sub_state == _ALTERNATES:
                choke = _NONE  # a real, non-denial alternate exists → not a single point of failure
            elif sub_state == _SOLE_SOURCE:
                choke = _CONFIRMED
            elif _foreign_control_backed(node) and not _all_inferred(sole_edges):
                choke = _CONFIRMED  # #4 evidence-backed foreign control, not an all-inferred nomination
            else:
                choke = _CANDIDATE  # UNKNOWN substitutability / inferred (#7) → candidate, never sole-source
            if choke == _CONFIRMED and _all_inferred(sole_edges):
                choke = _CANDIDATE  # #7 ceiling: all-inferred cannot confirm

        status_by_node[node.id] = choke
        node.materiality = MaterialityAttrs(
            chokepoint_status=choke,
            substitutability_state=sub_state,
            contributing_refs=sorted(set(contributing)),
        )

    # Pass 2: chokepoint_count = confirmed chokepoints in each node's sustainment-dependency closure
    # (#10: candidates are NOT folded into the confirmed count — they surface via status + Known Gap).
    # Same direction accessor as pass 1: a dependent depends on its supplier end.
    supplies: dict[str, list[str]] = {n.id: [] for n in view.nodes}
    for edge in view.edges:
        if edge.type in sustainment:
            supplier, dependent = ends(edge)
            if dependent in supplies and supplier_type_ok(edge, supplier):
                supplies[dependent].append(supplier)  # dependent depends on supplier

    def confirmed_in_closure(start: str) -> int:
        seen: set[str] = set()
        stack = [start]
        count = 0
        while stack:
            nid = stack.pop()
            if nid in seen:
                continue
            seen.add(nid)
            if status_by_node.get(nid) == _CONFIRMED:
                count += 1
            stack.extend(supplies.get(nid, []))
        return count

    known_gaps: list[KnownGap] = []
    for node in view.nodes:
        assert node.materiality is not None
        node.materiality.chokepoint_count = confirmed_in_closure(node.id)
        # A candidate chokepoint is a known-*unknown* → first-class Known Gap (collection tasking).
        if node.materiality.chokepoint_status == _CANDIDATE:
            known_gaps.append(
                KnownGap(
                    id=f"gap:chokepoint:{node.id}",
                    related_ref=node.id,
                    what_missing=f"confirmed sole-source supplier / substitutability for {node.name or node.id}",
                    observability_ceiling="probable-max",
                    missing_slots=["named_supplier", "substitutability"],
                )
            )

    existing = {g.id for g in view.known_gaps}
    view.known_gaps.extend(g for g in known_gaps if g.id not in existing)
    return view
