"""Shared helpers for the OBSERVE tests — build views/observables without depending on sibling code."""

from __future__ import annotations

from typing import Any

import pytest

from chanakya.schemas import ConfigBundle, GraphView, ObservableDef, ObservablesConfig
from tests.fixtures import loaders


def view(**parts: Any) -> GraphView:
    """A GraphView from loose ``nodes``/``edges``/``events`` dicts (validated)."""
    return GraphView.model_validate(parts)


def relocation_observable(**overrides: Any) -> ObservableDef:
    """The seeded occupancy-relocation tripwire shape (spine/08 §3.8), tweakable per test."""
    base: dict[str, Any] = {
        "observable_id": "obs-relocation",
        "subject": None,
        "watch_instances": [],
        "trigger": {
            "on": "occupancy_state_change",
            "edge_type": "based-at",
            "match_on": ["resolved_unit", "site_instance"],
            "anchors_within_hops": 0,
        },
        "severity": "notify",
    }
    base.update(overrides)
    return ObservableDef.model_validate(base)


def config_with(*observables: ObservableDef, base: ConfigBundle | None = None) -> ConfigBundle:
    """A ConfigBundle carrying the given observables (golden config as the base for lenses)."""
    bundle = base or loaders.golden_config_store().snapshot()
    return bundle.model_copy(update={"observables": ObservablesConfig(observables=list(observables))})


@pytest.fixture
def golden_config() -> ConfigBundle:
    return loaders.golden_config_store().snapshot()


@pytest.fixture
def alert_delta() -> dict[str, Any]:
    return loaders.per_stage("alert_delta")
