"""Disposition round-trip: HITL writes an ``alert_disposition`` record; MONITOR reads it back (spine/06).

Covers acceptance #5/#7 — MONITOR consumes the decision log for tripwire tuning without owning the
writeback. Proven through F0's real append-only ``DecisionLog`` (append → replay → read).
"""

from __future__ import annotations

from chanakya.observe import read_dispositions
from chanakya.observe.disposition import NEEDS_MORE, NOISE, REAL
from chanakya.schemas import DecisionRecord
from chanakya.store import DecisionLog


def _disposition(event_id: str, observable_id: str, verdict: str, instance: str = "") -> DecisionRecord:
    return DecisionRecord(
        event_id=event_id,
        ts="2026-07-18T00:00:00Z",
        actor="analyst",
        stage="alerting",
        type="alert_disposition",
        subject_ref=observable_id,
        context={"observable_id": observable_id, "instance": instance},
        decision={"disposition": verdict},
    )


def _fired(event_id: str, observable_id: str) -> DecisionRecord:
    return DecisionRecord(
        event_id=event_id, ts="2026-07-18T00:00:00Z", actor="system", stage="alerting",
        type="alert_fired", subject_ref=observable_id, context={"observable_id": observable_id},
    )


def test_roundtrip_through_the_decision_log() -> None:
    """The load-bearing proof: append a disposition to F0's log, MONITOR reads it back for tuning."""
    log = DecisionLog()
    log.append(_fired("ev-1", "obs-relocation"))
    log.append(_disposition("ev-2", "obs-relocation", REAL, instance="unit_acme"))

    stats = read_dispositions(log.replay())

    assert "obs-relocation" in stats
    s = stats["obs-relocation"]
    assert s.fired == 1
    assert s.counts[REAL] == 1


def test_needs_more_is_flagged_awaiting_coverage() -> None:
    """`needs-more` is first-class (the non-negotiable): tracked as awaiting coverage, not closed."""
    records = [
        _disposition("d1", "obs-x", NEEDS_MORE, instance="unit_a"),
        _disposition("d2", "obs-x", REAL, instance="unit_b"),
    ]
    stats = read_dispositions(records)
    assert stats["obs-x"].counts[NEEDS_MORE] == 1
    assert stats["obs-x"].open_needs_more == ["unit_a"]


def test_noise_rate_is_the_tuning_signal() -> None:
    """noise_rate over dispositioned alerts is the 'should I tighten this tripwire?' signal (analyst-driven)."""
    records = [
        _disposition("d1", "obs-y", NOISE),
        _disposition("d2", "obs-y", NOISE),
        _disposition("d3", "obs-y", REAL),
    ]
    stats = read_dispositions(records)
    assert stats["obs-y"].counts[NOISE] == 2
    assert stats["obs-y"].noise_rate == 2 / 3


def test_verdict_vocabulary_is_not_hardcoded() -> None:
    """Dispositions come from each observable's config vocabulary — a custom verdict still aggregates."""
    records = [_disposition("d1", "obs-z", "escalate")]
    stats = read_dispositions(records)
    assert stats["obs-z"].counts == {"escalate": 1}


def test_string_decision_form_is_accepted() -> None:
    """A record whose ``decision`` is a bare verdict string (not a dict) is read too."""
    rec = DecisionRecord(event_id="d1", ts="2026-07-18T00:00:00Z", actor="analyst", stage="alerting",
                         type="alert_disposition", subject_ref="obs-q", decision=REAL)
    stats = read_dispositions([rec])
    assert stats["obs-q"].counts[REAL] == 1


def test_non_alert_records_ignored() -> None:
    """A merge/override record in the same log is not miscounted as a disposition."""
    rec = DecisionRecord(event_id="m1", ts="2026-07-18T00:00:00Z", actor="analyst", stage="resolution",
                         type="merge_adjudication", subject_ref="merge-1", decision={"result": "accept"})
    assert read_dispositions([rec]) == {}
