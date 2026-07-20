"""Subject-as-lens scoping — **real F0 logic** (master §1 invariant #6, §4.3; gate G10).

A subject is a *query-time lens*, not a partition or a bespoke graph: ``apply_lens`` takes the one
shared view + a ``SubjectLens`` config (anchors + hop bound + materiality filter) and returns a scoped
view. Re-pointing to a new subject is a **config edit**, never new code — which is exactly what G10
enforces (the traversal takes the subject as a param; there is no per-subject table). At ~51 docs this
is a *required* build item so distractor/chaff nodes don't leak into a subject's answer.

Scoping = **N-hops-from-anchors (undirected reachability)** ∩ an optional **materiality filter**. Two
disciplines the design demands and this module now honours:

* **Anchors are resolved, not string-matched (AR-2).** An anchor is a config string; it is mapped to the
  node the analyst meant through the *one shared* :func:`chanakya.resolve.resolve_anchors` ladder
  (literal id → registry alias → alias class), so an alias/spelling drift can't silently re-empty the
  lens. A lens that cannot find its own subject is a **coverage condition and must say so** — the meta
  carries ``anchors_requested``/``anchors_resolved``/``anchors_missing`` + how each matched, and an
  all-miss anchor set returns a *diagnosed* empty view, never a bare one.
* **The materiality filter reads the keys the config actually declares (AR-3).** ``node_types_allow`` +
  the two chokepoint keys, with ``never_drop_indeterminate`` (default true) making the "absence-of-
  evidence ≠ exclusion" guarantee auditable rather than accidental. Unrecognised keys are surfaced in
  ``meta.unrecognised_filter_keys`` (a non-raising drift signal — config is ``extra="allow"`` by design).

Uses NetworkX for traversal (the locked stack).
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from chanakya.resolve import resolve_anchors
from chanakya.schemas import ConfigBundle, GraphView, NodeView, SubjectLens

# Keys ``_passes_materiality`` actually consumes. The gate test in tests/gates/ asserts every key the
# shipped ``config/subjects.yaml`` declares is in (or knowingly pending-removal from) this set, so a
# no-op filter key can never silently ship again. NOT a raising validator — config is extra="allow".
CONSUMED_FILTER_KEYS = frozenset(
    {"min_chokepoint_count", "chokepoint_status_in", "node_types_allow", "never_drop_indeterminate"}
)

# RESOLVE's marker for an endpoint it could not type. A type-indeterminate node is *absence of type
# evidence*, not chaff, so ``never_drop_indeterminate`` shields it from ``node_types_allow`` exactly as it
# shields an UNKNOWN materiality signal — otherwise the type allowlist would silently drop the material
# HT-233 radar (which RESOLVE leaves ``unknown``) out of the demo lens.
_INDETERMINATE_NODE_TYPE = "unknown"


def _passes_materiality(node: NodeView, filt: dict[str, Any]) -> bool:
    """Materiality gate over the keys the config declares. Indeterminate signals are kept (default).

    * ``node_types_allow`` (skip when absent): drop a node whose type is off the allowlist — the real
      chaff protection — **but** keep a type-indeterminate (``unknown``) node when ``never_drop_indeterminate``.
    * ``min_chokepoint_count`` / ``chokepoint_status_in``: drop an explicitly-below/mismatched node; an
      absent (UNKNOWN) attr is kept when ``never_drop_indeterminate``.
    * ``never_drop_indeterminate`` (default true): the "absence-of-evidence ≠ exclusion" guarantee, now
      read explicitly instead of falling out of the control flow by accident.
    """
    if not filt:
        return True
    never_drop = bool(filt.get("never_drop_indeterminate", True))

    allow = filt.get("node_types_allow")
    if allow is not None and node.type not in allow:
        if not (never_drop and node.type == _INDETERMINATE_NODE_TYPE):
            return False

    m = node.materiality
    if "min_chokepoint_count" in filt:
        cc = m.chokepoint_count if m else None
        if cc is None:
            if not never_drop:
                return False
        elif cc < filt["min_chokepoint_count"]:
            return False
    if "chokepoint_status_in" in filt:
        cs = m.chokepoint_status if m else None
        if cs is None:
            if not never_drop:
                return False
        elif cs not in filt["chokepoint_status_in"]:
            return False
    return True


def apply_lens(view: GraphView, subject: SubjectLens, *, config: ConfigBundle | None = None) -> GraphView:
    """Return ``view`` scoped to ``subject`` — N-hops-from-resolved-anchors ∩ materiality filter.

    Anchors are resolved via the shared resolver (``config`` enables registry/alias tiers; ``None`` ⇒
    literal-only, today's behaviour). Resolved anchors are always retained. Edges survive only when *both*
    endpoints do; events survive when any participant does; Known Gaps / alerts follow their related node.
    An anchor set that resolves to nothing yields a **diagnosed** empty view (``meta.anchors_missing``).
    """
    und = nx.Graph()
    for n in view.nodes:
        und.add_node(n.id)
    for e in view.edges:
        und.add_edge(e.source, e.target)

    # AR-2 — resolve each declared anchor to a real view node id (literal → registry alias → alias class).
    resolutions = resolve_anchors(subject.anchors, view, config)
    anchors = {r.node_id for r in resolutions if r.node_id is not None}

    # N-hop reachability (undirected) from every *resolved* anchor.
    reachable: set[str] = set()
    for aid in anchors:
        if aid in und:
            reachable |= set(nx.single_source_shortest_path_length(und, aid, cutoff=subject.max_hops))

    nodes_by_id = {n.id: n for n in view.nodes}
    scoped_ids = {
        nid
        for nid in reachable
        if nid in anchors or _passes_materiality(nodes_by_id[nid], subject.materiality_filter)
    }

    scoped_nodes = [n for n in view.nodes if n.id in scoped_ids]
    scoped_edges = [e for e in view.edges if e.source in scoped_ids and e.target in scoped_ids]
    scoped_events = [ev for ev in view.events if any(p in scoped_ids for p in ev.participants)]
    scoped_gaps = [g for g in view.known_gaps if g.related_ref is None or g.related_ref in scoped_ids]
    scoped_alerts = [a for a in view.alerts if a.subject is None or a.subject in scoped_ids or a.subject == subject.subject_id]

    unrecognised = sorted(set(subject.materiality_filter) - CONSUMED_FILTER_KEYS)

    meta = dict(view.meta)
    meta.update(
        {
            "subject": subject.subject_id,
            "scoped_from_nodes": len(view.nodes),
            # AR-2 diagnostics — a lens must say what it could and could not find (the non-negotiable).
            "anchors_requested": [r.requested for r in resolutions],
            "anchors_resolved": {r.requested: r.node_id for r in resolutions if r.node_id is not None},
            "anchors_missing": [r.requested for r in resolutions if r.node_id is None],
            "anchor_resolution": {r.requested: r.via for r in resolutions if r.via is not None},
            # AR-3 non-raising drift signal — filter keys the code doesn't consume (config is extra="allow").
            "unrecognised_filter_keys": unrecognised,
        }
    )
    return GraphView(
        nodes=scoped_nodes,
        edges=scoped_edges,
        events=scoped_events,
        known_gaps=scoped_gaps,
        alerts=scoped_alerts,
        meta=meta,
    )
