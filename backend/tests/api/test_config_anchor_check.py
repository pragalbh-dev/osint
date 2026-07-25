"""AH-1 (API half) — defining a tripwire against an id that resolves to nothing must be told to you.

``POST /config/observable`` validated nothing about anchors, and ``GET /config/observables`` served the
armed catalogue with no statement of whether any of those tripwires could actually fire. So a user who
typo'd an instance id in-app got a 200, an armed-looking card, and months of silence that reads as an
all-clear.

Two deliberate shapes, both tested here:

* it is a **warning, not a rejection** — an anchor may legitimately be armed before the entity that
  satisfies it exists ("arm the tripwire, then ingest the document"), and a 422 would break that;
* it is a **live** check, re-run on every read against the current view — never boot-time-only, and
  never a cached verdict (the hot-config rule).
"""

from __future__ import annotations

import copy


def _observables(client) -> dict:
    return client.get("/config/observables").json()


def _write(client, value: dict):
    return client.post("/config/observable", json={"section": "observable", "value": value})


def _broken_observable() -> dict:
    return {
        "observables": [
            {
                "observable_id": "obs-typo",
                "watch_instances": ["unit_that_does_not_exist"],
                "trigger": {"on": "occupancy_state_change", "edge_type": "based-at"},
                "severity": "notify",
            }
        ]
    }


# ── the read surface ─────────────────────────────────────────────────────────────────────────────

def test_get_observables_carries_a_positive_anchor_check_when_all_resolve(golden_client) -> None:
    """An empty ``unresolved`` list is the POSITIVE statement — not the absence of a statement."""
    body = _observables(golden_client)
    check = body["diagnostics"]["anchor_check"]
    assert check["checked"] is True
    assert check["unresolved"] == []


def test_get_observables_does_not_pollute_the_round_trip(golden_client) -> None:
    """``diagnostics`` is derived state — ``value`` must still POST straight back unchanged."""
    body = _observables(golden_client)
    assert "diagnostics" not in body["value"]
    r = _write(golden_client, body["value"])
    assert r.status_code == 200


def test_get_observables_names_a_tripwire_that_is_watching_nothing(golden_client) -> None:
    assert _write(golden_client, _broken_observable()).status_code == 200

    check = _observables(golden_client)["diagnostics"]["anchor_check"]
    assert [u["observable_id"] for u in check["unresolved"]] == ["obs-typo"]
    problem = check["unresolved"][0]
    assert problem["unresolved_anchors"] == ["unit_that_does_not_exist"]
    assert problem["watching_nothing"] is True
    assert "unit_that_does_not_exist" in problem["warning"]
    assert "all-clear" in problem["warning"]


# ── the write surface ────────────────────────────────────────────────────────────────────────────

def test_arming_a_typod_anchor_warns_but_does_not_reject(golden_client) -> None:
    """The judgement call, pinned: accepted (an anchor may precede its entity) and loudly flagged."""
    r = _write(golden_client, _broken_observable())
    assert r.status_code == 200, "a hard rejection would break arm-then-ingest"
    warnings = r.json()["warnings"]
    assert len(warnings) == 1
    assert warnings[0].startswith("obs-typo:")
    assert "unit_that_does_not_exist" in warnings[0]


def test_arming_a_good_anchor_warns_about_nothing(golden_client) -> None:
    """No cry-wolf: the shipped catalogue writes back clean."""
    r = _write(golden_client, _observables(golden_client)["value"])
    assert r.status_code == 200
    assert r.json()["warnings"] == []


def test_the_check_is_live_not_boot_time(golden_client, golden_state) -> None:
    """Hot-config: the same running process must change its verdict when the graph changes.

    Arm against an id no node carries → flagged. Ingest a claim that creates a node under that id →
    the same tripwire clears itself on the very next read, with no restart and no cache to bust.
    """
    # The id RESOLVE will mint for the entity below — declared here *before* anything carries it, which
    # is the legitimate arm-then-ingest workflow the check must not reject.
    ghost = "ent:unit:unit_ghost"
    value = copy.deepcopy(_broken_observable())
    value["observables"][0]["watch_instances"] = [ghost]
    assert _write(golden_client, value).json()["warnings"], "must flag before the entity exists"

    # Create the entity in-flight, exactly as an ingest would.
    entity = None
    for claim in golden_state.evidence.replay():
        row = claim.model_dump(mode="json")
        if (row.get("payload") or {}).get("form") == "entity" and row["payload"].get("entity_type") == "unit":
            entity = row
            break
    assert entity, "golden fixture missing a unit entity"
    new = copy.deepcopy(entity)
    new["claim_id"] = "api-anchor-ghost"
    new["payload"]["name"] = "unit_ghost"  # RESOLVE mints `ent:unit:unit_ghost` from this
    new["resolved_ref"] = None
    assert golden_client.post("/ingest", json={"bundle": [new]}).status_code == 200

    check = _observables(golden_client)["diagnostics"]["anchor_check"]
    ids = [u["observable_id"] for u in check["unresolved"]]
    assert "obs-typo" not in ids, (
        "a live check must clear itself once coverage creates the entity — same process, no restart"
    )


def test_other_sections_carry_no_anchor_check(golden_client) -> None:
    """The check belongs to observables; other sections must not grow a meaningless empty verdict."""
    assert golden_client.get("/config/credibility").json()["diagnostics"] == {}
