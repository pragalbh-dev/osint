"""Recall-biased triage — the deterministic escalate-vs-auto gate + queue ordering (session HITL §7).

Two separate concerns, both **deterministic** (no LLM, no clock, no RNG — gate G1):

1. **The escalate-vs-auto gate** (:func:`should_escalate`). Keyed on the three ranking dimensions
   carried in :class:`~chanakya.schemas.ReviewContext` — ``confidence`` band, ``materiality``,
   ``novelty``. We tune the *precision* of auto-proceed but **hold the recall of escalation ≈ 1.0**:
   an item auto-proceeds only on *positive* evidence of safety on every dimension; any unknown (a
   ``None``) escalates. When in doubt, escalate — never silently drop (spine/05).

2. **Queue ordering** (:func:`order_queue`). The ★ marquee items are **deterministically pinned to
   the top regardless of any rank**, so finite analyst attention can't bury a real low-ranked item.
   A *config-versioned NL triage rubric* LLM may rank the rest — but it is **raise-only, offline,
   applied to a frozen rubric version and replayed**: it enters here as a pre-baked ``frozen_rank``
   (data, not a live call), it can **never remove an item** (missing ids keep their place) and it can
   **never touch the pinned set or the escalate boundary**. Those guarantees are structural in the
   code below, not a promise.

``TriageConfig`` is **HITL-owned and overridable** (defaults here, or passed in per call) rather than
baked into the shared config store — so re-tuning the gate needs no F0-amendment. The numbers are
recall-biased *knobs*, not scoring literals; hitl/ is outside gate G6's scope.
"""

from __future__ import annotations

from pydantic import BaseModel

from chanakya.schemas import ReviewContext, ReviewQueueItem, ReviewType

# The three control points wired deep — always pinned to the top of the analyst queue.
STAR_TYPES: tuple[ReviewType, ...] = ("merge", "status-override", "alert-disposition")


class TriageConfig(BaseModel):
    """Recall-biased triage knobs (HITL-owned, overridable). Auto-proceed needs safety on *all* axes."""

    auto_proceed_min_confidence: float = 0.85  # auto only if confidence ≥ this (else escalate)
    material_threshold: float = 0.5  # materiality ≥ this ⇒ escalate (high stakes → a human looks)
    novelty_threshold: float = 0.5  # novelty ≥ this ⇒ escalate (unseen entity/alias → a human looks)
    gate_on_materiality: bool = True
    gate_on_novelty: bool = True
    # Deterministic tie-break priority among pinned ★ items (lower = higher in the queue).
    star_priority: dict[str, int] = {"status-override": 0, "merge": 1, "alert-disposition": 2}


def should_escalate(context: ReviewContext, cfg: TriageConfig | None = None) -> bool:
    """Deterministic recall-biased gate: escalate unless the item is *provably* safe on every axis.

    Safe requires a known, low-risk value on each gated dimension. A missing value (``None``) is
    treated as unsafe → escalate, so the recall of escalation stays ≈ 1.0 (never silently drop).
    """
    cfg = cfg or TriageConfig()

    safe_confidence = context.confidence is not None and context.confidence >= cfg.auto_proceed_min_confidence
    safe_materiality = (not cfg.gate_on_materiality) or (
        context.materiality is not None and context.materiality < cfg.material_threshold
    )
    safe_novelty = (not cfg.gate_on_novelty) or (
        context.novelty is not None and context.novelty < cfg.novelty_threshold
    )

    auto_proceed = safe_confidence and safe_materiality and safe_novelty
    return not auto_proceed


def order_queue(
    items: list[ReviewQueueItem],
    cfg: TriageConfig | None = None,
    frozen_rank: dict[str, int] | list[str] | None = None,
) -> list[ReviewQueueItem]:
    """Analyst-presentation order: ★ pinned first (deterministic), then the frozen LLM rank.

    Guarantees enforced *structurally* (the LLM can only ever have proposed ``frozen_rank``):

    * **Pinned ★ items always lead** — ordered by ``cfg.star_priority`` then ``item_id``, ignoring
      ``frozen_rank`` entirely. A hostile rank cannot bury them.
    * **No item can be removed** — items absent from ``frozen_rank`` are retained (sorted stably after
      the ranked ones), so the rubric can *raise* but never drop.
    * **No item can be injected** — ranks referencing unknown ids are ignored (we iterate ``items``).
    """
    cfg = cfg or TriageConfig()
    pinned = [it for it in items if it.pinned]
    rest = [it for it in items if not it.pinned]

    pinned.sort(key=lambda it: (cfg.star_priority.get(it.type, 99), it.item_id))

    if frozen_rank is None:
        rest_sorted = rest  # preserve insertion order
    else:
        if isinstance(frozen_rank, list):
            rank_map = {item_id: i for i, item_id in enumerate(frozen_rank)}
        else:
            rank_map = dict(frozen_rank)
        # Ranked items first (by rank), unranked retained after (stable by insertion) — never dropped.
        _UNRANKED = len(rest)  # sorts after any real rank; keeps unranked items in the queue
        rest_sorted = sorted(
            rest,
            key=lambda it: (rank_map.get(it.item_id, _UNRANKED), it.item_id),
        )

    return pinned + rest_sorted
