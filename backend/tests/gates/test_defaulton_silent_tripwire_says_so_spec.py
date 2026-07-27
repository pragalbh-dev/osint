"""AH-3, asserted where the ANALYST is — on the booted corpus, through the API the SPA actually reads.

**Why this file exists.** The abstract properties are pinned by ``tests/observe/test_trigger_reachability``
on hand-built views. What cannot be established abstractly is the statement this work was commissioned
over: *on the real running system, does a tripwire that cannot fire say so to a human?* Measured on the
booted corpus before the fix, the answer was no for two of the three shipped observables:

* ``obs-followon-interceptor-order`` waits on a ``replenishes`` edge. The view holds **zero** of them and
  **zero** ``interceptor_stockpile`` nodes. It rendered as an ordinary armed tripwire advertising
  *"watching 66 node(s)"*.
* ``obs-spares-tender-probable-induction`` compiles to ``arm-only`` — no detector exists for its trigger
  form, so it can never emit an alert. Nothing on any list surface said so.

An armed tripwire that cannot fire converts an absence of alerts into an all-clear. That is the
non-negotiable's monitoring case, and a judgement the backend computes but never delivers is the same
defect class as one it never computed.

Corpus-dependent on purpose. The assertions are written as **properties**, not as a snapshot of today's
graph: a verdict may legitimately flip to ``reachable`` the day a document produces the missing link (that
self-healing is the design), but it may never become *unreachable and unstated*.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from chanakya.api import create_app
from chanakya.api.state import build_default_state
from chanakya.observe import GAP_KIND, REACHABLE, reachability_diagnostics
from eval import harness


@pytest.fixture(scope="module")
def booted():
    """The real keyless boot — the same path a reviewer's ``make run`` takes."""
    if not harness.bundles_dir().is_dir():
        pytest.skip(f"no frozen claim bundles at {harness.bundles_dir()}")
    state = build_default_state()
    state.boot()
    return state


@pytest.fixture(scope="module")
def verdicts(booted):
    return {
        row["observable_id"]: row
        for row in reachability_diagnostics(booted.config.snapshot(), booted.view())
    }


def test_every_shipped_observable_gets_a_verdict(verdicts, booted) -> None:
    armed = {o.observable_id for o in booted.config.snapshot().observables.observables}
    assert set(verdicts) == armed, "an armed tripwire with no reachability verdict is an unchecked one"
    assert armed, "the shipped config arms no observables — this spec would be vacuous"


def test_the_arm_only_tripwire_is_not_presented_as_a_quiet_sentry(verdicts) -> None:
    """``obs-spares-tender-probable-induction`` can never alert; that must be stated, not implied.

    Unlike the coverage cases this one cannot self-heal — the trigger form has no detector — so the
    assertion is unconditional, and the gap kind must be the one that needs a human rather than a
    document.
    """
    row = verdicts["obs-spares-tender-probable-induction"]
    assert row["can_fire"] is False
    assert row["gap_kind"] == GAP_KIND["never_fires"] == "engine"
    assert row["warning"] and "all-clear" in row["warning"]
    assert any(m["name"] == "new_claim" for m in row["missing"])


def test_the_followon_tripwire_is_never_unreachable_and_unstated(verdicts) -> None:
    """Written as the property, not the snapshot: it may become reachable, never silently dead.

    On today's frozen corpus this is the ``replenishes`` coverage gap. If a document ever produces one,
    the verdict flips to ``reachable`` and this still passes — which is the point of the design.
    """
    row = verdicts["obs-followon-interceptor-order"]
    if row["can_fire"]:
        return
    assert row["gap_kind"] == "data", "a declared, extractable edge with no coverage is a data gap"
    assert {m["name"] for m in row["missing"]} >= {"replenishes"}
    assert row["warning"] and "replenishes" in row["warning"]


def test_the_hero_relocation_wire_is_not_falsely_declared_dead(verdicts) -> None:
    """The dangerous direction: a false 'unreachable' would tell an analyst to stop trusting it."""
    assert verdicts["obs-basing-relocation"]["status"] == REACHABLE
    assert verdicts["obs-basing-relocation"]["warning"] is None


def test_the_check_discriminates_on_the_real_graph(verdicts) -> None:
    """NON-VACUITY, at system level: fails if everything is blessed (or everything condemned).

    This is how the check would silently die — degrade to a constant and every surface goes back to
    rendering a dead tripwire exactly like a live one, with the tests still green.
    """
    can_fire = [row["can_fire"] for row in verdicts.values()]
    assert any(can_fire), "no shipped tripwire reachable — the check has degraded to condemning all"
    assert not all(can_fire), "every shipped tripwire reachable — the check has degraded to a constant"


def test_no_verdict_says_cannot_fire_without_naming_what_is_missing(verdicts) -> None:
    """"Not reachable" alone is useless to an analyst; the sentence must name the specific thing."""
    for observable_id, row in verdicts.items():
        if row["can_fire"]:
            continue
        assert row["missing"], f"{observable_id}: cannot fire, but names nothing missing"
        assert row["warning"], f"{observable_id}: cannot fire, but says nothing"
        for entry in row["missing"]:
            assert entry["name"] in row["warning"], f"{observable_id}: {entry} not in the sentence"


def test_it_reaches_the_analyst_through_the_read_the_spa_actually_makes(booted) -> None:
    """The whole point: computing the judgement is not delivering it. It must be on the API.

    ``GET /config/observables`` is the read the Watch panel makes to render the armed catalogue — the
    one surface where "3 armed" used to be the same string whether those three could fire or not.
    """
    with TestClient(create_app(booted)) as client:
        body = client.get("/config/observables").json()
    check = body["diagnostics"]["trigger_reachability"]

    assert check["checked"] is True
    assert len(check["observables"]) == len(body["value"]["observables"])
    dead = [row for row in check["observables"] if not row["can_fire"]]
    assert dead, "the measured defect is gone from the API — verify the corpus changed, not the check"
    for row in dead:
        assert row["warning"] and row["missing"]
    # And the diagnostics stay OUT of the round-trip value, so GET → edit → POST is unaffected.
    assert "trigger_reachability" not in body["value"]
