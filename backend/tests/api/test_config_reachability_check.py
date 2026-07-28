"""AH-3 (API half) — arming a tripwire whose condition cannot occur must be told to you.

The sibling ``test_config_anchor_check`` covers the anchor question ("do this tripwire's anchors bind to
a node?"). This covers the one layer up, and the one the running app was measured getting wrong: **given
that every anchor binds, could the watched condition occur on this graph at all?** A tripwire can resolve
every anchor, report "watching 66 node(s)", and still be waiting on an edge type no document in coverage
produces — armed, quiet, and structurally incapable of firing.

Same two deliberate shapes as the anchor check, for the same reasons:

* it is a **warning, not a rejection** — "tell me the day this becomes observable" is a legitimate thing
  to arm, and a 422 would forbid it. What is not legitimate is arming it and being told nothing;
* it is a **live** check, recomputed per read against the current view — so a coverage gap clears itself
  the moment an ingest produces the missing type, with no restart and no cached verdict.
"""

from __future__ import annotations


def _observables(client) -> dict:
    return client.get("/config/observables").json()


def _write(client, value: dict):
    return client.post("/config/observable", json={"section": "observable", "value": value})


def _unfireable() -> dict:
    """A tripwire watching for an edge type nothing in the golden ontology or view has ever heard of."""
    return {
        "observables": [
            {
                "observable_id": "obs-unfireable",
                "trigger": {"on": "new_edge", "edge_type": "resupplies-with"},
                "severity": "notify",
            }
        ]
    }


def _fireable() -> dict:
    """The golden relocation wire — a based-at crossing the golden view genuinely supports."""
    return {
        "observables": [
            {
                "observable_id": "obs-relocation",
                "subject": "lens-acme",
                "trigger": {
                    "on": "occupancy_state_change",
                    "edge_type": "based-at",
                    "match_on": ["resolved_unit", "site_instance"],
                    "anchors_within_hops": 2,
                },
                "severity": "notify",
            }
        ]
    }


# ── the read surface ─────────────────────────────────────────────────────────────────────────────

def test_get_observables_carries_a_reachability_verdict_per_armed_tripwire(golden_client) -> None:
    """Complete, not problems-only: a Watch card cannot state "it could fire" if nobody said so."""
    body = _observables(golden_client)
    check = body["diagnostics"]["trigger_reachability"]

    assert check["checked"] is True
    assert len(check["observables"]) == len(body["value"]["observables"])
    for row in check["observables"]:
        assert set(row) >= {"observable_id", "status", "can_fire", "gap_kind", "missing", "warning"}


def test_get_observables_does_not_pollute_the_round_trip(golden_client) -> None:
    """``diagnostics`` is derived state — ``value`` must still POST straight back unchanged."""
    body = _observables(golden_client)
    assert "trigger_reachability" not in body["value"]
    assert _write(golden_client, body["value"]).status_code == 200


def test_a_healthy_tripwire_is_not_cried_wolf_over(golden_client) -> None:
    """The dangerous direction. A false 'cannot fire' teaches an analyst to ignore a working wire."""
    assert _write(golden_client, _fireable()).status_code == 200
    rows = _observables(golden_client)["diagnostics"]["trigger_reachability"]["observables"]
    row = next(r for r in rows if r["observable_id"] == "obs-relocation")
    assert row["can_fire"] is True
    assert row["status"] == "reachable"
    assert row["warning"] is None


def test_a_tripwire_that_cannot_fire_is_named_on_the_read(golden_client) -> None:
    assert _write(golden_client, _unfireable()).status_code == 200
    rows = _observables(golden_client)["diagnostics"]["trigger_reachability"]["observables"]
    row = next(r for r in rows if r["observable_id"] == "obs-unfireable")

    assert row["can_fire"] is False
    assert row["gap_kind"] == "modelling"  # the ontology has no such relation — a document won't help
    assert {"kind": "edge_type", "name": "resupplies-with"} in row["missing"]
    assert "resupplies-with" in row["warning"]


# ── the write surface ────────────────────────────────────────────────────────────────────────────

def test_arming_an_unfireable_tripwire_warns_but_does_not_reject(golden_client) -> None:
    """A 200 with a warning: arming ahead of coverage is legitimate; silence about it is not."""
    r = _write(golden_client, _unfireable())
    assert r.status_code == 200
    warnings = r.json()["warnings"]
    assert any("resupplies-with" in w for w in warnings)
    assert any(w.startswith("obs-unfireable:") for w in warnings)


def test_arming_a_fireable_tripwire_produces_no_reachability_warning(golden_client) -> None:
    """NON-VACUITY for the write half: fails if every write warns regardless of the tripwire."""
    warnings = _write(golden_client, _fireable()).json()["warnings"]
    assert not [w for w in warnings if "cannot fire" in w], warnings


def test_the_verdict_is_live_not_cached_from_boot(golden_client) -> None:
    """Hot-config rule: re-arming a different tripwire must re-decide, never replay the boot verdict."""
    _write(golden_client, _unfireable())
    before = _observables(golden_client)["diagnostics"]["trigger_reachability"]["observables"]
    assert [r["can_fire"] for r in before] == [False]

    _write(golden_client, _fireable())
    after = _observables(golden_client)["diagnostics"]["trigger_reachability"]["observables"]
    assert [r["can_fire"] for r in after] == [True]


def test_a_scope_shortfall_the_anchor_check_cannot_see_is_still_reported(golden_client) -> None:
    """The dedup in the write path defers to the anchor check — it must not swallow this case.

    Every anchor here resolves (``site_north`` is a real node), so ``anchor_check`` is silent. But the
    trigger's candidates are ``based-at`` edges, whose watched instance is the **unit** at the other end,
    and ``anchors_within_hops: 0`` keeps the unit out of scope. The tripwire is armed, fully resolved,
    and cannot fire — invisible to the anchor check by construction, which is why the scope branch
    exists. Without this, "defer to the anchor check" could quietly become "never say it".
    """
    value = {
        "observables": [
            {
                "observable_id": "obs-hop-bound-too-tight",
                "watch_instances": ["site_north"],
                "trigger": {
                    "on": "occupancy_state_change",
                    "edge_type": "based-at",
                    "match_on": ["resolved_unit", "site_instance"],
                    "anchors_within_hops": 0,
                },
                "severity": "notify",
            }
        ]
    }
    r = _write(golden_client, value)
    assert r.status_code == 200
    warnings = r.json()["warnings"]
    assert any(w.startswith("obs-hop-bound-too-tight:") for w in warnings), warnings

    row = next(
        x
        for x in _observables(golden_client)["diagnostics"]["trigger_reachability"]["observables"]
        if x["observable_id"] == "obs-hop-bound-too-tight"
    )
    assert row["status"] == "out_of_watch_scope"
    assert row["gap_kind"] == "scope"
    assert row["candidate_count"] == 1  # it found the edge; the scope is what excluded it


def test_the_scope_verdict_is_not_repeated_when_the_anchor_check_already_said_it(golden_client) -> None:
    """One fault, one sentence. Two warnings for one finding is how a surface teaches skimming.

    The anchor sentence is strictly the more useful of the two (it names which anchor, where it was
    declared, and whether it is broken or merely uncovered), and the reachability sentence quotes it
    verbatim anyway — so the write emits the anchor one alone. The verdict itself still stands on the
    READ surface, which the second half of this test pins.
    """
    value = {
        "observables": [
            {
                "observable_id": "obs-typo-scope",
                "watch_instances": ["unit_that_does_not_exist"],
                "trigger": {"on": "occupancy_state_change", "edge_type": "based-at"},
                "severity": "notify",
            }
        ]
    }
    warnings = _write(golden_client, value).json()["warnings"]
    assert len([w for w in warnings if w.startswith("obs-typo-scope:")]) == 1

    row = next(
        x
        for x in _observables(golden_client)["diagnostics"]["trigger_reachability"]["observables"]
        if x["observable_id"] == "obs-typo-scope"
    )
    assert row["can_fire"] is False, "suppressing the duplicate warning must not suppress the verdict"
    assert row["status"] == "out_of_watch_scope"
