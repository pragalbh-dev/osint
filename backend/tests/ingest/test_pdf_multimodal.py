"""PDF multimodal extraction — page images fed to ONE forced-tool call, windowed only when oversized.

The PDF path now hands the doc text **and** every rendered page image to a single multimodal ``extract``
call so the model reads prose, tables and figures together. A document that exceeds the page/char size
guard is windowed by page (a guard, not the default); each window is its own call and the filled dicts
are merged **before** the single transform pass — so a multi-page PDF is still one doc, deduped and
id-assigned in one deterministic batch (gate G2). All offline/deterministic (a recording client, no net).
"""

from __future__ import annotations

from typing import Any

from chanakya import settings
from chanakya.config.store import ConfigStore
from chanakya.ingest.extract import (
    PDF_CHUNK_MAX_PAGES,
    _merge_filled,
    extract_document,
)
from chanakya.ingest.loaders import LoadedDoc, PageImage, Region
from chanakya.schemas.claim import ClaimRecord, EntityDescriptor
from chanakya.schemas.config_models import ConfigBundle


class _RecordingClient:
    """Records each ``extract`` call's ``(text, images)`` and replays queued filled dicts in order."""

    model_id = "recording"

    def __init__(self, *responses: dict[str, Any]) -> None:
        self._responses = list(responses)
        self._i = 0
        self.calls: list[tuple[str, list[tuple[bytes, str]]]] = []

    def extract(self, *, tool_name: str, input_schema: dict[str, Any], system: str, text: str,
                images: Any = ()) -> dict[str, Any]:
        self.calls.append((text, list(images)))
        out = self._responses[self._i]
        self._i += 1
        return out

    def read_image(self, **_: Any) -> dict[str, Any]:  # pragma: no cover - unused here
        raise AssertionError("read_image must not be called on the PDF multimodal path")


def _config() -> ConfigBundle:
    return ConfigStore.seed_from(settings.config_dir()).snapshot()


def _paged_doc(n_pages: int, *, per_page: int = 120) -> LoadedDoc:
    """A synthetic multi-page ``LoadedDoc`` — one spanned text region + one rendered image per page."""
    parts: list[str] = []
    regions: list[Region] = []
    cursor = 0
    for page in range(1, n_pages + 1):
        text = f"page{page}-marker " + ("x" * per_page)
        start = cursor
        end = start + len(text)
        regions.append(Region(kind="line", file="big.pdf", text=text, span=(start, end),
                              line=1, page=page))
        parts.append(text)
        cursor = end + 1  # +1 for the "\n" joiner
    images = [PageImage(page=p, data=b"\x89PNG-p%d" % p, media_type="image/png")
              for p in range(1, n_pages + 1)]
    return LoadedDoc(file="big.pdf", media_type="application/pdf", modality="text",
                     text="\n".join(parts), regions=regions, page_images=images)


def _sources(claims: list[ClaimRecord]) -> list[str]:
    return [c.payload.name for c in claims
            if isinstance(c.payload, EntityDescriptor) and c.payload.entity_type == "source"]


# ── one call carries the page images (the common, non-oversized case) ─────────────────────────────

def test_single_call_feeds_all_page_images() -> None:
    doc = _paged_doc(2)
    client = _RecordingClient({"sources": [{"name": "SIPRI", "source_quote": "page1-marker"}]})
    claims = extract_document(doc, source_id="p", source_type="curated-register",
                              config=_config(), client=client, format_hint="prose_claim")
    assert len(client.calls) == 1                      # not oversized → exactly one call
    _, images = client.calls[0]
    assert [m for _, m in images] == ["image/png", "image/png"]  # both pages' images attached
    assert images[0][0] == b"\x89PNG-p1"
    assert "SIPRI" in _sources(claims)


# ── an oversized doc is windowed by page; the filled dicts merge into one transform pass ──────────

def test_oversized_pdf_is_windowed_and_merged() -> None:
    n = PDF_CHUNK_MAX_PAGES + 2  # 10 pages → exceeds the page guard → windowed
    doc = _paged_doc(n)
    client = _RecordingClient(
        {"sources": [{"name": "WindowOneSrc", "source_quote": "page1-marker"}]},
        {"sources": [{"name": "WindowTwoSrc", "source_quote": "page9-marker"}]},
    )
    claims = extract_document(doc, source_id="big", source_type="curated-register",
                              config=_config(), client=client, format_hint="prose_claim")

    # two windows: pages 1..8 then 9..10 → two calls
    assert len(client.calls) == 2
    win1_images = client.calls[0][1]
    win2_images = client.calls[1][1]
    assert len(win1_images) == PDF_CHUNK_MAX_PAGES and len(win2_images) == 2
    # each window's text is a contiguous substring of the doc (provenance find still works)
    assert "page1-marker" in client.calls[0][0] and "page9-marker" in client.calls[1][0]
    assert "page9-marker" not in client.calls[0][0]

    # the merged filled dicts yield BOTH windows' claims in one deduped batch
    names = _sources(claims)
    assert "WindowOneSrc" in names and "WindowTwoSrc" in names
    # provenance survives: every source claim resolves to a page
    for c in claims:
        if isinstance(c.payload, EntityDescriptor) and c.payload.entity_type == "source":
            assert c.doc_ref.page in range(1, n + 1)


# ── the merge helper: list fields concatenate, scalars/objects take first non-empty ───────────────

def test_merge_filled_concatenates_lists_and_keeps_first_scalar() -> None:
    merged = _merge_filled([
        {"rows": [{"gd_no": "A"}], "tender_id": "T-1", "oem": {"name": "CPMIEC"}},
        {"rows": [{"gd_no": "B"}], "tender_id": "T-2", "oem": {"name": "OTHER"}},
    ])
    assert [r["gd_no"] for r in merged["rows"]] == ["A", "B"]  # lists concatenated
    assert merged["tender_id"] == "T-1"                        # first non-empty scalar wins
    assert merged["oem"] == {"name": "CPMIEC"}                 # first non-empty object wins


def test_merge_filled_single_part_passthrough() -> None:
    part = {"sources": [{"name": "X"}]}
    assert _merge_filled([part]) is part
