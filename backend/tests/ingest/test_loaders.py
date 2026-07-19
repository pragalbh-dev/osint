"""Loader tests — the (text, regions[]) contract + exact positional provenance (INGEST item 1a).

The load-bearing invariant, asserted for every text region: ``doc.text[span] == region.text`` — the
char span points at *exactly* the stated text (gate G4, "one click to the exact source").
"""

from __future__ import annotations

import pytest

from chanakya.ingest import loaders
from chanakya.ingest.loaders import (
    LoadedDoc,
    Region,
    load_document,
    load_html,
    load_image,
    load_pdf,
    load_text,
)


def _assert_spans_exact(doc: LoadedDoc) -> None:
    """Every text region's char span must slice back to its own text (provenance integrity)."""
    for r in doc.regions:
        if r.span is not None and r.kind != "image":
            s, e = r.span
            assert doc.text[s:e] == r.text, f"span {r.span} != {r.text!r} (got {doc.text[s:e]!r})"


# ── text ─────────────────────────────────────────────────────────────────────────────────────────

def test_text_line_and_span_provenance() -> None:
    text = "SIPRI register entry\nHQ-9 transfer to Pakistan, 2021\n2 systems delivered"
    doc = load_text(text, "d01_sipri_transfer.txt")
    assert doc.modality == "text"
    assert doc.media_type == "text/plain"
    assert [r.line for r in doc.regions] == [1, 2, 3]
    _assert_spans_exact(doc)
    # doc_ref for a span inside line 2 carries the exact span + the human-readable line number.
    start = text.index("2021")
    ref = doc.doc_ref(start, start + 4)
    assert ref.span == (start, start + 4)
    assert ref.line == 2
    assert doc.text[ref.span[0]:ref.span[1]] == "2021"


def test_text_blank_lines_skipped_but_spans_stay_aligned() -> None:
    text = "line one\n\n\nline four"
    doc = load_text(text, "d.txt")
    # Blank lines carry no citable content → no region, but line numbers of real lines are preserved.
    assert [r.line for r in doc.regions] == [1, 4]
    assert [r.text for r in doc.regions] == ["line one", "line four"]
    _assert_spans_exact(doc)


def test_text_locate_returns_overlapping_regions() -> None:
    text = "alpha\nbravo\ncharlie"
    doc = load_text(text, "d.txt")
    hits = doc.locate(0, 3)  # inside "alpha"
    assert [r.text for r in hits] == ["alpha"]
    # A span crossing the alpha/bravo boundary overlaps both lines.
    hits2 = doc.locate(3, text.index("bravo") + 2)
    assert {r.text for r in hits2} == {"alpha", "bravo"}


def test_text_region_maps_to_doc_ref() -> None:
    doc = load_text("only line", "d.txt")
    ref = doc.regions[0].to_doc_ref()
    assert ref.file == "d.txt"
    assert ref.line == 1
    assert ref.span == (0, 9)
    assert ref.row == 1  # a record-per-line locator too (customs BoL row)


def test_empty_text_flags_empty() -> None:
    doc = load_text("   \n  \n", "blank.txt")
    assert doc.regions == []
    assert doc.meta["empty"] is True


# ── html ─────────────────────────────────────────────────────────────────────────────────────────

def test_html_strips_boilerplate_keeps_visible_text() -> None:
    html = (
        "<html><head><style>.x{color:red}</style><title>t</title></head>"
        "<body><script>evil()</script><p>HQ-9 fielded at Karachi</p>"
        "<p>Second paragraph</p></body></html>"
    )
    doc = load_html(html, "page.html")
    assert doc.media_type == "text/html"
    assert doc.meta.get("stripped_from_html") is True
    assert "evil()" not in doc.text
    assert "color:red" not in doc.text
    assert "HQ-9 fielded at Karachi" in doc.text
    assert "Second paragraph" in doc.text
    _assert_spans_exact(doc)


# ── image ────────────────────────────────────────────────────────────────────────────────────────

def test_image_carries_bytes_and_whole_image_region() -> None:
    data = b"\x89PNG\r\n\x1a\n fake pixels"
    doc = load_image(data, "d07_sat_confirm_karachi.png")
    assert doc.modality == "image"
    assert doc.media_type == "image/png"
    assert doc.text == ""
    assert doc.raw_bytes == data
    assert len(doc.regions) == 1
    assert doc.regions[0].kind == "image"
    assert doc.regions[0].to_doc_ref().region == "full"
    # No text locator for an image (nothing required for images).
    assert doc.regions[0].to_doc_ref().span is None
    assert doc.regions[0].to_doc_ref().line is None


# ── pdf ──────────────────────────────────────────────────────────────────────────────────────────

def test_pdf_born_digital_multipage_spans(monkeypatch: pytest.MonkeyPatch) -> None:
    # Monkeypatch the poppler call so the test needs no real PDF and no subprocess.
    monkeypatch.setattr(loaders, "_pdf_page_texts", lambda data: ["line1\nline2", "page2 only line"])
    doc = load_pdf(b"%PDF-fake", "spec.pdf")
    assert doc.media_type == "application/pdf"
    assert doc.meta["pages"] == 2
    # page + line locators on every region, and exact span alignment across the page break.
    assert [(r.page, r.line, r.text) for r in doc.regions] == [
        (1, 1, "line1"), (1, 2, "line2"), (2, 1, "page2 only line"),
    ]
    _assert_spans_exact(doc)


def test_pdf_scanned_falls_back_to_ocr_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    # A born-digital extract with no text layer (scanned) + a configured OCR provider → OCR regions.
    monkeypatch.setattr(loaders, "_pdf_page_texts", lambda data: ["", "  \n "])

    class FakeOcr:
        def perform(self, data: bytes, *, file: str) -> list[Region]:
            return [Region(kind="paragraph", file=file, text="OCR read", page=1,
                           bbox=(0.1, 0.1, 0.9, 0.2), span=(0, 8))]

    doc = load_pdf(b"%PDF-scanned", "scan.pdf", ocr=FakeOcr())
    assert doc.meta["ocr"] is True
    assert doc.text == "OCR read"
    assert doc.regions[0].bbox == (0.1, 0.1, 0.9, 0.2)
    assert doc.regions[0].to_doc_ref().page == 1


def test_pdf_no_text_no_ocr_is_explicit_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(loaders, "_pdf_page_texts", lambda data: [""])
    doc = load_pdf(b"%PDF", "scan.pdf", ocr=None)
    assert doc.regions == []
    assert doc.meta["empty"] is True


def test_get_ocr_provider_none_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AZURE_DOCINTEL_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_DOCINTEL_KEY", raising=False)
    assert loaders.get_ocr_provider() is None


# ── dispatch ─────────────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("file", "modality"),
    [("a.txt", "text"), ("a.text", "text"), ("a.csv", "text"),
     ("a.html", "text"), ("a.png", "image"), ("a.jpg", "image")],
)
def test_dispatch_by_extension(file: str, modality: str) -> None:
    data: str | bytes = b"bytes" if modality == "image" else "some text"
    doc = load_document(data, file=file)
    assert doc.modality == modality


def test_dispatch_bytes_for_text_are_decoded() -> None:
    doc = load_document(b"decoded from bytes", file="d.txt")
    assert doc.text == "decoded from bytes"
    assert doc.regions[0].text == "decoded from bytes"


def test_dispatch_unknown_extension_treated_as_text_and_flagged() -> None:
    doc = load_document("payload", file="mystery.xyz")
    assert doc.modality == "text"
    assert doc.meta["unknown_extension"] == ".xyz"
