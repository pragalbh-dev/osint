"""Shared view-lookup helpers used by more than one route module."""

from __future__ import annotations

from chanakya.schemas import EdgeView, EventView, GraphView, NodeView

Assessed = NodeView | EdgeView | EventView


def find_assessed(view: GraphView, element_id: str) -> Assessed | None:
    """Locate a node, edge, or event by id — all three carry the same assessment fields (_Assessed)."""
    for collection in (view.nodes, view.edges, view.events):
        for element in collection:
            if element.id == element_id:
                return element
    return None
