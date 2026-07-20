"""The **held-back boot seed** — the reviewer's live-ingest demo, asserted end-to-end (P4 / G2).

``config/sources.yaml`` → ``withheld_from_seed`` names documents the boot seed skips, so the app stands
up in the state that *precedes* their arrival. That is the whole basis of the monitoring claim: an alert
means "new evidence arrived", which cannot be shown if the evidence is already in the graph at boot.
This module pins both halves against silent regression:

* the **before**-state is coherent — the unit is still at its old site, not stale (nothing has superseded
  it yet), no new-site basing edge, no supersession, and **zero** alerts;
* holding a document back holds back **everything derived from it** — a before-graph carrying an
  inference whose premises never arrived would be incoherent;
* ingesting the withheld bundles through the *real* keyless ``POST /ingest`` moves the graph to the
  after-state and fires **exactly one** alert with both sides' provenance — twice, identically (G2).

These run against the real ``config/`` + ``corpus/`` via ``create_app()`` (no injected fixture state), so
they exercise ``build_default_state`` + the lifespan boot — the production path a reviewer hits.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from chanakya import settings
from chanakya.api import create_app
from chanakya.api.state import resolve_withheld_docs
from chanakya.config import ConfigStore
from chanakya.ingest.seed import bundle_belongs_to_doc

# The seeded relocation beat: the watched unit and the two sites it moves between. Read off the graph
# here (never off ``answer_key.json`` — the pipeline and its tests never read the oracle).
WATCHED_UNIT = "unit_hq9b"
ORIGIN_SITE = "site_rawalpindi"
DESTINATION_SITE = "site_rahwali"


def _based_at(view: dict, source: str) -> dict[str, dict]:
    """``target → edge`` for every ``based-at`` edge leaving ``source``."""
    return {e["target"]: e for e in view["edges"] if e["type"] == "based-at" and e["source"] == source}


@pytest.fixture(scope="module")
def withheld() -> list[str]:
    return resolve_withheld_docs(ConfigStore.seed_from(settings.config_dir()))


def test_config_declares_the_withheld_documents(withheld: list[str]) -> None:
    """The withholding is *declared*, not hardcoded — a reviewer can read what is missing and why."""
    assert withheld, "config/sources.yaml must declare withheld_from_seed for the live-ingest demo"
    assert "d18_rahwali_pass1" in withheld and "d19_rahwali_confirm" in withheld


def test_derived_bundles_ride_with_their_source_document() -> None:
    """Excluding a document excludes what was inferred *from* it — one shared grouping rule."""
    assert bundle_belongs_to_doc("d18_rahwali_pass1.json", "d18_rahwali_pass1")
    assert bundle_belongs_to_doc("d18_rahwali_pass1__basing.json", "d18_rahwali_pass1")
    assert not bundle_belongs_to_doc("d18_rahwali_pass1.json", "d19_rahwali_confirm")
    # A name that merely starts with the same prefix is a *different* document, not a derivation.
    assert not bundle_belongs_to_doc("d18_rahwali_pass1b.json", "d18_rahwali_pass1")


def test_boot_withholds_declared_documents_from_the_seed(withheld: list[str]) -> None:
    """No claim from a withheld document (or its enrichments) is in the graph at boot."""
    with TestClient(create_app()) as client:
        claim_ids = {cid for e in client.get("/view").json()["edges"] for cid in (e["claim_ids"] or [])}
    # Claim ids are minted from the doc id with ``_`` → ``-`` (``dedup.assign_claim_ids``).
    for doc in withheld:
        prefix = doc.replace("_", "-")
        assert not [cid for cid in claim_ids if cid.startswith(prefix)], f"{doc} leaked into the seed"


def test_before_state_is_coherent() -> None:
    """The boot graph is the honest "before": unit still at the origin site, nothing superseded, quiet.

    Not-stale matters: staleness here would mean something newer displaced the assertion, and nothing
    has. The graph must read as "this is what we know", never as "this is what we knew".
    """
    with TestClient(create_app()) as client:
        assert client.get("/health").status_code == 200
        view = client.get("/view").json()

    assert view["nodes"] and view["edges"], "withholding must stage the graph, not empty it"
    edges = _based_at(view, WATCHED_UNIT)
    origin = edges.get(ORIGIN_SITE)
    assert origin is not None, "the before-state must still hold the unit at its original site"
    assert origin["status"] != "stale", "nothing has superseded it yet — it must not read as stale"
    assert origin["superseded_by"] is None
    assert DESTINATION_SITE not in edges, "the relocation edge must not exist before its evidence lands"
    assert not [e for e in view["edges"] if e["type"] == "supersedes"]
    assert (view.get("alerts") or []) == [], "an alert at boot would be a firing with no arrival"


def test_pending_endpoint_lists_the_withheld_documents_and_serves_their_bundles(
    withheld: list[str],
) -> None:
    """The withheld bundles ship and are reachable — a reviewer needs no repo checkout, key or network."""
    with TestClient(create_app()) as client:
        listing = client.get("/pending").json()
        assert [d["doc_id"] for d in listing["documents"]] == withheld
        for doc in listing["documents"]:
            assert doc["available"] is True and doc["claim_count"] > 0
            assert doc["ingested"] is False, "a withheld document has not arrived at boot"
            # The derived enrichment bundle is released with its source document, never apart from it.
            assert all(bundle_belongs_to_doc(name, doc["doc_id"]) for name in doc["bundles"])
            body = client.get(f"/pending/{doc['doc_id']}").json()
            assert len(body["bundle"]) == doc["claim_count"]
        assert client.get("/pending/d01_sipri_transfer").status_code == 404  # staged set only


def _run_staged_ingest() -> tuple[dict, dict, list[dict]]:
    """Boot withheld → ingest every withheld bundle in one keyless POST → (before, after, alerts)."""
    with TestClient(create_app()) as client:
        before = client.get("/view").json()
        bundle: list[dict] = []
        for doc in resolve_withheld_docs(client.app.state.chanakya.config):
            bundle.extend(client.get(f"/pending/{doc}").json()["bundle"])
        result = client.post("/ingest", json={"bundle": bundle}).json()
        assert result["rebuilt"] is True
        after = client.get("/view").json()
        # The listing now reports arrival off the live log — it never re-offers what has landed.
        assert all(d["ingested"] is True for d in client.get("/pending").json()["documents"])
        return before, after, after.get("alerts") or []


def test_ingesting_the_withheld_documents_relocates_the_unit_and_fires_one_alert() -> None:
    """The reviewer's click, end to end: new basing edge, old one stale + superseded, one alert."""
    before, after, alerts = _run_staged_ingest()
    assert len(after["nodes"]) > len(before["nodes"])

    edges = _based_at(after, WATCHED_UNIT)
    assert DESTINATION_SITE in edges, "the relocation edge must appear once its evidence lands"
    origin = edges[ORIGIN_SITE]
    assert origin["status"] == "stale"
    assert origin["superseded_by"] == edges[DESTINATION_SITE]["id"]
    assert [e for e in after["edges"] if e["type"] == "supersedes"], "supersession must be drawn"

    assert len(alerts) == 1, [a["observable_id"] for a in alerts]
    alert = alerts[0]
    assert alert["subject"] == WATCHED_UNIT
    assert alert["before"]["based-at"] == ORIGIN_SITE
    assert alert["after"]["based-at"] == DESTINATION_SITE
    prov = alert["provenance"]
    assert prov and prov["before_claim_ids"] and prov["after_claim_ids"]
    assert set(prov["claim_ids"]) == set(prov["before_claim_ids"]) | set(prov["after_claim_ids"])
    # Both sides trace to an element the provenance drawer can open — the one-click-to-source rule.
    assert prov["before_ref"] and prov["after_ref"]


def test_staged_ingest_is_deterministic() -> None:
    """Same bundles, same graph, same alert — twice (gate G2). ``fired_ts`` is the one wall-clock."""
    _, after_a, alerts_a = _run_staged_ingest()
    _, after_b, alerts_b = _run_staged_ingest()
    assert [e["id"] for e in after_a["edges"]] == [e["id"] for e in after_b["edges"]]
    assert [n["id"] for n in after_a["nodes"]] == [n["id"] for n in after_b["nodes"]]
    strip = lambda feed: [{k: v for k, v in a.items() if k != "fired_ts"} for a in feed]  # noqa: E731
    assert strip(alerts_a) == strip(alerts_b)


def test_env_override_can_seed_the_full_corpus(monkeypatch: pytest.MonkeyPatch) -> None:
    """``CHANAKYA_SEED_WITHHOLD=""`` withholds nothing — the escape hatch for a static graph review.

    With the full corpus seeded the relocation is already *in* the boot graph, so the old assertion reads
    stale from the start and there is nothing left to arrive — which is exactly why the demo withholds.
    """
    monkeypatch.setenv("CHANAKYA_SEED_WITHHOLD", "")
    with TestClient(create_app()) as client:
        view = client.get("/view").json()
    edges = _based_at(view, WATCHED_UNIT)
    assert DESTINATION_SITE in edges
    assert edges[ORIGIN_SITE]["status"] == "stale"
    assert (view.get("alerts") or []) == []  # boot is a cold delta — no "before" to fire against
