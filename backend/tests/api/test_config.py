"""``POST /config/{section}`` — hot-config writes + live-fire (API.md acceptance; §1 invariant 3)."""

from __future__ import annotations

import copy

from chanakya.api.state import AppState


def _new_unit_deployment_bundle(state: AppState) -> list[dict]:
    """Clone a unit entity + a based-at triple onto a BRAND-NEW unit → a new based-at edge instance
    (the natural 'a new unit just deployed' delta a relocation/deployment tripwire should catch)."""
    unit_entity = based_at = None
    for claim in state.evidence.replay():
        row = claim.model_dump(mode="json")
        payload = row.get("payload") or {}
        if payload.get("form") == "entity" and payload.get("entity_type") == "unit":
            unit_entity = row
        if payload.get("form") == "triple" and payload.get("predicate") == "based-at":
            based_at = row
    assert unit_entity and based_at, "golden fixture missing a unit entity / based-at triple"

    entity = copy.deepcopy(unit_entity)
    entity["claim_id"] = "api-cfg-unit-bravo"
    entity["payload"]["name"] = "unit_bravo"
    entity["resolved_ref"] = None
    triple = copy.deepcopy(based_at)
    triple["claim_id"] = "api-cfg-bravo-based-at"
    triple["payload"]["subject"] = "unit_bravo"
    triple["payload"]["object"] = "site_north"
    triple["resolved_ref"] = None
    return [entity, triple]


def test_config_credibility_write_bumps_version_and_rebuilds(golden_client, golden_state) -> None:
    cred = golden_state.config.snapshot().credibility.model_dump(mode="json")
    v0 = golden_state.config.version
    r = golden_client.post("/config/credibility", json={"section": "credibility", "value": cred})
    assert r.status_code == 200
    body = r.json()
    assert body["section"] == "credibility" and body["version"] > v0
    # the live config version is reflected everywhere with no restart
    assert golden_client.get("/health").json()["config_version"] == body["version"]


def test_config_unknown_section_404(golden_client) -> None:
    r = golden_client.post("/config/nonsense", json={"section": "nonsense", "value": {}})
    assert r.status_code == 404


def test_config_section_path_body_mismatch_400(golden_client) -> None:
    r = golden_client.post("/config/credibility", json={"section": "ontology", "value": {}})
    assert r.status_code == 400


def test_config_invalid_value_422(golden_client) -> None:
    r = golden_client.post(
        "/config/credibility", json={"section": "credibility", "value": {"thresholds": "not-a-dict"}}
    )
    assert r.status_code == 422


def test_define_observable_then_ingest_fires_it_live(golden_client, golden_state) -> None:
    # Define an unscoped tripwire on new based-at edges — hot-config, no restart.
    obs = {
        "observables": [
            {"observable_id": "obs-api-test", "trigger": {"on": "new_edge", "edge_type": "based-at"},
             "severity": "notify"}
        ]
    }
    r = golden_client.post("/config/observable", json={"section": "observables", "value": obs})
    assert r.status_code == 200

    # Ingest a bundle that creates a NEW based-at edge → the freshly-armed tripwire fires in the response.
    r2 = golden_client.post("/ingest", json={"bundle": _new_unit_deployment_bundle(golden_state)})
    assert r2.status_code == 200
    assert "obs-api-test" in r2.json()["alerts_fired"]
