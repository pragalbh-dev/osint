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
  all-miss anchor set returns a *diagnosed* empty view, never a bare one. **AH-1:** that meta had no
  consumer anywhere, so in practice the analyst still just got a quietly smaller graph. A miss now also
  emits a first-class **Known Gap** (``meta.anchor_warning`` carries the same sentence) — the object this
  system already uses for "what we do not know", which rides on ``GET /view`` and is read by the
  retrieval tools. A lens whose anchors all resolve is unchanged, byte for byte.
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
from chanakya.schemas import ConfigBundle, GraphView, KnownGap, NodeView, SubjectLens

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


def _anchor_warning(
    subject: SubjectLens, missing: list[str], declared: int, dangling: list[str] | None = None
) -> str:
    """The one sentence an analyst reads when a lens cannot find part of its own subject (AH-1).

    **AH-2** — ``dangling`` are the misses that match no view node *and* no declared registry entity.
    A miss that IS a declared entity is a coverage gap the lens will close by itself, so the remedy
    ("correct the anchor id") must not be attached to it; this system's own default boot state withholds
    a document precisely so one shipped anchor is uncovered at first paint.
    """
    named = ", ".join(missing)
    broken = list(dangling or [])
    if broken:
        fix = (
            f" Next step: correct the anchor id in the subject definition — {', '.join(broken)} "
            "match no node and no declared entity."
        )
    else:
        fix = (
            " These name entities that ARE declared in the registry but for which no source has yet "
            "produced a claim, so the lens will pick them up when coverage arrives — no edit needed."
        )
    if declared == 0:
        return (
            f"subject {subject.subject_id!r} declares NO anchors at all, so there is nothing for the lens "
            "to centre on and this view is empty by construction — NOT because there is nothing to "
            "report. Next step: declare at least one anchor in the subject definition."
        )
    if len(missing) >= declared:
        return (
            f"insufficient evidence to scope subject {subject.subject_id!r}: none of its declared "
            f"anchors resolve to a node in this view (unresolved: {named}). This view is empty because "
            f"the lens could not find its subject — NOT because there is nothing to report.{fix}"
        )
    return (
        f"subject {subject.subject_id!r} is partially scoped: {len(missing)} of {declared} declared "
        f"anchors resolve to no node in this view (unresolved: {named}). Anything reachable only from "
        f"those anchors is missing from this view, so its absence here is not evidence of absence.{fix}"
    )


def _anchor_gap(subject: SubjectLens, missing: list[str], warning: str) -> KnownGap:
    """A first-class Known Gap for an unresolved lens anchor — a refusal, not a quietly smaller graph.

    ``confirmable`` because the condition is resolvable by either correcting the anchor id or by coverage
    that creates the entity; ``next_coverage_due`` stays ``None`` because this is a scoping/resolution
    failure with no source cadence behind it, and inventing a date would be the fabrication this system
    forbids. The gap names the fix instead — inside ``warning``, which now carries the remedy that
    actually applies (AH-2), rather than appending a generic one that may be wrong advice.
    """
    return KnownGap(
        id=f"gap-anchor-unresolved-{subject.subject_id}",
        what_missing=(
            f"{warning}"
        ),
        observability_ceiling="confirmable",
        next_coverage_due=None,
        related_ref=None,
        missing_slots=[f"anchor:{a}" for a in missing],
    )


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

    missing = [r.requested for r in resolutions if r.node_id is None]
    # AH-2 — a miss that names a DECLARED registry entity is awaiting coverage, not broken; only the
    # rest earn "correct the anchor id". Registry-free (`config is None`) degrades to "all broken",
    # which is the honest reading when there is no registry to vouch for the id.
    registry = config.entities.as_map() if config is not None else {}
    dangling = [a for a in missing if a not in registry]
    # NB `len(resolutions)`, not `len(anchors)` — `anchors` is the *resolved* set, so using it would
    # call every partial miss a total one. A lens that declares NO anchors resolves nothing and returns
    # an EMPTY view; that is the same silence this whole change exists to kill, so it is diagnosed too.
    if missing or not subject.anchors:
        anchor_warning = _anchor_warning(subject, missing, len(resolutions), dangling)
    else:
        anchor_warning = None
    if anchor_warning is not None:
        # AH-1 — the meta fields below have existed since AR-2 and **nothing consumed them**, so a lens
        # that could not find its own subject still rendered as a smaller-but-confident graph. A Known
        # Gap is this system's own first-class "what we do not know" object: it rides on ``GET /view``,
        # the retrieval tools read it, and it is off the confidence scale rather than a low score. That
        # is where a scoping failure belongs. Emitted ONLY when an anchor misses, so a healthy lens is
        # byte-identical to before.
        scoped_gaps = [_anchor_gap(subject, missing, anchor_warning), *scoped_gaps]

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
    if anchor_warning is not None:
        # One plain sentence, so a consumer does not have to re-derive the meaning from three lists.
        meta["anchor_warning"] = anchor_warning
    return GraphView(
        nodes=scoped_nodes,
        edges=scoped_edges,
        events=scoped_events,
        known_gaps=scoped_gaps,
        alerts=scoped_alerts,
        meta=meta,
    )
