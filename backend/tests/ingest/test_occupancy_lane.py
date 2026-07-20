"""The observed-occupancy lane + relationship valid time (EVAL RCA §2.3, D-P4.2 / D-P4.6).

Two defects are pinned here as passing assertions, both of which silently disarmed the relocation beat:

1. **The GEOINT format could not state a relationship at all.** ``ImageryGeoint`` had no relations slot,
   and every ``source_type: satellite`` document routes to it — so the two documents that carry the
   relocation (a 2021 write-up and a 2025 one) emitted 21 claims between them and **zero** edges. Adding
   a date field to relations fixes nothing while the shape cannot emit one.
2. **Relationship claims carried no valid time.** Every other mention type has a date; ``RelationMention``
   did not, so 0 of 126 relationship claims could be aged, ordered or superseded — while the emitter's
   ``event_time`` plumbing sat complete and unused at both call sites.

The lane split is asserted too: equipment→site is ``observed-at`` (what a source can honestly observe),
never ``based-at`` (formation→site, which is derived elsewhere at its own lower confidence).

Offline + deterministic (gate G10): a :class:`ScriptedExtractionClient` replays a canned filled dict over
the real corpus text; the geocoder is stubbed out so no adapter touches the network.
"""

from __future__ import annotations

from typing import Any

import pytest

from chanakya import settings
from chanakya.config.store import ConfigStore
from chanakya.ingest import adapters, loaders
from chanakya.ingest.client import ScriptedExtractionClient
from chanakya.ingest.extract import ImageryGeoint, RelationMention, extract_document
from chanakya.schemas.claim import ClaimRecord, Triple
from chanakya.schemas.config_models import ConfigBundle
from chanakya.schemas.values import ExactDate, canonical_iso_bounds

_DOCS = settings.corpus_dir() / "scenarios" / "hq9p_primary" / "docs"


@pytest.fixture(autouse=True)
def _offline_geocoder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapters, "_default_geocoder", lambda: None)


@pytest.fixture(scope="module")
def config() -> ConfigBundle:
    """The real ontology, so ``observed-at`` and the re-lane behave exactly as they do in production."""
    return ConfigStore.seed_from(settings.config_dir()).snapshot()


def _load(name: str) -> loaders.LoadedDoc:
    return loaders.load_document((_DOCS / name).read_text(), file=name)


def _rels(claims: list[ClaimRecord]) -> list[Triple]:
    return [c.payload for c in claims if isinstance(c.payload, Triple)]


def _by_predicate(claims: list[ClaimRecord]) -> dict[str, ClaimRecord]:
    return {c.payload.predicate: c for c in claims if isinstance(c.payload, Triple)}


_REPORT_TIME = ExactDate(iso_date="2021-10-14", raw="14 OCT 2021")

#: What the model fills for d17: a site, a dated pass, an assessed system, and the occupancy statement
#: the document actually makes ("a fire unit consistent with HQ-9B occupying a revetment complex at …").
_D17_FILLED: dict[str, Any] = {
    "site": {"name": "PAF Base Nur Khan", "site_type": "airbase",
             "location_text": "43S CT 23715 21242", "source_quote": "PAF Base Nur Khan"},
    "observations": [{"pass_date": "03 AUG 2021", "object_type": "TEL-type objects",
                      "source_quote": "03 AUG pass"},
                     {"pass_date": "09 OCT 2021", "object_type": "launcher/visible objects",
                      "source_quote": "09 OCT pass"}],
    "assessed_types": [{"name": "HQ-9B", "family": "HQ-9",
                        "confidence_language": "moderate-to-high confidence",
                        "source_quote": "HQ-9B"}],
    "occupancy": [{"observed": "HQ-9B", "site": "PAF Base Nur Khan",
                   "observed_date": "09 OCT 2021", "occupancy_state": "occupied",
                   "source_quote": "occupying a prepared revetment complex"}],
}


def _extract(filled: dict[str, Any], doc: str, config: ConfigBundle, *,
             report_time: Any = _REPORT_TIME) -> list[ClaimRecord]:
    return extract_document(
        _load(doc), source_id=doc.removesuffix(".txt"), source_type="satellite", config=config,
        client=ScriptedExtractionClient([filled]), report_time=report_time,
    )


# ── §2.3: the GEOINT shape can now emit a relationship at all ────────────────────────────────────

def test_imagery_schema_exposes_the_relationship_slots_it_was_missing() -> None:
    fields = set(ImageryGeoint.model_fields)
    assert {"occupancy", "relations", "units"} <= fields


def test_geoint_document_emits_an_observed_at_edge(config: ConfigBundle) -> None:
    """d17 yielded 13 claims and zero relationships; the occupancy slot is what closes that."""
    claims = _extract(_D17_FILLED, "d17_rawalpindi_2021.txt", config)
    rels = _rels(claims)
    assert rels, "a GEOINT report stating equipment at a site must emit a relationship claim"
    occupancy = [t for t in rels if t.predicate == "observed-at"]
    assert len(occupancy) == 1
    assert occupancy[0].subject == "HQ-9B"          # equipment on the FROM end
    assert occupancy[0].object == "PAF Base Nur Khan"


def test_equipment_at_site_is_never_asserted_as_formation_basing(config: ConfigBundle) -> None:
    """The layer split: a sighting states occupancy, never that a unit is based there."""
    claims = _extract(_D17_FILLED, "d17_rawalpindi_2021.txt", config)
    assert "based-at" not in {t.predicate for t in _rels(claims)}


def test_occupancy_claim_is_traceable_to_the_stated_span(config: ConfigBundle) -> None:
    claim = _by_predicate(_extract(_D17_FILLED, "d17_rawalpindi_2021.txt", config))["observed-at"]
    ref = claim.doc_refs()[0]
    assert ref.file and (ref.span is not None or ref.line is not None)


# ── D-P4.6: relationship valid time + the fallback ladder ────────────────────────────────────────

def test_relation_mention_has_a_date_slot() -> None:
    assert "date_text" in RelationMention.model_fields


def test_stated_relation_date_becomes_the_claims_event_time(config: ConfigBundle) -> None:
    claim = _by_predicate(_extract(_D17_FILLED, "d17_rawalpindi_2021.txt", config))["observed-at"]
    assert canonical_iso_bounds(claim.event_time) == ("2021-10-09", "2021-10-09")
    assert (claim.attributes or {}).get("_event_time_rung") == "stated"


def test_undated_occupancy_falls_back_to_the_enclosing_pass_date(config: ConfigBundle) -> None:
    """Rung 2: the observation the statement sits in dates it — the LATEST pass the report rests on."""
    filled = {**_D17_FILLED,
              "occupancy": [{**_D17_FILLED["occupancy"][0], "observed_date": None}]}
    claim = _by_predicate(_extract(filled, "d17_rawalpindi_2021.txt", config))["observed-at"]
    assert canonical_iso_bounds(claim.event_time) == ("2021-10-09", "2021-10-09")
    assert (claim.attributes or {}).get("_event_time_rung") == "observation"


def test_no_observation_date_falls_back_to_report_time_restamped_as_derived(config: ConfigBundle) -> None:
    """Rung 3: the publication date bounds the fact — but is re-stamped, never laundered as explicit."""
    filled = {**_D17_FILLED, "observations": [],
              "occupancy": [{**_D17_FILLED["occupancy"][0], "observed_date": None}]}
    claim = _by_predicate(_extract(filled, "d17_rawalpindi_2021.txt", config))["observed-at"]
    assert canonical_iso_bounds(claim.event_time) == ("2021-10-14", "2021-10-14")
    assert (claim.attributes or {}).get("_event_time_rung") == "report_time"
    assert getattr(claim.event_time, "boundary_source", None) == "relative"


def test_perishable_relation_with_no_date_anywhere_is_flagged_not_invented(config: ConfigBundle) -> None:
    filled = {**_D17_FILLED, "observations": [],
              "occupancy": [{**_D17_FILLED["occupancy"][0], "observed_date": None}]}
    claim = _by_predicate(_extract(filled, "d17_rawalpindi_2021.txt", config, report_time=None))["observed-at"]
    assert claim.event_time is None
    assert (claim.attributes or {}).get("_undated_perishable") is True


def test_durable_relation_is_not_given_a_publication_date(config: ConfigBundle) -> None:
    """D-P4.6's rejected option: dating every relation would stamp 115 of 126 claims with a date nobody
    asserted. Only a decaying edge walks the fallback rungs; a durable one stays honestly undated."""
    filled = {
        "site": _D17_FILLED["site"],
        "components": [{"name": "HT-233", "functional_role": "engagement_fire_control",
                        "source_quote": "HT-233"}],
        "assessed_types": _D17_FILLED["assessed_types"],
        "relations": [{"relation": "equips", "subject": "HT-233", "object": "HQ-9B",
                       "source_quote": "engagement radar associated with the HQ-9B fire unit"}],
    }
    claim = _by_predicate(_extract(filled, "d17_rawalpindi_2021.txt", config))["equips"]
    assert claim.event_time is None
    assert "_event_time_rung" not in (claim.attributes or {})
