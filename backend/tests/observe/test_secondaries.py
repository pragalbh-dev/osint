"""Config-only observables: the DATA-C secondaries (and any new tripwire) load + arm with no code.

Covers acceptance #3/#6: a secondary observable (``replenishes`` follow-on order; spares tender →
probable-induction) parses, compiles, and arms with **no bespoke branch** — proving the engine is
declarative, not hardcoded. Also proves an arbitrary *new* tripwire an analyst invents (a chokepoint
threshold over a precomputed materiality attr) works purely from config.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from chanakya.config import ConfigStore
from chanakya.observe import arm, compile_trigger, explain
from chanakya.observe.observable import ARM_ONLY, CROSSING, EXISTS, MATCH
from chanakya.schemas import ObservableDef
from tests.observe.conftest import config_with, view

REPO_ROOT = Path(__file__).resolve().parents[3]
REAL_CONFIG = REPO_ROOT / "config"


@pytest.mark.skipif(not (REAL_CONFIG / "observables.yaml").exists(), reason="repo-root config/ absent")
def test_datac_observables_all_parse_and_compile() -> None:
    """The real DATA-C config/observables.yaml — every entry parses and compiles with no per-obs code."""
    store = ConfigStore.seed_from(REAL_CONFIG)
    observables = store.snapshot().observables.observables
    ids = {o.observable_id for o in observables}
    assert {"obs-basing-relocation", "obs-followon-interceptor-order",
            "obs-spares-tender-probable-induction"} <= ids

    modes = {o.observable_id: compile_trigger(o.trigger).mode for o in observables}
    assert modes["obs-basing-relocation"] == CROSSING  # the flagship fires on the view delta
    assert modes["obs-followon-interceptor-order"] == EXISTS  # a new `replenishes` edge appearing
    # a new_claim (source-class) tripwire lives in the evidence log, not the view → arm-only (honest).
    assert modes["obs-spares-tender-probable-induction"] == ARM_ONLY


def test_followon_interceptor_order_arms_via_backscan() -> None:
    """The ``replenishes`` new-edge secondary arms and back-scans an already-present matching edge."""
    obs = ObservableDef.model_validate({
        "observable_id": "obs-followon-interceptor-order",
        "trigger": {"on": "new_edge", "edge_type": "replenishes"},
        "severity": "notify",
    })
    current = view(edges=[{"id": "r1", "type": "replenishes", "source": "contract_x",
                           "target": "stock_y", "edge_instance": "edge:contract_x:replenishes:stock_y"}])
    armed = arm(obs, current, config_with(obs))
    assert len(armed) == 1
    assert armed[0].observable_id == "obs-followon-interceptor-order"


def test_arm_only_observable_arms_but_does_not_fire() -> None:
    """A new_claim tripwire parses + arms but cannot fire from a view delta — and says why (honest)."""
    obs = ObservableDef.model_validate({
        "observable_id": "obs-spares-tender-probable-induction",
        "trigger": {"on": "new_claim", "source_class": "customs-tender", "target_status_ceiling": "probable"},
        "severity": "notify",
    })
    info = explain(obs)
    assert info["fires_from_view_delta"] is False
    assert "evidence log" in (info["arm_only_reason"] or "")
    assert arm(obs, view(), config_with(obs)) == []  # arms silently; no view-delta fire


def test_new_analyst_tripwire_needs_no_code() -> None:
    """An analyst invents a chokepoint-threshold tripwire over a precomputed attr — config only, it fires.

    Generic ``on: ge`` + ``field`` proves the DSL is not hardcoded to the seeded triggers.
    """
    obs = ObservableDef.model_validate({
        "observable_id": "obs-chokepoint-emerges",
        "watch_instances": ["comp_ht233"],
        "trigger": {"on": "ge", "node_type": "component",
                    "field": "materiality.chokepoint_count", "value": 1, "anchors_within_hops": 0},
        "severity": "notify",
    })
    assert compile_trigger(obs.trigger).mode == MATCH
    before = view(nodes=[{"id": "comp_ht233", "type": "component",
                          "materiality": {"chokepoint_count": 0}}])
    after = view(nodes=[{"id": "comp_ht233", "type": "component",
                         "materiality": {"chokepoint_count": 2}}])
    from chanakya.observe import evaluate
    alerts = evaluate(before, after, config_with(obs))
    assert len(alerts) == 1
    assert alerts[0].subject == "comp_ht233"
    assert alerts[0].after == {"materiality.chokepoint_count": 2}
