"""Durable per-document run artefacts, so one exception cannot throw away calls already paid for.

WHY THIS EXISTS
───────────────
On 2026-07-26 a three-way live run was attempted three times and died three times — twice on a
concurrency race in the Gemini client, once on ``openai.RateLimitError``. ``anthropic-opus-5`` completed
all five of its runs on **every** attempt and was billed for all three, because the harness kept every
result in memory and had no way to re-enter a run: one raised exception discarded roughly 225 Opus calls
and produced no scorecard at all. The retry wrapper (:mod:`.resilience`) closes only the transport-fault
case; it cannot help when the process itself ends.

So a run is now **durable at the document**. Each document's result is written the moment it comes back —
its claims *and* the call records the scorer needs — and a later invocation reuses what is on disk instead
of re-buying it. The unit is the document rather than the run because that is the unit a call is bought
at: a run that dies on document five keeps the four that were paid for.

WHAT IS STORED, AND WHY BOTH HALVES
───────────────────────────────────
``<out_dir>/<candidate>/run-NN/``

* ``<source_id>.json`` — the claim bundle, byte-identical in shape to what ``ingest.seed`` freezes. This
  is the artefact that already existed and it is unchanged, so a reviewer diffing bundles sees the same
  file they always did.
* ``_resume/<source_id>.json`` — the sidecar: the recorded calls, the fingerprint, and which invocation
  bought them.

Both halves are needed and neither is optional. Three of the scored criteria
(``structured_output_reliability``, ``discriminator_capture`` and its fabrication half, and cost/latency)
are measured **at the call** and never reach a ``ClaimRecord`` — so a cache that stored only claims would
resume into a run whose reliability line was silently unmeasured. That is the failure mode this project
keeps hitting: a green artefact carrying a claim nobody checked.

THE TWO CORRECTNESS RULES
─────────────────────────
1. **A resumed run is honest about being one.** Every cached document records the invocation that bought
   it, and :class:`RunProvenance` reports when a candidate's runs did not all come from one sitting.
   ``determinism`` is a *measured line* here — the spread across runs is what the margin rule subtracts
   before calling any gap real — so stitching runs from different sessions and printing determinism as if
   it had been sampled in one is a corrupted measurement, not a cosmetic detail. The scorecard says so.

2. **A bundle whose inputs changed is never reused.** The fingerprint covers the pinned model id, the
   document set (identity *and* content), and the prompt/schema version the pipeline would send. Re-pin a
   candidate, edit a document, or change a system prompt or a tool schema, and every cached bundle for it
   stops matching and is re-bought. A stale bundle silently scored as fresh would be a benchmark result
   about code that no longer exists.

   The gold is deliberately **not** in the fingerprint. It is a scoring-side input: re-scoring a recorded
   run against a corrected answer file costs nothing and buys a better number from calls already paid for,
   which is the whole point of keeping the bundles.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chanakya.ingest.lane import DocInput
from chanakya.schemas import ClaimRecord

from .recording import CallRecord

#: Bump when the sidecar's shape changes in a way that makes an older one unreadable. An unrecognised
#: version is treated as a miss (re-bought), never as something to guess the shape of.
SCHEMA = "rk-bakeoff-resume/1"

#: Subdirectory of a run directory holding the sidecars, so the claim bundles stay the only ``*.json`` at
#: the top level and a reviewer diffing bundles is not handed harness bookkeeping.
SIDECAR_DIR = "_resume"


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# The fingerprint — what makes a cached bundle still valid.
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def _sha(*parts: bytes) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(len(part).to_bytes(8, "big"))
        h.update(part)
    return h.hexdigest()


def _raw_bytes(raw: str | bytes) -> bytes:
    return raw.encode("utf-8") if isinstance(raw, str) else raw


def document_set_digest(docs: Sequence[DocInput]) -> str:
    """A digest over the slice's identity **and** content, including co-located frames.

    Deliberately covers the whole slice rather than one document, and is therefore deliberately
    conservative: editing any document invalidates every cached bundle in the run, not just that
    document's. That is the safe direction. Recall and precision are scored over the slice as a whole, so
    a slice that changed under a half-reused run is a different measurement wearing the old one's numbers,
    and cheap re-buying is a far better failure than a quiet one.
    """
    rows: list[str] = []
    for doc in sorted(docs, key=lambda d: d.source_id):
        images = "|".join(f"{rel}:{_sha(data)}" for data, rel in doc.images)
        rows.append("\x1f".join([doc.source_id, doc.source_type, doc.file,
                                 _sha(_raw_bytes(doc.raw)), images]))
    return _sha(*(row.encode("utf-8") for row in rows))


def prompt_schema_digest() -> str:
    """A digest over every system prompt and forced-tool schema the extraction path would send.

    **Derived, never hand-maintained.** A version constant someone has to remember to bump is a constant
    that will not be bumped on the one commit where it mattered, and the consequence here is a cached
    bundle produced by a prompt that no longer exists being scored as current. So this reads the shipped
    prompts and the live ``model_json_schema()`` of every extraction tool — pass 1 per format, pass 2
    (coreference), and the imagery lane — and any edit to any of them changes the digest on its own.

    An import failure is not swallowed into a benign-looking constant: it raises, because a fingerprint
    that silently stops covering the prompts is worse than no cache at all.
    """
    from chanakya.ingest import coref, extract, imagery

    parts: list[str] = []
    for fmt in sorted(extract.SCHEMAS):
        model = extract.SCHEMAS[fmt]
        parts.append(fmt)
        parts.append(extract._TOOL_NAMES[fmt])
        parts.append(extract._SYSTEM_PROMPTS[fmt])
        parts.append(json.dumps(model.model_json_schema(), sort_keys=True))
    parts.append(coref.TOOL_NAME)
    parts.append(coref.SYSTEM)
    parts.append(json.dumps(coref.CoreferenceClusters.model_json_schema(), sort_keys=True))
    parts.append(imagery._VLM_SYSTEM)
    parts.append(imagery._CORROBORATION_SYSTEM)
    for name in ("ImageryObservation", "SignatureCorroboration"):
        imagery_model = getattr(imagery, name, None)
        if imagery_model is not None and hasattr(imagery_model, "model_json_schema"):
            parts.append(name)
            parts.append(json.dumps(imagery_model.model_json_schema(), sort_keys=True))
    return _sha(*(p.encode("utf-8") for p in parts))


#: Producer kinds. A cached bundle records which one made it, and the two can never satisfy each other's
#: lookups — see :func:`fingerprint`.
LIVE = "live"
DRY = "dry"


def fingerprint(*, model_id: str, docs: Sequence[DocInput], producer: str = LIVE) -> str:
    """The cache key's validity half: producer kind + pinned model id + document set + prompt/schema.

    ``producer`` is the fourth component and it is not bookkeeping. ``--dry-run`` walks the identical path
    with a scripted double that reports the candidate's real ``model_id``, so without this every dry run
    would leave behind bundles a *live* run would happily reuse — and a scorecard would then rank three
    models on invented text while every gate read green. That is the precise failure this project keeps
    hitting, so the two kinds are made mutually unreadable at the key rather than kept apart by
    convention.
    """
    return _sha(producer.encode("utf-8"),
                model_id.encode("utf-8"),
                document_set_digest(docs).encode("utf-8"),
                prompt_schema_digest().encode("utf-8"))


def new_invocation_id() -> str:
    """One id per ``python -m eval.extraction run``, stamped onto everything that invocation buys."""
    return f"inv-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:6]}"


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# What a cached document is.
# ══════════════════════════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CachedDoc:
    """One document of one run, as recovered from disk — both halves the scorer needs."""

    source_id: str
    claims: tuple[ClaimRecord, ...]
    calls: tuple[CallRecord, ...]
    invocation: str
    recorded_at: str


def _call_to_json(call: CallRecord) -> dict[str, Any]:
    return {
        "lane": call.lane,
        "tool_name": call.tool_name,
        "offered_fields": list(call.offered_fields),
        "payload": call.payload,
        "latency_s": call.latency_s,
        "error": call.error,
        "usage": call.usage,
    }


def _call_from_json(row: dict[str, Any]) -> CallRecord:
    return CallRecord(
        lane=str(row.get("lane", "text")),
        tool_name=str(row.get("tool_name", "")),
        offered_fields=tuple(row.get("offered_fields") or ()),
        payload=row.get("payload") if isinstance(row.get("payload"), dict) else None,
        latency_s=float(row.get("latency_s") or 0.0),
        error=row.get("error"),
        usage=row.get("usage") if isinstance(row.get("usage"), dict) else None,
    )


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# The store.
# ══════════════════════════════════════════════════════════════════════════════════════════════════

@dataclass
class ResumeStore:
    """Reads and writes the per-document artefacts under ``<root>/<candidate>/run-NN/``.

    ``enabled=False`` turns the whole thing into a writer with no reader: artefacts are still produced
    (they always were) but nothing is ever reused. That is what ``--no-resume`` gives an operator who
    wants a clean, single-invocation measurement and is willing to pay for it — the honest way to get
    determinism sampled in one sitting, rather than deleting a directory and hoping.
    """

    root: Path
    invocation: str
    enabled: bool = True

    def run_dir(self, candidate_id: str, run_index: int) -> Path:
        return self.root / candidate_id / f"run-{run_index:02d}"

    def _sidecar(self, candidate_id: str, run_index: int, source_id: str) -> Path:
        return self.run_dir(candidate_id, run_index) / SIDECAR_DIR / f"{source_id}.json"

    def _bundle(self, candidate_id: str, run_index: int, source_id: str) -> Path:
        return self.run_dir(candidate_id, run_index) / f"{source_id}.json"

    # ── read ──────────────────────────────────────────────────────────────────────────────────────

    def load(self, candidate_id: str, run_index: int, source_id: str,
             expected_fingerprint: str) -> CachedDoc | None:
        """The cached document, or ``None`` for **any** doubt at all.

        Every failure path returns a miss rather than a partial result: a missing half, an unreadable
        file, an unrecognised schema, a fingerprint that does not match. The cost of a miss is one call
        re-bought; the cost of a wrong hit is a benchmark number about inputs that no longer exist.
        """
        if not self.enabled:
            return None
        sidecar = self._sidecar(candidate_id, run_index, source_id)
        bundle = self._bundle(candidate_id, run_index, source_id)
        if not sidecar.exists() or not bundle.exists():
            return None
        try:
            meta = json.loads(sidecar.read_text(encoding="utf-8"))
            if meta.get("schema") != SCHEMA:
                return None
            if meta.get("fingerprint") != expected_fingerprint:
                return None
            rows = json.loads(bundle.read_text(encoding="utf-8"))
            claims = tuple(ClaimRecord.model_validate(r) for r in rows)
            calls = tuple(_call_from_json(c) for c in (meta.get("calls") or []))
        except Exception:
            return None
        return CachedDoc(
            source_id=source_id, claims=claims, calls=calls,
            invocation=str(meta.get("invocation") or "unknown"),
            recorded_at=str(meta.get("recorded_at") or ""),
        )

    # ── write ─────────────────────────────────────────────────────────────────────────────────────

    def save(self, candidate_id: str, run_index: int, doc: DocInput,
             claims: Sequence[ClaimRecord], calls: Sequence[CallRecord],
             expected_fingerprint: str) -> None:
        """Persist one document's result **as it completes**, both halves, atomically each.

        Written via a temp file and ``os.replace`` so a process killed mid-write leaves either the old
        file or the new one, never a half-written JSON that the next invocation would read as a miss
        after having already been paid for. The claim bundle keeps the exact byte-stable shape
        ``ingest.seed`` freezes.
        """
        run = self.run_dir(candidate_id, run_index)
        (run / SIDECAR_DIR).mkdir(parents=True, exist_ok=True)
        rows = [c.model_dump(mode="json") for c in claims]
        _atomic_write(self._bundle(candidate_id, run_index, doc.source_id),
                      json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        meta = {
            "schema": SCHEMA,
            "candidate_id": candidate_id,
            "run_index": run_index,
            "source_id": doc.source_id,
            "fingerprint": expected_fingerprint,
            "invocation": self.invocation,
            "recorded_at": datetime.now(UTC).isoformat(),
            "calls": [_call_to_json(c) for c in calls],
        }
        _atomic_write(self._sidecar(candidate_id, run_index, doc.source_id),
                      json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# Provenance — the honesty half.
# ══════════════════════════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class RunProvenance:
    """Which invocations bought a candidate's runs, and how much of the result was reused.

    Carried onto the scorecard rather than kept as a log line because ``determinism`` is one of the
    measured criteria: it is the mean claim-set agreement between a candidate's runs, and a set of runs
    assembled across sittings has been sampled over provider-side change as well as model variance. That
    does not make the number wrong, but it makes it a different number than the one a reader assumes, and
    the difference has to be stated where the number is printed.
    """

    #: Every invocation that contributed a document, in first-seen order.
    invocations: tuple[str, ...] = ()
    #: This process's own id — so a reader can tell which of the above was "now".
    current: str = ""
    documents_reused: int = 0
    documents_bought: int = 0

    @property
    def single_invocation(self) -> bool:
        """Did every document of every run come from one sitting? The condition determinism assumes."""
        return len(self.invocations) <= 1

    @property
    def resumed(self) -> bool:
        return self.documents_reused > 0

    def statement(self) -> str:
        if not self.invocations:
            return "no documents were recorded, so there is nothing to attribute"
        if self.single_invocation:
            source = self.invocations[0]
            if self.documents_reused and source != self.current:
                return (f"every run was REPLAYED from one earlier invocation ({source}); this invocation "
                        f"({self.current}) bought nothing. The runs were still sampled in a single "
                        "sitting, so `determinism` means what it usually means — but the numbers describe "
                        "that session, not this one")
            return (f"every run came from ONE invocation ({source}); "
                    f"{self.documents_bought} document-extraction(s) bought, none reused")
        return (
            f"STITCHED ACROSS {len(self.invocations)} INVOCATIONS "
            f"({', '.join(self.invocations)}): {self.documents_reused} document-extraction(s) reused from "
            f"disk and {self.documents_bought} bought now. The inputs are pinned identical (same model id, "
            "same documents, same prompts and schemas — a cached bundle is refused otherwise), but the "
            "runs were NOT sampled in one sitting, so `determinism` has been measured across provider-side "
            "change as well as model variance. Re-run with --no-resume for a single-invocation number."
        )


def summarize(reused: Iterable[tuple[str, str]], bought: Iterable[str], current: str) -> RunProvenance:
    """Fold ``(source_id, invocation)`` reuses and freshly-bought source ids into a provenance record."""
    order: list[str] = []
    reused_list = list(reused)
    for _, inv in reused_list:
        if inv not in order:
            order.append(inv)
    bought_list = list(bought)
    if bought_list and current not in order:
        order.append(current)
    return RunProvenance(invocations=tuple(order), current=current,
                         documents_reused=len(reused_list), documents_bought=len(bought_list))


def merge(provenances: Iterable[RunProvenance], current: str) -> RunProvenance:
    """One candidate's provenance across its N runs."""
    order: list[str] = []
    reused = bought = 0
    for prov in provenances:
        for inv in prov.invocations:
            if inv not in order:
                order.append(inv)
        reused += prov.documents_reused
        bought += prov.documents_bought
    return RunProvenance(invocations=tuple(order), current=current,
                         documents_reused=reused, documents_bought=bought)


__all__ = [
    "DRY",
    "LIVE",
    "SCHEMA",
    "SIDECAR_DIR",
    "CachedDoc",
    "ResumeStore",
    "RunProvenance",
    "document_set_digest",
    "fingerprint",
    "merge",
    "new_invocation_id",
    "prompt_schema_digest",
    "summarize",
]
