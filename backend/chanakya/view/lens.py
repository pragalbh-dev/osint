"""Subject-as-lens scoping — **real F0 logic** (master §1 invariant #6, §4.3; gate G10).

A subject is a *query-time lens*, not a partition or a bespoke graph: ``apply_lens`` takes the one
shared view + a ``SubjectLens`` config (anchors + hop bound + materiality filter) and returns a scoped
view. Re-pointing to a new subject is a **config edit**, never new code — which is exactly what G10
enforces (the traversal takes the subject as a param; there is no per-subject table). At ~51 docs this
is a *required* build item so distractor/chaff nodes don't leak into a subject's answer.

Scoping = **N-hops-from-anchors (undirected reachability)** ∩ an optional **materiality filter**. The
hop bound is the load-bearing part and is fully real here; the materiality filter is lenient at F0
(materiality attrs are precomputed by SCORE — unknown attrs are kept, absence-of-evidence ≠ exclusion)
and tightens once SCORE lands. Uses NetworkX for traversal (the locked stack).
"""

from __future__ import annotations

from typing import Any

import networkx as nx

from chanakya.schemas import GraphView, NodeView, SubjectLens


def _passes_materiality(node: NodeView, filt: dict[str, Any]) -> bool:
    """Lenient materiality gate: unknown attrs pass (absence-of-evidence ≠ exclusion)."""
    if not filt:
        return True
    m = node.materiality
    if "min_chokepoint_count" in filt:
        cc = m.chokepoint_count if m else None
        if cc is not None and cc < filt["min_chokepoint_count"]:
            return False
    if "chokepoint_status_in" in filt:
        cs = m.chokepoint_status if m else None
        if cs is not None and cs not in filt["chokepoint_status_in"]:
            return False
    return True


def apply_lens(view: GraphView, subject: SubjectLens) -> GraphView:
    """Return ``view`` scoped to ``subject`` — N-hops-from-anchors ∩ materiality filter.

    Anchors are always retained. Edges survive only when *both* endpoints do; events survive when any
    participant does; Known Gaps / alerts follow their related node.
    """
    und = nx.Graph()
    for n in view.nodes:
        und.add_node(n.id)
    for e in view.edges:
        und.add_edge(e.source, e.target)

    # N-hop reachability (undirected) from every anchor present in the graph.
    reachable: set[str] = set()
    for anchor in subject.anchors:
        if anchor in und:
            reachable |= set(nx.single_source_shortest_path_length(und, anchor, cutoff=subject.max_hops))
    anchors = {a for a in subject.anchors if a in und}

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

    meta = dict(view.meta)
    meta.update({"subject": subject.subject_id, "scoped_from_nodes": len(view.nodes)})
    return GraphView(
        nodes=scoped_nodes,
        edges=scoped_edges,
        events=scoped_events,
        known_gaps=scoped_gaps,
        alerts=scoped_alerts,
        meta=meta,
    )
