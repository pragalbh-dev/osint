"""The reusable review-queue envelope + the in-process queue container (session HITL, master §4.7).

**One envelope, many payloads.** Every control point — merge, status-override, alert, integrity —
raises the *same* :class:`~chanakya.schemas.ReviewQueueItem` shape; only its ``type``/``payload``/
``options``/``effects`` differ. That sameness is the portability flex: wiring a new HITL point is a
new ``build_item`` call, not a new code path (spine/05; spine/08 §3.10).

The envelope's ``effects`` is a **per-option preview** — ``{option: effect_dict}`` — so the UI can
show *what each choice does to the graph* before the analyst picks, and :mod:`writeback` can look up
the chosen option's effect verbatim. The field↔:class:`~chanakya.schemas.DecisionRecord` map (session
§2): ``type→type`` · ``subject→subject_ref`` · ``context→context`` · ``options→options`` ·
``effects[chosen]→effects`` · ``actor→actor`` · ``ts→ts``; ``decision`` and ``stage`` are filled at
writeback.

The :class:`ReviewQueue` here is **transient in-process state** (the pending worklist), *not* the
audit trail — the durable record is the append-only decision log (:mod:`writeback`). Popping a
disposed item off the worklist is fine; it never touches the log.
"""

from __future__ import annotations

from typing import Any

from chanakya.schemas import ReviewContext, ReviewQueueItem, ReviewType

from .triage import TriageConfig, order_queue


def build_item(
    *,
    item_id: str,
    type: ReviewType,
    subject: str,
    options: list[str],
    effects: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    context: ReviewContext | None = None,
    pinned: bool = False,
    actor: str = "system",
    ts: str | None = None,
) -> ReviewQueueItem:
    """Construct one review-queue envelope. ``item_id``/``ts`` are *supplied*, never generated here.

    No clock or RNG: the id and timestamp come from the caller (like ``claim_id``/``event_id`` in the
    logs) so the whole HITL path stays deterministic and replayable (gate G2). ``effects`` is the
    per-option preview map; ``payload`` is the type-specific card body the UI renders.
    """
    return ReviewQueueItem(
        item_id=item_id,
        type=type,
        subject=subject,
        context=context or ReviewContext(),
        options=options,
        effects=effects or {},
        payload=payload or {},
        actor=actor,
        ts=ts,
        pinned=pinned,
    )


class ReviewQueue:
    """The pending worklist — escalated items awaiting an analyst. Transient, not the audit log.

    Ordering is delegated to :func:`chanakya.hitl.triage.order_queue` (★ pinned to the top, then an
    optional *frozen, replayed* LLM rank that can only reorder the rest). The queue never runs an LLM
    itself — it accepts a pre-baked rank as data, so the disposing path stays LLM-free (gate G1).
    """

    def __init__(self) -> None:
        self._items: dict[str, ReviewQueueItem] = {}  # insertion-ordered (py3.7+), keyed by item_id

    def add(self, item: ReviewQueueItem) -> None:
        """Register an escalated item. Re-adding the same ``item_id`` replaces it (idempotent enqueue)."""
        self._items[item.item_id] = item

    def get(self, item_id: str) -> ReviewQueueItem | None:
        return self._items.get(item_id)

    def resolve(self, item_id: str) -> ReviewQueueItem | None:
        """Pop a disposed item off the worklist (the *decision* is durable in the log, not here)."""
        return self._items.pop(item_id, None)

    def pending(self) -> list[ReviewQueueItem]:
        """All un-disposed items in insertion order (before triage ordering is applied)."""
        return list(self._items.values())

    def ordered(
        self,
        cfg: TriageConfig | None = None,
        frozen_rank: dict[str, int] | list[str] | None = None,
    ) -> list[ReviewQueueItem]:
        """Pending items in analyst-presentation order — ★ pinned first, then the frozen rank."""
        return order_queue(self.pending(), cfg=cfg, frozen_rank=frozen_rank)

    def __len__(self) -> int:
        return len(self._items)
