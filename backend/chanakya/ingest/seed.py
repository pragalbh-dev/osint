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
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

from chanakya import settings
from chanakya.ingest import adapters, dedup, extract, imagery, loaders
from chanakya.ingest.client import ExtractionClient
from chanakya.schemas import ClaimRecord, ConfigBundle, SourceRegistryEntry
from chanakya.schemas.claim import EntityDescriptor
from chanakya.schemas.values import DateValue, ExactDate, Location

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


#: Bundle-name suffixes written by the OFFLINE ENRICHMENT passes rather than by the per-source recorder
#: (the attribution proposer and the basing proposer). They carry derived ``inference`` claims whose
#: provenance spans two source documents, so they belong to no single ``<source_id>.json`` and must
#: survive a re-record — the one convention both the recorder's prune step and the loader agree on.
_DERIVED_BUNDLE_SUFFIXES: tuple[str, ...] = ("__attr.json", "__basing.json")


def _is_derived_bundle(name: str) -> bool:
    """Is this bundle the output of an offline enrichment pass (never of :func:`extract_corpus`)?"""
    return name.endswith(_DERIVED_BUNDLE_SUFFIXES)


def bundle_belongs_to_doc(bundle_name: str, doc_id: str) -> bool:
    """Does ``bundle_name`` carry ``doc_id``'s claims — its own bundle or an enrichment riding on it?

    The recorder writes ``<doc_id>.json``; the offline enrichment passes write ``<doc_id>__basing.json`` /
    ``<doc_id>__attr.json`` (:data:`_DERIVED_BUNDLE_SUFFIXES`). Both are "what we learned from that
    document", so any staged/held-back seed must hold them back or release them **together** — otherwise
    the held-back "before" graph would still carry a derived fact whose premises had not arrived, which
    is incoherent. This is the one definition of that grouping; the boot seed
    (:func:`seed_store_from_bundles`) and the EVAL staged-ingest harness both call it rather than each
    re-deriving the convention.
    """
    return bundle_name == f"{doc_id}.json" or bundle_name.startswith(f"{doc_id}__")


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


def seed_store_from_bundles(
    store: SupportsAppendMany, bundles_dir: str | Path, *, exclude_docs: Sequence[str] = ()
) -> int:
    """Append every ``<source_id>.json`` bundle under ``bundles_dir`` into ``store``; return the count.

    Bundles are appended in filename-sorted order so the store's insertion order — and therefore every
    downstream ``replay()`` / ``rebuild()`` — is deterministic (gate G2). The append is a plain
    :meth:`append_many`; no extraction runs, so this is the keyless boot path in full.

    ``exclude_docs`` names source documents to **hold back** from the seed — the same append, in the same
    sorted order, minus those documents *and everything derived from them*
    (:func:`bundle_belongs_to_doc`). The held-back bundles stay on disk, so the withheld document can be
    ingested later through the live keyless ``POST /ingest`` lane; the resulting graph is the same one a
    full seed would have produced (the append is order-independent at the reduction, and the arrival is
    what an alert is *about*). A held-back document is a demo/staging choice, never a data edit: no bundle
    contents change, only which of them are present at boot.
    """
    total = 0
    for path in sorted(Path(bundles_dir).glob("*.json")):
        if any(bundle_belongs_to_doc(path.name, doc) for doc in exclude_docs):
            continue
        claims = ingest_bundle(path)
        if claims:
            store.append_many(claims)
        total += len(claims)
    return total


def bundles_for_doc(bundles_dir: str | Path, doc_id: str) -> list[Path]:
    """Every frozen bundle carrying ``doc_id``'s claims — its own plus its enrichments — sorted.

    The inverse of the hold-back filter: what a reviewer must ingest to *release* a withheld document.
    Sorted so the release order equals the order a full boot seed would have appended them in (G2).
    """
    return sorted(p for p in Path(bundles_dir).glob("*.json") if bundle_belongs_to_doc(p.name, doc_id))


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
    each call's ids, then rewrite that call's own cross-claim references — inference ``premises``,
    retraction ``targets``, endpoint mention refs — in lockstep via the one shared
    :func:`~chanakya.ingest.dedup.remap_claim_refs`) — the seed path must reshape multi-call output exactly
    like the live path does, or the two would diverge on a source with co-loaded imagery (breaking
    KEYLESS ≡ LIVE).
    """
    claims: list[ClaimRecord] = []
    for k, chunk in enumerate(chunks):
        remap = {c.claim_id: f"chunk{k}-{c.claim_id}" for c in chunk}
        for c in chunk:
            update: dict[str, Any] = {"claim_id": remap[c.claim_id], **dedup.remap_claim_refs(c, remap)}
            claims.append(c.model_copy(update=update))
    return claims


def _read_geo_sidecar(image_url: str, *, geocoder: adapters.Geocoder | None) -> Location | None:
    """Read an optional ``<image>.geo.json`` georeference sidecar beside the frame → a canonical Location.

    The satellite product's DECLARED georeference (its AOI/tasking coordinate), carried as metadata beside
    the image — never inferred from pixels, so the VLM stays subject-blind. Normalised through the same
    Stage-A canonicaliser every stated location uses, so the coordinate lands on the imagery observation's
    ``coordinates`` attr and RESOLVE merges the frame onto the real ``basing_site`` by coordinate. No
    sidecar ⇒ ``None`` (the frame stays un-georeferenced, exactly as before). ``precision_class`` may be
    overridden to reflect the product's real geolocation accuracy (an AOI centre is usually site-, not
    pad-, precise). Format: ``{"location_text": "<coord|toponym>", "surface_format"?, "precision_class"?}``.
    """
    sidecar = _resolve_source_path(image_url).with_suffix(".geo.json")
    if not sidecar.exists():
        return None
    data = json.loads(sidecar.read_text(encoding="utf-8"))
    raw = data.get("location_text") or data.get("raw")
    if not raw:
        return None
    loc = adapters.normalize_location(raw, surface_format=data.get("surface_format"), geocoder=geocoder)
    if loc is not None and data.get("precision_class"):
        loc = loc.model_copy(update={"precision_class": data["precision_class"]})
    return loc


def apply_geo_sidecars(scenario: str, *, geocoder: adapters.Geocoder | None = None) -> list[Path]:
    """Deterministically stamp declared image georeferences onto a scenario's frozen imagery observations.

    For every ``*.json`` bundle in ``corpus/scenarios/<scenario>/claims`` and every subject-blind VLM image
    observation in it, read the optional ``<image>.geo.json`` sidecar beside the frame and freeze its
    coordinate onto the observation's ``coordinates`` attr — **without re-running extraction**, so the
    curated bundle structure is preserved (a full LLM re-record drifts/fragments it). RESOLVE then merges
    that frame onto the real ``basing_site`` by coordinate at the next ``rebuild``. This is the frozen-bundle
    counterpart of the live/record path (:func:`_read_geo_sidecar` in :func:`_extract_source`): the *same*
    sidecar, applied to already-frozen bundles. Byte-stable and idempotent (re-stamping the same coordinate
    is a no-op). ``geocoder`` defaults to ``None`` (offline — coord sidecars parse deterministically). Returns
    the bundles it modified.
    """
    claims_dir = settings.corpus_dir() / "scenarios" / scenario / "claims"
    modified: list[Path] = []
    for bundle in sorted(claims_dir.glob("*.json")):
        claims = [ClaimRecord.model_validate(r) for r in json.loads(bundle.read_text(encoding="utf-8"))]
        changed = False
        for c in claims:
            p = c.payload
            if not (isinstance(p, EntityDescriptor) and c.kind == "observation"
                    and c.extraction.method == "vlm" and p.entity_type == "basing_site"
                    and str(p.name or "").startswith("imagery-site:")):
                continue
            refs = c.doc_refs()
            if not refs:
                continue
            loc = _read_geo_sidecar(refs[0].file, geocoder=geocoder)
            if loc is None:
                continue
            dumped = loc.model_dump(mode="json")
            if (p.attrs or {}).get("coordinates") == dumped:
                continue  # idempotent — already stamped
            attrs = dict(p.attrs or {})
            attrs["coordinates"] = dumped
            p.attrs.clear()
            p.attrs.update(attrs)
            changed = True
        if changed:
            _write_bundle(bundle, claims)
            modified.append(bundle)
    return modified


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
            geo=_read_geo_sidecar(citation_url, geocoder=geocoder),
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
                geo=_read_geo_sidecar(image_url, geocoder=geocoder),
            ))

    claims = _merge_chunks(chunks)
    # The frame carries no date of its own; the sibling write-up states the pass date. Inherit it before
    # dedup/id-assignment — exactly where ``lane._finalize`` does, so the recording equals the live run.
    claims = imagery.inherit_observation_time(claims)
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
    geocoder: adapters.Geocoder | None = None, only: Sequence[str] | None = None,
) -> list[Path]:
    """Record the frozen bundles for one scenario — the keyed path that produces the keyless baseline.

    For every source in ``config.sources.sources`` whose ``citation_url`` falls under ``scenario``, run
    the live extraction pipeline (:func:`_extract_source`) over the cited document and write its claims
    to ``<out_dir>/<source_id>.json``. ``ingest_time`` defaults to the pinned :data:`FROZEN_INGEST_TIME`
    and ``out_dir`` to ``corpus/scenarios/<scenario>/claims`` — so a bare ``extract_corpus("hq9p_primary",
    …)`` re-freezes the checked-in baseline in place. ``geocoder`` defaults to ``None`` (offline — no
    network at record time, fully deterministic); the CLI passes a live gazetteer→Nominatim chain so a
    keyed ``make extract`` freezes anchor coordinates. Returns the written bundle paths (source order).

    ``only`` restricts the run to the named ``source_id``\\ s — a **scoped re-record** for when one lane of
    the extractor changed and re-running the whole corpus would burn budget and churn bundles that cannot
    have changed. The stale-bundle prune is skipped in that mode (the un-recorded sources are still
    current, not orphans), so a scoped run is purely additive; a full run remains the way to reconcile
    the baseline with the config.

    Deterministic given the client's output **and** an offline (or gazetteer-only) geocoder: two runs
    write byte-identical files. Runs entirely upstream of ``store.append`` (G1).
    """
    ingest_time = ingest_time or FROZEN_INGEST_TIME
    wanted = set(only) if only else None
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
        if wanted is not None and entry.source_id not in wanted:
            continue
        claims = _extract_source(entry, client=client, config=config, ingest_time=ingest_time,
                                 geocoder=geocoder)
        out_path = target / f"{entry.source_id}.json"
        _write_bundle(out_path, claims)
        written.append(out_path)
        kept.add(out_path.name)
    if wanted is not None:
        return written  # scoped re-record: the un-recorded bundles are current, not orphans
    # Prune stale bundles: a source removed from config (or re-scoped to another scenario) must not leave
    # an orphan ``<source_id>.json`` that :func:`seed_store_from_bundles` still globs + appends — that
    # would drift the keyless baseline away from the current config (keyless ≢ live).
    for stale in target.glob("*.json"):
        # Preserve DERIVED-inference bundles (``<source>__attr.json`` / ``<source>__basing.json``): they
        # are produced by the separate offline enrichment passes (``python -m chanakya.ingest attribute
        # --record`` / ``basing --record``), not this per-source recorder, so they are never in ``kept`` —
        # but they belong to the frozen baseline and must survive a re-record of the source documents.
        if stale.name not in kept and not _is_derived_bundle(stale.name):
            stale.unlink()
    return written
