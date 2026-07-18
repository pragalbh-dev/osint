"""Azure OCR provider tests — the pure ``transform_layout`` (fixture-driven, offline) + the lazy client.

The load-bearing invariants: every emitted ``Region`` carries its ``page`` and a ``bbox`` normalised to
the unit square ``[0, 1]``; table cells additionally carry their ``row`` (gate G4 provenance). All tests
run with zero network and zero Azure SDK — the transform is SDK-free, and the client's SDK import is lazy,
so the "not installed" / "not configured" paths are exercised without ever touching the wire.
"""

from __future__ import annotations

import importlib.util

import pytest

from chanakya.ingest import loaders
from chanakya.ingest.ocr_azure import (
    AzureDocIntelProvider,
    _polygon_bbox,
    transform_layout,
)

_AZURE_INSTALLED = importlib.util.find_spec("azure.ai.documentintelligence") is not None


# A small hand-authored ``prebuilt-layout`` response (camelCase, the REST/``as_dict()`` wire form):
# one page, two paragraphs (one with a role), one 2×2 table. Coordinates are in the page's units.
_LAYOUT: dict = {
    "pages": [{"pageNumber": 1, "width": 8.5, "height": 11.0, "unit": "inch"}],
    "paragraphs": [
        {
            "role": "title",
            "content": "GOODS DECLARATION",
            "boundingRegions": [
                {"pageNumber": 1, "polygon": [1.0, 1.0, 4.0, 1.0, 4.0, 1.5, 1.0, 1.5]}
            ],
        },
        {
            "content": "Consignee: NORTHERN TRADING CO",
            "boundingRegions": [
                {"pageNumber": 1, "polygon": [1.0, 2.0, 6.0, 2.0, 6.0, 2.4, 1.0, 2.4]}
            ],
        },
    ],
    "tables": [
        {
            "rowCount": 2,
            "columnCount": 2,
            "cells": [
                {"rowIndex": 1, "columnIndex": 1, "content": "6",
                 "boundingRegions": [{"pageNumber": 1, "polygon": [3.0, 3.5, 5.0, 3.5, 5.0, 4.0, 3.0, 4.0]}]},
                {"rowIndex": 0, "columnIndex": 0, "content": "HS Code",
                 "boundingRegions": [{"pageNumber": 1, "polygon": [1.0, 3.0, 3.0, 3.0, 3.0, 3.5, 1.0, 3.5]}]},
                {"rowIndex": 1, "columnIndex": 0, "content": "Qty",
                 "boundingRegions": [{"pageNumber": 1, "polygon": [1.0, 3.5, 3.0, 3.5, 3.0, 4.0, 1.0, 4.0]}]},
                {"rowIndex": 0, "columnIndex": 1, "content": "8526",
                 "boundingRegions": [{"pageNumber": 1, "polygon": [3.0, 3.0, 5.0, 3.0, 5.0, 3.5, 3.0, 3.5]}]},
            ],
        }
    ],
}


# ── the pure polygon → bbox helper ─────────────────────────────────────────────────────────────

def test_polygon_bbox_flat_coordinate_list() -> None:
    # min/max corner of a flat [x1,y1,x2,y2,...] polygon.
    assert _polygon_bbox([2.0, 4.0, 8.0, 4.0, 8.0, 10.0, 2.0, 10.0]) == (2.0, 4.0, 8.0, 10.0)


def test_polygon_bbox_point_dicts() -> None:
    poly = [{"x": 2, "y": 4}, {"x": 8, "y": 4}, {"x": 8, "y": 10}, {"x": 2, "y": 10}]
    assert _polygon_bbox(poly) == (2.0, 4.0, 8.0, 10.0)


def test_polygon_bbox_empty_is_none() -> None:
    assert _polygon_bbox([]) is None
    assert _polygon_bbox(None) is None


# ── paragraphs ─────────────────────────────────────────────────────────────────────────────────

def test_paragraph_regions_carry_page_and_normalised_bbox() -> None:
    regions = transform_layout(_LAYOUT, file="scan.pdf")
    paras = [r for r in regions if r.kind == "paragraph"]
    assert [r.text for r in paras] == ["GOODS DECLARATION", "Consignee: NORTHERN TRADING CO"]
    for r in paras:
        assert r.file == "scan.pdf"
        assert r.page == 1
        assert r.bbox is not None
        assert all(0.0 <= c <= 1.0 for c in r.bbox)
        assert r.span is None  # no born-digital char layer for OCR
    # title paragraph keeps its role in `name`; the plain paragraph has none.
    assert paras[0].name == "title"
    assert paras[1].name is None
    # bbox normalised by page width/height (8.5 × 11.0): title polygon x∈[1,4], y∈[1,1.5].
    assert paras[0].bbox == (
        round(1.0 / 8.5, 6), round(1.0 / 11.0, 6), round(4.0 / 8.5, 6), round(1.5 / 11.0, 6),
    )


# ── table cells ────────────────────────────────────────────────────────────────────────────────

def test_table_cells_carry_row_and_are_row_col_ordered() -> None:
    regions = transform_layout(_LAYOUT, file="scan.pdf")
    cells = [r for r in regions if r.kind == "table_cell"]
    # Emitted deterministically by (rowIndex, columnIndex) regardless of the input cell order.
    assert [(r.row, r.name, r.text) for r in cells] == [
        (0, "r0c0", "HS Code"),
        (0, "r0c1", "8526"),
        (1, "r1c0", "Qty"),
        (1, "r1c1", "6"),
    ]
    for r in cells:
        assert r.page == 1
        assert r.bbox is not None
        assert all(0.0 <= c <= 1.0 for c in r.bbox)


def test_paragraphs_then_cells_and_doc_ref_projection() -> None:
    regions = transform_layout(_LAYOUT, file="scan.pdf")
    kinds = [r.kind for r in regions]
    assert kinds == ["paragraph", "paragraph", "table_cell", "table_cell", "table_cell", "table_cell"]
    # Regions project onto an F0 DocRef carrying the page + bbox + row locators.
    cell = next(r for r in regions if r.kind == "table_cell")
    ref = cell.to_doc_ref()
    assert ref.file == "scan.pdf"
    assert ref.page == 1
    assert ref.row == 0
    assert ref.bbox is not None


# ── normalisation edges ──────────────────────────────────────────────────────────────────────────

def test_bbox_normalisation_exact() -> None:
    layout = {
        "pages": [{"pageNumber": 1, "width": 10.0, "height": 20.0}],
        "paragraphs": [
            {"content": "x", "boundingRegions": [
                {"pageNumber": 1, "polygon": [2.0, 4.0, 8.0, 4.0, 8.0, 10.0, 2.0, 10.0]}]}
        ],
    }
    (region,) = transform_layout(layout, file="f.pdf")
    assert region.bbox == (0.2, 0.2, 0.8, 0.5)


def test_bbox_clamped_to_unit_square() -> None:
    # A polygon overshooting the declared page bounds is clamped, never emitted > 1 or < 0.
    layout = {
        "pages": [{"pageNumber": 1, "width": 10.0, "height": 10.0}],
        "paragraphs": [
            {"content": "x", "boundingRegions": [
                {"pageNumber": 1, "polygon": [-1.0, -2.0, 12.0, -2.0, 12.0, 15.0, -1.0, 15.0]}]}
        ],
    }
    (region,) = transform_layout(layout, file="f.pdf")
    assert region.bbox == (0.0, 0.0, 1.0, 1.0)


def test_single_page_bounding_region_without_page_number() -> None:
    # A region that omits pageNumber falls back to the lone page's dimensions.
    layout = {
        "pages": [{"pageNumber": 1, "width": 10.0, "height": 10.0}],
        "paragraphs": [{"content": "x", "boundingRegions": [{"polygon": [1.0, 1.0, 6.0, 1.0, 6.0, 6.0, 1.0, 6.0]}]}],
    }
    (region,) = transform_layout(layout, file="f.pdf")
    assert region.page == 1
    assert region.bbox == (0.1, 0.1, 0.6, 0.6)


def test_missing_bounding_region_still_emits_region_without_geo() -> None:
    layout = {"pages": [{"pageNumber": 1, "width": 10.0, "height": 10.0}],
              "paragraphs": [{"content": "orphan"}]}
    (region,) = transform_layout(layout, file="f.pdf")
    assert region.text == "orphan"
    assert region.page is None
    assert region.bbox is None


def test_missing_page_dimensions_yields_no_bbox() -> None:
    # Page declares no width/height → the box cannot be normalised → no fabricated bbox.
    layout = {
        "pages": [{"pageNumber": 1}],
        "paragraphs": [{"content": "x", "boundingRegions": [
            {"pageNumber": 1, "polygon": [1.0, 1.0, 2.0, 1.0, 2.0, 2.0, 1.0, 2.0]}]}],
    }
    (region,) = transform_layout(layout, file="f.pdf")
    assert region.page == 1
    assert region.bbox is None


def test_snake_case_response_is_tolerated() -> None:
    layout = {
        "pages": [{"page_number": 1, "width": 10.0, "height": 10.0}],
        "tables": [{"cells": [
            {"row_index": 0, "column_index": 0, "content": "c",
             "bounding_regions": [{"page_number": 1, "bounding_box": [1.0, 1.0, 3.0, 1.0, 3.0, 3.0, 1.0, 3.0]}]}
        ]}],
    }
    (region,) = transform_layout(layout, file="f.pdf")
    assert region.kind == "table_cell"
    assert region.row == 0
    assert region.page == 1
    assert region.bbox == (0.1, 0.1, 0.3, 0.3)


def test_empty_response_yields_no_regions() -> None:
    assert transform_layout({}, file="f.pdf") == []


# ── provider (lazy client; offline) ───────────────────────────────────────────────────────────────

def test_provider_conforms_to_ocr_provider_protocol() -> None:
    provider = AzureDocIntelProvider(endpoint="https://x", key="k")
    assert isinstance(provider, loaders.OcrProvider)  # runtime_checkable structural conformance


def test_provider_reads_env_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_DOCINTEL_ENDPOINT", "https://env-endpoint")
    monkeypatch.setenv("AZURE_DOCINTEL_KEY", "env-key")
    provider = AzureDocIntelProvider()
    assert provider.endpoint == "https://env-endpoint"
    assert provider.key == "env-key"
    assert provider.model_id == "prebuilt-layout"


def test_provider_unconfigured_perform_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AZURE_DOCINTEL_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_DOCINTEL_KEY", raising=False)
    provider = AzureDocIntelProvider()
    with pytest.raises(RuntimeError, match="not configured"):
        provider.perform(b"%PDF-fake", file="scan.pdf")


def test_provider_perform_wires_client_into_transform(monkeypatch: pytest.MonkeyPatch) -> None:
    # Exercise perform() end-to-end offline: a fake SDK client returns the canned layout dict, which
    # perform must route through transform_layout. Verifies the model id + call shape too.
    class _FakeResult:
        def as_dict(self) -> dict:
            return _LAYOUT

    class _FakePoller:
        def result(self) -> _FakeResult:
            return _FakeResult()

    class _FakeClient:
        def begin_analyze_document(self, model_id: str, data: bytes, *, content_type: str) -> _FakePoller:
            assert model_id == "prebuilt-layout"
            assert isinstance(data, bytes)
            assert content_type == "application/octet-stream"
            return _FakePoller()

    provider = AzureDocIntelProvider(endpoint="https://x", key="k")
    monkeypatch.setattr(provider, "_build_client", lambda: _FakeClient())
    regions = provider.perform(b"%PDF-fake", file="scan.pdf")
    assert [r.kind for r in regions] == [
        "paragraph", "paragraph", "table_cell", "table_cell", "table_cell", "table_cell",
    ]
    assert regions[0].page == 1
    assert regions[0].bbox is not None


@pytest.mark.skipif(_AZURE_INSTALLED, reason="azure SDK present; the missing-SDK path is not exercised")
def test_provider_missing_sdk_raises() -> None:
    # Configured but the optional SDK is absent (the intended keyless state) → a clear RuntimeError.
    provider = AzureDocIntelProvider(endpoint="https://x", key="k")
    with pytest.raises(RuntimeError, match="not installed"):
        provider.perform(b"%PDF-fake", file="scan.pdf")


@pytest.mark.live
def test_provider_perform_live_smoke() -> None:  # pragma: no cover - opt-in, needs a real key + SDK
    import os

    if not os.getenv("AZURE_DOCINTEL_ENDPOINT") or not os.getenv("AZURE_DOCINTEL_KEY"):
        pytest.skip("no Azure Document Intelligence key configured")
    if not _AZURE_INSTALLED:
        pytest.skip("azure-ai-documentintelligence not installed")
    provider = AzureDocIntelProvider()
    regions = provider.perform(b"%PDF-1.4\n", file="live.pdf")
    assert isinstance(regions, list)
