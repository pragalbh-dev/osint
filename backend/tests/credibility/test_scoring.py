"""Per-claim credibility arithmetic — R(source) × Π(integrity) × freshness (spine/04 §C)."""

from __future__ import annotations

from pytest import approx

from chanakya.credibility.scoring import reliability, score_claims
from tests.credibility.builders import bundle, claim, cred_config, source


def test_reliability_is_the_weighted_factor_sum() -> None:
    cfg = bundle()
    assert reliability(source("s", "text"), cfg) == approx(0.6)
    assert reliability(source("s", "strong"), cfg) == approx(0.9)


def test_unknown_source_fails_closed_to_zero() -> None:
    # A claim from an unrecognised source class scores 0.0 — never a fabricated prior.
    cfg = bundle()
    assert score_claims([claim("c1", "ghost")], {}, cfg)["c1"] == 0.0


def test_durable_claim_credibility_is_just_reliability() -> None:
    cfg = bundle(cred_config(as_of="2025-01-01"))
    out = score_claims([claim("c1", "s", predicate="manufactures")], {"s": source("s", "text")}, cfg)
    assert out["c1"] == approx(0.6)  # durable edge → freshness 1.0; no integrity flags → Π = 1.0


def test_freshness_halves_at_one_half_life() -> None:
    cfg = bundle(cred_config(as_of="2025-01-01"))  # based-at half-life = 365d
    c = claim("c1", "s", predicate="based-at", event="2024-01-02")  # 365 days before as_of
    out = score_claims([c], {"s": source("s", "text")}, cfg)
    assert out["c1"] == approx(0.6 * 0.5)  # 2^(-365/365) = 0.5


def test_coordinated_inauthenticity_penalty_from_source_flag() -> None:
    cfg = bundle()
    out = score_claims(
        [claim("c1", "s", predicate="manufactures")], {"s": source("s", "text", coordinated=True)}, cfg
    )
    assert out["c1"] == approx(0.6 * 0.5)  # suspected → 0.5


def test_recycled_image_is_penalised_second_occurrence_only() -> None:
    cfg = bundle()
    srcs = {"a": source("a", "text"), "b": source("b", "text")}
    c1 = claim("c1", "a", predicate="manufactures", attributes={"sha256": "IMG"})
    c2 = claim("c2", "b", predicate="manufactures", attributes={"sha256": "IMG"})  # same picture
    out = score_claims([c1, c2], srcs, cfg)
    assert out["c1"] == approx(0.6)          # first occurrence = original
    assert out["c2"] == approx(0.6 * 0.3)    # re-seen fingerprint = recycled → 0.3


def test_future_dated_claim_clamps_to_fresh() -> None:
    cfg = bundle(cred_config(as_of="2025-01-01"))
    c = claim("c1", "s", predicate="based-at", event="2026-01-01")  # event after as_of
    out = score_claims([c], {"s": source("s", "text")}, cfg)
    assert out["c1"] == approx(0.6)  # never "fresher than now" — clamped to 1.0
