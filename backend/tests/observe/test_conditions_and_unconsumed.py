"""The generic condition block + the no-silent-drop rule for trigger keys (MON-1).

Two things the trigger grammar owes an analyst:

* **Anything a bespoke key would have said is expressible generically.** The seeded observable used to
  carry ``from_site`` / ``to_site`` / ``window``, all of them inert. The replacement is not three more
  keys — it is ``where_before`` / ``where_after`` / ``where_change``, evaluated by the *existing* DSL
  operators, so the next tripwire an analyst invents needs no code either.
* **A key that isn't read must say so.** ``ConfigModel`` is ``extra="allow"`` by design (hot-config
  writes), so the schema cannot reject a stray key; ``explain()`` — which the proposer already pipes to
  the analyst's confirm screen — has to show the drop instead.
"""

from __future__ import annotations

import pytest

from chanakya.observe import compile_trigger, evaluate, explain
from chanakya.schemas import ObservableDef
from tests.observe.conftest import config_with, view


def relocation(**trigger: object) -> ObservableDef:
    base = {"on": "occupancy_state_change", "edge_type": "based-at",
            "match_on": ["resolved_unit", "site_instance"], "anchors_within_hops": 0}
    base.update(trigger)
    return ObservableDef.model_validate({
        "observable_id": "obs-cond", "watch_instances": ["unit_hq9b"],
        "trigger": base, "severity": "notify",
    })


def edge(edge_id: str, site: str, **extra: object) -> dict[str, object]:
    return {"id": edge_id, "type": "based-at", "source": "unit_hq9b", "target": site,
            "edge_instance": "edge:unit_hq9b:based-at", **extra}


BEFORE = view(edges=[edge("e:2021", "site_rawalpindi", attrs={"as_of": "2021-06-01"})])
AFTER = view(edges=[edge("e:2025", "site_rahwali", attrs={"as_of": "2025-05-01"})])


# ── where_after / where_before: what from_site & to_site used to try to say ─────────────────────

def test_where_after_restricts_the_destination() -> None:
    assert len(evaluate(BEFORE, AFTER, config_with(
        relocation(where_after={"field": "target", "op": "eq", "value": "site_rahwali"})))) == 1
    assert evaluate(BEFORE, AFTER, config_with(
        relocation(where_after={"field": "target", "op": "eq", "value": "site_elsewhere"}))) == []


def test_where_before_restricts_the_origin() -> None:
    assert len(evaluate(BEFORE, AFTER, config_with(
        relocation(where_before={"field": "target", "value": "site_rawalpindi"})))) == 1
    assert evaluate(BEFORE, AFTER, config_with(
        relocation(where_before={"field": "target", "value": "site_elsewhere"}))) == []


def test_where_change_requires_the_named_field_to_differ() -> None:
    """Fire only if the observation date *also* moved — the delta leg, plus an optional new-value test.

    (The DSL's ``ge``/``le`` are numeric comparators by design, so a date bound is expressed as an
    equality/change test, not a string threshold.)
    """
    assert len(evaluate(BEFORE, AFTER, config_with(
        relocation(where_change={"field": "attrs.as_of", "op": "eq", "value": "2025-05-01"})))) == 1
    # changed, but the new value fails the extra test → no fire.
    assert evaluate(BEFORE, AFTER, config_with(
        relocation(where_change={"field": "attrs.as_of", "op": "eq", "value": "2030-01-01"}))) == []
    # same field value on both sides → not a change → no fire, even though the site moved.
    stale_after = view(edges=[edge("e:2025", "site_rahwali", attrs={"as_of": "2021-06-01"})])
    assert evaluate(BEFORE, stale_after, config_with(
        relocation(where_change={"field": "attrs.as_of"}))) == []


def test_a_block_needing_a_prior_state_never_fires_without_one() -> None:
    """No prior element = we cannot testify to the prior state; the gate fails closed (no invention)."""
    obs = ObservableDef.model_validate({
        "observable_id": "obs-new-edge-gated", "watch_instances": ["unit_hq9b"],
        "trigger": {"on": "new_edge", "edge_type": "based-at", "anchors_within_hops": 0,
                    "where_before": {"field": "target", "value": "site_rawalpindi"}},
        "severity": "notify",
    })
    assert evaluate(view(), AFTER, config_with(obs)) == []


def test_where_after_also_gates_a_new_edge() -> None:
    obs = ObservableDef.model_validate({
        "observable_id": "obs-new-edge-gated", "watch_instances": ["unit_hq9b"],
        "trigger": {"on": "new_edge", "edge_type": "based-at", "anchors_within_hops": 0,
                    "where_after": {"field": "target", "value": "site_rahwali"}},
        "severity": "notify",
    })
    assert len(evaluate(view(), AFTER, config_with(obs))) == 1


def test_condition_blocks_reuse_the_existing_dsl_operators() -> None:
    """A comparator the DSL doesn't know is rejected at compile time, not silently ignored."""
    with pytest.raises(ValueError, match="unknown where_after operator"):
        compile_trigger({"on": "occupancy_state_change", "edge_type": "based-at",
                         "where_after": {"field": "target", "op": "sorta_like", "value": "x"}})


def test_malformed_condition_is_rejected() -> None:
    with pytest.raises(ValueError, match="must be a mapping with a 'field'"):
        compile_trigger({"on": "new_edge", "edge_type": "based-at", "where_after": ["site_rahwali"]})


# ── unconsumed keys are surfaced, never dropped in silence ──────────────────────────────────────

def test_dead_trigger_keys_are_reported_on_the_compiled_trigger() -> None:
    """The exact keys the seeded observable used to carry — inert, and now visibly so."""
    ct = compile_trigger({"on": "occupancy_state_change", "edge_type": "based-at",
                          "match_on": ["resolved_unit", "site_instance"], "anchors_within_hops": 2,
                          "unit": "unit_hq9b", "from_site": "site_rawalpindi",
                          "to_site": "site_rahwali", "window": "2025"})
    assert set(ct.unconsumed) == {"unit", "from_site", "to_site", "window"}


def test_explain_warns_the_analyst_about_unconsumed_keys() -> None:
    info = explain(ObservableDef.model_validate({
        "observable_id": "obs-drifted",
        "trigger": {"on": "occupancy_state_change", "edge_type": "based-at", "to_site": "site_x"},
        "severity": "notify",
    }))
    assert info["unconsumed_keys"] == ["to_site"]
    assert "to_site" in info["unconsumed_warning"]


def test_consumed_keys_are_not_reported_as_unconsumed() -> None:
    ct = compile_trigger({"on": "ge", "node_type": "component", "field": "materiality.chokepoint_count",
                          "value": 1, "anchors_within_hops": 0, "label": "chokepoints",
                          "match_on": ["resolved_instance"]})
    assert ct.unconsumed == ()


def test_explain_reports_the_compiled_conditions() -> None:
    info = explain(relocation(where_after={"field": "target", "op": "eq", "value": "site_rahwali"}))
    assert info["conditions"]["where_after"] == ["target eq 'site_rahwali'"]
    assert info["tracked_state_field"] == "target"
