"""``chanakya.api.quotes`` — resolving a ``doc_ref`` back to the VERBATIM text it cites.

The drawer's one-click-to-source used to end at ``d18_rahwali_pass1.txt · L16 · 1092–1249``. That is a
pointer, not a source: an analyst cannot audit a claim from a byte range. These tests pin the three
properties that make reading the span back safe — it is the document's own words, an unreadable span
yields nothing rather than a paraphrase, and a doc_ref cannot read outside the repo.
"""

from __future__ import annotations

from chanakya import settings
from chanakya.api import quotes as q
from chanakya.schemas import ClaimRecord, DocRef, Triple

DOC = "corpus/scenarios/hq9p_primary/docs/d18_rahwali_pass1.txt"


def _claim(claim_id: str, refs: list[DocRef]) -> ClaimRecord:
    return ClaimRecord(
        claim_id=claim_id,
        source_id="s",
        doc_ref=refs,
        kind="observation",
        asserts="relationship",
        payload=Triple(subject="a", predicate="based-at", object="b"),
    )


def test_span_resolves_to_the_documents_own_words() -> None:
    text = (settings.repo_root() / DOC).read_text(encoding="utf-8")
    quote = q.quote_for(DocRef(file=DOC, span=(309, 572)))
    assert quote  # the corpus doc is committed; this is a real span from the real d18 claim
    assert "Rahwali airfield" in quote
    # verbatim: every word of the quote comes out of the cited document, nothing added
    assert " ".join(text[309:572].split()) == quote


def test_line_locator_is_used_when_no_span_is_recorded() -> None:
    quote = q.quote_for(DocRef(file=DOC, line=10))
    assert quote.startswith("A single commercial electro-optical satellite pass")


def test_unreadable_or_structural_locator_yields_empty_never_a_guess() -> None:
    # a row/page locator points into structure this module cannot slice
    assert q.quote_for(DocRef(file=DOC, row=3)) == ""
    # a span past the end of the doc is not silently clamped to "something nearby"
    assert q.quote_for(DocRef(file=DOC, span=(10**9, 10**9 + 5))) == ""
    assert q.quote_for(DocRef(file="corpus/scenarios/hq9p_primary/docs/does_not_exist.txt", line=1)) == ""


def test_doc_ref_cannot_read_outside_the_repo() -> None:
    assert q.quote_for(DocRef(file="/etc/passwd", line=1)) == ""
    assert q.quote_for(DocRef(file="../../../../etc/passwd", line=1)) == ""


def test_quotes_for_is_parallel_to_doc_refs_and_omits_all_empty_claims() -> None:
    claim = _claim("c1", [DocRef(file=DOC, span=(309, 572)), DocRef(file=DOC, row=99)])
    empty = _claim("c2", [DocRef(file="nope.txt", line=1)])
    out = q.quotes_for([claim, empty])
    assert list(out) == ["c1"]  # a claim with nothing readable is omitted, not padded with blanks
    assert len(out["c1"]) == 2 and out["c1"][0] and out["c1"][1] == ""


def test_long_span_is_truncated_visibly_rather_than_silently() -> None:
    text = (settings.repo_root() / DOC).read_text(encoding="utf-8")
    assert len(text) > q.MAX_QUOTE_CHARS, "fixture doc must be long enough to truncate"
    quote = q.quote_for(DocRef(file=DOC, span=(0, len(text))))
    assert quote.endswith("…")
    assert len(quote) <= q.MAX_QUOTE_CHARS + 1
