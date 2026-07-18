"""The location seam: geofence-crossing + location-scope work as pure config (task 10).

Per the locked decision (2026-07-18): build the location axis so a geofence entry/exit tripwire and a
"near a place" scope filter are **config edits, not code** — but keep the demo led by the instance-scoped
Rawalpindi→Rahwali relocation. So these tests prove the primitive parses/arms/fires on synthetic coords
and that no geofence observable is wired into the shipped config (it is a seam + roadmap line).
"""

from __future__ import annotations

from pathlib import Path

from chanakya.config import ConfigStore
from chanakya.observe import compile_trigger, evaluate, within_area
from chanakya.observe.observable import CROSSING
from chanakya.schemas import NodeView, ObservableDef
from tests.observe.conftest import config_with, view

REPO_ROOT = Path(__file__).resolve().parents[3]

# A small area around a synthetic centre; radius is config data, never a code literal (G6).
_ZONE = {"center": [32.0, 72.0], "radius_km": 50}


def _node_at(lat: float, lon: float) -> dict:
    return {"id": "tel_mobile", "type": "unit",
            "location": {"raw": "field", "wgs84_lat": lat, "wgs84_lon": lon}}


def test_within_area_primitive() -> None:
    inside = NodeView.model_validate(_node_at(32.05, 72.05))  # ~7 km from centre
    outside = NodeView.model_validate(_node_at(33.5, 73.5))  # ~200 km from centre
    bare = NodeView.model_validate({"id": "x", "type": "unit"})  # no coord
    assert within_area(inside, _ZONE) is True
    assert within_area(outside, _ZONE) is False
    assert within_area(bare, _ZONE) is None  # honest: no coordinate → indeterminate, not False


def _geofence_obs() -> ObservableDef:
    return ObservableDef.model_validate({
        "observable_id": "obs-geofence-demo",
        "watch_instances": ["tel_mobile"],
        "trigger": {"on": "geofence_crossing", "node_type": "unit", "area": _ZONE,
                    "label": "zone", "anchors_within_hops": 0},
        "severity": "notify",
    })


def test_geofence_crossing_parses_and_fires_on_synthetic_coords() -> None:
    """A watched entity leaving the area fires a crossing inside→outside — pure config, no new code."""
    obs = _geofence_obs()
    assert compile_trigger(obs.trigger).mode == CROSSING

    before = view(nodes=[_node_at(32.05, 72.05)])  # inside
    after = view(nodes=[_node_at(33.5, 73.5)])  # outside
    alerts = evaluate(before, after, config_with(obs))

    assert len(alerts) == 1
    assert alerts[0].before == {"zone": "inside"}
    assert alerts[0].after == {"zone": "outside"}


def test_location_scope_filters_candidates_outside_the_area() -> None:
    """A `within_area` scope filter watches only entities inside the area (same offline primitive)."""
    obs = ObservableDef.model_validate({
        "observable_id": "obs-near-zone-relocation",
        "trigger": {"on": "state_change", "node_type": "unit", "field": "attrs.readiness",
                    "within_area": _ZONE, "anchors_within_hops": 0},
        "severity": "notify",
    })
    # near_unit is inside the zone and changes; far_unit changes too but sits outside → filtered out.
    before = view(nodes=[
        {"id": "near_unit", "type": "unit", "attrs": {"readiness": "low"},
         "location": {"raw": "a", "wgs84_lat": 32.05, "wgs84_lon": 72.05}},
        {"id": "far_unit", "type": "unit", "attrs": {"readiness": "low"},
         "location": {"raw": "b", "wgs84_lat": 33.5, "wgs84_lon": 73.5}},
    ])
    after = view(nodes=[
        {"id": "near_unit", "type": "unit", "attrs": {"readiness": "high"},
         "location": {"raw": "a", "wgs84_lat": 32.05, "wgs84_lon": 72.05}},
        {"id": "far_unit", "type": "unit", "attrs": {"readiness": "high"},
         "location": {"raw": "b", "wgs84_lat": 33.5, "wgs84_lon": 73.5}},
    ])
    alerts = evaluate(before, after, config_with(obs))
    assert [a.subject for a in alerts] == ["near_unit"]


def test_shipped_config_wires_no_geofence_observable() -> None:
    """Honesty: the demo is led by the instance-scoped relocation — no geofence tripwire is shipped."""
    cfg_dir = REPO_ROOT / "config"
    if not (cfg_dir / "observables.yaml").exists():
        return
    observables = ConfigStore.seed_from(cfg_dir).snapshot().observables.observables
    modes_by_on = [o.trigger.get("on") for o in observables]
    assert "geofence_crossing" not in modes_by_on
