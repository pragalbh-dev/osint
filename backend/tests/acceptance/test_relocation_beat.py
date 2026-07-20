"""The relocation beat, end-to-end off a **staged live ingest** (RCA D-P4.5).

The tripwire's whole claim is that an analyst is warned *when new evidence arrives*. So the harness holds
the two 2025 Rahwali overhead passes out of the evidence log, rebuilds, ingests them, rebuilds again, and
runs MONITOR over that before/after pair — a transaction-time delta, no date rewind, no scripted reveal.

These tests assert both halves of the demonstration:

* it **fires** — one alert, on the watched unit, naming the origin and destination sites it read off the
  graph, carrying the claim ids behind both sides (the observable itself names no site — D-P4.10);
* it **stays silent** where it should — no second alert on any other entity, and nothing at all when the
  planted ``d20`` social-media spoof is the arriving evidence instead.
"""

from __future__ import annotations

import pytest

from eval import harness

#: The planted adversarial document: five social posts claiming the battery left Rahwali for Rawalpindi.
SPOOF_DOC = "d20_supersede_spoof"


@pytest.fixture(scope="module")
def alerts(scenario: harness.ScenarioInputs):
    """The alerts a staged ingest of the relocation evidence fires."""
    return harness.fire_relocation_observable(scenario)


def test_staged_ingest_adds_the_relocation_evidence(scenario: harness.ScenarioInputs) -> None:
    """The staged "before" is the same graph minus what those documents taught us — nothing else."""
    before, after = harness.staged_ingest_views(scenario)
    assert before.nodes and before.edges, "staging must hold back documents, not empty the graph"
    assert len(after.nodes) > len(before.nodes)
    assert len(after.edges) > len(before.edges)


def test_relocation_alert_fires_once_with_before_after_and_provenance(alerts: list) -> None:
    """Exactly one alert: the watched unit moved from one site to another, with the claims behind both."""
    assert len(alerts) == 1, [a.observable_id for a in alerts]
    alert = alerts[0]
    assert alert.observable_id == "obs-basing-relocation"
    assert alert.subject == "unit_hq9b"

    before_site = alert.before.get("based-at")
    after_site = alert.after.get("based-at")
    assert before_site and after_site and before_site != after_site

    prov = alert.provenance
    assert prov is not None, "an alert with no provenance is an assertion with no source (G4)"
    assert prov.before_claim_ids and prov.after_claim_ids
    assert set(prov.claim_ids) == set(prov.before_claim_ids) | set(prov.after_claim_ids)
    # The after-side evidence is exactly what we staged in — the alert is traceable to that ingest.
    assert any(
        cid.startswith(doc.replace("_", "-")) for doc in harness.STAGED_RELOCATION_DOCS
        for cid in prov.after_claim_ids
    )


def test_the_only_alert_is_the_watched_unit(alerts: list) -> None:
    """No collateral firing: one subject, and it is the declared watched instance (not, say, a factory
    whose street address resolved differently between the two rebuilds)."""
    assert {a.subject for a in alerts} == {"unit_hq9b"}


def test_spoof_ingest_fires_nothing(scenario: harness.ScenarioInputs) -> None:
    """Staging the planted spoof in produces **no** relocation alert.

    Honest reason: ``d20`` is five unattributable social posts, and the extractor read them as sightings —
    the bundle carries entity + event claims and **no relationship claim**, so nothing ever proposes a
    competing ``based-at`` edge for the tripwire to cross on. The defence here is structural (the spoof
    never reaches the occupancy lane), *not* a credibility score beating it in a contest. The scoring
    gate (D-P4.4's four supersession conditions) is the second line, and is tested at its own layer.
    """
    assert harness.fire_relocation_observable(scenario, staged_docs=(SPOOF_DOC,)) == []
