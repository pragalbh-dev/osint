"""The VLM imagery gate, evidenced deliberately — because no text score can evidence it.

Dropping the locked VLM imagery path **disqualifies** a candidate (plan §8): it is a precondition, not a
heavy score line. But the labeled gold slice is text-only, so no number the scorer computes from it says
anything about imagery. Left alone the gate reads ``UNKNOWN`` forever — which is the honest answer, and
also a useless one, because UNKNOWN blocks every candidate equally and the bake-off can never conclude.

So the gate gets its own small, deliberate experiment, and this module is it. Four properties are
load-bearing:

* **The real path, not an imitation.** The probe drives ``chanakya.ingest.imagery.read_image_document``
  on a real corpus image with the shipped config. That is the exact call the ingest lane makes for a
  standalone ``.png``, forcing the real ``ImageryObservation`` tool through the real
  ``ExtractionClient.read_image`` seam. A probe that hand-rolled its own image request would evidence a
  path the system does not use — the same mistake as measuring a model on a parallel implementation.
* **Same image, every candidate.** One frame, chosen once (:data:`DEFAULT_IMAGE`), so the comparison is
  between providers rather than between pictures.
* **Evidence, not assumption.** A candidate PASSes only when a standalone-image call was *attempted and
  returned*. Attempted-and-raised is FAIL. Never attempted is UNKNOWN — and UNKNOWN blocks winning, so
  "we did not check" can never quietly become "it works".
* **Recorded, and pinned to the model id it was recorded against.** The verdict is persisted so
  ``preflight`` can read it without re-spending, and a record whose ``model_id`` no longer matches the
  candidate's declared pinned id is treated as **absent**. Re-pinning a candidate must not inherit the
  previous model's evidence.

One image per candidate is one call: ``literature_ref`` is left unset, so the optional second
(corroboration) call is never eligible. The probe therefore costs exactly one standalone-image call per
candidate, which is the minimum that can evidence the gate at all.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .gates import GateResult, gate_vlm_imagery
from .policy import Candidate
from .recording import RecordingExtractionClient

#: Bumped when the probe's *procedure* changes in a way that invalidates an older record.
PROBE_VERSION = 1

#: The one frame every candidate is shown. A real corpus image (a satellite frame whose coverage is
#: withheld), so the read exercises the same shape the demo does. Content is irrelevant to the gate —
#: this measures that the standalone-image lane survives, not what the model saw.
DEFAULT_IMAGE = Path("corpus/scenarios/hq9p_primary/docs/d17b_withheld_gap.png")


def default_image_path() -> Path:
    """:data:`DEFAULT_IMAGE` resolved against the repository root."""
    from chanakya import settings

    return settings.repo_root() / DEFAULT_IMAGE


def default_evidence_path() -> Path:
    """Where the recorded verdicts live by default — a readable artefact, not a hidden cache."""
    from chanakya import settings

    return settings.repo_root() / "tmp" / "rk-bakeoff" / "vlm-gate-evidence.json"


# ── the record ────────────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ImageryEvidence:
    """One candidate's standalone-image result: what was run, against what, and what came back."""

    candidate_id: str
    #: The pinned model id the call was actually made against. A record for a *different* id is stale.
    model_id: str
    image: str
    calls_ok: int
    calls_total: int
    recorded_at: str
    probe_version: int = PROBE_VERSION
    #: The exception text when the call raised, verbatim. Never a summary: a provider's own words about
    #: why an image request failed are the whole value of a failed probe.
    error: str | None = None

    @property
    def fresh_for(self) -> tuple[str, int]:
        return self.model_id, self.probe_version

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, raw: dict[str, Any]) -> ImageryEvidence:
        fields = {k: raw.get(k) for k in
                  ("candidate_id", "model_id", "image", "calls_ok", "calls_total", "recorded_at",
                   "probe_version", "error")}
        return cls(
            candidate_id=str(fields["candidate_id"] or ""),
            model_id=str(fields["model_id"] or ""),
            image=str(fields["image"] or ""),
            calls_ok=int(fields["calls_ok"] or 0),
            calls_total=int(fields["calls_total"] or 0),
            recorded_at=str(fields["recorded_at"] or ""),
            probe_version=int(fields["probe_version"] or 0),
            error=fields["error"] if isinstance(fields["error"], str) else None,
        )


def load_evidence(path: Path | str | None = None) -> dict[str, ImageryEvidence]:
    """Read the recorded verdicts. A missing or malformed file yields ``{}`` — i.e. nothing verified."""
    target = Path(path) if path is not None else default_evidence_path()
    if not target.is_file():
        return {}
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    rows = raw.get("evidence") if isinstance(raw, dict) else None
    if not isinstance(rows, list):
        return {}
    out: dict[str, ImageryEvidence] = {}
    for row in rows:
        if isinstance(row, dict) and row.get("candidate_id"):
            record = ImageryEvidence.from_json(row)
            out[record.candidate_id] = record
    return out


def save_evidence(records: dict[str, ImageryEvidence], path: Path | str | None = None) -> Path:
    """Write the verdicts byte-stably (sorted, indented), creating the directory if needed."""
    target = Path(path) if path is not None else default_evidence_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "rk-bakeoff-vlm-evidence/1.0",
        "note": ("Evidence for the PASS/FAIL VLM imagery gate. A record is honoured only while its "
                 "model_id matches the candidate's pinned model_id and its probe_version matches the "
                 "current probe. No record, or a stale one, means UNKNOWN — never a pass."),
        "evidence": [records[k].to_json() for k in sorted(records)],
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def evidence_for(candidate: Candidate, records: dict[str, ImageryEvidence]) -> ImageryEvidence | None:
    """The record that may be honoured for this candidate, or ``None`` when absent or stale."""
    record = records.get(candidate.id)
    if record is None:
        return None
    if record.model_id != candidate.model_id or record.probe_version != PROBE_VERSION:
        return None
    return record


def gate_from_evidence(candidate: Candidate,
                       records: dict[str, ImageryEvidence]) -> tuple[GateResult, ImageryEvidence | None]:
    """The VLM gate judged on recorded evidence. Reuses the one gate function — no second rule."""
    record = evidence_for(candidate, records)
    ok = record.calls_ok if record else 0
    total = record.calls_total if record else 0
    return gate_vlm_imagery(candidate, image_calls_ok=ok, image_calls_total=total), record


# ── running the probe ─────────────────────────────────────────────────────────────────────────────

#: ``(candidate) -> client | None``. ``None`` marks the candidate unexercisable (no key, no SDK).
ProbeClientFactory = Callable[[Candidate], Any | None]


def _live_factory(candidate: Candidate) -> Any | None:
    from .runner import live_client_factory

    return live_client_factory(candidate, 1)


def probe_candidate(candidate: Candidate, *, config: Any, image_path: Path | str | None = None,
                    client_factory: ProbeClientFactory = _live_factory,
                    now: datetime | None = None) -> ImageryEvidence | None:
    """Show one candidate one image through the real imagery lane. ``None`` ⇒ not exercisable.

    Returning ``None`` rather than a zero-call record is deliberate: "no key, so nothing ran" is already
    reported by the ``exercisable`` gate, and writing a ``0/0`` record would look like a probe that ran
    and found nothing. An exception inside the call *is* recorded — a provider that 500s on an image is
    a FAIL of this gate, and the message is the evidence.

    **A failure that never reached the provider is UNKNOWN, not FAIL.** The recorder wraps ``read_image``
    itself, so every provider-side error lands in ``image_calls`` with its message; an exception with *no*
    image call recorded therefore happened upstream of the request — an unreadable file, a loader problem,
    our bug — and says nothing about whether that model can read a frame. It is recorded as ``0/0`` plus
    the verbatim error, which the gate reads as UNKNOWN (still blocking) rather than as a disqualification
    the candidate did not earn.
    """
    from chanakya.ingest.imagery import read_image_document

    client = client_factory(candidate)
    if client is None:
        return None

    target = Path(image_path) if image_path is not None else default_image_path()
    data = target.read_bytes()
    recorder = RecordingExtractionClient(client)
    error: str | None = None
    try:
        read_image_document(
            data, file=target.name, source_id=f"vlm-gate-{candidate.id}", config=config,
            client=recorder,
        )
    except Exception as exc:  # recorded as the gate result it is, never swallowed into a pass
        error = f"{type(exc).__name__}: {exc}"

    image_calls = recorder.image_calls()
    stamp = (now or datetime.now(UTC)).replace(microsecond=0).isoformat()
    return ImageryEvidence(
        candidate_id=candidate.id,
        model_id=getattr(client, "model_id", candidate.model_id),
        image=target.name,
        calls_ok=sum(1 for c in image_calls if c.ok),
        calls_total=len(image_calls),
        recorded_at=stamp,
        error=error,
    )


__all__ = [
    "DEFAULT_IMAGE",
    "PROBE_VERSION",
    "ImageryEvidence",
    "ProbeClientFactory",
    "default_evidence_path",
    "default_image_path",
    "evidence_for",
    "gate_from_evidence",
    "load_evidence",
    "probe_candidate",
    "save_evidence",
]
