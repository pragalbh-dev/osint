"""Source-typed document loaders — normalise any raw input to **(text, regions[])** *before* the
single extraction call (INGEST session, item 1a).

The loader is where per-source **input** handling lives; its **output** is always the same
source-agnostic pair — a flat ``text`` string plus a list of ``Region``s that locate every piece of
that text back in the original document. A ``Region``'s locator (``span``/``line``/``row``/``page``/
``bbox``) is what a claim's ``DocRef`` is built from, so "one click to the exact source" (gate G4)
falls out structurally. Dispatch is keyed on **file type only** — never on subject/use-case (G9): a
customs doc loads identically regardless of who consumes it.

Design (patterns adapted from the `ai_extraction_v2` OCR stack — *patterns, not code*):

* **Provider seam.** The rich PDF/OCR path is a lazy, env-gated ``OcrProvider`` split into a network
  *client* and a pure *transform*, so the transform is fixture-testable with zero network. When no
  OCR key is present the loader **degrades to the keyless born-digital path** (``pdftotext``) — it
  never refuses to start (the reference's one anti-pattern, inverted here).
* **Positional provenance, three axes.** char ``span`` into the assembled ``text`` (exact highlight),
  a 1-indexed ``line`` (the human-readable ``.txt`` locator), and ``page``/``bbox`` for PDFs. Line
  numbers are derived once by a prefix-sum over newline offsets. Images carry no text locator (nothing
  required for images — a whole-image region only).
* **Explicit-empty sentinel.** A loader that finds no extractable text returns a ``LoadedDoc`` with
  ``regions == []`` and ``meta["empty"] = True`` rather than a silent empty success — feeding the
  "insufficient evidence, name what's missing" discipline downstream.

Nothing here touches the ontology, resolves an entity, or calls an LLM — the VLM read of an image and
the LLM extraction of text both run *downstream* of the loader (extract.py), upstream of the append.
"""

from __future__ import annotations

import bisect
from collections.abc import Iterable
from html.parser import HTMLParser
from pathlib import PurePosixPath
from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from chanakya.schemas.claim import DocRef

# ── media-type dispatch ────────────────────────────────────────────────────────────────────────

# Extension → the loader family. Kept small + explicit (the reference's queue-based worker-per-type
# split is over-engineered for a single-process loader — a dispatch dict is enough).
_TEXT_EXT = {".txt", ".text", ".md", ".csv", ".tsv", ".log"}
_HTML_EXT = {".html", ".htm", ".xhtml"}
_PDF_EXT = {".pdf"}
_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp", ".gif"}

Modality = Literal["text", "image"]
RegionKind = Literal["line", "paragraph", "table_cell", "page", "image"]


# ── the positional model ───────────────────────────────────────────────────────────────────────

class Region(BaseModel):
    """One located element of a document — the loader's unit of provenance.

    A region carries its **content** (``text``) plus one or more **locators** into the source. The
    ``span`` is always a char range into the owning ``LoadedDoc.text`` (so highlighting is exact); the
    other locators are format-specific. ``to_doc_ref()`` projects a region onto the F0 ``DocRef``.
    """

    model_config = ConfigDict(extra="forbid")

    kind: RegionKind
    file: str
    text: str = ""
    span: tuple[int, int] | None = None  # [start, end) char offsets into LoadedDoc.text
    line: int | None = None  # 1-indexed line (text docs)
    row: int | None = None  # table/record row (customs manifest)
    page: int | None = None  # 1-indexed PDF page
    bbox: tuple[float, float, float, float] | None = None  # [x0,y0,x1,y1] normalised to [0,1]
    name: str | None = None  # a named image region ("full", "central berm")

    def to_doc_ref(self) -> DocRef:
        """Project this region onto an F0 ``DocRef`` (the claim-side provenance locator)."""
        return DocRef(
            file=self.file,
            span=self.span,
            line=self.line,
            row=self.row,
            page=self.page,
            bbox=self.bbox,
            region=self.name,
        )


class LoadedDoc(BaseModel):
    """The uniform loader output: assembled ``text`` + located ``regions`` + modality.

    ``raw_bytes`` is populated only for images (the VLM reads them downstream). ``locate`` / ``doc_ref``
    are the helpers the extractor+transformer use to attach exact provenance to a claim given the char
    span the extraction identified.
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    file: str
    media_type: str
    modality: Modality
    text: str = ""
    regions: list[Region] = []
    raw_bytes: bytes | None = None
    meta: dict[str, object] = {}

    # ── provenance helpers ──────────────────────────────────────────────────────────────────────

    def locate(self, start: int, end: int) -> list[Region]:
        """Regions whose ``span`` overlaps the half-open char range ``[start, end)``."""
        hits = []
        for r in self.regions:
            if r.span is None:
                continue
            rs, re = r.span
            if rs < end and start < re:  # overlap
                hits.append(r)
        return hits

    def doc_ref(self, start: int, end: int) -> DocRef:
        """Build a ``DocRef`` for a stated char span — exact ``span`` + the line the span starts on.

        This is the primary claim-provenance path for text docs: the extractor reports where in the
        assembled text a claim was stated, and this stamps the exact + human-readable locator.
        """
        overlapping = self.locate(start, end)
        line = overlapping[0].line if overlapping else None
        page = overlapping[0].page if overlapping else None
        return DocRef(file=self.file, span=(start, end), line=line, page=page)


# ── OCR provider seam (lazy, env-gated) ──────────────────────────────────────────────────────────

@runtime_checkable
class OcrProvider(Protocol):
    """A pluggable OCR backend for scanned/complex PDFs. ``perform`` is the *only* required method.

    Implementations (e.g. Azure AI Document Intelligence) own the network call + the transform of the
    provider response into ``Region``s (page + bbox + table cells). Kept behind this Protocol so the
    born-digital path never depends on the OCR SDK, and so tests inject a fake provider offline.
    """

    def perform(self, data: bytes, *, file: str) -> list[Region]: ...


def get_ocr_provider() -> OcrProvider | None:
    """Return a configured OCR provider, or ``None`` when no key is present (keyless boot).

    Env-gated on ``AZURE_DOCINTEL_ENDPOINT`` + ``AZURE_DOCINTEL_KEY`` (like the LLM key). Constructed
    lazily and tolerantly: a missing key yields ``None`` (→ born-digital fallback), never an exception,
    so the loader is never taken down by an absent optional provider.
    """
    import os

    endpoint = os.getenv("AZURE_DOCINTEL_ENDPOINT")
    key = os.getenv("AZURE_DOCINTEL_KEY")
    if not endpoint or not key:
        return None
    # Concrete Azure provider is a separate slice (needs the azure-ai-documentintelligence SDK dep);
    # the seam + selection logic + born-digital fallback are what this module owns. Until it lands,
    # a configured-but-unbuilt provider still degrades gracefully rather than crashing the loader.
    return None


# ── text ─────────────────────────────────────────────────────────────────────────────────────────

def _line_starts(text: str) -> list[int]:
    """Char offset at which each line begins — prefix-sum over newline positions (pure, O(n))."""
    starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            starts.append(i + 1)
    return starts


def _line_of(offset: int, line_starts: list[int]) -> int:
    """1-indexed line number containing char ``offset`` (``bisect`` over the prefix-sum)."""
    return bisect.bisect_right(line_starts, offset)


def _text_regions(text: str, file: str) -> list[Region]:
    """One ``Region`` per line — a uniform, record-per-line model (a customs BoL row *is* a line)."""
    regions: list[Region] = []
    cursor = 0
    for lineno, raw in enumerate(text.split("\n"), start=1):
        start = cursor
        end = start + len(raw)
        # Skip purely-blank lines as regions (they carry no citable content) but keep the char cursor
        # advancing so spans stay aligned to the original text.
        if raw.strip():
            regions.append(
                Region(kind="line", file=file, text=raw, span=(start, end), line=lineno, row=lineno)
            )
        cursor = end + 1  # +1 for the consumed "\n"
    return regions


def load_text(text: str, file: str, *, media_type: str = "text/plain") -> LoadedDoc:
    """Load a plain-text document: the text *is* the payload; per-line regions carry the locators."""
    regions = _text_regions(text, file)
    return LoadedDoc(
        file=file,
        media_type=media_type,
        modality="text",
        text=text,
        regions=regions,
        meta={"line_count": text.count("\n") + 1, "empty": not regions},
    )


# ── html ─────────────────────────────────────────────────────────────────────────────────────────

class _BoilerplateStripper(HTMLParser):
    """Minimal stdlib boilerplate strip — drops ``<script>/<style>`` bodies, keeps visible text.

    Deliberately dependency-free (no bs4): HTML is a *seam* here (the frozen corpus is ``.txt`` +
    ``.png``), so a lightweight, well-behaved strip beats pulling a parser dep for an unexercised path.
    """

    _DROP = {"script", "style", "head", "meta", "link", "noscript"}
    _BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article"}

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: object) -> None:
        if tag in self._DROP:
            self._skip += 1
        elif tag in self._BLOCK:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._DROP and self._skip:
            self._skip -= 1
        elif tag in self._BLOCK:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip and data.strip():
            self._chunks.append(data)

    def text(self) -> str:
        # Collapse runs of blank lines the block tags introduced; keep single newlines as structure.
        raw = "".join(self._chunks)
        lines = [ln.strip() for ln in raw.splitlines()]
        out: list[str] = []
        for ln in lines:
            if ln or (out and out[-1]):
                out.append(ln)
        return "\n".join(out).strip()


def load_html(html: str, file: str) -> LoadedDoc:
    """Strip HTML boilerplate to visible text, then load it as text (regions on the stripped text)."""
    stripper = _BoilerplateStripper()
    stripper.feed(html)
    doc = load_text(stripper.text(), file, media_type="text/html")
    doc.meta["stripped_from_html"] = True
    return doc


# ── image ────────────────────────────────────────────────────────────────────────────────────────

def load_image(data: bytes, file: str, *, media_type: str | None = None) -> LoadedDoc:
    """Package an image: no text (the VLM reads it downstream), one whole-image region + raw bytes.

    Two-hash integrity (sha256 + PDQ) and the VLM read are separate concerns (INGEST item 6) — the
    loader only carries the bytes + a citable image region so provenance exists before any read.
    """
    ext = PurePosixPath(file).suffix.lower()
    media_type = media_type or {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".tif": "image/tiff", ".tiff": "image/tiff",
        ".bmp": "image/bmp", ".gif": "image/gif",
    }.get(ext, "application/octet-stream")
    return LoadedDoc(
        file=file,
        media_type=media_type,
        modality="image",
        text="",
        regions=[Region(kind="image", file=file, name="full")],
        raw_bytes=data,
        meta={"bytes": len(data)},
    )


# ── pdf (born-digital keyless path + OCR seam) ───────────────────────────────────────────────────

def _pdftotext_available() -> bool:
    import shutil

    return shutil.which("pdftotext") is not None


def _pdf_page_texts(data: bytes) -> list[str]:
    """Born-digital per-page text via poppler ``pdftotext`` (keyless). One string per page.

    Isolated in its own function so tests monkeypatch it instead of needing a real PDF on disk.
    Raises ``RuntimeError`` if poppler is unavailable (the caller decides whether OCR can cover it).
    """
    import subprocess
    import tempfile

    if not _pdftotext_available():
        raise RuntimeError("pdftotext (poppler) not available for the born-digital PDF path")
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tf:
        tf.write(data)
        tf.flush()
        # -layout preserves reading order; the ASCII form-feed (\x0c) delimits pages in pdftotext.
        out = subprocess.run(
            ["pdftotext", "-layout", tf.name, "-"],
            capture_output=True, timeout=120, check=True,
        )
    return out.stdout.decode("utf-8", errors="replace").split("\f")


def load_pdf(data: bytes, file: str, *, ocr: OcrProvider | None = None) -> LoadedDoc:
    """Load a PDF to (text, regions). Born-digital pages via ``pdftotext``; scanned pages via ``ocr``.

    Per page: use the born-digital text layer when present; if a page has no text layer **and** an OCR
    provider is configured, hand that page to OCR (page + bbox regions). With neither, the page yields
    no regions (a coverage gap, surfaced — never a fabricated read).
    """
    ocr = ocr if ocr is not None else get_ocr_provider()
    try:
        page_texts = _pdf_page_texts(data)
    except RuntimeError:
        page_texts = []

    if not any(p.strip() for p in page_texts) and ocr is not None:
        ocr_regions = ocr.perform(data, file=file)
        text = "\n".join(r.text for r in ocr_regions)
        return LoadedDoc(file=file, media_type="application/pdf", modality="text",
                         text=text, regions=ocr_regions, meta={"ocr": True, "empty": not ocr_regions})

    # Born-digital: assemble one text string across pages, tracking per-page + per-line spans.
    regions: list[Region] = []
    parts: list[str] = []
    cursor = 0
    for pageno, ptext in enumerate(page_texts, start=1):
        if parts:  # page separator in the assembled text
            parts.append("\n")
            cursor += 1
        page_start = cursor
        for lineno, raw in enumerate(ptext.split("\n"), start=1):
            start = cursor
            end = start + len(raw)
            if raw.strip():
                regions.append(Region(kind="line", file=file, text=raw, span=(start, end),
                                      line=lineno, page=pageno))
            cursor = end + 1
        parts.append(ptext)
        cursor = page_start + len(ptext)
    text = "".join(parts)
    return LoadedDoc(file=file, media_type="application/pdf", modality="text", text=text,
                     regions=regions, meta={"pages": len(page_texts), "empty": not regions})


# ── dispatch ─────────────────────────────────────────────────────────────────────────────────────

def load_document(
    data: str | bytes,
    *,
    file: str,
    media_type: str | None = None,
    ocr: OcrProvider | None = None,
) -> LoadedDoc:
    """Normalise any raw input to ``LoadedDoc`` (text + located regions), keyed on file type only (G9).

    ``file`` supplies the extension used for dispatch (and is stamped on every region for traceability).
    ``data`` is ``str`` for text/html and ``bytes`` for pdf/image; a ``str`` for a binary type is
    encoded utf-8, and ``bytes`` for a text type is decoded utf-8 (tolerant to how a caller passes it).
    """
    ext = PurePosixPath(file).suffix.lower()

    if ext in _IMAGE_EXT:
        raw = data.encode("utf-8") if isinstance(data, str) else data
        return load_image(raw, file, media_type=media_type)
    if ext in _PDF_EXT:
        raw = data.encode("utf-8") if isinstance(data, str) else data
        return load_pdf(raw, file, ocr=ocr)

    text = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else data
    if ext in _HTML_EXT:
        return load_html(text, file)
    if ext in _TEXT_EXT or ext == "":
        return load_text(text, file, media_type=media_type or "text/plain")

    # Unknown extension: treat as text (tolerant), but flag it so a caller can notice the guess.
    doc = load_text(text, file, media_type=media_type or "application/octet-stream")
    doc.meta["unknown_extension"] = ext
    return doc


def doc_refs_for_regions(regions: Iterable[Region]) -> list[DocRef]:
    """Convenience: project a set of regions to ``DocRef``s (e.g. a within-doc restatement group)."""
    return [r.to_doc_ref() for r in regions]
