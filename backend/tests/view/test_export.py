"""Unit tests for deterministic JSON export (sorted elements + stable keys)."""

from __future__ import annotations

import json

from chanakya.view import sorted_view, view_to_dict, view_to_json
from tests.fixtures import loaders


def test_elements_are_sorted_by_id() -> None:
    view = sorted_view(loaders.golden_view())
    assert [n.id for n in view.nodes] == sorted(n.id for n in view.nodes)
    assert [e.id for e in view.edges] == sorted(e.id for e in view.edges)


def test_json_is_valid_and_stable() -> None:
    js = view_to_json(loaders.golden_view())
    parsed = json.loads(js)
    assert parsed["meta"]["node_count"] == 5
    assert js == view_to_json(loaders.golden_view())  # stable across calls


def test_view_to_dict_round_trips_through_json() -> None:
    d = view_to_dict(loaders.golden_view())
    assert json.loads(json.dumps(d)) == d
