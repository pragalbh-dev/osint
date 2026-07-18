"""Triage — the deterministic recall-biased gate + queue ordering (session HITL §7)."""

from __future__ import annotations

from chanakya.hitl import build_item, order_queue, should_escalate
from chanakya.hitl.triage import TriageConfig
from chanakya.schemas import ReviewContext

# ── the escalate-vs-auto gate: recall of escalation ≈ 1.0 ────────────────────────────────────────

def test_fully_safe_item_auto_proceeds() -> None:
    ctx = ReviewContext(confidence=0.95, materiality=0.1, novelty=0.1)
    assert should_escalate(ctx) is False


def test_low_confidence_escalates() -> None:
    assert should_escalate(ReviewContext(confidence=0.4, materiality=0.1, novelty=0.1)) is True


def test_high_materiality_escalates_even_when_confident() -> None:
    assert should_escalate(ReviewContext(confidence=0.99, materiality=0.9, novelty=0.0)) is True


def test_high_novelty_escalates_even_when_confident() -> None:
    assert should_escalate(ReviewContext(confidence=0.99, materiality=0.0, novelty=0.9)) is True


def test_unknown_dimension_escalates_never_silently_drops() -> None:
    # Any missing signal is treated as unsafe → escalate (recall-biased).
    assert should_escalate(ReviewContext(confidence=None, materiality=0.0, novelty=0.0)) is True
    assert should_escalate(ReviewContext(confidence=0.99, materiality=None, novelty=0.0)) is True
    assert should_escalate(ReviewContext(confidence=0.99, materiality=0.0, novelty=None)) is True
    assert should_escalate(ReviewContext()) is True  # nothing known → escalate


def test_thresholds_are_configurable() -> None:
    ctx = ReviewContext(confidence=0.7, materiality=0.1, novelty=0.1)
    assert should_escalate(ctx) is True  # default auto-min 0.85
    assert should_escalate(ctx, TriageConfig(auto_proceed_min_confidence=0.6)) is False


# ── queue ordering: ★ pinned; LLM rank is raise-only ────────────────────────────────────────────

def _item(item_id: str, type: str = "merge", pinned: bool = False):
    return build_item(item_id=item_id, type=type, subject=item_id, options=["accept"], pinned=pinned)


def test_pinned_star_items_lead_regardless_of_rank() -> None:
    star = _item("star", type="status-override", pinned=True)
    a, b = _item("a"), _item("b")
    hostile = ["a", "b", "star"]  # rank tries to bury the ★ item last
    ordered = order_queue([a, b, star], frozen_rank=hostile)
    assert ordered[0].item_id == "star"


def test_frozen_rank_cannot_remove_an_item() -> None:
    items = [_item("a"), _item("b"), _item("c")]
    ordered = order_queue(items, frozen_rank=["b"])  # rank names only b
    assert {i.item_id for i in ordered} == {"a", "b", "c"}  # a and c retained, not dropped
    assert ordered[0].item_id == "b"  # b raised to the front of the non-pinned set


def test_frozen_rank_cannot_inject_an_unknown_item() -> None:
    items = [_item("a"), _item("b")]
    ordered = order_queue(items, frozen_rank=["ghost", "a", "b"])  # 'ghost' is not in the queue
    assert {i.item_id for i in ordered} == {"a", "b"}


def test_multiple_pinned_ordered_by_priority_then_id() -> None:
    m = _item("m", type="merge", pinned=True)
    s = _item("s", type="status-override", pinned=True)
    al = _item("al", type="alert-disposition", pinned=True)
    ordered = order_queue([m, al, s])  # priority: status-override < merge < alert-disposition
    assert [i.item_id for i in ordered] == ["s", "m", "al"]
