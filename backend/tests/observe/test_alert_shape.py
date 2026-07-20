"""The fired Alert matches the frozen §4.2 / product-03 F shape and records before→after (accept. #4)."""

from __future__ import annotations

from chanakya.observe import evaluate
from chanakya.schemas import Alert
from tests.observe.conftest import config_with, relocation_observable, view


def test_alert_has_the_frozen_fields() -> None:
    alert = Alert(observable_id="o", subject="unit_acme",
                  before={"based-at": "site_a"}, after={"based-at": "site_b"}, severity="notify")
    dumped = alert.model_dump()
    assert set(dumped) == {"observable_id", "subject", "before", "after", "severity", "fired_ts",
                           "disposition", "provenance"}
    assert dumped["provenance"] is None  # MON-4: optional + additive — absent unless evidence was attached


def test_fired_alert_records_before_and_after() -> None:
    """A real fired alert carries the change (before→after) and leaves fired_ts for the API to stamp."""
    before = view(edges=[{"id": "e1", "type": "based-at", "source": "unit_acme", "target": "site_a",
                          "edge_instance": "edge:unit_acme:based-at"}])
    after = view(edges=[{"id": "e2", "type": "based-at", "source": "unit_acme", "target": "site_b",
                         "edge_instance": "edge:unit_acme:based-at"}])
    obs = relocation_observable(watch_instances=["unit_acme"])

    alert = evaluate(before, after, config_with(obs))[0]

    assert alert.before == {"based-at": "site_a"}
    assert alert.after == {"based-at": "site_b"}
    assert alert.severity == "notify"
    assert alert.fired_ts is None  # evaluate() stamps no clock; the API stamps on persist
    assert alert.disposition is None  # set later by HITL, not by MONITOR


def test_severity_flows_from_config_not_code() -> None:
    """The alert's severity is whatever the observable declares — no hardcoded severity (G6)."""
    before = view(edges=[{"id": "e1", "type": "based-at", "source": "unit_acme", "target": "site_a",
                          "edge_instance": "edge:unit_acme:based-at"}])
    after = view(edges=[{"id": "e2", "type": "based-at", "source": "unit_acme", "target": "site_b",
                         "edge_instance": "edge:unit_acme:based-at"}])
    obs = relocation_observable(watch_instances=["unit_acme"], severity="critical")

    assert evaluate(before, after, config_with(obs))[0].severity == "critical"
