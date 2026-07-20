"""``match_on`` is the observable's declared grouping key — MON-3 / D-P4.10.

The relocation beat only works if a unit's *old* and *new* basing edge are treated as one wire. Two
things have to be true at once:

* the wire is keyed on the part of the edge that is the **identity** (the unit), not the part that is
  the **state** (the site) — otherwise the before and after land in different groups and nothing ever
  crosses; and
* the wire is scoped to the watched instance — the pre-fix bug fired the HQ-9B relocation tripwire on
  a *manufacturer's street address* changing, because an unscoped watch saw the whole graph.

These run on synthetic edges built to the production ``edge_instance`` shape
(``edge:<subject>:<predicate>`` for a functional edge, per ``ontology.build_edge_instance_key``), so
they hold whether or not the corpus currently carries real basing edges.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from chanakya.config import ConfigStore
from chanakya.observe import compile_trigger, evaluate, explain
from chanakya.observe.observable import INSTANCE_KEY
from chanakya.ontology import build_edge_instance_key
from chanakya.schemas import ObservableDef
from tests.observe.conftest import config_with, relocation_observable, view

REAL_CONFIG = Path(__file__).resolve().parents[3] / "config"

# The production key for a FUNCTIONAL edge: the object is dropped, so both sites share one instance.
FUNCTIONAL_KEY = ("from",)


def based_at(edge_id: str, unit: str, site: str, **extra: object) -> dict[str, object]:
    return {
        "id": edge_id, "type": "based-at", "source": unit, "target": site,
        "edge_instance": build_edge_instance_key(unit, "based-at", site, FUNCTIONAL_KEY),
        **extra,
    }


def test_production_key_shape_is_what_the_test_uses() -> None:
    """Guard the fixture against drift: the two sites really do share one edge_instance."""
    a = based_at("e1", "unit_hq9b", "site_rawalpindi")
    b = based_at("e2", "unit_hq9b", "site_rahwali")
    assert a["edge_instance"] == b["edge_instance"] == "edge:unit_hq9b:based-at"


# ── the crossing fires ──────────────────────────────────────────────────────────────────────────

def test_relocation_crossing_fires_with_before_old_site_and_after_new_site() -> None:
    """The flagship beat, on synthetic production-shaped edges: occupied@Rawalpindi → occupied@Rahwali."""
    before = view(
        nodes=[{"id": "unit_hq9b", "type": "unit"}, {"id": "site_rawalpindi", "type": "basing_site"}],
        edges=[based_at("e:2021", "unit_hq9b", "site_rawalpindi", claim_ids=["c-2021"])],
    )
    after = view(
        nodes=[{"id": "unit_hq9b", "type": "unit"}, {"id": "site_rahwali", "type": "basing_site"}],
        edges=[based_at("e:2025", "unit_hq9b", "site_rahwali", claim_ids=["c-2025"])],
    )
    obs = relocation_observable(observable_id="obs-basing-relocation", watch_instances=["unit_hq9b"])

    alerts = evaluate(before, after, config_with(obs))

    assert len(alerts) == 1
    assert alerts[0].subject == "unit_hq9b"
    assert alerts[0].before == {"based-at": "site_rawalpindi"}
    assert alerts[0].after == {"based-at": "site_rahwali"}


def test_crossing_fires_when_the_after_view_still_holds_the_superseded_edge() -> None:
    """The production shape after supersede: both edges present, one retired → fire off the live one."""
    before = view(edges=[based_at("e:2021", "unit_hq9b", "site_rawalpindi", claim_ids=["c-2021"])])
    after = view(edges=[
        based_at("e:2021", "unit_hq9b", "site_rawalpindi", claim_ids=["c-2021"], superseded_by="e:2025"),
        based_at("e:2025", "unit_hq9b", "site_rahwali", claim_ids=["c-2025"], supersedes="e:2021"),
    ])
    obs = relocation_observable(watch_instances=["unit_hq9b"])

    alerts = evaluate(before, after, config_with(obs))
    assert [(a.before, a.after) for a in alerts] == [
        ({"based-at": "site_rawalpindi"}, {"based-at": "site_rahwali"})
    ]


# ── it does NOT over-fire ───────────────────────────────────────────────────────────────────────

def test_unrelated_entity_change_does_not_trip_the_wire() -> None:
    """The pre-fix bug: an unscoped watch fired the HQ-9B tripwire on a manufacturer's address change.

    The watched unit does not move; a *different* subject's ``based-at``-shaped edge does. Nothing fires.
    """
    before = view(edges=[
        based_at("e:2021", "unit_hq9b", "site_rawalpindi"),
        based_at("m:1", "mfr_casic", "addr_beijing_a"),
    ])
    after = view(edges=[
        based_at("e:2021", "unit_hq9b", "site_rawalpindi"),
        based_at("m:2", "mfr_casic", "addr_beijing_b"),  # street address restated → different target
    ])
    obs = relocation_observable(watch_instances=["unit_hq9b"])

    assert evaluate(before, after, config_with(obs)) == []


def test_two_units_move_only_the_watched_one_fires() -> None:
    before = view(edges=[
        based_at("a1", "unit_hq9b", "site_rawalpindi"),
        based_at("o1", "unit_paad", "site_karachi"),
    ])
    after = view(edges=[
        based_at("a2", "unit_hq9b", "site_rahwali"),
        based_at("o2", "unit_paad", "site_lahore"),
    ])
    obs = relocation_observable(watch_instances=["unit_hq9b"])

    assert [a.subject for a in evaluate(before, after, config_with(obs))] == ["unit_hq9b"]


# ── the grouping key is genuinely read from config ──────────────────────────────────────────────

def test_match_on_compiles_to_a_grouping_key_and_a_tracked_state() -> None:
    ct = compile_trigger({"on": "occupancy_state_change", "edge_type": "based-at",
                          "match_on": ["resolved_unit", "site_instance"]})
    assert ct.group_by == ("source",)  # identity = the unit
    assert ct.state_field == "target"  # state = the site (NOT part of the key)


def test_resolved_instance_token_groups_on_the_edge_instance() -> None:
    ct = compile_trigger({"on": "state_change", "edge_type": "based-at", "field": "attrs.readiness",
                          "match_on": ["resolved_instance"]})
    assert ct.group_by == (INSTANCE_KEY,)


def test_no_match_on_keeps_the_legacy_edge_instance_grouping() -> None:
    ct = compile_trigger({"on": "occupancy_state_change", "edge_type": "based-at"})
    assert ct.group_by == ()

    # …and behaviourally: grouping still falls back to edge_instance, so the beat still works.
    before = view(edges=[based_at("e1", "unit_hq9b", "site_rawalpindi")])
    after = view(edges=[based_at("e2", "unit_hq9b", "site_rahwali")])
    obs = ObservableDef.model_validate({
        "observable_id": "obs-no-match-on", "watch_instances": ["unit_hq9b"],
        "trigger": {"on": "occupancy_state_change", "edge_type": "based-at", "anchors_within_hops": 0},
        "severity": "notify",
    })
    assert len(evaluate(before, after, config_with(obs))) == 1


def test_declared_grouping_beats_a_broken_edge_instance() -> None:
    """``match_on: [resolved_unit]`` fires even if the producer wrote the *pre-fix* per-target key.

    This is the point of reading the observable's own declaration rather than trusting one field: the
    detector is not hostage to how a upstream producer happened to mint ``edge_instance``.
    """
    before = view(edges=[{"id": "e1", "type": "based-at", "source": "unit_hq9b",
                          "target": "site_rawalpindi", "edge_instance": "edge:unit_hq9b:based-at:site_rawalpindi"}])
    after = view(edges=[{"id": "e2", "type": "based-at", "source": "unit_hq9b",
                         "target": "site_rahwali", "edge_instance": "edge:unit_hq9b:based-at:site_rahwali"}])
    obs = relocation_observable(watch_instances=["unit_hq9b"])

    alerts = evaluate(before, after, config_with(obs))
    assert len(alerts) == 1
    assert alerts[0].after == {"based-at": "site_rahwali"}


def test_missing_key_part_falls_back_rather_than_merging_unrelated_elements() -> None:
    """A node candidate has no ``source``; it must not collapse into one bucket with every other node."""
    obs = ObservableDef.model_validate({
        "observable_id": "obs-node-state", "watch_instances": ["n1", "n2"],
        "trigger": {"on": "state_change", "node_type": "component", "field": "attrs.role",
                    "match_on": ["resolved_unit"], "anchors_within_hops": 0},
        "severity": "notify",
    })
    before = view(nodes=[{"id": "n1", "type": "component", "attrs": {"role": "a"}},
                         {"id": "n2", "type": "component", "attrs": {"role": "x"}}])
    after = view(nodes=[{"id": "n1", "type": "component", "attrs": {"role": "b"}},
                        {"id": "n2", "type": "component", "attrs": {"role": "x"}}])

    alerts = evaluate(before, after, config_with(obs))
    assert [a.subject for a in alerts] == ["n1"]  # n2 unchanged; the two never merged


@pytest.mark.parametrize("token", ["resolved_unit", "resolved_src", "resolved_contract"])
def test_subject_side_tokens_all_key_on_the_edge_source(token: str) -> None:
    assert compile_trigger({"on": "new_edge", "edge_type": "replenishes",
                            "match_on": [token]}).group_by == ("source",)


# ── the SHIPPED seeded observable, on synthetic production-shaped edges ─────────────────────────

@pytest.mark.skipif(not (REAL_CONFIG / "observables.yaml").exists(), reason="repo-root config/ absent")
def test_shipped_relocation_observable_fires_once_and_only_for_its_subject() -> None:
    """End-to-end on the real ``config/observables.yaml`` — the de-pinned definition still detects.

    The definition names no site and no year (D-P4.10); the sites appear only in the fired alert. The
    decoy is the exact shape of the pre-fix over-fire: a *manufacturer* whose address restated in the
    same delta. One alert, about the unit, citing both sides' claims.
    """
    config = ConfigStore.seed_from(REAL_CONFIG).snapshot()
    seeded = [o for o in config.observables.observables if o.observable_id == "obs-basing-relocation"]
    assert seeded, "the flagship tripwire must stay in the shipped config"
    assert not compile_trigger(seeded[0].trigger).unconsumed  # nothing in it is inert

    before = view(edges=[
        based_at("e:2021", "unit_hq9b", "site_rawalpindi", claim_ids=["c-d07"]),
        based_at("m:1", "mfr_casic", "addr_beijing_a", claim_ids=["c-x"]),
    ])
    after = view(edges=[
        based_at("e:2021", "unit_hq9b", "site_rawalpindi", claim_ids=["c-d07"], superseded_by="e:2025"),
        based_at("e:2025", "unit_hq9b", "site_rahwali", claim_ids=["c-d18"], supersedes="e:2021",
                 status="probable"),
        based_at("m:2", "mfr_casic", "addr_beijing_b", claim_ids=["c-y"]),
    ])

    alerts = evaluate(before, after, config)

    assert len(alerts) == 1
    got = alerts[0]
    assert got.subject == "unit_hq9b"
    assert (got.before, got.after) == ({"based-at": "site_rawalpindi"}, {"based-at": "site_rahwali"})
    assert got.provenance is not None
    assert got.provenance.claim_ids == ["c-d07", "c-d18"]


@pytest.mark.skipif(not (REAL_CONFIG / "observables.yaml").exists(), reason="repo-root config/ absent")
def test_shipped_relocation_observable_names_no_destination() -> None:
    """D-P4.10: a tripwire that names its own destination confirms a relocation, it doesn't detect one."""
    trigger = [o for o in ConfigStore.seed_from(REAL_CONFIG).snapshot().observables.observables
               if o.observable_id == "obs-basing-relocation"][0].trigger
    assert not ({"from_site", "to_site", "window", "unit"} & set(trigger))
    assert "rahwali" not in repr(trigger).lower()
    assert "rawalpindi" not in repr(trigger).lower()


def test_unknown_match_on_token_is_reported_not_silently_dropped() -> None:
    info = explain(ObservableDef.model_validate({
        "observable_id": "obs-typo",
        "trigger": {"on": "occupancy_state_change", "edge_type": "based-at",
                    "match_on": ["resolved_unit", "resolved_gizmo"]},
        "severity": "notify",
    }))
    assert "match_on:resolved_gizmo" in info["unconsumed_keys"]
    assert info["match_on_group_by"] == ["source"]
