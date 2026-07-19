"""Ingest-lane tests — the concurrent extraction fan-out + the serial single-writer append/rebuild.

Everything is **offline + deterministic** (gate G10): the real config bundle is seeded from
``config/*.yaml``, the evidence/decision logs are in-memory, and the extraction client is either a
:class:`ScriptedExtractionClient` (a single-call doc, where the FIFO cannot race) or a small
thread-safe, input-routed ``_ProbeClient`` that also records how many calls were simultaneously in
flight — so concurrency can be *asserted*, not hoped for.

``rebuild``/``evaluate`` are **injected** into :func:`ingest_document` (gate G9 — the lane imports no
pipeline stage). A test *may* import those stages (only ``chanakya/ingest`` *source* is G9-scanned), so
the :func:`_ingest` helper wires the real ones exactly as the ``/ingest`` API will. The graded beats:

* **text doc ingests** — a prose doc → claims appended + ``rebuilt=True``, every id namespaced by doc.
* **the batch is concurrent** — ``extract_many`` over several docs overlaps their I/O (``max_in_flight``
  climbs above 1) and yields one canonical claim list per doc.
* **within-doc concurrency** — a multimodal doc's text extraction runs in parallel with its image read,
  emitting both an ``llm`` text claim and a ``vlm`` observation.
* **serialisation / determinism** — the same doc + client mints byte-identical ids across runs despite
  the phase-1 race (append + id assignment is the serial single-writer section).
* **G1** — the client is called only in phase 1; it is never touched inside the injected ``rebuild()``.
* **anti-fabrication guard** — an empty text payload triggers no extraction call at all.
"""

from __future__ import annotations

import asyncio
import io
import threading
import time
from typing import Any

from chanakya import settings
from chanakya.config.store import ConfigStore
from chanakya.ingest.client import ScriptedExtractionClient
from chanakya.ingest.lane import DocInput, extract_many, ingest_document
from chanakya.observe import (
    evaluate,  # a test may import stages; only chanakya/ingest source is G9-scanned
)
from chanakya.schemas import ClaimRecord, ConfigBundle
from chanakya.store import DecisionLog, EvidenceLog
from chanakya.view import rebuild

# ── fixtures / helpers ─────────────────────────────────────────────────────────────────────────

_PROSE_TEXT = "CPMIEC is the export agent for the launcher family.\n"


def _ingest(*args: Any, **kwargs: Any) -> Any:
    """:func:`ingest_document` with the real ``rebuild``/``evaluate`` injected — the wiring the ``/ingest``
    API performs. Individual tests override ``rebuild_fn`` (the G1 spy) or drop the rebuild via
    ``live_rebuild=False``; both defaults are set here so the common case reads cleanly."""
    kwargs.setdefault("rebuild_fn", rebuild)
    kwargs.setdefault("observe_fn", evaluate)
    return ingest_document(*args, **kwargs)


def _config() -> ConfigBundle:
    """The real config bundle (ontology + sources + credibility + observables) — no network."""
    return ConfigStore.seed_from(settings.config_dir()).snapshot()


def _png(color: tuple[int, int, int] = (40, 90, 160), size: int = 32) -> bytes:
    """A tiny deterministic PNG (real bytes, so the imagery fingerprint actually computes)."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (size, size), color).save(buf, format="PNG")
    return buf.getvalue()


def _prose_fill() -> dict[str, Any]:
    """A prose-format tool fill that yields exactly one manufacturer entity claim."""
    return {
        "manufacturers": [
            {"name": "CPMIEC", "role": "export-agent", "source_quote": "CPMIEC is the export agent"}
        ]
    }


def _obs_fill() -> dict[str, Any]:
    """A corroboration-eligible imagery-observation tool fill (occupied, overhead, features present)."""
    return {
        "geometry_tokens": ["radial-revetments", "central-radar-berm"],
        "occupancy_state": "occupied",
        "object_count_min": 4,
        "object_count_max": 6,
        "count_object": "revetments",
        "description": "A prepared site: revetments ringing a central berm.",
        "resolution_sufficiency": "sufficient",
        "frame_kind": "overhead",
    }


def _route(tool_name: str) -> dict[str, Any]:
    """Deterministically route a forced-tool call to its canned fill by the tool name (never the FIFO).

    Thread-safe by construction (returns a fresh dict per call, keyed only on the immutable tool name),
    so it stays correct under the concurrent within-doc / across-doc fan-out where a shared FIFO races.
    """
    if tool_name == "read_overhead_image":
        return _obs_fill()
    if tool_name == "corroborate_signature":
        return {"consistent": False}
    return _prose_fill()


class _ProbeClient:
    """A thread-safe, input-routed extraction client that records peak in-flight concurrency.

    Each call sleeps briefly while holding an in-flight counter, so a genuinely-parallel fan-out drives
    ``max_in_flight`` above 1 — the concurrency assertion. Routing is by tool name (not a FIFO), so the
    read is deterministic regardless of which thread dequeues first.
    """

    def __init__(self, *, model_id: str = "probe", delay: float = 0.05) -> None:
        self.model_id = model_id
        self._delay = delay
        self._lock = threading.Lock()
        self.in_flight = 0
        self.max_in_flight = 0
        self.calls = 0

    def _enter(self) -> None:
        with self._lock:
            self.in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self.in_flight)
            self.calls += 1

    def _leave(self) -> None:
        with self._lock:
            self.in_flight -= 1

    def extract(self, *, tool_name: str, input_schema: dict[str, Any], system: str, text: str) -> dict[str, Any]:
        self._enter()
        try:
            time.sleep(self._delay)
            return _route(tool_name)
        finally:
            self._leave()

    def read_image(self, *, tool_name: str, input_schema: dict[str, Any], system: str,
                   image: bytes, media_type: str) -> dict[str, Any]:
        self._enter()
        try:
            time.sleep(self._delay)
            return _route(tool_name)
        finally:
            self._leave()


# ── a text doc ingests → appended + rebuilt ──────────────────────────────────────────────────────

def test_text_doc_ingests_appends_and_rebuilds() -> None:
    store = EvidenceLog()
    client = ScriptedExtractionClient([_prose_fill()])  # exactly one call → no FIFO race
    res = _ingest(_PROSE_TEXT, source_id="d01", source_type="curated-register",
                  config=_config(), client=client, store=store, file="d01.txt")
    assert res.rebuilt is True
    assert res.appended_claim_ids  # non-empty
    assert all(cid.startswith("d01-") for cid in res.appended_claim_ids)
    assert store.count() == len(res.appended_claim_ids)
    replayed = {c.claim_id for c in store.replay()}
    assert set(res.appended_claim_ids) <= replayed
    # prev_view is None on a cold ingest → the baseline is the reference point, no alerts.
    assert res.alerts_fired == []


def test_live_rebuild_false_appends_without_rebuilding() -> None:
    store = EvidenceLog()
    client = ScriptedExtractionClient([_prose_fill()])
    res = _ingest(_PROSE_TEXT, source_id="d01", source_type="curated-register",
                  config=_config(), client=client, store=store, file="d01.txt",
                  live_rebuild=False)
    assert res.rebuilt is False
    assert res.alerts_fired == []
    assert store.count() == len(res.appended_claim_ids) > 0  # claims still committed


def test_no_rebuild_fn_skips_rebuild_even_when_live() -> None:
    # G9: with no injected rebuild_fn the lane cannot reach a pipeline stage — it appends, and skips.
    store = EvidenceLog()
    client = ScriptedExtractionClient([_prose_fill()])
    res = ingest_document(_PROSE_TEXT, source_id="d01", source_type="curated-register",
                          config=_config(), client=client, store=store, file="d01.txt")
    assert res.rebuilt is False  # no rebuild_fn supplied
    assert store.count() == len(res.appended_claim_ids) > 0  # but claims are still committed


def test_decision_store_is_accepted() -> None:
    store, decisions = EvidenceLog(), DecisionLog()
    client = ScriptedExtractionClient([_prose_fill()])
    res = _ingest(_PROSE_TEXT, source_id="d01", source_type="curated-register",
                  config=_config(), client=client, store=store, file="d01.txt",
                  decision_store=decisions)
    assert res.rebuilt is True
    assert res.appended_claim_ids


# ── the batch runs concurrently and yields per-doc claim lists ────────────────────────────────────

def test_extract_many_runs_concurrently_and_yields_per_doc_lists() -> None:
    client = _ProbeClient(delay=0.05)
    docs = [
        DocInput(raw=_PROSE_TEXT, source_id=f"d{i:02d}", source_type="curated-register",
                 file=f"d{i:02d}.txt")
        for i in range(1, 5)  # four docs
    ]
    result = asyncio.run(extract_many(docs, concurrency=8, client=client, config=_config()))

    assert len(result) == 4  # one claim list per doc, in docs order
    for claim_list in result:
        assert claim_list and all(isinstance(c, ClaimRecord) for c in claim_list)
    assert result[0][0].claim_id.startswith("d01-")
    assert result[3][0].claim_id.startswith("d04-")
    # the fan-out genuinely overlapped: more than one call was in flight at once.
    assert client.calls == 4
    assert client.max_in_flight >= 2


# ── within-doc concurrency: text ∥ image, both emit claims ────────────────────────────────────────

def test_multimodal_doc_emits_text_claim_and_vlm_observation() -> None:
    store = EvidenceLog()
    client = _ProbeClient(delay=0.05)
    res = _ingest(_PROSE_TEXT, source_id="d07", source_type="curated-register",
                  config=_config(), client=client, store=store, file="d07.txt",
                  images=[(_png(), "d07.png")])
    claims = store.replay()
    methods = {c.extraction.method for c in claims}
    assert "llm" in methods   # the text extraction
    assert "vlm" in methods   # the co-located imagery observation
    assert res.rebuilt is True
    # the text extract ran in parallel with the image read.
    assert client.calls == 2
    assert client.max_in_flight >= 2


def test_empty_text_with_image_makes_no_text_extraction_call() -> None:
    store = EvidenceLog()
    client = _ProbeClient(delay=0.0)
    res = _ingest("", source_id="d10", source_type="satellite-imagery",
                  config=_config(), client=client, store=store, file="d10.txt",
                  images=[(_png(), "d10.png")])
    assert client.calls == 1  # ONLY the image was read; empty text triggered no extract call
    assert {c.extraction.method for c in store.replay()} == {"vlm"}
    assert res.rebuilt is True


# ── serialisation: ids are byte-stable across runs despite the phase-1 race ───────────────────────

def test_append_and_ids_are_deterministic_across_runs() -> None:
    config = _config()

    def run() -> list[str]:
        store = EvidenceLog()
        client = _ProbeClient(delay=0.02)
        res = _ingest(_PROSE_TEXT, source_id="d07", source_type="curated-register",
                      config=config, client=client, store=store, file="d07.txt",
                      images=[(_png(), "d07.png")])
        return res.appended_claim_ids

    first, second = run(), run()
    assert first  # non-empty
    assert first == second  # canonical ids are byte-identical regardless of extraction order


# ── G1: the client is called only upstream of the append, never inside rebuild ────────────────────

def test_client_is_never_called_inside_rebuild() -> None:
    store = EvidenceLog()
    client = _ProbeClient(delay=0.0)
    seen: dict[str, int] = {}

    def spy(evidence: object, decision: object, config: ConfigBundle,
            prev_view: object | None = None) -> object:
        seen["entry"] = client.calls
        view = rebuild(evidence, decision, config, prev_view)  # type: ignore[arg-type]
        seen["exit"] = client.calls
        return view

    res = ingest_document(_PROSE_TEXT, source_id="d01", source_type="curated-register",
                          config=_config(), client=client, store=store, file="d01.txt",
                          rebuild_fn=spy, observe_fn=evaluate)

    assert res.rebuilt is True
    assert seen["entry"] > 0             # extraction already ran before the rebuild
    assert seen["entry"] == seen["exit"]  # not a single client call happened inside rebuild() (G1)
