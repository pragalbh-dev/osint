"""Resolve a claim's ``doc_ref`` back to the **verbatim text it cites** — the last hop of
one-click-to-source.

The evidence log stores a *locator* (file + char span / line / row / page), not the words. A locator
is enough to be auditable in principle, but ``d19_rahwali_confirm.txt · L11 · 843–849`` is a pointer,
not a source: an analyst reading the drawer cannot check the claim without leaving the app. This
module reads the cited span back out of the document **at request time** and hands it over untouched.

Three rules make that safe:

* **Never stored.** The quote is derived on read, so it cannot drift away from the append-only claim
  it belongs to. If the doc changed under us, the drawer shows what the doc says *now* — which is the
  honest thing to show, and the locator is still displayed beside it.
* **Never reconstructed.** No span (or an unreadable/foreign file) yields ``""``, and the UI falls
  back to the locator alone. A missing quote is never paraphrased, summarised, or inferred from the
  claim payload — that would be exactly the fabrication the non-negotiable forbids.
* **Never escapes the repo.** Only files resolving inside the repo root are read, so a doc_ref cannot
  be used to exfiltrate an arbitrary path.
"""

from __future__ import annotations

from pathlib import Path

from chanakya import settings
from chanakya.schemas import ClaimRecord, DocRef

# A cited source doc is prose/CSV, not a blob. Anything larger is not something we quote a span out of.
MAX_DOC_BYTES = 4_000_000
# The drawer shows a quote, not a chapter. Longer spans are cut on a word boundary with an explicit
# ellipsis, so the analyst can always see that they are looking at a truncation.
MAX_QUOTE_CHARS = 700

# (resolved path, mtime_ns, size) -> text. Keyed on the stat so a re-ingested/edited doc is re-read
# rather than served stale; bounded so a long session cannot grow without limit.
_CACHE: dict[tuple[str, int, int], str] = {}
_CACHE_MAX = 64


def _read_doc(rel_or_abs: str) -> str | None:
    """Read a cited doc as text, or ``None`` if it is missing/outside the repo/too big/not text."""
    root = settings.repo_root().resolve()
    raw = Path(rel_or_abs)
    path = (raw if raw.is_absolute() else root / raw).resolve()
    if root not in path.parents and path != root:
        return None  # a doc_ref must not be able to read outside the repo
    try:
        stat = path.stat()
        if not path.is_file() or stat.st_size > MAX_DOC_BYTES:
            return None
        key = (str(path), stat.st_mtime_ns, stat.st_size)
        hit = _CACHE.get(key)
        if hit is not None:
            return hit
        text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        return None
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.clear()
    _CACHE[key] = text
    return text


def _truncate(text: str) -> str:
    if len(text) <= MAX_QUOTE_CHARS:
        return text
    cut = text[:MAX_QUOTE_CHARS]
    space = cut.rfind(" ")
    return (cut[:space] if space > MAX_QUOTE_CHARS // 2 else cut).rstrip() + "…"


def quote_for(ref: DocRef) -> str:
    """The verbatim text at one ``DocRef`` — span first, then line, then nothing. Never invents."""
    text = _read_doc(ref.file)
    if text is None:
        return ""
    if ref.span is not None:
        start, end = ref.span
        if 0 <= start < end <= len(text):
            return _truncate(" ".join(text[start:end].split()))
    if ref.line is not None and ref.line >= 1:
        lines = text.splitlines()
        if ref.line <= len(lines):
            return _truncate(" ".join(lines[ref.line - 1].split()))
    # row/page/frame/region locators point into structure this module cannot slice — the drawer
    # shows the locator alone rather than a guess at what it contains.
    return ""


def quotes_for(claims: list[ClaimRecord]) -> dict[str, list[str]]:
    """``claim_id -> [verbatim per doc_ref]``, positionally parallel to ``claim.doc_refs()``.

    Claims whose every ref came back empty are omitted, so the payload carries evidence rather than
    a row of blanks.
    """
    out: dict[str, list[str]] = {}
    for claim in claims:
        spans = [quote_for(ref) for ref in claim.doc_refs()]
        if any(spans):
            out[claim.claim_id] = spans
    return out
