"""G12 — HITL propagation. A status-override decision appended to the log changes the view on rebuild
(master §1 #2, §5). This is what makes "human in control" structural rather than a log side-note.

A ``status_override`` with ``effects.set_status`` flips an element's status on the next rebuild; a
second appended override can flip it again (reversible, replayable) — the decision log *is* the input.
"""

from __future__ import annotations

from chanakya.schemas import DecisionRecord
from chanakya.store import DecisionLog
from chanakya.view import rebuild
from tests.fixtures import loaders

_TARGET = "e:mfr_foundry:supplies-component:comp_gizmo"


def _status_of(view, edge_id: str):
    return next(e.status for e in view.edges if e.id == edge_id)


def _override(event_id: str, status: str) -> DecisionRecord:
    return DecisionRecord(
        event_id=event_id, ts="2026-07-17T00:00:00Z", actor="analyst", stage="credibility",
        type="status_override", subject_ref=_TARGET,
        decision={"chosen": status}, effects={"set_status": {_TARGET: status}},
    )


def test_appended_override_changes_the_view() -> None:
    cfg = loaders.golden_config_store().snapshot()

    before = rebuild(loaders.golden_evidence_log(), [], cfg)
    assert _status_of(before, _TARGET) is None  # nothing overrides it yet

    dl = DecisionLog()
    dl.append(_override("ovr-1", "probable"))
    after = rebuild(loaders.golden_evidence_log(), dl, cfg)
    assert _status_of(after, _TARGET) == "probable"  # the override propagated on rebuild


def test_a_later_override_supersedes_the_earlier() -> None:
    cfg = loaders.golden_config_store().snapshot()
    dl = DecisionLog()
    dl.append(_override("ovr-1", "probable"))
    dl.append(_override("ovr-2", "confirmed"))  # analyst changes their mind; replay applies both in order
    after = rebuild(loaders.golden_evidence_log(), dl, cfg)
    assert _status_of(after, _TARGET) == "confirmed"
