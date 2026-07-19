"""Azure AI Document Intelligence OCR provider — the concrete ``OcrProvider`` for the loaders seam.

The loader (``loaders.py``) keeps the rich scanned-PDF path behind a lazy, env-gated ``OcrProvider``
Protocol so the born-digital path never depends on an OCR SDK. This module supplies the one concrete
implementation, split into the two halves the seam was designed around:

* **Client (lazy, network).** ``AzureDocIntelProvider.perform`` imports the ``azure-ai-documentintelligence``
  SDK *only when actually called* and runs the ``prebuilt-layout`` model over the raw bytes. The SDK is an
  **optional extra** — a keyless boot never constructs this provider (``loaders.get_ocr_provider`` returns
  ``None`` without the Azure key), so the absent dependency never takes the app down.
* **Transform (pure, SDK-free).** ``transform_layout`` converts the layout response *dict* into located
  ``Region``s with zero network and zero SDK import, so the whole response-shape mapping is fixture-testable.
  One ``Region`` per paragraph and one per table cell; every region carries its ``page`` and a ``bbox``
  normalised to the unit square ``[0, 1]`` (via the page ``width``/``height``), and table cells additionally
  carry their ``row`` — the locators a claim's ``DocRef`` is later built from (gate G4).

This runs at *ingest* — upstream of ``store.append`` — never inside ``rebuild`` (gate G1); its ``Region``
output is frozen onto the loaded document before any claim is emitted. It is source-typed, not
use-case-typed (gate G9): the layout of a scanned page has nothing to do with who consumes it.

The response shapes accepted are the REST/`as_dict()` forms of the ``prebuilt-layout`` result — camelCase
keys (``pageNumber``, ``boundingRegions``, ``rowIndex``, ``polygon`` …) with a snake_case fallback so a
hand-built or older-SDK response parses too. A bounding region's box may be a flat ``polygon``/``boundingBox``
coordinate list ``[x1, y1, x2, y2, …]`` or a list of ``{"x", "y"}`` points.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from chanakya.ingest.loaders import Region

# Azure model + env gates (mirrors ``loaders.get_ocr_provider``). Kept as constants — no magic strings.
_LAYOUT_MODEL = "prebuilt-layout"
_ENDPOINT_ENV = "AZURE_DOCINTEL_ENDPOINT"
_KEY_ENV = "AZURE_DOCINTEL_KEY"


# ── pure transform (SDK-free, fixture-testable) ──────────────────────────────────────────────────

def _get(mapping: dict[str, Any], *names: str, default: Any = None) -> Any:
    """First present, non-``None`` value among ``names`` (camelCase/snake tolerance), else ``default``."""
    for name in names:
        value = mapping.get(name)
        if value is not None:
            return value
    return default


def _unit(value: float) -> float:
    """Clamp a normalised coordinate into the unit interval ``[0, 1]`` (guards OCR overshoot/rounding)."""
    return 0.0 if value < 0.0 else 1.0 if value > 1.0 else value


def _polygon_bbox(polygon: Any) -> tuple[float, float, float, float] | None:
    """Axis-aligned ``(min_x, min_y, max_x, max_y)`` of a bounding polygon, in raw page units.

    Accepts a flat coordinate list ``[x1, y1, x2, y2, …]`` (the Azure wire form) or a list of
    ``{"x", "y"}`` point dicts. Returns ``None`` when no usable coordinates are present.
    """
    if not polygon:
        return None
    if all(isinstance(v, (int, float)) for v in polygon):
        xs = [float(v) for v in polygon[0::2]]
        ys = [float(v) for v in polygon[1::2]]
    else:
        xs = [float(p["x"]) for p in polygon if isinstance(p, dict) and p.get("x") is not None]
        ys = [float(p["y"]) for p in polygon if isinstance(p, dict) and p.get("y") is not None]
    if not xs or not ys:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def _region_geo(
    bounding_regions: Any,
    pages_dims: dict[int, tuple[float, float]],
) -> tuple[int | None, tuple[float, float, float, float] | None]:
    """``(page, unit-normalised bbox)`` from the first bounding region, or ``(page?, None)``.

    The bbox is normalised by the referenced page's ``width``/``height`` so it is resolution-independent
    (Azure pages may be measured in inches or pixels). A single-page document whose region omits an
    explicit page number falls back to that lone page. Missing dimensions → no bbox (never a fabricated
    one, never a divide-by-zero).
    """
    if not bounding_regions:
        return (None, None)
    br = bounding_regions[0]
    raw_page = _get(br, "pageNumber", "page_number")
    page = int(raw_page) if raw_page is not None else None
    box = _polygon_bbox(_get(br, "polygon", "boundingBox", "bounding_box"))
    if box is None:
        return (page, None)

    dims = pages_dims.get(page) if page is not None else None
    if dims is None and len(pages_dims) == 1:
        only_page, dims = next(iter(pages_dims.items()))
        page = page if page is not None else only_page
    if not dims:
        return (page, None)
    width, height = dims
    if not width or not height:
        return (page, None)

    x0, y0, x1, y1 = box
    bbox = (
        round(_unit(x0 / width), 6),
        round(_unit(y0 / height), 6),
        round(_unit(x1 / width), 6),
        round(_unit(y1 / height), 6),
    )
    return (page, bbox)


def _page_dimensions(response: dict[str, Any]) -> dict[int, tuple[float, float]]:
    """Map ``pageNumber → (width, height)`` for every page that declares both (else it is skipped)."""
    dims: dict[int, tuple[float, float]] = {}
    for index, page in enumerate(response.get("pages") or [], start=1):
        number = _get(page, "pageNumber", "page_number", default=index)
        width = _get(page, "width")
        height = _get(page, "height")
        if width is not None and height is not None:
            dims[int(number)] = (float(width), float(height))
    return dims


def transform_layout(response: dict[str, Any], *, file: str) -> list[Region]:
    """Convert a ``prebuilt-layout`` response *dict* into located ``Region``s (pure — no network/SDK).

    Emits one ``Region`` per paragraph (``kind="paragraph"``, carrying its role in ``name`` if present),
    then one per table cell (``kind="table_cell"``, carrying its ``row`` and an ``r<row>c<col>`` cell
    locator in ``name``). Table cells are ordered by ``(rowIndex, columnIndex)`` so the output is
    deterministic regardless of the provider's cell ordering (byte-stable bundles, gate G9/G11). No
    char ``span`` is set — an OCR'd page has no born-digital text layer, so ``page``/``bbox``/``row``
    are the locators; the loader assembles the flat text from the regions' content.
    """
    pages_dims = _page_dimensions(response)
    regions: list[Region] = []

    for para in response.get("paragraphs") or []:
        page, bbox = _region_geo(_get(para, "boundingRegions", "bounding_regions", default=[]), pages_dims)
        regions.append(
            Region(
                kind="paragraph",
                file=file,
                text=_get(para, "content", default="") or "",
                page=page,
                bbox=bbox,
                name=_get(para, "role"),
            )
        )

    for table in response.get("tables") or []:
        cells = _get(table, "cells", default=[]) or []
        for cell in sorted(
            cells,
            key=lambda c: (
                _get(c, "rowIndex", "row_index", default=0),
                _get(c, "columnIndex", "column_index", default=0),
            ),
        ):
            page, bbox = _region_geo(_get(cell, "boundingRegions", "bounding_regions", default=[]), pages_dims)
            row = _get(cell, "rowIndex", "row_index")
            col = _get(cell, "columnIndex", "column_index")
            name = f"r{row}c{col}" if row is not None and col is not None else None
            regions.append(
                Region(
                    kind="table_cell",
                    file=file,
                    text=_get(cell, "content", default="") or "",
                    page=page,
                    row=int(row) if row is not None else None,
                    bbox=bbox,
                    name=name,
                )
            )

    return regions


# ── provider (lazy network client) ───────────────────────────────────────────────────────────────

class AzureDocIntelProvider:
    """Concrete :class:`~chanakya.ingest.loaders.OcrProvider` backed by Azure AI Document Intelligence.

    Constructed with an explicit ``endpoint``/``key`` or, lazily, from the ``AZURE_DOCINTEL_ENDPOINT`` /
    ``AZURE_DOCINTEL_KEY`` environment variables — never eagerly (a keyless boot never constructs it). The
    SDK import is deferred to :meth:`perform`, so importing this module (and running the pure transform)
    needs neither the optional ``azure-ai-documentintelligence`` dependency nor the network.
    """

    def __init__(self, endpoint: str | None = None, key: str | None = None) -> None:
        self.endpoint = endpoint or os.getenv(_ENDPOINT_ENV)
        self.key = key or os.getenv(_KEY_ENV)
        self.model_id = _LAYOUT_MODEL

    def _build_client(self) -> Any:
        """Lazily import + construct the Azure SDK client; raise a clear error when it is unusable.

        Two distinct failure modes are named explicitly (not swallowed): unconfigured credentials, and
        the optional SDK not being installed. Both surface as ``RuntimeError`` so the caller can degrade.
        """
        if not self.endpoint or not self.key:
            raise RuntimeError(
                f"Azure Document Intelligence is not configured "
                f"(set {_ENDPOINT_ENV} + {_KEY_ENV}, or pass endpoint/key)"
            )
        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential
        except ImportError as exc:  # optional extra, intentionally absent on a keyless boot
            raise RuntimeError(
                "azure-ai-documentintelligence is not installed "
                "(optional OCR extra; install it to enable the Azure scanned-PDF path)"
            ) from exc
        return DocumentIntelligenceClient(self.endpoint, AzureKeyCredential(self.key))

    def perform(self, data: bytes, *, file: str) -> list[Region]:
        """Run ``prebuilt-layout`` OCR over ``data`` → located ``Region``s (network; ingest-time only).

        The SDK response is converted to a plain dict and handed to the pure :func:`transform_layout`,
        keeping all shape logic testable without the SDK. Runs upstream of the append, never inside
        ``rebuild`` (gate G1). ``file`` is stamped on every region for provenance.
        """
        client = self._build_client()
        poller = client.begin_analyze_document(
            self.model_id, data, content_type="application/octet-stream"
        )
        result = poller.result()
        response = result.as_dict() if hasattr(result, "as_dict") else dict(result)
        return transform_layout(response, file=file)


if TYPE_CHECKING:
    # Static conformance guard: the concrete provider must satisfy the loaders OCR seam.
    from chanakya.ingest.loaders import OcrProvider

    _conforms: type[OcrProvider] = AzureDocIntelProvider
