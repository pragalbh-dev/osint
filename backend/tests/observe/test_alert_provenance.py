"""A fired Alert cites its evidence (MON-4 / G4).

Before this, the alert was the only derived artifact in the system with no claim ids on it: the analyst
was told "the unit moved" and had nothing to click. The split before/after claim lists are the point —
"what changed" is only auditable when both the prior state and the new state are separately traceable.
"""

from __future__ import annotations

from chanakya.observe import evaluate
from chanakya.schemas import ObservableDef
from tests.observe.conftest import config_with, relocation_observable, view


def based_at(edge_id: str, site: str, **extra: object) -> dict[str, object]:
    return {"id": edge_id, "type": "based-at", "source": "unit_hq9b", "target": site,
            "edge_instance": "edge:unit_hq9b:based-at", **extra}


def test_relocation_alert_carries_the_claims_behind_both_states() -> None:
    before = view(edges=[based_at("e:2021", "site_rawalpindi", claim_ids=["c-2021a", "c-2021b"])])
    after = view(edges=[based_at("e:2025", "site_rahwali", claim_ids=["c-2025"],
                                 status="probable",
                                 confidence={"assertion_confidence": 0.71})])
    obs = relocation_observable(watch_instances=["unit_hq9b"])

    prov = evaluate(before, after, config_with(obs))[0].provenance

    assert prov is not None
    assert prov.before_claim_ids == ["c-2021a", "c-2021b"]
    assert prov.after_claim_ids == ["c-2025"]
    assert prov.claim_ids == ["c-2021a", "c-2021b", "c-2025"]  # union, before-first, de-duplicated
    assert prov.before_ref == "e:2021"
    assert prov.after_ref == "e:2025"
    assert prov.status == "probable"  # copied off the after-element; MONITOR never derives a score
    assert prov.assertion_confidence == 0.71


def test_shared_claim_is_not_double_counted() -> None:
    before = view(edges=[based_at("e:1", "site_a", claim_ids=["c-shared"])])
    after = view(edges=[based_at("e:2", "site_b", claim_ids=["c-shared", "c-new"])])
    prov = evaluate(before, after, config_with(
        relocation_observable(watch_instances=["unit_hq9b"])))[0].provenance
    assert prov is not None
    assert prov.claim_ids == ["c-shared", "c-new"]


def test_an_element_with_no_claims_reports_empty_not_invented() -> None:
    before = view(edges=[based_at("e:1", "site_a")])
    after = view(edges=[based_at("e:2", "site_b")])
    prov = evaluate(before, after, config_with(
        relocation_observable(watch_instances=["unit_hq9b"])))[0].provenance
    assert prov is not None
    assert prov.claim_ids == []
    assert prov.status is None and prov.assertion_confidence is None


def test_new_element_alert_has_no_before_evidence_but_still_cites_the_after() -> None:
    """An ``exists`` alert has no prior state — the before list is empty, the after list is real."""
    obs = ObservableDef.model_validate({
        "observable_id": "obs-followon", "watch_instances": ["contract_x"],
        "trigger": {"on": "new_edge", "edge_type": "replenishes", "anchors_within_hops": 0},
        "severity": "notify",
    })
    after = view(edges=[{"id": "r1", "type": "replenishes", "source": "contract_x", "target": "stock_y",
                         "edge_instance": "edge:contract_x:replenishes:stock_y", "claim_ids": ["c-tender"]}])

    prov = evaluate(view(), after, config_with(obs))[0].provenance
    assert prov is not None
    assert prov.before_ref is None and prov.before_claim_ids == []
    assert prov.after_claim_ids == ["c-tender"]


def test_provenance_survives_the_json_round_trip() -> None:
    """It has to reach the SPA: the alert serialises with its evidence attached (GET /view)."""
    before = view(edges=[based_at("e:1", "site_a", claim_ids=["c1"])])
    after = view(edges=[based_at("e:2", "site_b", claim_ids=["c2"])])
    alert = evaluate(before, after, config_with(
        relocation_observable(watch_instances=["unit_hq9b"])))[0]
    dumped = alert.model_dump()
    assert dumped["provenance"]["claim_ids"] == ["c1", "c2"]
