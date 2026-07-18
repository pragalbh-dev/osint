"""The adjudication service — enqueue (escalate/auto) + dispose (analyst path)."""

from __future__ import annotations

import pytest

from chanakya.hitl import ReviewQueue, bind_writeback, build_item, dispose, enqueue
from chanakya.schemas import ReviewContext
from chanakya.store import DecisionLog


def _status_item(item_id: str = "s1"):
    return build_item(
        item_id=item_id, type="status-override", subject="e:x:rel:y",
        options=["promote", "demote", "reject"],
        effects={"demote": {"set_status": {"e:x:rel:y": "probable"}}},
    )


def test_escalate_parks_on_queue_and_returns_pending() -> None:
    q = ReviewQueue()
    dl = DecisionLog()
    item = _status_item()
    wb = bind_writeback(item, dl, ts="t")
    # low-confidence context → escalate → None (pending), nothing appended yet
    result = enqueue(item, ReviewContext(confidence=0.3), item.options, wb, queue=q)
    assert result is None
    assert len(q) == 1
    assert dl.count() == 0  # no disposition written on escalation


def test_auto_proceed_with_auto_option_writes_a_system_decision() -> None:
    dl = DecisionLog()
    item = _status_item()
    wb = bind_writeback(item, dl, ts="t")
    safe = ReviewContext(confidence=0.99, materiality=0.0, novelty=0.0)
    result = enqueue(item, safe, item.options, wb, auto_option="demote")
    assert result is not None
    assert result.actor == "system" and result.decision == "demote"
    assert dl.count() == 1


def test_auto_proceed_without_auto_option_writes_nothing() -> None:
    dl = DecisionLog()
    item = _status_item()
    wb = bind_writeback(item, dl, ts="t")
    safe = ReviewContext(confidence=0.99, materiality=0.0, novelty=0.0)
    assert enqueue(item, safe, item.options, wb) is None
    assert dl.count() == 0  # the machine's proposal stands; no override recorded


def test_dispose_appends_and_resolves_the_queue_item() -> None:
    q = ReviewQueue()
    dl = DecisionLog()
    item = _status_item()
    q.add(item)
    wb = bind_writeback(item, dl, ts="t")
    decision = dispose(item, "demote", wb, rationale="one aggregator source", queue=q)
    assert decision.decision == "demote" and decision.actor == "analyst"
    assert dl.count() == 1
    assert len(q) == 0  # popped off the transient worklist; the record is durable in the log


def test_dispose_rejects_an_unoffered_option() -> None:
    dl = DecisionLog()
    item = _status_item()
    wb = bind_writeback(item, dl, ts="t")
    with pytest.raises(ValueError, match="not offered"):
        dispose(item, "obliterate", wb)
    assert dl.count() == 0  # nothing written on an invalid option
