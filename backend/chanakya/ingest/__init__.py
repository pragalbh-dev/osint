"""INGEST — source-typed extraction → ClaimRecord + the live-ingest lane + keyless seed bundles.

The one package that turns a raw document (prose / structured record / imagery) into **sourced,
provenance-bearing, deduplicated claims** and appends them to the evidence log — faithfully, never
resolving or scoring (that is RESOLVE/SCORE downstream). Public surface (submodules carry the detail):

* :func:`~chanakya.ingest.lane.ingest_document` — the always-available live lane: raw doc → concurrent
  extraction → serial dedup+id → single-writer append → (injected) rebuild → observe. The one call the
  ``/ingest`` API wraps.
* :func:`~chanakya.ingest.extract.extract_document` — the source-typed extraction entrypoint (a loaded
  doc → claims), off the rebuild path; :data:`~chanakya.ingest.extract.SCHEMAS` + ``format_sniffer``.
* :func:`~chanakya.ingest.imagery.read_image_document` — the subject-blind VLM imagery lane (two-hash +
  signature→variant corroboration).
* :func:`ingest_bundle` — parse a pre-extracted claim bundle (``list[dict]`` → claims): the keyless
  append body of ``POST /ingest``. The frozen bundles are the output of live extraction over the same
  docs, so appending them yields the *identical* claims a live extract would (keyless ≡ live).
* :func:`~chanakya.ingest.seed.seed_store_from_bundles` / ``extract_corpus`` — the frozen-seed baseline +
  the ``python -m chanakya.ingest`` CLI (``make extract``).
* :func:`~chanakya.ingest.loaders.load_document` / :func:`~chanakya.ingest.client.build_extraction_client`.

**Gate G9:** nothing here imports a subject/ontology-instance or a downstream pipeline stage (the
``view`` reducer, ``resolve``, the scoring stages, or ``observe``). The lane triggers ``rebuild`` /
``observe`` via **injected** callables the API supplies — never an import — so ingest stays decoupled
and source-typed.
"""

from __future__ import annotations

from typing import Any

from chanakya.ingest.client import ExtractionClient, build_extraction_client
from chanakya.ingest.extract import SCHEMAS, extract_document, format_sniffer
from chanakya.ingest.imagery import LiteratureRef, read_image_document
from chanakya.ingest.lane import DocInput, extract_many, ingest_document
from chanakya.ingest.loaders import LoadedDoc, Region, load_document
from chanakya.ingest.seed import extract_corpus, seed_store_from_bundles
from chanakya.schemas import ClaimRecord


def ingest_bundle(bundle: list[dict[str, Any]]) -> list[ClaimRecord]:
    """Parse a pre-extracted claim bundle (a list of ``ClaimRecord`` dicts) → claims. Pure, keyless.

    The append body of ``POST /ingest``'s keyless path (``IngestRequest.bundle``) — the in-memory twin of
    :func:`chanakya.ingest.seed.ingest_bundle`, which reads the same JSON from a file. No LLM, no network:
    a frozen bundle is the output of live extraction over the same doc, so appending it is byte-for-byte
    the keyless equal of the live lane.
    """
    return [ClaimRecord.model_validate(row) for row in bundle]


__all__ = [
    # the live lane
    "ingest_document", "extract_many", "DocInput",
    # extraction
    "extract_document", "format_sniffer", "SCHEMAS", "read_image_document", "LiteratureRef",
    # keyless bundles + seed baseline
    "ingest_bundle", "seed_store_from_bundles", "extract_corpus",
    # building blocks
    "load_document", "LoadedDoc", "Region", "build_extraction_client", "ExtractionClient",
]
