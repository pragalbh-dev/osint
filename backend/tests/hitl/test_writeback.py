"""Writeback — maps a disposition to the §4.2 DecisionRecord and appends it (append-only)."""

from __future__ import annotations

from chanakya.hitl import bind_writeback, build_item, build_record
from chanakya.schemas import HitlDecision
from chanakya.store import DecisionLog


def _item(type_: str, subject: str, effects: dict):
    return build_item(item_id="it-1", type=type_, subject=subject, options=list(effects), effects=effects)


def _decision(item, chosen: str, actor: str = "analyst"):
    return HitlDecision(item_id=item.item_id, type=item.type, subject=item.subject, decision=chosen, actor=actor)


def test_stage_and_type_are_set_from_the_card_type() -> None:
    cases = {
        "merge": ("resolution", "merge_adjudication"),
        "status-override": ("credibility", "status_override"),
        "alert-disposition": ("alerting", "alert_disposition"),
        "integrity-flag": ("integrity", "integrity_flag"),
    }
    for card_type, (stage, dtype) in cases.items():
        item = _item(card_type, "subj", {"x": {"noop": True}})
        rec = build_record(item, _decision(item, "x"), ts="t")
        assert rec.stage == stage and rec.type == dtype
        assert rec.subject_ref == "subj"


def test_effects_come_from_the_chosen_options_preview() -> None:
    item = _item("status-override", "e:x:rel:y", {
        "promote": {"set_status": {"e:x:rel:y": "confirmed"}},
        "demote": {"set_status": {"e:x:rel:y": "probable"}},
    })
    rec = build_record(item, _decision(item, "promote"), ts="t")
    assert rec.effects == {"set_status": {"e:x:rel:y": "confirmed"}}
    # the analyst saw this exact effect before choosing — no re-derivation.


def test_event_id_is_deterministic_no_rng() -> None:
    item = _item("merge", "merge:a:b", {"accept": {"grow_alias": {}}})
    r1 = build_record(item, _decision(item, "accept"), ts="t1")
    r2 = build_record(item, _decision(item, "accept"), ts="t2")  # different wall-clock
    assert r1.event_id == r2.event_id == "dec:it-1:accept"  # id derived from (item, option), not time


def test_writeback_appends_only_and_returns_the_record() -> None:
    dl = DecisionLog()
    item = _item("merge", "merge:a:b", {"accept": {"grow_alias": {"same_as": ["a", "b"]}}})
    wb = bind_writeback(item, dl, ts="t")
    rec = wb(_decision(item, "accept"))
    assert dl.count() == 1
    assert dl.replay()[0].event_id == rec.event_id
    # the store exposes no update/delete — the only mutation is append (gate G3)
    assert not hasattr(DecisionLog, "update") and not hasattr(DecisionLog, "delete")
