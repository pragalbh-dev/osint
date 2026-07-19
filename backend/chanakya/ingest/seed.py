"""The **keyless bundle lane** + the **frozen seed baseline** — INGEST's boot + reproducibility path.

Live extraction (LLM/VLM) needs an API key; the demo must boot and run *without* one. The bridge is a
frozen **claim bundle**: the byte-stable JSON output of running the live extraction pipeline once over a
corpus document, checked in under ``corpus/scenarios/<scenario>/claims/<source_id>.json``. Booting then
becomes a pure *append* of those bundles — no model, no network, no fabrication (master §, INGEST
contract "seed.py"). The governing invariant is **KEYLESS ≡ LIVE**: a bundle is *nothing but* the frozen
result of live extraction over the same source, so appending a bundle materialises exactly the claims a
live re-extract of that document would — the offline path is a recording of the online one, never a
second, divergent code path.

Three surfaces, split by who has a key:

* :func:`ingest_bundle` — **pure, keyless.** Read a bundle JSON (a list of ``ClaimRecord`` dicts) and
  validate it back to records. No LLM, no clock, no network — safe to call inside the boot path and in
  ``rebuild``-adjacent code (gate G1: nothing here runs a model).
* :func:`seed_store_from_bundles` — append every ``<source_id>.json`` bundle in a directory into an
  append-only store, in a deterministic (sorted) order, and report the count.
* :func:`extract_corpus` — **keyed, the recorder.** Iterate the source registry for one scenario, run the
  real extraction pipeline (``load_document`` → ``extract_document`` / ``read_image_document`` → dedup →
  id-assignment) over each cited document, and dump the claims as **byte-stable** JSON. The
  ``ingest_time`` is *pinned* (:data:`FROZEN_INGEST_TIME`) and every clock/RNG is already excluded from
  the emit path (gates G1/G9/G10), so re-recording the same corpus with the same client yields
  byte-identical bundles — which is what lets the frozen files live in version control and a reviewer
  diff a re-extract against them.

Dispatch is **source-shape only** (gate G9): a ``.png`` citation runs the VLM imagery lane, everything
else the text extraction lane. Nothing here imports a subject, an anchor, or the answer key, and nothing
branches on *who* a document is about — a customs manifest and a satellite frame seed identically
regardless of the use case that later reads them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

from chanakya import settings
from chanakya.ingest import adapters, dedup, extract, imagery, loaders
from chanakya.ingest.client import ExtractionClient
from chanakya.schemas import ClaimRecord, ConfigBundle, SourceRegistryEntry
from chanakya.schemas.values import DateValue, ExactDate

# The pinned ingest timestamp for the frozen baseline. A fixed value (never ``date.today()``) is what
# makes the recorded bundles byte-stable across re-runs and machines (gate G10) — the demo's "the live
# query runs the same every time" guarantee begins here, at the frozen input.
FROZEN_INGEST_TIME: ExactDate = ExactDate(
    iso_date="2026-07-19", raw="frozen-seed-baseline", boundary_source="explicit"
)

# Source-shape dispatch: a citation with one of these suffixes is an image → the VLM imagery lane.
_IMAGE_EXTS: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp", ".gif"}
)


class SupportsAppendMany(Protocol):
    """The minimal append-only-store surface :func:`seed_store_from_bundles` needs (an ``EvidenceLog``)."""

    def append_many(self, records: list[ClaimRecord]) -> None: ...


# ── the keyless read path (pure — no LLM, no clock, no network) ────────────────────────────────────

def ingest_bundle(path: str | Path) -> list[ClaimRecord]:
    """Read a frozen claim bundle back into ``ClaimRecord``\\ s — the keyless append input (pure).

    Accepts either a JSON array of claim dicts (the canonical bundle form :func:`extract_corpus` writes)
    or a JSONL file (one claim per line), so a hand-authored bundle round-trips too. An empty file yields
    ``[]``. Validation is the F0 ``ClaimRecord`` schema; a malformed record raises, loudly — the boot path
    must never silently drop a claim. Because the bundle *is* the recorded output of live extraction,
    the records returned here are byte-for-byte what a live re-extract of the same document would produce
    (the KEYLESS ≡ LIVE invariant).
    """
    text = Path(path).read_text(encoding="utf-8").strip()
    if not text:
        return []
    rows = json.loads(text) if text[0] == "[" else [json.loads(ln) for ln in text.splitlines() if ln.strip()]
    return [ClaimRecord.model_validate(row) for row in rows]


def seed_store_from_bundles(store: SupportsAppendMany, bundles_dir: str | Path) -> int:
    """Append every ``<source_id>.json`` bundle under ``bundles_dir`` into ``store``; return the count.

    Bundles are appended in filename-sorted order so the store's insertion order — and therefore every
    downstream ``replay()`` / ``rebuild()`` — is deterministic (gate G2). The append is a plain
    :meth:`append_many`; no extraction runs, so this is the keyless boot path in full.
    """
    total = 0
    for path in sorted(Path(bundles_dir).glob("*.json")):
        claims = ingest_bundle(path)
        if claims:
            store.append_many(claims)
        total += len(claims)
    return total


# ── the keyed recorder (runs the live pipeline, freezes byte-stable bundles) ───────────────────────

def _resolve_source_path(citation_url: str) -> Path:
    """The on-disk path a ``citation_url`` names — absolute as-is, else rooted at the repo (settings)."""
    p = Path(citation_url)
    return p if p.is_absolute() else settings.repo_root() / p


def _under_scenario(citation_url: str, scenario: str) -> bool:
    """Whether a ``citation_url`` belongs to ``scenario`` — an exact path-component match, never a
    substring (so ``hq9p_primary`` never captures a hypothetical ``hq9p_primary_2``)."""
    return scenario in Path(citation_url).parts


def _report_time_for(entry: SourceRegistryEntry) -> DateValue | None:
    """The source's ``report_time`` built from its registry ``report_date`` (ING-7) — or ``None``.

    ``report_date`` is only ever a verbatim day-level date the document itself states (see the field's
    docstring); when unset, this returns ``None`` rather than fabricating one — the same "we looked but
    cannot say" discipline the imagery lane applies to counts. ``boundary_source="explicit"`` because a
    stamped ``report_date`` is, by construction, read directly off the document, never guessed.
    """
    if not entry.report_date:
        return None
    return ExactDate(iso_date=entry.report_date, raw=entry.report_date, boundary_source="explicit")


def _merge_chunks(chunks: list[list[ClaimRecord]]) -> list[ClaimRecord]:
    """Namespace + flatten several extraction calls' claims before dedup/id-assignment.

    Provisional claim ids are unique only *within* one extraction call (``extract_document`` / one
    ``read_image_document`` read); a source whose text lane runs alongside one or more co-loaded images
    makes several such calls, each minting its own provisional ids that can collide once concatenated.
    Mirrors the identical namespacing the live lane applies in ``lane._extract_doc_claims`` (chunk-prefix
    each call's ids, then remap that call's own inference ``premises`` / retraction ``targets`` in
    lockstep) — the seed path must reshape multi-call output exactly like the live path does, or the two
    would diverge on a source with co-loaded imagery (breaking KEYLESS ≡ LIVE).
    """
    claims: list[ClaimRecord] = []
    for k, chunk in enumerate(chunks):
        remap = {c.claim_id: f"chunk{k}-{c.claim_id}" for c in chunk}
        for c in chunk:
            update: dict[str, Any] = {"claim_id": remap[c.claim_id]}
            if c.premises:
                update["premises"] = [remap.get(p, p) for p in c.premises]
            if c.targets is not None and c.targets in remap:
                update["targets"] = remap[c.targets]
            claims.append(c.model_copy(update=update))
    return claims


def _extract_source(
    entry: SourceRegistryEntry, *, client: ExtractionClient, config: ConfigBundle,
    ingest_time: DateValue, geocoder: adapters.Geocoder | None = None,
) -> list[ClaimRecord]:
    """Run the full live pipeline over one registered source → its final, id-assigned claims.

    Dispatches on the citation's file shape only (gate G9): a ``.png`` citation runs the subject-blind
    VLM lane (:func:`~chanakya.ingest.imagery.read_image_document`, no ``literature_ref`` — the seed
    asserts only what a single frame states); everything else runs the text lane (``load_document`` →
    ``extract_document``). A source also carrying ``images`` (ING-8: a GEOINT ``.txt`` write-up beside
    its satellite/social ``.png``) co-loads each of those frames through the *same* VLM lane, run
    alongside the text lane — mirroring how the live (keyed) lane feeds co-located frames via
    ``DocInput.images`` (:mod:`chanakya.ingest.lane`) — so the frozen bundle carries both the prose
    extraction *and* the subject-blind imagery observation a live keyed extract would produce, never one
    at the expense of the other. ``report_time`` is built from the registry's ``report_date`` (ING-7) and
    threaded to every call this source makes. ``geocoder`` (the gazetteer coord-cache → Nominatim chain,
    or ``None`` = offline) is threaded to the text lane so anchor coordinates are frozen onto the bundle.
    The closing passes — chunk-namespacing, within-doc dedup, then deterministic id-assignment — are
    exactly what the live lane runs, so the frozen output equals the live output (KEYLESS ≡ LIVE).
    """
    citation_url = entry.citation_url or ""
    src_path = _resolve_source_path(citation_url)
    ext = Path(citation_url).suffix.lower()
    report_time = _report_time_for(entry)

    chunks: list[list[ClaimRecord]] = []
    if ext in _IMAGE_EXTS:
        chunks.append(imagery.read_image_document(
            src_path.read_bytes(), file=citation_url, source_id=entry.source_id,
            config=config, client=client, report_time=report_time, ingest_time=ingest_time,
        ))
    else:
        loaded = loaders.load_document(src_path.read_bytes(), file=citation_url)
        chunks.append(extract.extract_document(
            loaded, source_id=entry.source_id, source_type=entry.source_type,
            config=config, client=client, report_time=report_time, ingest_time=ingest_time,
            geocoder=geocoder,
        ))
        for image_url in entry.images:
            image_path = _resolve_source_path(image_url)
            chunks.append(imagery.read_image_document(
                image_path.read_bytes(), file=image_url, source_id=entry.source_id,
                config=config, client=client, report_time=report_time, ingest_time=ingest_time,
            ))

    claims = _merge_chunks(chunks)
    claims = dedup.dedup_within_doc(claims)
    return dedup.assign_claim_ids(claims, doc_id=entry.source_id)


def _write_bundle(path: Path, claims: list[ClaimRecord]) -> None:
    """Dump claims to a **byte-stable** JSON bundle: canonical, ``sort_keys``-sorted, trailing newline.

    ``sort_keys`` makes the bytes independent of any dict-insertion order in the payload, so two recorder
    runs over the same input produce byte-identical files (gate G10). The array of ``model_dump`` dicts
    round-trips exactly through :func:`ingest_bundle` (JSON objects are order-free on read)."""
    rows = [claim.model_dump(mode="json") for claim in claims]
    path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def extract_corpus(
    scenario: str, *, client: ExtractionClient, config: ConfigBundle,
    ingest_time: DateValue | None = None, out_dir: str | Path | None = None,
    geocoder: adapters.Geocoder | None = None,
) -> list[Path]:
    """Record the frozen bundles for one scenario — the keyed path that produces the keyless baseline.

    For every source in ``config.sources.sources`` whose ``citation_url`` falls under ``scenario``, run
    the live extraction pipeline (:func:`_extract_source`) over the cited document and write its claims
    to ``<out_dir>/<source_id>.json``. ``ingest_time`` defaults to the pinned :data:`FROZEN_INGEST_TIME`
    and ``out_dir`` to ``corpus/scenarios/<scenario>/claims`` — so a bare ``extract_corpus("hq9p_primary",
    …)`` re-freezes the checked-in baseline in place. ``geocoder`` defaults to ``None`` (offline — no
    network at record time, fully deterministic); the CLI passes a live gazetteer→Nominatim chain so a
    keyed ``make extract`` freezes anchor coordinates. Returns the written bundle paths (source order).

    Deterministic given the client's output **and** an offline (or gazetteer-only) geocoder: two runs
    write byte-identical files. Runs entirely upstream of ``store.append`` (G1).
    """
    ingest_time = ingest_time or FROZEN_INGEST_TIME
    target = (
        Path(out_dir) if out_dir is not None
        else settings.corpus_dir() / "scenarios" / scenario / "claims"
    )
    target.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    kept: set[str] = set()
    for entry in config.sources.sources:
        if not entry.citation_url or not _under_scenario(entry.citation_url, scenario):
            continue
        claims = _extract_source(entry, client=client, config=config, ingest_time=ingest_time,
                                 geocoder=geocoder)
        out_path = target / f"{entry.source_id}.json"
        _write_bundle(out_path, claims)
        written.append(out_path)
        kept.add(out_path.name)
    # Prune stale bundles: a source removed from config (or re-scoped to another scenario) must not leave
    # an orphan ``<source_id>.json`` that :func:`seed_store_from_bundles` still globs + appends — that
    # would drift the keyless baseline away from the current config (keyless ≢ live).
    for stale in target.glob("*.json"):
        # Preserve attribution-inference bundles (``*__attr.json``): they are produced by the separate
        # offline enrichment pass (``python -m chanakya.ingest attribute --record``), not this per-source
        # recorder, so they are never in ``kept`` — but they belong to the frozen baseline and must survive
        # a re-record of the source documents.
        if stale.name not in kept and not stale.name.endswith("__attr.json"):
            stale.unlink()
    return written
