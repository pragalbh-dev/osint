"""Writeback = **append a DecisionRecord** — the one act that turns a disposition into graph state.

This is the load-bearing move of the whole session: HITL *never mutates the view*. It appends a
:class:`~chanakya.schemas.DecisionRecord` to the append-only decision log; the next ``rebuild()``
(F0-owned) reads that log and applies the record's ``effects``. So "override changes downstream
state" is **structural** — it falls out of event-sourcing, not a per-stage fan-out (master §1 #2,
gate G12). No LLM, no network, no clock is invoked here (gate G1): the wall-clock ``ts`` is *supplied*
by the caller (rebuild never reads it), and the ``event_id`` is *derived* deterministically from the
item + chosen option, so replaying the log is byte-identical (gate G2).

Reversibility is another *appended* record — a merge ``split`` reverses an ``accept``, a re-promote
reverses a demote — **never** an edit or delete of the prior record (append-only, gate G3).

One writeback per card (session §3); :func:`bind_writeback` returns the ``Callable[[HitlDecision],
DecisionRecord]`` that :func:`chanakya.hitl.service.enqueue` expects, selecting the right stage/type
from the item.
"""

from __future__ import annotations

from collections.abc import Callable

from chanakya.schemas import DecisionRecord, HitlDecision, ReviewQueueItem, Stage
from chanakya.schemas.decision import DecisionType
from chanakya.store import DecisionLog

# Card type → (decision-log stage, decision-log record type). The one place the mapping lives.
_STAGE_TYPE: dict[str, tuple[Stage, DecisionType]] = {
    "merge": ("resolution", "merge_adjudication"),
    "status-override": ("credibility", "status_override"),
    "alert-disposition": ("alerting", "alert_disposition"),
    "integrity-flag": ("integrity", "integrity_flag"),
}


def _derive_event_id(item: ReviewQueueItem, decision: HitlDecision) -> str:
    """Deterministic id from (item, chosen option) — no RNG, so the same disposition replays identically."""
    return f"dec:{item.item_id}:{decision.decision}"


def build_record(item: ReviewQueueItem, decision: HitlDecision, *, ts: str, event_id: str | None = None) -> DecisionRecord:
    """Map a review item + its chosen disposition to the §4.2 decision record (does *not* append).

    ``effects`` is looked up from the item's per-option preview (``item.effects[chosen]``): the exact
    state change the analyst was shown is the one written to the log — no re-derivation, no surprise.
    """
    if item.type not in _STAGE_TYPE:
        raise ValueError(f"unknown review type {item.type!r}; expected one of {list(_STAGE_TYPE)}")
    stage, dtype = _STAGE_TYPE[item.type]
    effects = item.effects.get(decision.decision, {})
    return DecisionRecord(
        event_id=event_id or _derive_event_id(item, decision),
        ts=ts,
        actor=decision.actor,  # analyst on the human path; system on an auto-disposition
        stage=stage,
        type=dtype,
        subject_ref=item.subject,
        context=item.context.model_dump() if item.context else {},
        options=list(item.options),
        decision={"chosen": decision.decision, "rationale": decision.rationale},
        effects=effects,
    )


def bind_writeback(
    item: ReviewQueueItem,
    log: DecisionLog,
    *,
    ts: str,
    event_id: str | None = None,
) -> Callable[[HitlDecision], DecisionRecord]:
    """Bind an item + log + timestamp into the one-arg writeback ``enqueue`` calls on disposition.

    The returned closure builds the record for the chosen option and **appends it** (the only
    mutation the store allows — gate G3), then returns it. This is the ``Callable[[HitlDecision],
    Any]`` in F0's frozen ``enqueue`` signature.
    """

    def _writeback(decision: HitlDecision) -> DecisionRecord:
        record = build_record(item, decision, ts=ts, event_id=event_id)
        log.append(record)  # append-only; propagation happens on the next rebuild(), not here
        return record

    return _writeback
