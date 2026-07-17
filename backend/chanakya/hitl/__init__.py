"""HITL stage — the one cross-cutting adjudication service (owned by session HITL).

One service, one signature, callable from any spine layer: ``enqueue(item, context, options,
writeback) → decision → mutate view + emit trace`` (spine/05, spine/08 §3.10). Writeback appends a
decision-log entry; the next ``rebuild()`` applies its ``effects`` (propagation is structural — gate
G12). All 8 control points exist in the service; HITL wires 3 deep (merge / status-override /
alert-disposition).

F0 ships a stub raising ``NotImplementedError`` — the service is HITL's to build; F0 only freezes the
review-queue/decision shapes (``schemas.api_models``) and the decision-log record it writes back.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from chanakya.schemas import HitlDecision, ReviewContext, ReviewQueueItem


def enqueue(
    item: ReviewQueueItem,
    context: ReviewContext,
    options: list[str],
    writeback: Callable[[HitlDecision], Any],
) -> HitlDecision | None:
    """STUB: the adjudication service. HITL implements enqueue → decide → writeback → propagate."""
    raise NotImplementedError("HITL session implements the adjudication service")
