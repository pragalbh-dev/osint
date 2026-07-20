"""``GET|POST /config/{section}`` — hot-config reads + writes + live-fire (API.md acceptance; §1 inv. 3)."""

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


# ── GET /config/{section} — the read half of the hot-config seam ──────────────────────────────


def test_config_get_returns_live_section_with_version(golden_client, golden_state) -> None:
    r = golden_client.get("/config/credibility")
    assert r.status_code == 200
    body = r.json()
    assert body["section"] == "credibility"
    assert body["version"] == golden_state.config.version
    # served from the live store, verbatim — no bespoke DTO, so a GET round-trips into a POST
    assert body["value"] == golden_state.config.snapshot().credibility.model_dump(mode="json")


def test_config_get_every_section_is_readable(golden_client) -> None:
    """No section is withheld — config/ holds no secrets (those live in .env), and a config editor
    that cannot read a section cannot edit it."""
    from chanakya.schemas import CONFIG_SECTIONS

    for name in CONFIG_SECTIONS:
        r = golden_client.get(f"/config/{name}")
        assert r.status_code == 200, name
        assert r.json()["section"] == name


def test_config_get_accepts_the_same_singular_aliases_as_post(golden_client) -> None:
    """Read and write share one section vocabulary — /config/observable == /config/observables."""
    singular = golden_client.get("/config/observable").json()
    plural = golden_client.get("/config/observables").json()
    assert singular == plural
    assert singular["section"] == "observables"


def test_config_get_unknown_section_404(golden_client) -> None:
    r = golden_client.get("/config/nonsense")
    assert r.status_code == 404
    assert "available" in r.json()["detail"]


def test_config_get_exposes_the_armed_observable_catalogue(golden_client, golden_state) -> None:
    """The rail's 'watching N' count: armed tripwires are knowable BEFORE any of them fires.
    Until this route existed only the fired alert feed was readable, so a cold boot read as 0 —
    which said 'nothing is being monitored' about a system that was monitoring three things."""
    value = golden_client.get("/config/observables").json()["value"]
    ids = [o["observable_id"] for o in value["observables"]]
    assert ids, "config should ship at least one armed observable"
    assert ids == [o.observable_id for o in golden_state.config.snapshot().observables.observables]
    # ...and this is knowable with an empty alert feed, i.e. nothing has fired yet
    assert golden_client.get("/view").json()["alerts"] == []


def test_config_get_reflects_a_post_with_no_restart(golden_client) -> None:
    """THE hot-config test: a write through the API is visible to the very next read, same process,
    no restart — and the version the read reports is the one the write returned (spine/09)."""
    before = golden_client.get("/config/observables").json()
    obs = {
        "observables": [
            *before["value"]["observables"],
            {
                "observable_id": "obs-hot-read-check",
                "trigger": {"on": "new_edge", "edge_type": "based-at"},
                "severity": "notify",
            },
        ]
    }
    w = golden_client.post("/config/observable", json={"section": "observables", "value": obs})
    assert w.status_code == 200

    after = golden_client.get("/config/observables").json()
    assert after["version"] == w.json()["version"] > before["version"]
    ids = [o["observable_id"] for o in after["value"]["observables"]]
    assert "obs-hot-read-check" in ids
    # read-modify-write preserved everything that was already armed
    assert {o["observable_id"] for o in before["value"]["observables"]} <= set(ids)


def test_config_read_modify_write_round_trip_of_one_credibility_weight(golden_client) -> None:
    """The frontend's blocked flow, end to end: GET the section, change ONE field, POST it back —
    and nothing else in the section is collateral damage."""
    read = golden_client.get("/config/credibility").json()
    value = read["value"]
    key = next(iter(value["factor_weights"]))
    edited = {**value, "factor_weights": {**value["factor_weights"], key: 0.99}}

    w = golden_client.post(
        "/config/credibility",
        json={"section": "credibility", "value": edited, "if_version": read["version"]},
    )
    assert w.status_code == 200

    after = golden_client.get("/config/credibility").json()["value"]
    assert after["factor_weights"][key] == 0.99
    for section_key, original in value.items():
        if section_key != "factor_weights":
            assert after[section_key] == original, f"{section_key} was clobbered"


def test_config_write_with_stale_if_version_409s(golden_client) -> None:
    read = golden_client.get("/config/credibility").json()
    r = golden_client.post(
        "/config/credibility",
        json={"section": "credibility", "value": read["value"], "if_version": read["version"] - 1},
    )
    assert r.status_code == 409
    assert r.json()["detail"]["current"] == read["version"]


def test_config_write_without_if_version_is_unguarded(golden_client) -> None:
    """Backward compatibility: the guard is opt-in, so the pre-existing write contract still works."""
    read = golden_client.get("/config/credibility").json()
    r = golden_client.post("/config/credibility", json={"section": "credibility", "value": read["value"]})
    assert r.status_code == 200


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
