"""The one cross-cutting adjudication service (session HITL §1; master §4.7; spine/05).

Every spine stage and the analyst call the *same* service to escalate an ambiguous / high-stakes
item; there is no per-stage adjudication code. The flow:

    enqueue(item, context, options, writeback)
        ├─ triage says AUTO-PROCEED → (optionally) system auto-disposes → writeback → return decision
        └─ triage says ESCALATE     → item parked on the queue → return None (pending a human)

    dispose(item, chosen, writeback)   # the analyst path the API's POST /hitl/* funnels through
        └─ build the HitlDecision → writeback → return decision

**No LLM, no network, no clock, no RNG on this disposing path** (gate G1): triage is deterministic,
writeback only *appends*, and the wall-clock ``ts`` is supplied by the caller. The disposition never
changes the view directly — the appended record's ``effects`` are applied by the next ``rebuild()``
(gate G12). System-proposes / analyst-disposes, mechanised once, here.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from chanakya.schemas import HitlDecision, ReviewContext, ReviewQueueItem

from .queue import ReviewQueue
from .triage import TriageConfig, should_escalate


def enqueue(
    item: ReviewQueueItem,
    context: ReviewContext,
    options: list[str],
    writeback: Callable[[HitlDecision], Any],
    *,
    cfg: TriageConfig | None = None,
    queue: ReviewQueue | None = None,
    auto_option: str | None = None,
) -> HitlDecision | None:
    """Escalate-or-auto an item through the one service. Returns the decision, or ``None`` if pending.

    ``context``/``options`` are F0's frozen positional args; they refresh the item so the record and
    the triage gate see the same snapshot the caller intended. On escalation the item is parked on
    ``queue`` (if given) and ``None`` is returned — the human disposes later via :func:`dispose`. On
    auto-proceed, if ``auto_option`` is set the *system* disposes it (an audited auto-decision);
    otherwise ``None`` is returned and the stage's own proposal simply stands.
    """
    if context is not None:
        item.context = context
    if options:
        item.options = options

    if should_escalate(item.context, cfg):
        if queue is not None:
            queue.add(item)
        return None  # pending: a human will call dispose()

    if auto_option is None:
        return None  # safe on all axes and nothing to override — the machine's proposal stands

    decision = HitlDecision(
        item_id=item.item_id,
        type=item.type,
        subject=item.subject,
        decision=auto_option,
        actor="system",
        rationale="auto-proceed (triage: safe on confidence/materiality/novelty)",
    )
    writeback(decision)
    return decision


def dispose(
    item: ReviewQueueItem,
    chosen: str,
    writeback: Callable[[HitlDecision], Any],
    *,
    actor: str = "analyst",
    rationale: str | None = None,
    queue: ReviewQueue | None = None,
) -> HitlDecision:
    """The analyst disposition (the API's ``POST /hitl/*`` funnels here). Appends via ``writeback``.

    ``chosen`` must be one of the item's offered ``options`` — an unknown option is a hard error, never
    silently accepted (system-proposes / analyst-disposes stays honest). The item is popped off the
    pending worklist; the durable record lives in the decision log, not the queue.
    """
    if chosen not in item.options:
        raise ValueError(f"option {chosen!r} not offered for item {item.item_id!r}; options={item.options}")
    decision = HitlDecision(
        item_id=item.item_id,
        type=item.type,
        subject=item.subject,
        decision=chosen,
        actor=actor,
        rationale=rationale,
    )
    writeback(decision)
    if queue is not None:
        queue.resolve(item.item_id)
    return decision
