"""Within-doc claim de-duplication + deterministic claim-ID assignment (INGEST, master §3.1).

Two pure, offline passes the lane runs *after* extraction and *before* ``store.append`` — both
strictly upstream of ``rebuild()`` (gate G1): they only reshape already-frozen ``ClaimRecord``s, and
call no LLM/VLM, no geocoder, no clock, no RNG.

* :func:`dedup_within_doc` — a source that *restates the same assertion* (the same sentence twice, a
  headline echoed in the body) should yield **one** claim carrying **many** provenance spans, not two
  near-identical claims (master §3.1). Members are grouped by a **lexical signature over the stated
  content** — normalised subject/predicate/object (or entity/event) strings plus the full stated
  payload — *scoped to one document*. This is deliberately **not** entity resolution: two
  differently-worded assertions never merge, and two identical assertions in **different** documents
  never merge (that corroboration is RESOLVE/SCORE's job, on the knowledge layer). The signature is a
  *superset* of the minimal ``(kind, polarity, asserts, s/p/o)`` key — it folds in the structured
  object value, event fields, premises and target so the pass errs toward *keeping* two claims apart
  (an audit-safe direction) and never silently drops a distinct assertion.

* :func:`assign_claim_ids` — mints the human-readable ``<doc>-<locator>`` claim IDs (``schemas.ids``)
  in a **deterministic serial pass**: claims are ordered by their earliest provenance span (then a
  content tiebreak), and each is stamped from the locator of that span (``row12`` / ``l3`` / an image
  region), with a running index disambiguating collisions (``d02-l3-2``). Because the order is derived
  from content — never input order — the same set of claims mints byte-identical IDs on every run
  (gate G9/G10), which is what makes the frozen bundles reproducible.

Neither pass touches the ontology, an anchor, or a subject (gates G9/G11): grouping is a string
comparison over what the source *stated*, and ID minting is positional. Nothing here branches on a
use case.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from typing import Any

from chanakya.schemas import ClaimRecord, DocRef, make_claim_id

# A total-order key over a ``DocRef``: the exact span, then the coarser locators, then the image
# locators, then file — missing numeric locators sort last via ``+inf`` so a precise span always
# wins. Every position is internally homogeneous (all float, or all str) so the tuple is comparable.
_SortKey = tuple[float, float, float, float, float, float, float, float, float, float, str, str]
_INF = math.inf

# The stated free-text fields normalised lexically before they enter a signature (case + whitespace
# only — never a rename/resolution). Structured value objects are compared by their canonical dump.
_TEXT_FIELDS = ("subject", "predicate", "object", "name", "entity_type", "event_type")


# ── lexical + positional keys ────────────────────────────────────────────────────────────────────

def _normalize_text(value: str) -> str:
    """Collapse internal whitespace and casefold — the lexical normalisation for a stated string.

    This is a *within-string* clean-up (``"HQ-9  "`` ≡ ``"hq-9"``), never a cross-string decision that
    two different surface forms name the same entity (that is RESOLVE's job — the extract-raw guardrail).
    """
    return " ".join(value.split()).casefold()


def _docref_sort_key(ref: DocRef) -> _SortKey:
    """Project a ``DocRef`` onto a comparable ``_SortKey`` (exact span first, file last)."""
    span = ref.span if ref.span is not None else (_INF, _INF)
    bbox = ref.bbox if ref.bbox is not None else (_INF, _INF, _INF, _INF)
    return (
        float(span[0]),
        float(span[1]),
        float(ref.line) if ref.line is not None else _INF,
        float(ref.row) if ref.row is not None else _INF,
        float(ref.page) if ref.page is not None else _INF,
        float(ref.frame) if ref.frame is not None else _INF,
        float(bbox[0]),
        float(bbox[1]),
        float(bbox[2]),
        float(bbox[3]),
        ref.region or "",
        ref.file,
    )


def _earliest_docref_key(claim: ClaimRecord) -> _SortKey:
    """The sort key of a claim's *first* provenance span — its position in the source."""
    refs = claim.doc_refs()
    if not refs:
        return _docref_sort_key(DocRef(file=""))
    return min(_docref_sort_key(ref) for ref in refs)


# ── content signature (the lexical dedup key) ─────────────────────────────────────────────────────

def _doc_key(claim: ClaimRecord) -> tuple[str, str]:
    """The document a claim belongs to — ``(source_id, file)``. The dedup scope; never crossed."""
    refs = claim.doc_refs()
    return (claim.source_id, refs[0].file if refs else "")


def _payload_core(payload: Any) -> dict[str, Any]:
    """Canonical dict of a payload's *stated* content, with free-text fields lexically normalised."""
    data: dict[str, Any] = payload.model_dump(mode="json")
    for field in _TEXT_FIELDS:
        if isinstance(data.get(field), str):
            data[field] = _normalize_text(data[field])
    parts = data.get("participants")
    if isinstance(parts, list):
        data["participants"] = [_normalize_text(p) if isinstance(p, str) else p for p in parts]
    return data


def _claim_signature(claim: ClaimRecord) -> str:
    """A deterministic string identifying *this stated assertion, in this document*.

    Two claims share a signature iff they are the same assertion (same document, kind, polarity,
    asserts, stated payload, event time, premises and target). ``report_time``/``ingest_time`` are
    excluded — they are document-level constants, so they can never separate two claims of one doc —
    and ``claim_id``/``resolved_ref``/``extraction`` are excluded so a restatement still collapses.
    """
    sig: dict[str, Any] = {
        "doc": _doc_key(claim),
        "kind": claim.kind,
        "polarity": claim.polarity,
        "asserts": claim.asserts,
        "payload": _payload_core(claim.payload),
        "event_time": claim.event_time.model_dump(mode="json") if claim.event_time is not None else None,
        "premises": list(claim.premises),
        "targets": claim.targets,
    }
    return json.dumps(sig, sort_keys=True, ensure_ascii=False, default=str)


# ── locators ──────────────────────────────────────────────────────────────────────────────────────

def _base_locator(ref: DocRef) -> str:
    """The readable locator stem for a span — ``row12`` / ``l3`` / ``p2`` / an image region / ``c<off>``.

    Row wins over line (a customs manifest cites its row; prose cites its line), and any image region
    name is reduced to an alphanumeric stem. ``make_claim_id`` re-validates the assembled ID, so the
    stem is kept strictly ``[a-z0-9]``.
    """
    if ref.row is not None:
        return f"row{ref.row}"
    if ref.line is not None:
        return f"l{ref.line}"
    if ref.frame is not None:
        return f"f{ref.frame}"
    if ref.page is not None:
        return f"p{ref.page}"
    if ref.region is not None:
        stem = "".join(ch for ch in ref.region.casefold() if ch.isalnum())
        return stem or "img"
    if ref.span is not None:
        return f"c{ref.span[0]}"
    return "c0"


def _locator_for_claim(claim: ClaimRecord) -> str:
    """The base locator of a claim's earliest provenance span (its first occurrence in the source)."""
    refs = sorted(claim.doc_refs(), key=_docref_sort_key)
    return _base_locator(refs[0]) if refs else "c0"


# ── public passes ───────────────────────────────────────────────────────────────────────────────

def dedup_within_doc(claims: list[ClaimRecord]) -> list[ClaimRecord]:
    """Collapse within-document restatements: one assertion → one claim carrying every stated span.

    Claims sharing a :func:`_claim_signature` (same document *and* same stated content) are merged into
    a single representative whose ``doc_ref`` is the sorted, de-duplicated union of the group's spans.
    Claims in different documents, or with any differing stated content (polarity, kind, asserts, the
    normalised s/p/o, the structured value, premises …), are **never** merged. Inputs are not mutated;
    the output is ordered deterministically (by earliest span, then signature), so the pass is itself
    order-independent.
    """
    groups: dict[str, list[ClaimRecord]] = defaultdict(list)
    for claim in claims:
        groups[_claim_signature(claim)].append(claim)

    merged: list[ClaimRecord] = []
    for members in groups.values():
        # Sorted, de-duplicated union of every span the group cited (identical refs collapse once).
        by_ref: dict[str, DocRef] = {}
        for member in members:
            for ref in member.doc_refs():
                by_ref.setdefault(ref.model_dump_json(), ref)
        refs = sorted(by_ref.values(), key=_docref_sort_key)
        doc_ref: DocRef | list[DocRef] = refs[0] if len(refs) == 1 else refs
        representative = min(members, key=_earliest_docref_key)
        merged.append(representative.model_copy(update={"doc_ref": doc_ref}))

    merged.sort(key=lambda c: (_earliest_docref_key(c), _claim_signature(c)))
    return merged


def assign_claim_ids(claims: list[ClaimRecord], *, doc_id: str) -> list[ClaimRecord]:
    """Stamp deterministic ``<doc_id>-<locator>`` claim IDs, stable regardless of input order.

    Claims are ordered by their earliest provenance span (a content tiebreak resolves exact ties), then
    walked serially: each is stamped from the locator of that span, and a running per-locator count
    disambiguates collisions via ``make_claim_id(..., index=)`` (``d02-l3`` then ``d02-l3-2``). Because
    the order and the counts are derived from content, the same claim set mints byte-identical IDs on
    every run (gates G9/G10). Inputs are not mutated; the returned list is in the deterministic order.

    **Cross-claim references follow the reassignment.** An ``inference`` claim's ``premises`` and a
    ``retraction``'s ``targets`` name *other claims by id*; those provisional ids change here, so this
    pass remaps them onto the reassigned ids (an old→new map built while stamping). Without this, the
    imagery signature→variant inference (premises = [observation_id, literature_id]) — and any future
    inference/retraction — would dangle after id assignment. This is why the fix lives here, not in a
    single caller: every path that assigns ids (the live lane *and* the frozen-bundle seed) inherits it.
    """
    ordered = sorted(claims, key=lambda c: (_earliest_docref_key(c), _claim_signature(c)))
    seen: dict[str, int] = {}
    remap: dict[str, str] = {}
    staged: list[tuple[ClaimRecord, str]] = []
    for claim in ordered:
        locator = _locator_for_claim(claim)
        seen[locator] = seen.get(locator, 0) + 1
        occurrence = seen[locator]
        new_id = make_claim_id(doc_id, locator, index=None if occurrence == 1 else occurrence)
        remap[claim.claim_id] = new_id
        staged.append((claim, new_id))

    out: list[ClaimRecord] = []
    for claim, new_id in staged:
        update: dict[str, Any] = {"claim_id": new_id}
        if claim.premises:
            update["premises"] = [remap.get(p, p) for p in claim.premises]
        if claim.targets is not None and claim.targets in remap:
            update["targets"] = remap[claim.targets]
        out.append(claim.model_copy(update=update))
    return out
