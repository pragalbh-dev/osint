"""The always-available **ingest lane** — the one call that takes a raw document (text and/or
imagery) all the way to a rebuilt, alert-evaluated knowledge view, and the concurrent batch helper
the corpus seed drives (INGEST session, item 7; master §4.2, gate G1).

The lane is where the two halves of INGEST are stitched together and where the system's single
serialisation boundary lives. Its shape is deliberately two phases, because the two phases have
opposite concurrency rules:

1. **fan-out extraction (I/O-bound, parallel).** Every LLM/VLM call a document needs — the one text
   :func:`~chanakya.ingest.extract.extract_document` call **in parallel with** each image
   :func:`~chanakya.ingest.imagery.read_image_document` call, and every *document* of a batch in
   parallel with the others — is run under one :class:`asyncio.Semaphore`. The client calls are
   synchronous (the :class:`~chanakya.ingest.client.ExtractionClient` protocol is sync, so a scripted
   offline client works unchanged), so each is off-loaded with :func:`asyncio.to_thread`; the semaphore
   bounds how many are in flight at once. This is pure network latency being overlapped — nothing here
   touches shared state.

2. **the serial deterministic pass (single-writer).** Once a document's claims are back, a *pure*
   reshaping runs with no concurrency and no clock/RNG: :func:`~chanakya.ingest.dedup.dedup_within_doc`
   folds within-doc restatements, :func:`~chanakya.ingest.dedup.assign_claim_ids` mints the canonical
   byte-stable ids (and this module remaps any inference ``premises`` onto those reassigned ids — the
   imagery corroboration references an observation whose id has just changed), then a **single writer**
   ``store.append_many`` commits them, ``rebuild()`` folds the log into a view, and ``evaluate()`` fires
   observables on the delta. Append → rebuild → evaluate is one critical section: it is never
   parallelised, so ids and the view are byte-identical across runs.

The wall between the phases is gate **G1**: the LLM/VLM (and, upstream in the adapters, the geocoder and
the hashes) run **only** in phase 1, and their outputs are frozen onto the ``ClaimRecord`` before the
append. ``rebuild()`` in phase 2 is handed the *store* (and the config), never the client — so nothing
it does can reach an LLM. Extraction concurrency and the pure rebuild never touch: the concurrency lives
entirely upstream of the append.

The lane is source-blind (gate G9): it dispatches on document shape via the loader + extractor, never on
a subject or the ontology's instance content, and it imports no subject/answer-key content.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from chanakya.ingest import loaders
from chanakya.ingest.client import ExtractionClient
from chanakya.ingest.dedup import assign_claim_ids, dedup_within_doc
from chanakya.ingest.extract import extract_document
from chanakya.ingest.imagery import LiteratureRef, read_image_document
from chanakya.schemas import Alert, ClaimRecord, ConfigBundle, GraphView, IngestResult
from chanakya.schemas.values import DateValue, Location
from chanakya.store import DecisionLog, EvidenceLog

#: ``rebuild`` + observable-``evaluate`` are **injected**, never imported (gate **G9**: ``chanakya/ingest``
#: must not import ``chanakya.view`` / ``chanakya.observe`` or any pipeline stage). The caller — the
#: ``/ingest`` API endpoint, or a test — passes ``chanakya.view.rebuild`` and ``chanakya.observe.evaluate``;
#: the lane stays decoupled from the stages it triggers, which is also what makes it trivially testable.
RebuildFn = Callable[..., GraphView]
ObserveFn = Callable[..., "list[Alert]"]

#: Default cap on simultaneously-in-flight extraction calls for a single :func:`ingest_document`
#: (its text ∥ image calls). Batch callers set their own via ``extract_many(concurrency=…)``.
DEFAULT_CONCURRENCY = 8


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# The per-document extraction input.
# ══════════════════════════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class DocInput:
    """One document to extract — the unit :func:`extract_many` fans out over.

    ``raw`` is the primary payload (prose/record text, or the bytes of a standalone image whose ``file``
    carries an image extension); ``images`` are any co-located frames (the ``.png`` beside a GEOINT
    ``.txt``). ``geo``/``literature_ref`` ride only on the imagery path: authoritative text coordinates
    frozen onto the observation, and the ingested reference the corroboration is judged against.
    """

    raw: str | bytes
    source_id: str
    source_type: str
    file: str
    images: Sequence[tuple[bytes, str]] = ()
    report_time: DateValue | None = None
    ingest_time: DateValue | None = None
    format_hint: str | None = None
    geo: Location | None = None
    literature_ref: LiteratureRef | None = None


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# Small deterministic helpers (pure — no client, no clock, no RNG).
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def _nonempty(raw: str | bytes) -> bool:
    """Does ``raw`` carry any content? An empty/whitespace payload triggers *no* extraction call."""
    return bool(raw.strip()) if isinstance(raw, (str, bytes)) else False


def _doc_token(source_id: str) -> str:
    """A kebab ``[a-z0-9-]`` doc token for the canonical claim-id prefix (``d05_x`` → ``d05-x``)."""
    out: list[str] = []
    prev_dash = False
    for ch in source_id.lower():
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    return "".join(out).strip("-") or "doc"


def _finalize(claims: list[ClaimRecord], source_id: str) -> list[ClaimRecord]:
    """The pure per-document reshaping: fold restatements → mint canonical ids.

    :func:`~chanakya.ingest.dedup.assign_claim_ids` also remaps any inference ``premises`` / retraction
    ``targets`` onto the reassigned ids, so the imagery signature→variant inference keeps pointing at its
    observation. Runs *after* all of a document's extraction I/O has completed (serial + deterministic)
    yet still upstream of the append; the returned order is the canonical sorted order.
    """
    folded = dedup_within_doc(claims)
    return assign_claim_ids(folded, doc_id=_doc_token(source_id))


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# Phase 1 — the concurrent extraction fan-out (I/O only, upstream of the append — G1).
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def _extract_primary(doc: DocInput, client: ExtractionClient, config: ConfigBundle) -> list[ClaimRecord]:
    """Extract the primary payload — the text path, or the VLM path when ``file`` is an image.

    The loader's own file-type dispatch is the single arbiter of modality (gate G9): a text document
    goes through :func:`extract_document`, an image document through :func:`read_image_document`.
    """
    loaded = loaders.load_document(doc.raw, file=doc.file)
    if loaded.modality == "image":
        data = loaded.raw_bytes if loaded.raw_bytes is not None else (
            doc.raw if isinstance(doc.raw, bytes) else doc.raw.encode("utf-8")
        )
        return read_image_document(
            data, file=doc.file, source_id=doc.source_id, config=config, client=client,
            report_time=doc.report_time, ingest_time=doc.ingest_time,
            geo=doc.geo, literature_ref=doc.literature_ref,
        )
    return extract_document(
        loaded, source_id=doc.source_id, source_type=doc.source_type, config=config, client=client,
        report_time=doc.report_time, ingest_time=doc.ingest_time, format_hint=doc.format_hint,
    )


def _extract_image(
    image: bytes, file: str, doc: DocInput, client: ExtractionClient, config: ConfigBundle
) -> list[ClaimRecord]:
    """Extract one co-located image via the subject-blind VLM path (``read_image_document``)."""
    return read_image_document(
        image, file=file, source_id=doc.source_id, config=config, client=client,
        report_time=doc.report_time, ingest_time=doc.ingest_time,
        geo=doc.geo, literature_ref=doc.literature_ref,
    )


async def _guarded(sem: asyncio.Semaphore, func: Any, *args: Any) -> list[ClaimRecord]:
    """Run one synchronous extraction call off the event loop, bounded by the shared semaphore.

    ``to_thread`` keeps the sync client (scripted or live) working unchanged while overlapping its
    network latency; the semaphore caps how many such calls are simultaneously in flight.
    """
    async with sem:
        return await asyncio.to_thread(func, *args)


async def _extract_doc_claims(
    doc: DocInput, *, client: ExtractionClient, config: ConfigBundle, sem: asyncio.Semaphore
) -> list[ClaimRecord]:
    """Extract one document — its text ∥ each image call fanned out — then the pure reshaping pass.

    All extraction I/O for the document is gathered concurrently under ``sem``; only once every call has
    returned does the deterministic :func:`_finalize` run. An empty document yields zero claims.
    """
    tasks: list[Any] = []
    if _nonempty(doc.raw):
        tasks.append(_guarded(sem, _extract_primary, doc, client, config))
    for image, image_file in doc.images:
        tasks.append(_guarded(sem, _extract_image, image, image_file, doc, client, config))
    if not tasks:
        return []
    results = await asyncio.gather(*tasks)
    # Provisional claim ids are unique only *within* one extraction call; a doc with several images makes
    # several calls that can mint colliding provisional ids (each imagery call mints its own obs/inf pair).
    # Namespace each chunk before ``assign_claim_ids`` remaps premises off those ids — rewriting each
    # chunk's own inference ``premises`` / retraction ``targets`` in lockstep so the linkage survives.
    claims: list[ClaimRecord] = []
    for k, chunk in enumerate(results):
        remap = {c.claim_id: f"chunk{k}-{c.claim_id}" for c in chunk}
        for c in chunk:
            update: dict[str, Any] = {"claim_id": remap[c.claim_id]}
            if c.premises:
                update["premises"] = [remap.get(p, p) for p in c.premises]
            if c.targets is not None and c.targets in remap:
                update["targets"] = remap[c.targets]
            claims.append(c.model_copy(update=update))
    return _finalize(claims, doc.source_id)


async def _extract_batch(
    docs: Sequence[DocInput], *, concurrency: int, client: ExtractionClient, config: ConfigBundle
) -> list[list[ClaimRecord]]:
    """Fan out extraction across a batch **and** within each document under one shared semaphore."""
    sem = asyncio.Semaphore(concurrency)
    coros = [_extract_doc_claims(doc, client=client, config=config, sem=sem) for doc in docs]
    results = await asyncio.gather(*coros)
    return list(results)


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# The public entry points.
# ══════════════════════════════════════════════════════════════════════════════════════════════════

async def extract_many(
    docs: Sequence[DocInput], *, concurrency: int = 8, client: ExtractionClient, config: ConfigBundle
) -> list[list[ClaimRecord]]:
    """Concurrently extract a batch of documents → one canonical claim list per document (seed path).

    Pure extraction (gate G1): it appends nothing and rebuilds nothing — it is the off-the-rebuild-path
    helper the corpus seed drives to write byte-stable bundles. Every document's I/O overlaps every
    other's (and its own text ∥ image calls) under a single ``asyncio.Semaphore(concurrency)``; each
    returned list is already deduped, canonically id'd and premise-remapped, in ``docs`` order.
    """
    return await _extract_batch(docs, concurrency=concurrency, client=client, config=config)


def ingest_document(
    raw: str | bytes,
    *,
    source_id: str,
    source_type: str,
    config: ConfigBundle,
    client: ExtractionClient,
    store: EvidenceLog,
    file: str,
    images: Sequence[tuple[bytes, str]] = (),
    report_time: DateValue | None = None,
    ingest_time: DateValue | None = None,
    live_rebuild: bool = True,
    decision_store: DecisionLog | None = None,
    prev_view: GraphView | None = None,
    rebuild_fn: RebuildFn | None = None,
    observe_fn: ObserveFn | None = None,
) -> IngestResult:
    """Ingest one document end-to-end: concurrent extraction → single-writer append → rebuild → alerts.

    Phase 1 (upstream of the append — G1): the text extraction runs **in parallel with** each image's
    VLM read (``to_thread`` under a semaphore), then the pure :func:`_finalize` folds restatements and
    mints canonical ids. Phase 2 (the serial single-writer critical section): ``store.append_many`` is
    the sole writer, then — when ``live_rebuild`` — ``rebuild()`` folds the log into a view (handed the
    *store*, never the client) and ``evaluate()`` fires observables on the ``prev_view → view`` delta.

    Returns the appended claim ids (canonical order), whether a rebuild ran, and the ids of any fired
    observables. With ``live_rebuild=False`` the claims are still appended but no view is rebuilt (the
    batch/seed pattern: append many, rebuild once). Deterministic: the same document + client yields the
    same ids and the same view on every run, regardless of the extraction race in phase 1.
    """
    doc = DocInput(
        raw=raw, source_id=source_id, source_type=source_type, file=file, images=tuple(images),
        report_time=report_time, ingest_time=ingest_time,
    )
    # Phase 1 — concurrent extraction (the only place the client is ever called).
    claims = asyncio.run(
        _extract_batch([doc], concurrency=DEFAULT_CONCURRENCY, client=client, config=config)
    )[0]

    # Phase 2 — the serial single-writer critical section: append → rebuild → evaluate.
    store.append_many(claims)
    appended = [c.claim_id for c in claims]

    rebuilt = False
    alerts_fired: list[str] = []
    if live_rebuild and rebuild_fn is not None:
        decisions: object = decision_store if decision_store is not None else []
        view = rebuild_fn(store, decisions, config)
        rebuilt = True
        if observe_fn is not None:
            alerts_fired = [alert.observable_id for alert in observe_fn(prev_view, view, config)]

    return IngestResult(appended_claim_ids=appended, rebuilt=rebuilt, alerts_fired=alerts_fired)


__all__ = ["DocInput", "ingest_document", "extract_many", "DEFAULT_CONCURRENCY"]
