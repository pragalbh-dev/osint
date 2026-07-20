"""``GET /pending`` — the documents deliberately held out of the boot seed, and their claim bundles.

The demo's whole point about *monitoring* is that an analyst is warned when new evidence **arrives**. That
is only demonstrable if some evidence has not arrived yet — so ``config/sources.yaml`` →
``withheld_from_seed`` names a small set of documents the boot seed skips
(:func:`chanakya.api.state.resolve_withheld_docs`). Their frozen claim bundles ship with the app; they are
simply not appended at startup.

This router is how a reviewer *gets at* them without a checkout of the repo — the prebuilt image has no
files on the reviewer's machine to drag into the drop zone:

* ``GET /pending`` — what is being withheld, and why (the audit surface: the withholding is never silent);
* ``GET /pending/{doc_id}`` — that document's claims, in one array, ready to ``POST /ingest`` as
  ``{"bundle": [...]}``.

Both are **read-only, keyless and offline** — a file read of a checked-in bundle, no model, no network.
The array a reviewer posts back is byte-for-byte the recorded output of live extraction over that document
(the KEYLESS ≡ LIVE invariant in :mod:`chanakya.ingest.seed`), so ingesting it exercises the real lane,
not a scripted reveal. A document's *derived* enrichment bundles (``<doc>__basing.json``) ride along with
it, exactly as the hold-back withheld them together — releasing a document must release everything
inferred from it, or the graph would gain premises with no conclusion.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from chanakya.api.routes.deps import get_state
from chanakya.api.state import AppState, resolve_withheld_docs, scenario_bundles_dir
from chanakya.ingest.seed import bundles_for_doc, ingest_bundle

router = APIRouter()


class PendingDocument(BaseModel):
    """One withheld source document — what it is, and what ingesting it would append."""

    doc_id: str
    source_type: str | None = None  # from the source registry; None if the doc is not registered
    citation_url: str | None = None  # the on-disk document the bundle was extracted from
    bundles: list[str] = Field(default_factory=list)  # its own bundle + any derived enrichment bundles
    claim_count: int = 0
    available: bool = True  # False when the bundle is declared withheld but not present on disk
    #: True once every claim in this document's bundles is already in the evidence log — i.e. a reviewer
    #: (or an earlier session) has ingested it. Read off the live log, never a client-side guess about
    #: what landed. Re-ingesting is harmless (the reduction is idempotent: same graph, no second alert),
    #: but the list must say what has already arrived rather than invite a pointless second click.
    ingested: bool = False


class PendingResponse(BaseModel):
    """The withheld set. Empty ``documents`` = nothing is being held back (a full-corpus boot)."""

    scenario: str | None = None
    documents: list[PendingDocument] = Field(default_factory=list)


class PendingBundle(BaseModel):
    """A withheld document's claims, shaped for a direct ``POST /ingest`` (keyless lane)."""

    doc_id: str
    bundles: list[str] = Field(default_factory=list)
    bundle: list[dict[str, Any]] = Field(default_factory=list)


def _registry_entry(state: AppState, doc_id: str) -> Any | None:
    return state.config.snapshot().sources.as_map().get(doc_id)


@router.get("/pending", response_model=PendingResponse)
def get_pending(state: AppState = Depends(get_state)) -> PendingResponse:
    """List the documents held out of the boot seed — the reviewer's live-ingest set."""
    bdir = scenario_bundles_dir()
    seeded = set(state.claims_map())  # what the evidence log already holds — the honest arrival test
    docs: list[PendingDocument] = []
    for doc_id in resolve_withheld_docs(state.config):
        paths = bundles_for_doc(bdir, doc_id) if bdir.is_dir() else []
        entry = _registry_entry(state, doc_id)
        claim_ids = [c.claim_id for p in paths for c in ingest_bundle(p)]
        docs.append(
            PendingDocument(
                doc_id=doc_id,
                source_type=getattr(entry, "source_type", None),
                citation_url=getattr(entry, "citation_url", None),
                bundles=[p.name for p in paths],
                claim_count=len(claim_ids),
                available=bool(paths),
                ingested=bool(claim_ids) and set(claim_ids) <= seeded,
            )
        )
    return PendingResponse(scenario=bdir.parent.name if bdir.parent.name else None, documents=docs)


@router.get("/pending/{doc_id}", response_model=PendingBundle)
def get_pending_bundle(doc_id: str, state: AppState = Depends(get_state)) -> PendingBundle:
    """One withheld document's claims, merged across its own + derived bundles, ready to ``POST /ingest``.

    404s for anything not on the declared withheld list — this endpoint hands out the *staged* documents,
    not the corpus at large (a general bundle-download surface is not what the demo needs, and would let a
    caller re-append claims already in the graph).
    """
    withheld = resolve_withheld_docs(state.config)
    if doc_id not in withheld:
        raise HTTPException(404, detail=f"{doc_id!r} is not a withheld document; see GET /pending")
    paths = bundles_for_doc(scenario_bundles_dir(), doc_id)
    if not paths:
        raise HTTPException(
            404, detail=f"no claim bundle on disk for withheld document {doc_id!r} — nothing to ingest"
        )
    claims: list[dict[str, Any]] = []
    for path in paths:  # sorted: the source bundle before its derived enrichments, as the seed appends
        claims.extend(claim.model_dump(mode="json") for claim in ingest_bundle(path))
    return PendingBundle(doc_id=doc_id, bundles=[p.name for p in paths], bundle=claims)
