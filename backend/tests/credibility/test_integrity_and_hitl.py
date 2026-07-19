"""The two HITL pickups SCORE lands (SCORE.md §"HITL pickups"): origin-wide integrity flag + reject-recompute."""

from __future__ import annotations

from pytest import approx

from chanakya.credibility.scoring import score_claims
from chanakya.schemas import DecisionRecord
from chanakya.view import rebuild
from tests.credibility.builders import bundle, claim, source

_EDGE = "e:u:manufactures:s"


def _flag_origin(origin: str, flag: str) -> DecisionRecord:
    return DecisionRecord(
        event_id="dec-flag", ts="2026-01-01T00:00:00Z", actor="analyst", stage="integrity",
        type="integrity_flag", subject_ref=origin,
        effects={"flag_origin": {"primary_origin_id": origin, "flag": flag}},
    )


def _exclude(claim_id: str) -> DecisionRecord:
    return DecisionRecord(
        event_id="dec-reject", ts="2026-01-01T00:00:00Z", actor="analyst", stage="credibility",
        type="status_override", subject_ref=_EDGE, effects={"exclude_claims": [claim_id]},
    )


def test_analyst_origin_flag_penalises_all_claims_including_future() -> None:
    # Pickup #2: flagging a primary_origin_id taints EVERY claim of that origin — even one ingested later.
    cfg = bundle()
    srcs = {
        "s1": source("s1", "text", origin="fakeO"),
        "s2": source("s2", "text2", origin="fakeO"),
        "s3": source("s3", "imint", origin="fakeO"),  # ingested after the flag
    }
    claims = [claim(c, s, predicate="manufactures") for c, s in [("c1", "s1"), ("c2", "s2"), ("c3", "s3")]]
    out = score_claims(claims, srcs, cfg, [_flag_origin("fakeO", "too_clean")])
    for cid in ("c1", "c2", "c3"):
        assert out[cid] == approx(0.6 * 0.4)  # too_clean (0.4) applied origin-wide, incl. the later c3


def test_reject_claim_recomputes_confirmed_to_probable() -> None:
    # Pickup #1: rejecting a look EXCLUDES it upstream so the machine re-derives (not a forced label flip).
    cfg = bundle(sources=[source("sa", "imint"), source("sb", "strong")])  # cross-discipline, R = 0.6 / 0.9
    claims = [claim("c1", "sa", predicate="manufactures"), claim("c2", "sb", predicate="manufactures")]

    confirmed = rebuild(claims, [], cfg)
    edge = next(e for e in confirmed.edges if e.id == _EDGE)
    assert edge.status == "confirmed"  # two independent, cross-discipline, fresh looks over threshold

    after = rebuild(claims, [_exclude("c2")], cfg)
    edge2 = next(e for e in after.edges if e.id == _EDGE)
    assert edge2.status == "probable"  # one look left → below the ≥2-independent-groups gate


def test_single_pass_decoy_caps_but_a_second_independent_look_resolves_it() -> None:
    # The INGEST attribution-inference (D) net effect: a lone pixel-read caps at probable; the same read
    # plus an independent clean look reaches confirmed (decoy resolved) — and it's gate-G7-safe.
    cfg = bundle(sources=[source("sa", "imint"), source("sb", "strong")])
    d = claim("cD", "sa", predicate="manufactures", attributes={"decoy_risk_flag": True})  # IMINT decoy look
    c = claim("cC", "sb", predicate="manufactures")  # independent, clean, cross-discipline

    solo = rebuild([d], [], cfg)
    assert next(e for e in solo.edges if e.id == _EDGE).status == "probable"  # single-pass → decoy-capped

    both = rebuild([d, c], [], cfg)
    edge = next(e for e in both.edges if e.id == _EDGE)
    assert edge.status == "confirmed"  # second independent look resolves the decoy
    assert "decoy-risk" not in (edge.confidence.integrity_flags if edge.confidence else [])  # G7-safe
