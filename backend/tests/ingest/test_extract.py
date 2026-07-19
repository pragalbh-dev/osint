"""Extraction tests — the six format schemas, the deterministic sniffer, and the transform disciplines.

Everything here is **offline + deterministic** (gate G10): a :class:`ScriptedExtractionClient` replays a
canned filled tool-dict over the *real* corpus text loaded by ``loaders.load_document``, and the geocoder
is stubbed out so no adapter ever touches the network. The graded acceptance beats are asserted directly:

* **extract-raw guardrail** — a stated alias → a ``same-as`` claim; NEVER a resolved shell→depot edge.
* **all-optional / anti-fabrication** — a source that states nothing yields ZERO claims.
* **many-claims-per-row + 3-tier** — one customs row → org + event + Location + Date + Quantity, with
  HS-code / container# / B-L# in the tier-3 ``attributes`` bag.
* **structural provenance (G4)** — every emitted claim carries a resolvable ``doc_ref`` whose span
  slices back to the stated text.
* **sniffer** — the two ambiguous source families (official→PR|NOTAM, customs-tender→BoL|tender) split
  on raw-text cues.
"""

from __future__ import annotations

from typing import Any

import pytest

from chanakya import settings
from chanakya.config.store import ConfigStore
from chanakya.ingest import adapters, loaders
from chanakya.ingest.client import ScriptedExtractionClient
from chanakya.ingest.extract import (
    SCHEMAS,
    TRANSFORMS,
    extract_document,
    format_sniffer,
)
from chanakya.schemas.claim import ClaimRecord, DocRef, EntityDescriptor, EventDescriptor, Triple
from chanakya.schemas.config_models import ConfigBundle

_DOCS = settings.corpus_dir() / "scenarios" / "hq9p_primary" / "docs"
_CHAFF = settings.corpus_dir() / "scenarios" / "hq9p_chaff" / "docs"


# ── fixtures ───────────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _offline_geocoder(monkeypatch: pytest.MonkeyPatch) -> None:
    """No adapter may hit Nominatim: the default geocoder resolves to ``None`` (raw preserved, no net)."""
    monkeypatch.setattr(adapters, "_default_geocoder", lambda: None)


@pytest.fixture(scope="module")
def config() -> ConfigBundle:
    """The real ontology vocabulary, seeded from ``config/ontology.yaml`` (offline yaml read)."""
    return ConfigStore.seed_from(settings.config_dir()).snapshot()


def _load(name: str, *, chaff: bool = False) -> loaders.LoadedDoc:
    base = _CHAFF if chaff else _DOCS
    path = base / name
    return loaders.load_document(path.read_text(), file=name)


def _client(*filled: dict[str, Any]) -> ScriptedExtractionClient:
    return ScriptedExtractionClient(list(filled))


# ── helpers ────────────────────────────────────────────────────────────────────────────────────

def _entities(claims: list[ClaimRecord]) -> list[EntityDescriptor]:
    return [c.payload for c in claims if isinstance(c.payload, EntityDescriptor)]


def _events(claims: list[ClaimRecord]) -> list[EventDescriptor]:
    return [c.payload for c in claims if isinstance(c.payload, EventDescriptor)]


def _rels(claims: list[ClaimRecord]) -> list[Triple]:
    return [c.payload for c in claims if isinstance(c.payload, Triple)]


def _ref_resolvable(ref: DocRef) -> bool:
    return bool(ref.file) and (ref.span is not None or ref.line is not None or ref.row is not None)


def _all_refs_resolvable(claims: list[ClaimRecord]) -> bool:
    return all(_ref_resolvable(r) for c in claims for r in c.doc_refs())


# ── sniffer: the two ambiguous families split on raw-text cues ───────────────────────────────────

def test_sniffer_splits_official_pr_vs_notam() -> None:
    pr = _load("d02_ispr_induction.txt").text
    notam = _load("cd05_civ_notam.txt", chaff=True).text
    assert format_sniffer(pr, "official") == "prose_claim"
    assert format_sniffer(notam, "official") == "notam_navwarning"


def test_sniffer_splits_customs_vs_tender() -> None:
    customs = _load("d05_customs_manifest.txt").text
    tender = _load("d06_spares_tender.txt").text
    assert format_sniffer(customs, "customs-tender") == "customs_gd_bol"
    assert format_sniffer(tender, "customs-tender") == "tender_procurement"


def test_sniffer_unknown_source_type_falls_back_to_raw_text() -> None:
    # No source_type at all: the raw shape still routes each document correctly.
    assert format_sniffer(_load("d05_customs_manifest.txt").text, None) == "customs_gd_bol"
    assert format_sniffer(_load("cd05_civ_notam.txt", chaff=True).text, "") == "notam_navwarning"
    assert format_sniffer(_load("d01_sipri_transfer.txt").text, "curated-register") == "prose_claim"


# ── all-optional = anti-fabrication ──────────────────────────────────────────────────────────────

def test_empty_source_yields_zero_claims() -> None:
    loaded = _load("d01_sipri_transfer.txt")
    claims = extract_document(loaded, source_id="d01", source_type="curated-register",
                              config=ConfigBundle(), client=_client({}))
    assert claims == []


def test_partial_fill_emits_only_stated_slots() -> None:
    """A source that states one thing yields exactly that one claim family — nothing invented."""
    loaded = _load("d01_sipri_transfer.txt")
    filled = {"sources": [{"name": "SIPRI Arms Transfers Database",
                           "source_quote": "SIPRI Arms Transfers Database"}]}
    claims = extract_document(loaded, source_id="d01", source_type="curated-register",
                              config=ConfigBundle(), client=_client(filled))
    assert [c.asserts for c in claims] == ["entity"]
    assert _entities(claims)[0].entity_type == "source"


# ── SIPRI aggregator prose → source + transfer claims ────────────────────────────────────────────

def test_sipri_prose_emits_source_and_transfer_claims(config: ConfigBundle) -> None:
    loaded = _load("d01_sipri_transfer.txt")
    filled = {
        "sources": [{"name": "SIPRI Arms Transfers Database", "source_type": "curated-register",
                     "source_quote": "SIPRI Arms Transfers Database"}],
        "events": [{"event_kind": "transfer", "system": "HQ-9(P)", "supplier": "China",
                    "recipient": "Pakistan", "date_text": "2021",
                    "source_quote": "a Pakistan order for an HQ-9(P) SAM system from China"}],
    }
    claims = extract_document(loaded, source_id="d01", source_type="curated-register",
                              config=config, client=_client(filled))
    sources = [e for e in _entities(claims) if e.entity_type == "source"]
    transfers = [e for e in _events(claims) if e.event_type == "TransferEvent"]
    assert sources and "SIPRI" in sources[0].name
    assert transfers and "China" in transfers[0].participants
    assert transfers[0].time_interval is not None  # "2021" normalized to a DateValue
    assert _all_refs_resolvable(claims)


# ── many-claims-per-row + 3-tier promotion (customs) ─────────────────────────────────────────────

def _customs_row_filled() -> dict[str, Any]:
    return {"rows": [{
        "gd_no": "KPQA-HC-2020-118834",
        "bl_no": "YMLUW189234567",
        "consignee": {"name": "ORIENT ELECTRO TRADING (PVT) LTD",
                      "source_quote": "ORIENT ELECTRO TRADING (PVT) LTD"},
        "shipper": {"name": "SINO-GALAXY IMP/EXP CO. LTD", "origin_country": "CHINA",
                    "aka": "SINO-GALAXY IMPEX CO, LTD",
                    "source_quote": "see also SINO-GALAXY IMPEX CO"},
        "port_of_discharge": "PORT MUHAMMAD BIN QASIM (PQ)",
        "filing_date": "04-11-2020",
        "declared_value": "USD 612,400 (CIF PQ)",
        "hs_code": "8526.91.00",
        "containers": ["TCNU7712204", "TCNU7712341"],
        "description": "RADAR APPARATUS PARTS / ELECTRONIC ASSEMBLY",
        "source_quote": "GD No: KPQA-HC-2020-118834",
    }]}


def test_customs_row_yields_many_typed_claims_and_three_tiers(config: ConfigBundle) -> None:
    loaded = _load("d05_customs_manifest.txt")
    claims = extract_document(loaded, source_id="d05", source_type="customs-tender",
                              config=config, client=_client(_customs_row_filled()))

    # tier-1: consignee & shipper get their own org nodes; the shipment gets its own event.
    orgs = [e for e in _entities(claims) if e.entity_type == "manufacturer"]
    roles = {e.attrs.get("role") for e in orgs}
    assert {"consignee", "shipper"} <= roles
    events = [e for e in _events(claims) if e.event_type == "TransferEvent"]
    assert len(events) == 1
    ev = events[0]

    # ports as Location, date as Date, value as Quantity — the typed slots on the event.
    assert ev.location is not None and "QASIM" in str(ev.location.raw).upper()
    assert ev.time_interval is not None
    assert ev.attrs.get("declared_value") is not None

    # tier-3: HS-code / container# / B-L# live in the loose attributes bag, never traversed.
    bag = {k: v for c in claims if c.attributes for k, v in c.attributes.items()}
    assert bag.get("hs_code") == "8526.91.00"
    assert "TCNU7712204" in bag.get("containers", [])
    assert bag.get("bl_no") == "YMLUW189234567"

    # every claim keeps a resolvable, row-citing doc_ref.
    assert _all_refs_resolvable(claims)
    assert any(r.row is not None for c in claims for r in c.doc_refs())


# ── extract-raw guardrail: stated alias → same-as; never a shell→depot edge ───────────────────────

def test_guardrail_stated_alias_emitted_no_unstated_shell_to_depot_edge(config: ConfigBundle) -> None:
    loaded = _load("d05_customs_manifest.txt")
    filled = {"rows": [{
        "gd_no": "KPQA-HC-2020-119011",
        "consignee": {"name": "ORIENT ELECTRO TRADING PVT LTD",
                      "aka": "ORIENT ELECTRONIC TRADING CO",
                      "source_quote": "formerly ORIENT ELECTRONIC"},
        "destination_ref": "Air Defence Depot, ~12 km NNW of Kala Chitta / Attock Cantt area",
        "destination_quote": "~12 km NNW of Kala Chitta",
        "source_quote": "GD No: KPQA-HC-2020-119011",
    }]}
    claims = extract_document(loaded, source_id="d05", source_type="customs-tender",
                              config=config, client=_client(filled))

    rels = _rels(claims)
    # the STATED alias is emitted as a same-as pair …
    same_as = [t for t in rels if t.predicate == "same-as"]
    assert any("ORIENT ELECTRO" in t.subject and "ORIENT ELECTRONIC" in t.object for t in same_as)

    # … but the UNSTATED shell→depot identity is NEVER resolved into an edge.
    for t in rels:
        pair = f"{t.subject} || {t.object}"
        assert not ("ORIENT ELECTRO" in pair and "Depot" in pair), (
            f"leaked an unstated shell→depot edge: {t.predicate} {pair!r}"
        )

    # the stated destination IS captured — as its own place, not a resolved link.
    sites = [e for e in _entities(claims) if e.entity_type == "basing_site"]
    assert any("Air Defence Depot" in e.name for e in sites)


# ── tender: aliases → same-as, comparisons → distinct-from (not merged) ───────────────────────────

def test_tender_aliases_and_distinctions(config: ConfigBundle) -> None:
    loaded = _load("d06_spares_tender.txt")
    filled = {
        "tender_id": "AHQ/AD-PROC/[REDACTED]/2023",
        "system": {"name": "HQ-9/P", "designators": ["HQ-9P", "FD-2000"], "source_quote": "HQ-9/P"},
        "line_items": [{"name": "TVM uplink/downlink test sets", "quantity_text": "[REDACTED]",
                        "source_quote": "TVM (track-via-missile) uplink/downlink test sets"}],
        "distinctions": [{"name_a": "HQ-9/P", "name_b": "S-400/Triumf",
                          "source_quote": "no such interoperability is claimed"}],
    }
    claims = extract_document(loaded, source_id="d06", source_type="customs-tender",
                              config=config, client=_client(filled))
    rels = _rels(claims)
    assert any(t.predicate == "same-as" and t.object == "FD-2000" for t in rels)
    distinct = [t for t in rels if t.predicate == "distinct-from"]
    assert distinct and "S-400" in distinct[0].object
    # the two systems are held apart, never merged into one same-as.
    assert not any(t.predicate == "same-as" and "S-400" in t.object for t in rels)


# ── social: a "nothing to report" negation → a negative-polarity observation ──────────────────────

def test_social_negation_is_negative_polarity(config: ConfigBundle) -> None:
    loaded = _load("d08_social_sighting.txt")
    filled = {"posts": [{
        "handle": "@Reh_Baloch",
        "status_url": "https://x.com/Reh_Baloch/status/1920783341122009871",
        "sightings": [{"system": "HQ9", "activity": "battery shifting position",
                       "source_quote": "HQ9 battery shifting position"}],
        "negations": [{"subject": "Karachi air defence site", "predicate": "shows",
                       "object": "vehicle movement",
                       "source_quote": "no vehicle movement"}],
        "source_quote": "Handle: @Reh_Baloch",
    }]}
    claims = extract_document(loaded, source_id="d08", source_type="named-social",
                              config=config, client=_client(filled))
    negatives = [c for c in claims if c.polarity == "negative"]
    assert negatives and negatives[0].asserts == "relationship"
    # the handle is registered as a social source; the sighting is a positive event.
    assert any(e.entity_type == "source" for e in _entities(claims))
    assert any(ev.event_type == "SightingEvent" for ev in _events(claims))


# ── civil NOTAM: a located fact, never a fabricated military read ─────────────────────────────────

def test_civil_notam_extracts_location_without_sam_assertion(config: ConfigBundle) -> None:
    loaded = _load("cd05_civ_notam.txt", chaff=True)
    filled = {"notices": [{
        "notice_id": "A1187/25", "location_ref": "OPKC", "activity": "RWY 07L/25R CLSD",
        "hazard_type": "runway-closure", "source_quote": "RWY 07L/25R CLSD",
    }]}
    claims = extract_document(loaded, source_id="cd05", source_type="official",
                              config=config, client=_client(filled))
    # a civil notice (no event_kind) → an indicator observation; no variant/SAM entity, no event.
    assert any(e.entity_type == "indicator" for e in _entities(claims))
    assert not _events(claims)
    assert not any(e.entity_type == "variant" for e in _entities(claims))
    assert _all_refs_resolvable(claims)


# ── every format yields valid ClaimRecords with resolvable doc_refs ───────────────────────────────

_FORMAT_CASES: list[tuple[str, str, bool, dict[str, Any]]] = [
    ("prose_claim", "d01_sipri_transfer.txt", False,
     {"sources": [{"name": "SIPRI Arms Transfers Database",
                   "source_quote": "SIPRI Arms Transfers Database"}]}),
    ("notam_navwarning", "cd05_civ_notam.txt", True,
     {"notices": [{"notice_id": "A1187/25", "activity": "RWY 07L/25R CLSD",
                   "source_quote": "RWY 07L/25R CLSD"}]}),
    ("customs_gd_bol", "d05_customs_manifest.txt", False, _customs_row_filled()),
    ("tender_procurement", "d06_spares_tender.txt", False,
     {"system": {"name": "HQ-9/P", "source_quote": "HQ-9/P"},
      "tender_id": "AHQ/AD-PROC/[REDACTED]/2023"}),
    ("social_post", "d08_social_sighting.txt", False,
     {"posts": [{"handle": "@Reh_Baloch",
                 "sightings": [{"system": "HQ9", "source_quote": "HQ9 battery shifting position"}],
                 "source_quote": "Handle: @Reh_Baloch"}]}),
    ("imagery_geoint", "d07_sat_confirm_karachi.txt", False,
     {"site": {"name": "Malir SAM site", "location_text": "24.9012 N, 67.2034 E",
               "source_quote": "24.9012 N, 67.2034 E"},
      "observations": [{"pass_date": "2021-11-02", "object_type": "TEL revetments",
                        "object_count_text": "2", "source_quote": "TEL revetments"}],
      "collection_gaps": [{"description": "No SAR pass available",
                           "source_quote": "No SAR pass available"}]}),
]


@pytest.mark.parametrize("fmt,doc,chaff,filled", _FORMAT_CASES)
def test_each_format_yields_valid_claims(config: ConfigBundle, fmt: str, doc: str, chaff: bool,
                                         filled: dict[str, Any]) -> None:
    loaded = _load(doc, chaff=chaff)
    claims = extract_document(loaded, source_id=doc.split("_")[0], source_type="",
                              config=config, client=_client(filled), format_hint=fmt)
    assert claims, f"{fmt} produced no claims"
    assert all(isinstance(c, ClaimRecord) for c in claims)
    assert _all_refs_resolvable(claims)
    # every claim is stamped with the extractor provenance (method + model-id string).
    assert all(c.extraction.method == "llm" and c.extraction.version == "scripted" for c in claims)


# ── provenance: a source_quote resolves to an exact char span ────────────────────────────────────

def test_source_quote_resolves_to_exact_span() -> None:
    loaded = _load("d01_sipri_transfer.txt")
    quote = "SIPRI Arms Transfers Database"
    filled = {"sources": [{"name": "SIPRI Arms Transfers Database", "source_quote": quote}]}
    claims = extract_document(loaded, source_id="d01", source_type="curated-register",
                              config=ConfigBundle(), client=_client(filled))
    ref = claims[0].doc_refs()[0]
    assert ref.span is not None
    start, end = ref.span
    assert loaded.text[start:end] == quote  # the span slices back to the verbatim stated text


# ── registry wiring: a schema + transform for every format ───────────────────────────────────────

def test_registry_covers_all_six_formats() -> None:
    assert set(SCHEMAS) == set(TRANSFORMS)
    assert len(SCHEMAS) == 6
    for model in SCHEMAS.values():
        schema = model.model_json_schema()
        # permissive tool schema: no forced fields, no closed object (would 400 Anthropic strict-mode).
        assert "required" not in schema or not schema["required"]
        assert schema.get("additionalProperties") is not False


def test_offontology_type_flagged_when_absent_from_config() -> None:
    """A type not in the *live* ontology is still emitted, flagged in tier-3 (extensible, not silent)."""
    loaded = _load("d01_sipri_transfer.txt")
    # A config whose ontology has NO node types → 'source' is off-ontology and must be flagged.
    bare = ConfigBundle()
    filled = {"sources": [{"name": "SIPRI", "source_quote": "SIPRI Arms Transfers Database"}]}
    # bare has empty ontology → vocab empty → validation skipped (nothing flagged); use a partial one.
    partial = ConfigBundle.model_validate({"ontology": {"node_types": [{"name": "unit"}]}})
    claims = extract_document(loaded, source_id="d01", source_type="curated-register",
                              config=partial, client=_client(filled))
    assert claims[0].attributes is not None
    assert claims[0].attributes.get("_offontology_type") == "source"
    # sanity: with the empty bundle, no flag is added (vocab empty → skip).
    claims2 = extract_document(loaded, source_id="d01", source_type="curated-register",
                               config=bare, client=_client(filled))
    assert not (claims2[0].attributes or {}).get("_offontology_type")


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# Geocoder threading — extract_document → em.location → normalize_location, all sites in one place.
# A seeded name resolves offline to its gazetteer coordinate (frozen onto the claim); default = offline.
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def _basing_site_coords(claims: list[ClaimRecord]) -> dict[str, Any] | None:
    for c in claims:
        p = c.payload
        if isinstance(p, EntityDescriptor) and p.entity_type == "basing_site":
            return p.attrs.get("coordinates")
    return None


def test_geocoder_threads_to_site_location(config: ConfigBundle) -> None:
    gaz = adapters.GazetteerGeocoder(config.places.places, config.resolution.transliteration)
    loaded = loaders.load_document(
        "A battery was reported at PAF Base Nur Khan.", file="g01.txt"
    )
    filled = {"basing_sites": [{
        "name": "the reported base", "location_text": "PAF Base Nur Khan",
        "source_quote": "PAF Base Nur Khan",
    }]}
    claims = extract_document(loaded, source_id="g01", source_type="curated-register",
                              config=config, client=_client(filled), geocoder=gaz)
    coords = _basing_site_coords(claims)
    assert coords is not None
    assert coords["wgs84_lat"] == pytest.approx(33.61639)
    assert coords["geocode_candidates"][0]["source"] == "gazetteer"
    # INGEST freezes the coordinate only — identity stays RESOLVE's, at rebuild.
    assert coords.get("resolved_place_ref") is None


def test_default_no_geocoder_keeps_toponym_raw(config: ConfigBundle) -> None:
    # No geocoder passed (+ the autouse offline default) → the toponym is preserved, no coordinate.
    loaded = loaders.load_document(
        "A battery was reported at PAF Base Nur Khan.", file="g02.txt"
    )
    filled = {"basing_sites": [{
        "name": "the reported base", "location_text": "PAF Base Nur Khan",
        "source_quote": "PAF Base Nur Khan",
    }]}
    claims = extract_document(loaded, source_id="g02", source_type="curated-register",
                              config=config, client=_client(filled))
    coords = _basing_site_coords(claims)
    assert coords is not None
    assert coords.get("wgs84_lat") is None  # offline: no network, no gazetteer → raw toponym only
    assert coords["raw"] == "PAF Base Nur Khan"
