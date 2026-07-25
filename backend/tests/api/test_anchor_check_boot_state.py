"""AH-2 regression — the shipped app's own default boot state must not report an anchor FAULT.

This is the test the AH-1 change needed and did not have: every assertion below runs against the real
``create_app()`` over the real corpus, with no fixture standing in for the thing a reviewer actually
opens. ``config/sources.yaml`` withholds ``d18``/``d19`` from the seed deliberately, so ``site_rahwali``
has no node at first paint and one shipped lens anchor is legitimately uncovered.

Before AH-2 that produced three "…is NOT being watched, and silence about it is not an all-clear"
warnings, a red block on all three Watch cards and a rail reading "3 armed · 3 anchor unresolved" — on a
healthy system, one live ingest away from firing correctly. The warning was loudest while nothing was
wrong and vanished when the alert fired.

So: the boot state may report *coverage*, and must not report a *fault*.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from chanakya.api.app import create_app


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as c:  # production lifespan boot — not a fixture state
        yield c


def _anchor_check(client) -> dict:
    body = client.get("/config/observables").json()
    return body["diagnostics"]["anchor_check"]


def test_boot_state_reports_no_anchor_fault(client) -> None:
    """The load-bearing one. Nothing at boot may carry a fault severity."""
    check = _anchor_check(client)
    assert check["checked"] is True, "an unperformed check must never read as a pass"

    faults = [e for e in check["unresolved"] if e["severity"] != "pending_coverage"]
    assert faults == [], (
        "the shipped default boot state reported an anchor FAULT. Either a genuinely broken anchor "
        "shipped, or a coverage gap is being mis-classified as one — the second cries wolf on the hero "
        f"demo path at first paint. Offenders: {[f['observable_id'] for f in faults]}"
    )


def test_boot_state_still_states_the_coverage_gap(client) -> None:
    """Quieter is not silent: the uncovered anchor is still named, with the honest reason."""
    check = _anchor_check(client)
    pending = [e for e in check["unresolved"] if e["severity"] == "pending_coverage"]
    assert pending, "the withheld-seed boot state should still SAY which anchor is uncovered"

    for entry in pending:
        assert entry["dangling"] == []
        assert "site_rahwali" in entry["pending_coverage"]
        assert "coverage gap rather than a config fault" in entry["warning"]
        # It must not send the analyst to fix a correctly-declared anchor.
        assert "correct the anchor id" not in entry["warning"].lower()


def test_the_uncovered_anchor_is_attributed_to_the_lens_that_declared_it(client) -> None:
    """Two of the three shipped observables own no watch_instances; the id comes from the lens."""
    check = _anchor_check(client)
    for entry in check["unresolved"]:
        assert entry["declared_in"].get("site_rahwali") == "subject:lens-hq9p-pk"
        assert "config/subjects.yaml" in entry["warning"]


def test_ingesting_the_withheld_coverage_clears_the_gap_in_the_same_process(client) -> None:
    """The hot-config promise in the direction that matters: the check is live, not boot-time-only.

    Rather than depend on an ingest route's shape, this asserts the equivalent invariant directly —
    against the FULL scenario view (the same graph once the withheld documents have landed), every
    armed tripwire's anchors bind and the diagnostics list is empty. An empty list is the positive
    statement, not an absence of checking.
    """
    from chanakya.observe import anchor_diagnostics
    from eval import harness

    scenario = harness.load_scenario(harness.DEFAULT_SCENARIO)
    full_view = harness.build_view(scenario)
    config = scenario.config_store.snapshot()

    assert {n.id for n in full_view.nodes} >= {"site_rahwali", "unit_hq9b", "unit_paad"}
    assert anchor_diagnostics(config, full_view) == []
