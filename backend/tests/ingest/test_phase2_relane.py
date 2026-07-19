"""Phase-2 INGEST rework — write-time edge re-lane, the provenance rule, and the structural transforms.

These encode the RCA fixes (DECISIONS §6 "EVAL") as offline, deterministic assertions over the *pure*
transforms (a :class:`ScriptedExtractionClient` replays a synthetic filled-dict — no key, no network):

* **enum narrowing (ING-1/D-A)** — the ``relations`` predicate enum is the extractor edges, nothing else.
* **write-time re-lane (D-A)** — a mis-verbed / backwards relation lands on the edge its endpoints imply,
  and a rejected-endpoint relation becomes a tier-3 note, never an ad-hoc edge.
* **the provenance rule** — a re-laned claim preserves the as-stated predicate + verbatim quote + reason.
* **denials (ING-1)** — a negation mints zero edges and zero junk endpoint nodes.
* **structural transforms (ING-2/3, ING-4)** — customs mints a contract_import_event + role edges over
  trading_org endpoints; a tender mints the sustainment nodes; imagery gaps mint no verbose-sentence node.
* **identity untouched (Phase-3 boundary)** — stated aliases still emit as same-as / distinct-from.
"""

from __future__ import annotations

from typing import Any

import pytest

from chanakya import settings
from chanakya.config.store import ConfigStore
from chanakya.ingest import adapters, loaders
from chanakya.ingest.client import ScriptedExtractionClient
from chanakya.ingest.extract import (
    ProseClaim,
    _constrain_relation_enum,
    extract_document,
)
from chanakya.ontology import EdgeLaneIndex
from chanakya.schemas.claim import ClaimRecord, EntityDescriptor, Triple
from chanakya.schemas.config_models import ConfigBundle


@pytest.fixture(autouse=True)
def _offline_geocoder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapters, "_default_geocoder", lambda: None)


@pytest.fixture(scope="module")
def config() -> ConfigBundle:
    return ConfigStore.seed_from(settings.config_dir()).snapshot()


def _run(fmt: str, text: str, filled: dict[str, Any], config: ConfigBundle) -> list[ClaimRecord]:
    loaded = loaders.load_document(text, file="syn.txt")
    return extract_document(loaded, source_id="syn", source_type="", config=config,
                            client=ScriptedExtractionClient([filled]), format_hint=fmt)


def _rels(claims: list[ClaimRecord]) -> list[Triple]:
    return [c.payload for c in claims if isinstance(c.payload, Triple)]


def _rel_claim(claims: list[ClaimRecord], predicate: str) -> ClaimRecord:
    hits = [c for c in claims if isinstance(c.payload, Triple) and c.payload.predicate == predicate]
    assert len(hits) == 1, f"expected exactly one {predicate!r} edge, got {len(hits)}"
    return hits[0]


def _entities(claims: list[ClaimRecord]) -> list[EntityDescriptor]:
    return [c.payload for c in claims if isinstance(c.payload, EntityDescriptor)]


# ── task 1: the relations enum is driven from the extractor edges ─────────────────────────────────

def test_relation_enum_is_the_extractor_edges(config: ConfigBundle) -> None:
    allowed = EdgeLaneIndex(config.ontology).extractor_edges()
    schema = _constrain_relation_enum(ProseClaim.model_json_schema(), allowed)
    enum = schema["$defs"]["RelationMention"]["properties"]["relation"]["anyOf"][0]["enum"]
    assert enum == allowed
    # the identity / evidence / derived edges are NOT assertable through the relations slot.
    for forbidden in ("same-as", "distinct-from", "corroborates", "supersedes", "derived-from"):
        assert forbidden not in enum


# ── task 2/3: a mis-verbed relation re-lanes to the endpoint-implied edge, provenance preserved ────

def test_misverbed_relation_relanes_and_preserves_provenance(config: ConfigBundle) -> None:
    text = "HT-233 is part of the HQ-9/P system."
    filled = {
        "components": [{"name": "HT-233", "source_quote": "HT-233"}],
        "variants": [{"name": "HQ-9/P", "source_quote": "HQ-9/P"}],
        "relations": [{"relation": "component-of", "subject": "HT-233", "object": "HQ-9/P",
                       "source_quote": "HT-233 is part of the HQ-9/P"}],
    }
    claims = _run("prose_claim", text, filled, config)
    # component-of(component, variant) is the classic mis-lane → the hero `equips` edge.
    c = _rel_claim(claims, "equips")
    assert c.payload.subject == "HT-233" and c.payload.object == "HQ-9/P"
    assert not any(t.predicate == "component-of" for t in _rels(claims))
    # THE PROVENANCE RULE: as-stated predicate + verbatim quote + reason all survive on the claim.
    attrs = c.attributes or {}
    assert attrs["_as_stated_predicate"] == "component-of"
    assert attrs["source_quote"] == "HT-233 is part of the HQ-9/P"
    assert "component-of" in attrs["_relane_reason"] and "equips" in attrs["_relane_reason"]


def test_deep_tier_mfr_component_relanes_to_supplies_component(config: ConfigBundle) -> None:
    text = "Taian manufactures the 8x8 chassis for the launcher."
    filled = {
        "manufacturers": [{"name": "Taian", "source_quote": "Taian"}],
        "components": [{"name": "8x8 chassis", "source_quote": "8x8 chassis"}],
        "relations": [{"relation": "manufactures", "subject": "Taian", "object": "8x8 chassis",
                       "source_quote": "Taian manufactures the 8x8 chassis"}],
    }
    claims = _run("prose_claim", text, filled, config)
    c = _rel_claim(claims, "supplies-component")  # Mfr->Component is supplies-component, not manufactures
    assert c.payload.subject == "Taian" and c.payload.object == "8x8 chassis"
    assert (c.attributes or {})["_as_stated_predicate"] == "manufactures"


def test_backwards_written_relation_is_reoriented(config: ConfigBundle) -> None:
    text = "PAF equips the HQ-9/P."
    filled = {
        "units": [{"name": "PAF", "source_quote": "PAF"}],
        "variants": [{"name": "HQ-9/P", "source_quote": "HQ-9/P"}],
        "relations": [{"relation": "equips", "subject": "PAF", "object": "HQ-9/P",
                       "source_quote": "PAF equips the HQ-9/P"}],
    }
    claims = _run("prose_claim", text, filled, config)
    # equips(unit, variant) has no forward edge; the swap names inducted-into (variant->unit).
    c = _rel_claim(claims, "inducted-into")
    assert c.payload.subject == "HQ-9/P" and c.payload.object == "PAF"
    assert (c.attributes or {})["_as_stated_predicate"] == "equips"


def test_rejected_endpoint_relation_becomes_tier3_note_not_an_edge(config: ConfigBundle) -> None:
    text = "SIPRI reports on the HQ-9/P."
    filled = {
        "sources": [{"name": "SIPRI", "source_quote": "SIPRI"}],
        "variants": [{"name": "HQ-9/P", "source_quote": "HQ-9/P"}],
        # source->variant fits no extractor edge in either direction → rejected.
        "relations": [{"relation": "manufactures", "subject": "SIPRI", "object": "HQ-9/P",
                       "source_quote": "SIPRI manufactures HQ-9/P"}],
    }
    claims = _run("prose_claim", text, filled, config)
    # no first-class edge, no invented predicate.
    assert not _rels(claims)
    # the fact is preserved as a tier-3 note on the subject node.
    notes = [c.attributes["_rejected_relation"] for c in claims
             if c.attributes and "_rejected_relation" in c.attributes]
    assert len(notes) == 1
    assert notes[0]["predicate"] == "manufactures" and notes[0]["object"] == "HQ-9/P"


def test_untypable_relation_keeps_as_stated_and_flags_tier3(config: ConfigBundle) -> None:
    text = "Foo Corp manufactures the Bar System."
    filled = {  # neither endpoint is emitted as an entity → neither can be typed.
        "relations": [{"relation": "manufactures", "subject": "Foo Corp", "object": "Bar System",
                       "source_quote": "Foo Corp manufactures the Bar System"}],
    }
    claims = _run("prose_claim", text, filled, config)
    c = _rel_claim(claims, "manufactures")  # as-stated predicate kept (a valid extractor edge)
    assert c.payload.subject == "Foo Corp" and c.payload.object == "Bar System"
    assert (c.attributes or {})["_endpoint_typing"] == "unresolved"


# ── task 4: denials mint zero edges and zero junk nodes ───────────────────────────────────────────

def test_prose_denial_mints_no_edge_and_no_unknown_node(config: ConfigBundle) -> None:
    text = "Chinese state media has not acknowledged the transfer."
    filled = {
        "denials": [{"subject": "Chinese state media", "predicate": "has not acknowledged",
                     "object": "the transfer",
                     "source_quote": "Chinese state media has not acknowledged the transfer"}],
    }
    claims = _run("prose_claim", text, filled, config)
    assert not _rels(claims), "a denial must not become an edge"
    names = {e.name for e in _entities(claims)}
    assert "Chinese state media" not in names and "the transfer" not in names


# ── task 5: identity still emits (same-as / distinct-from), NOT re-laned ───────────────────────────

def test_identity_assertions_still_emit_unchanged(config: ConfigBundle) -> None:
    text = "CASIC (aka China Aerospace) makes the HQ-9/P, also called FD-2000, not the FT-2000. HQ-9P too."
    filled = {
        "manufacturers": [{"name": "CASIC", "aka": "China Aerospace", "source_quote": "CASIC"}],
        "variants": [{"name": "HQ-9/P", "designators": ["FD-2000"], "source_quote": "HQ-9/P"}],
        "aliases": [{"name_a": "HQ-9P", "name_b": "HQ-9/P", "source_quote": "HQ-9P"}],
        "distinctions": [{"name_a": "HQ-9/P", "name_b": "FT-2000", "source_quote": "not the FT-2000"}],
    }
    claims = _run("prose_claim", text, filled, config)
    same_as = {(t.subject, t.object) for t in _rels(claims) if t.predicate == "same-as"}
    distinct = {(t.subject, t.object) for t in _rels(claims) if t.predicate == "distinct-from"}
    assert ("CASIC", "China Aerospace") in same_as          # a stated aka
    assert ("HQ-9/P", "FD-2000") in same_as                 # a stated designator
    assert ("HQ-9P", "HQ-9/P") in same_as                   # a stated alias pair
    assert ("HQ-9/P", "FT-2000") in distinct                # a stated distinction (false-merge trap)
    # identity predicates are emitted verbatim — never re-laned into a knowledge edge.
    for t in _rels(claims):
        assert t.predicate in ("same-as", "distinct-from")


# ── task 6: imagery collection gaps mint no verbose-sentence node ─────────────────────────────────

def test_imagery_gap_mints_no_verbose_node_only_slot_keyed(config: ConfigBundle) -> None:
    text = "Cloud cover ~15%. The launcher count could not be confirmed this pass."
    filled = {
        "site": {"name": "Malir SAM site", "location_text": "24.9 N, 67.2 E", "source_quote": "Malir"},
        "collection_gaps": [
            {"description": "Cloud cover ~15% obscured the northern revetments",
             "source_quote": "Cloud cover ~15%"},  # no missing_slot → NO node
            {"description": "the launcher count could not be confirmed",
             "missing_slot": "launcher_count",
             "source_quote": "launcher count could not be confirmed"},
        ],
    }
    claims = _run("imagery_geoint", text, filled, config)
    gaps = [e for e in _entities(claims) if e.entity_type == "known_gap"]
    assert [g.name for g in gaps] == ["launcher_count"]  # slot-keyed only; the sentence mints nothing
    assert not any("Cloud cover" in (g.name or "") for g in gaps)


# ── task 7: a sustainment tender mints the sustainment nodes (nodes only — no sustained-by edge) ───

def test_tender_mints_sustainment_nodes_without_sustained_by(config: ConfigBundle) -> None:
    text = "Tender for spares. Technical data and calibration held by the OEM authority."
    filled = {
        "tender_id": "AHQ/AD-PROC/X/2023",
        "stockpile": {"name": "interceptor spares", "magazine_depth": "[REDACTED]",
                      "source_quote": "spares"},
        "techdata_authority": {"name": "TDP/calibration authority", "holds": "calibration-ref",
                               "source_quote": "calibration"},
    }
    claims = _run("tender_procurement", text, filled, config)
    types = {e.entity_type for e in _entities(claims)}
    assert "interceptor_stockpile" in types and "techdata_authority" in types
    # the sustained-by rollup is SCORE's — never emitted here.
    assert not any(t.predicate == "sustained-by" for t in _rels(claims))
