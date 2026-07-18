"""The value-level DSL: operators, dotted field access over view elements, UNKNOWN honesty."""

from __future__ import annotations

import pytest

from chanakya.observe import OPERATORS, evaluate_condition
from chanakya.observe.dsl import MISSING, resolve_field
from chanakya.schemas import EdgeView, NodeView


def _node() -> NodeView:
    return NodeView.model_validate({
        "id": "comp_ht233", "type": "component", "attrs": {"functional_role": "seeker"},
        "materiality": {"chokepoint_count": 2, "substitutability_state": "known-sole-source"},
        "location": {"raw": "Sargodha", "wgs84_lat": 32.05, "wgs84_lon": 72.67, "resolved_place_ref": "place_sargodha"},
    })


def test_resolve_field_walks_pydantic_and_dict() -> None:
    n = _node()
    assert resolve_field(n, "type") == "component"
    assert resolve_field(n, "attrs.functional_role") == "seeker"
    assert resolve_field(n, "materiality.chokepoint_count") == 2
    assert resolve_field(n, "location.resolved_place_ref") == "place_sargodha"


def test_resolve_field_missing_is_distinct_from_none() -> None:
    n = _node()
    assert resolve_field(n, "attrs.nonexistent") is MISSING
    assert resolve_field(n, "materiality.chokepoint_status") is None  # present field, unset → None


@pytest.mark.parametrize(
    ("op", "actual_field", "value", "expected"),
    [
        ("eq", "type", "component", True),
        ("eq", "type", "unit", False),
        ("ne", "type", "unit", True),
        ("ge", "materiality.chokepoint_count", 1, True),
        ("ge", "materiality.chokepoint_count", 3, False),
        ("lt", "materiality.chokepoint_count", 3, True),
        ("eq", "materiality.substitutability_state", "known-sole-source", True),
        ("exists", "location.resolved_place_ref", None, True),
        ("not_exists", "attrs.nonexistent", None, True),
        ("exists", "attrs.nonexistent", None, False),
    ],
)
def test_operators(op: str, actual_field: str, value: object, expected: bool) -> None:
    assert evaluate_condition(_node(), actual_field, op, value) is expected


def test_threshold_on_unknown_never_fires() -> None:
    """A missing/UNKNOWN value never satisfies a threshold — we don't print ignorance as a finding."""
    n = NodeView.model_validate({"id": "x", "type": "component"})  # no materiality
    assert evaluate_condition(n, "materiality.chokepoint_count", "ge", 1) is False


def test_unknown_operator_raises() -> None:
    with pytest.raises(ValueError, match="unknown observable operator"):
        evaluate_condition(_node(), "type", "approximately", "component")


def test_operator_set_is_the_documented_grammar() -> None:
    """Equality / threshold / exists — the spine/09 operator vocabulary (crossing is a delta mode)."""
    assert set(OPERATORS) == {"eq", "ne", "lt", "le", "gt", "ge", "exists", "not_exists"}


def test_edge_target_field() -> None:
    e = EdgeView.model_validate({"id": "e", "type": "based-at", "source": "u", "target": "s1"})
    assert resolve_field(e, "target") == "s1"
