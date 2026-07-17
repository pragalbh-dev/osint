"""Deterministic JSON export of the view — **real F0 logic** (master §4.8; gate G2).

The ``GET /view`` payload. Determinism is enforced structurally so two rebuilds are byte-identical:
elements are sorted by id, and JSON keys are emitted in a stable order. No timestamps or RNG here —
those would break gate G2 (and there is nowhere for them to come from: the view is a pure function of
the logs + config).
"""

from __future__ import annotations

import json

from chanakya.schemas import GraphView


def sorted_view(view: GraphView) -> GraphView:
    """A copy of ``view`` with every collection in a stable order (the determinism guarantee)."""
    return GraphView(
        nodes=sorted(view.nodes, key=lambda n: n.id),
        edges=sorted(view.edges, key=lambda e: e.id),
        events=sorted(view.events, key=lambda ev: ev.id),
        known_gaps=sorted(view.known_gaps, key=lambda g: g.id),
        alerts=sorted(view.alerts, key=lambda a: (a.observable_id, a.fired_ts or "")),
        meta=view.meta,
    )


def view_to_dict(view: GraphView) -> dict:
    """The view as a plain dict (sorted), suitable for ``json.dumps`` or a FastAPI response."""
    return sorted_view(view).model_dump(mode="json")


def view_to_json(view: GraphView, *, indent: int | None = 2) -> str:
    """The view as a deterministic JSON string (sorted keys + sorted elements → byte-identical)."""
    return json.dumps(view_to_dict(view), indent=indent, sort_keys=True, ensure_ascii=False)
