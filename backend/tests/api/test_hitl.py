"""``POST /hitl/*`` — adjudication writeback + structural propagation over HTTP (API.md acceptance; G12)."""

from __future__ import annotations


def _edge_status(client) -> dict[str, str]:
    return {e["id"]: e["status"] for e in client.get("/view").json()["edges"]}


def test_hitl_status_demote_propagates_with_no_restart(golden_client) -> None:
    target = "e:unit_acme:based-at:site_north"
    assert _edge_status(golden_client)[target] == "probable"

    r = golden_client.post(
        "/hitl/status",
        json={
            "item_id": "o1",
            "type": "status-override",
            "subject": target,
            "decision": "demote",
            "rationale": "single aggregator source; not yet actionable",
            "actor": "analyst",
        },
    )
    assert r.status_code == 200
    # The POST response is the rebuilt view — the demotion is already visible (no restart).
    after = {e["id"]: e["status"] for e in r.json()["edges"]}
    assert after[target] == "possible"
    # A fresh GET /view sees the same propagated state.
    assert _edge_status(golden_client)[target] == "possible"


def test_hitl_status_unknown_subject_404(golden_client) -> None:
    r = golden_client.post(
        "/hitl/status",
        json={"item_id": "x", "type": "status-override", "subject": "nope", "decision": "demote"},
    )
    assert r.status_code == 404


def test_hitl_invalid_decision_option_400(golden_client) -> None:
    r = golden_client.post(
        "/hitl/status",
        json={
            "item_id": "x",
            "type": "status-override",
            "subject": "e:unit_acme:based-at:site_north",
            "decision": "obliterate",  # not one of promote/demote/reject
        },
    )
    assert r.status_code == 400
    assert "options" in r.json()["detail"]


def test_hitl_merge_no_candidate_edge_404(golden_client) -> None:
    r = golden_client.post(
        "/hitl/merge",
        json={"item_id": "m", "type": "merge", "subject": "same-as:nope:nope", "decision": "accept"},
    )
    assert r.status_code == 404


def test_hitl_alert_no_fired_alert_404(golden_client) -> None:
    r = golden_client.post(
        "/hitl/alert",
        json={"item_id": "a", "type": "alert-disposition", "subject": "obs-nope", "decision": "noise"},
    )
    assert r.status_code == 404
