"""The frozen-bundle location re-normalisation pass (offline, deterministic, narrow, auditable)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from chanakya import settings
from chanakya.ingest import renormalize


def _claim(coords: dict[str, object]) -> dict[str, object]:
    return {
        "claim_id": "d17-x-l4",
        "source_id": "d17_x",
        "doc_ref": {"file": "corpus/x.txt", "line": 4},
        "kind": "observation",
        "polarity": "positive",
        "asserts": "entity",
        "payload": {"form": "entity", "entity_type": "basing_site", "name": "PAF Base Nur Khan",
                    "attrs": {"coordinates": coords, "site_type": "prepared revetment complex"}},
        "report_time": {"kind": "exact", "iso_date": "2021-10-14", "raw": "2021-10-14"},
        "ingest_time": {"kind": "exact", "iso_date": "2026-07-19", "raw": "frozen-seed-baseline"},
        "extraction": {"method": "llm", "version": "gemini-flash-latest", "model_conf": 1.0},
    }


_MISLABELLED_GRID = {
    "raw": "Grid: 43S CT 23715 21242 (MGRS, WGS84)",
    "surface_format": "toponym",
    "proposed_alias": "Grid: 43S CT 23715 21242 (MGRS, WGS84)",
    "wgs84_lat": None, "wgs84_lon": None, "geocode_candidates": [],
    "precision_class": None, "resolved_place_ref": None,
}


def test_mislabelled_grid_in_a_frozen_bundle_is_recovered_offline() -> None:
    rows = [_claim(copy.deepcopy(_MISLABELLED_GRID))]
    changes = renormalize.renormalize_rows(rows, bundle="d17.json")

    coords = rows[0]["payload"]["attrs"]["coordinates"]  # type: ignore[index]
    assert coords["surface_format"] == "MGRS"
    assert coords["wgs84_lat"] is not None and coords["wgs84_lon"] is not None
    assert coords["precision_class"] == "pad"
    assert coords["geocode_candidates"][0]["source"] == "coord-parse"
    # The verbatim source text and every RESOLVE-owned slot survive untouched.
    assert coords["raw"] == _MISLABELLED_GRID["raw"]
    assert coords["resolved_place_ref"] is None
    assert {c.field_path.rsplit(".", 1)[-1] for c in changes} <= set(renormalize.MUTABLE_FIELDS)
    assert all(c.claim_id == "d17-x-l4" for c in changes)


def test_pass_is_idempotent() -> None:
    rows = [_claim(copy.deepcopy(_MISLABELLED_GRID))]
    assert renormalize.renormalize_rows(rows, bundle="d17.json")
    assert renormalize.renormalize_rows(rows, bundle="d17.json") == []


def test_a_geocoded_coordinate_is_never_re_derived_or_dropped() -> None:
    # A toponym whose coordinate came from a geocode: this pass has no geocoder and must leave it be
    # rather than blank it out (additive-only).
    geocoded = {
        "raw": "Port Qasim", "surface_format": "toponym", "proposed_alias": "Port Qasim",
        "wgs84_lat": 24.767, "wgs84_lon": 67.333, "precision_class": None,
        "resolved_place_ref": None,
        "geocode_candidates": [{"lat": 24.767, "lon": 67.333, "label": "Port Muhammad Bin Qasim",
                                "source": "gazetteer", "confidence": None}],
    }
    rows = [_claim(copy.deepcopy(geocoded))]
    assert renormalize.renormalize_rows(rows, bundle="d05.json") == []
    assert rows[0]["payload"]["attrs"]["coordinates"] == geocoded  # type: ignore[index]


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    bundle = tmp_path / "d17.json"
    bundle.write_text(json.dumps([_claim(copy.deepcopy(_MISLABELLED_GRID))]), encoding="utf-8")
    before = bundle.read_text(encoding="utf-8")

    assert renormalize.renormalize_bundles(tmp_path, apply=False)
    assert bundle.read_text(encoding="utf-8") == before

    assert renormalize.renormalize_bundles(tmp_path, apply=True)
    assert bundle.read_text(encoding="utf-8") != before


def test_shipped_corpus_is_already_fully_normalized() -> None:
    """The frozen bundles must agree with the current canonicaliser (the KEYLESS ≡ LIVE invariant).

    A failure here means a re-record would disagree with what is checked in — run
    ``python -m chanakya.ingest renormalize --scenario hq9p_primary --apply``.
    """
    claims_dir = settings.corpus_dir() / "scenarios" / "hq9p_primary" / "claims"
    if not claims_dir.is_dir():  # pragma: no cover - corpus is optional in a bare checkout
        return
    assert renormalize.renormalize_bundles(claims_dir, apply=False) == []
