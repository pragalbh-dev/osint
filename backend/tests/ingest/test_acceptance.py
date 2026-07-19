"""INGEST acceptance — the graded beats verified END-TO-END through the real lane + F0 rebuild.

The per-module tests prove each piece; this file proves they *compose* on a real corpus document, at
the **view** level (after ``rebuild``), which is where the graded behaviours actually have to hold:

* **the extract-raw guardrail** — a stated alias survives as a ``same-as`` edge, but the *unstated*
  shell-consignee→SAM-depot link is **never** created (the depot is its own place).
* **G4 traceability** — every node/edge in the rebuilt view carries ≥1 real ``claim_id``.
* **many-claims-per-row + 3-tier** — one customs row yields several typed claims, and the source-native
  context (HS-code / B-L# / container#) rides in the tier-3 ``attributes`` bag.
* **keyless ≡ live** — the frozen bundle (the live claims serialised) re-appends to a byte-identical view.

Offline + deterministic: a :class:`ScriptedExtractionClient` replays the fill a real LLM would return,
so no key/network is touched; ``rebuild``/``evaluate`` are injected (the lane imports no pipeline stage).
"""

from __future__ import annotations

import json
from typing import Any

from chanakya import settings
from chanakya.config.store import ConfigStore
from chanakya.ingest import ingest_bundle, ingest_document
from chanakya.ingest.client import ScriptedExtractionClient
from chanakya.schemas import ClaimRecord, ConfigBundle
from chanakya.store import EvidenceLog
from chanakya.view import rebuild


def _config() -> ConfigBundle:
    return ConfigStore.seed_from(settings.config_dir()).snapshot()


def _d05_text() -> str:
    return (settings.corpus_dir() / "scenarios/hq9p_primary/docs/d05_customs_manifest.txt").read_text()


def _customs_fill() -> dict[str, Any]:
    """What a live extraction returns for d05 — two GD rows incl. the stated alias + the depot ref."""
    return {"rows": [
        {"source_quote": "GD No: KPQA-HC-2020-118834", "gd_no": "KPQA-HC-2020-118834",
         "bl_no": "YMLUW189234567", "hs_code": "8526.91.00", "containers": ["TCNU7712204"],
         "consignee": {"name": "ORIENT ELECTRO TRADING (PVT) LTD",
                       "source_quote": "ORIENT ELECTRO TRADING (PVT) LTD", "origin_country": "Pakistan"},
         "shipper": {"name": "SINO-GALAXY IMP/EXP CO. LTD",
                     "source_quote": "SINO-GALAXY IMP/EXP CO. LTD", "origin_country": "China"},
         "port_of_discharge": "PORT MUHAMMAD BIN QASIM", "filing_date": "04-11-2020",
         "declared_value": "USD 612,400",
         "destination_ref": "Air Defence Depot, ~12 km NNW of Kala Chitta / Attock Cantt area",
         "destination_quote": "Air Defence Depot"},
        {"source_quote": "GD No: KPQA-HC-2020-119011", "gd_no": "KPQA-HC-2020-119011",
         "consignee": {"name": "ORIENT ELECTRO TRADING PVT LTD", "aka": "ORIENT ELECTRONIC TRADING CO",
                       "source_quote": "formerly ORIENT ELECTRONIC"},
         "shipper": {"name": "SINO-GALAXY IMPEX CO, LTD", "source_quote": "SINO-GALAXY IMPEX CO, LTD"},
         "aliases": [{"name_a": "SINO-GALAXY IMPEX CO, LTD", "name_b": "SINO GALAXY IMP. & EXP. CO.",
                      "source_quote": "SINO-GALAXY"}],
         "filing_date": "09-11-2020", "declared_value": "USD 244,150"},
    ]}


def _ingest_d05(store: EvidenceLog, config: ConfigBundle) -> Any:
    client = ScriptedExtractionClient([_customs_fill()])
    return ingest_document(
        _d05_text(), source_id="d05_customs_manifest", source_type="customs-tender",
        config=config, client=client, store=store, file="d05_customs_manifest.txt", rebuild_fn=rebuild,
    )


# ── the guardrail + G4 + 3-tier, at the view level ────────────────────────────────────────────────

def test_customs_guardrail_and_traceability_through_the_lane() -> None:
    config = _config()
    store = EvidenceLog()
    res = _ingest_d05(store, config)
    assert res.rebuilt is True

    claims = store.replay()
    edges = [c.payload for c in claims if c.asserts == "relationship"]

    # the extract-raw guardrail: stated aliases become same-as; the shell→depot link is NEVER resolved.
    same_as = [(e.subject, e.object) for e in edges if e.predicate == "same-as"]
    assert same_as, "a stated alias must surface as a same-as claim"
    assert any("ORIENT" in a and "ORIENT" in b for a, b in same_as)   # ORIENT ELECTRO ↔ ELECTRONIC
    assert any("SINO" in a and "SINO" in b for a, b in same_as)       # SINO-GALAXY spelling variants
    depot_links = [e for e in edges if "Depot" in (e.object or "") or "Depot" in (e.subject or "")]
    assert not depot_links, "GUARDRAIL VIOLATED: the consignee was linked to the SAM depot (unstated)"

    # many-claims-per-row + 3-tier: the source-native HS-code / B-L# / container# ride in `attributes`.
    tier3 = [c.attributes for c in claims if c.attributes]
    assert any("hs_code" in (a or {}) for a in tier3)
    assert any("bl_no" in (a or {}) for a in tier3)

    # G4: rebuild composes and every node/edge carries a real claim provenance.
    view = rebuild(store, [], config)
    assert view.nodes and view.edges
    for node in view.nodes:
        assert node.claim_ids, f"node {node.id} has no claim provenance (G4)"
    for edge in view.edges:
        assert edge.claim_ids, f"edge {edge.id} has no claim provenance (G4)"
    # every cited claim id resolves back to a real claim → a real doc_ref file (one-click-to-source).
    by_id = {c.claim_id: c for c in claims}
    for node in view.nodes:
        for cid in node.claim_ids:
            assert by_id[cid].doc_refs()[0].file  # traceable to a source span


# ── keyless ≡ live: the frozen bundle re-appends to the same claims + the same view ────────────────

def test_keyless_bundle_equals_live_extraction() -> None:
    config = _config()

    live_store = EvidenceLog()
    _ingest_d05(live_store, config)
    live_claims = live_store.replay()

    # freeze the live claims as a bundle (the committed artifact), then re-append keyless (no LLM).
    bundle = json.loads(json.dumps([c.model_dump(mode="json") for c in live_claims]))
    keyless_claims = ingest_bundle(bundle)

    assert [c.claim_id for c in keyless_claims] == [c.claim_id for c in live_claims]
    assert all(isinstance(c, ClaimRecord) for c in keyless_claims)
    # the keyless store rebuilds to the same graph shape as the live one.
    keyless_store = EvidenceLog()
    keyless_store.append_many(keyless_claims)
    live_view, keyless_view = rebuild(live_store, [], config), rebuild(keyless_store, [], config)
    assert {n.id for n in keyless_view.nodes} == {n.id for n in live_view.nodes}
    assert {e.id for e in keyless_view.edges} == {e.id for e in live_view.edges}
