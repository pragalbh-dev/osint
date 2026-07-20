"""Core evaluator: the seeded relocation fires on the delta, matched on the resolved instance.

Covers MONITOR acceptance criteria #1 (fires on F0's before→after two-view fixture), #2 (match on the
resolved unit×site instance, not a designator string), and the delta discipline (no baseline → no fire;
first-appearance is not a crossing).
"""

from __future__ import annotations

from chanakya.observe import evaluate
from tests.observe.conftest import config_with, relocation_observable, view


def test_seeded_relocation_fires_on_fixture(golden_config, alert_delta) -> None:
    """#1 — obs-relocation fires a based-at occupancy state-change: occupied@A → occupied@B."""
    before = view(**alert_delta["before"])
    after = view(**alert_delta["after"])

    alerts = evaluate(before, after, golden_config)

    assert len(alerts) == 1
    got = alerts[0]
    exp = alert_delta["expected_alert"]
    assert got.observable_id == exp["observable_id"]
    assert got.subject == exp["subject"]
    assert got.before == exp["before"]  # {"based-at": "site_acme_a"}
    assert got.after == exp["after"]  # {"based-at": "site_acme_b"}
    assert got.severity == exp["severity"]


def test_no_baseline_no_alert(golden_config, alert_delta) -> None:
    """A cold boot (prev_view=None) is the reference point, not a change — nothing fires."""
    after = view(**alert_delta["after"])
    assert evaluate(None, after, golden_config) == []


def test_first_appearance_is_not_a_crossing(golden_config) -> None:
    """A unit appearing at a site for the first time is not an occupancy *state-change* (use new_edge)."""
    before = view(nodes=[{"id": "unit_acme", "type": "unit"}])
    after = view(
        nodes=[{"id": "unit_acme", "type": "unit"}, {"id": "site_z", "type": "basing_site"}],
        edges=[{"id": "e1", "type": "based-at", "source": "unit_acme", "target": "site_z",
                "edge_instance": "edge:unit_acme:based-at"}],
    )
    obs = relocation_observable(watch_instances=["unit_acme"])
    assert evaluate(before, after, config_with(obs)) == []


def test_match_on_resolved_instance_survives_designator_variant() -> None:
    """#2a — the unit's designator changes but the resolved edge_instance is the same → still fires.

    Matching is on ``edge_instance``/``source`` (the resolved identity), never the designator string.
    """
    before = view(edges=[{"id": "e:a", "type": "based-at", "source": "unit_acme", "target": "site_a",
                          "edge_instance": "edge:unit_acme:based-at", "attrs": {"designator": "HQ-9B"}}])
    after = view(edges=[{"id": "e:b", "type": "based-at", "source": "unit_acme", "target": "site_b",
                         "edge_instance": "edge:unit_acme:based-at", "attrs": {"designator": "HQ 9B (variant)"}}])
    obs = relocation_observable(watch_instances=["unit_acme"])

    alerts = evaluate(before, after, config_with(obs))

    assert len(alerts) == 1
    assert alerts[0].subject == "unit_acme"
    assert alerts[0].after == {"based-at": "site_b"}


def test_different_instance_does_not_trip_the_wire() -> None:
    """#2b — a relocation of a *different* unit does not fire an observable scoped to unit_acme."""
    before = view(edges=[
        {"id": "a1", "type": "based-at", "source": "unit_acme", "target": "site_a", "edge_instance": "edge:unit_acme:based-at"},
        {"id": "o1", "type": "based-at", "source": "unit_other", "target": "site_c", "edge_instance": "edge:unit_other:based-at"},
    ])
    # only unit_other moves; unit_acme stays put.
    after = view(edges=[
        {"id": "a1", "type": "based-at", "source": "unit_acme", "target": "site_a", "edge_instance": "edge:unit_acme:based-at"},
        {"id": "o2", "type": "based-at", "source": "unit_other", "target": "site_d", "edge_instance": "edge:unit_other:based-at"},
    ])
    obs = relocation_observable(watch_instances=["unit_acme"])

    assert evaluate(before, after, config_with(obs)) == []


def test_watched_unit_moves_while_other_unit_present() -> None:
    """Only the watched instance's crossing fires, even when other units churn in the same view."""
    before = view(edges=[
        {"id": "a1", "type": "based-at", "source": "unit_acme", "target": "site_a", "edge_instance": "edge:unit_acme:based-at"},
        {"id": "o1", "type": "based-at", "source": "unit_other", "target": "site_c", "edge_instance": "edge:unit_other:based-at"},
    ])
    after = view(edges=[
        {"id": "a2", "type": "based-at", "source": "unit_acme", "target": "site_b", "edge_instance": "edge:unit_acme:based-at"},
        {"id": "o2", "type": "based-at", "source": "unit_other", "target": "site_d", "edge_instance": "edge:unit_other:based-at"},
    ])
    obs = relocation_observable(watch_instances=["unit_acme"])

    alerts = evaluate(before, after, config_with(obs))
    assert [a.subject for a in alerts] == ["unit_acme"]


def test_supersede_markers_pick_the_active_edge() -> None:
    """When the after-view holds both the old (superseded) and new based-at edges, fire off the live one."""
    before = view(edges=[{"id": "e:old", "type": "based-at", "source": "unit_acme", "target": "site_a",
                          "edge_instance": "edge:unit_acme:based-at"}])
    after = view(edges=[
        {"id": "e:old", "type": "based-at", "source": "unit_acme", "target": "site_a",
         "edge_instance": "edge:unit_acme:based-at", "superseded_by": "e:new"},
        {"id": "e:new", "type": "based-at", "source": "unit_acme", "target": "site_b",
         "edge_instance": "edge:unit_acme:based-at", "supersedes": "e:old"},
    ])
    obs = relocation_observable(watch_instances=["unit_acme"])

    alerts = evaluate(before, after, config_with(obs))
    assert len(alerts) == 1
    assert alerts[0].before == {"based-at": "site_a"}
    assert alerts[0].after == {"based-at": "site_b"}
