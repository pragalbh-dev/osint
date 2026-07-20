"""SC-2 fix — the freshness-CLASS half-life default (D-P4.13) + its honest provenance flag.

Before this fix ``config/ontology.yaml`` declared ``freshness_class`` on every edge but no backend code
read it, and ``credibility.half_lives_days`` carried only VARIANT sub-keys for ``based-at`` (never a bare
``based-at``) while nothing tagged ``freshness_variant`` on a claim — so a perishable basing claim fell
through to no-decay and could **never** go STALE. These lock the mechanism:

* a perishable edge with no bare/variant key now decays via ``half_life_defaults[<class>]`` (non-None),
* a durable edge still returns None (no decay — eternal by design),
* the STALE flag/status now flows, and
* the fallback is stamped ``freshness-variant-assumed:<class>`` so provenance never silently pretends we
  knew the variant.
"""

from __future__ import annotations

from pytest import approx

from chanakya.credibility import assign_status, score_claims
from chanakya.credibility.scoring import assertion_freshness
from chanakya.schemas.config_models import OntologyConfig, TypeDef
from tests.credibility.builders import assertion, bundle, claim, cred_config, group, source

_OLD = "2021-09-01"       # a perishable basing observation, ~4.9y before the pinned evaluation date
_NOW = "2026-07-20"


def _ontology() -> OntologyConfig:
    # based-at declares perishable but the config below carries NO bare/variant based-at key → it MUST
    # reach the class default; manufactures is durable → never decays.
    return OntologyConfig(
        edge_types=[
            TypeDef(name="based-at", from_type="unit", to_type="basing_site",
                    extractor=True, freshness_class="perishable"),
            TypeDef(name="manufactures", from_type="manufacturer", to_type="variant",
                    extractor=True, freshness_class="durable"),
        ]
    )


def _cfg():
    # half_lives_days={} removes the builder's bare `based-at` short-circuit so the class default is the
    # ONLY reachable half-life for the perishable edge.
    return bundle(
        credibility=cred_config(
            as_of=_NOW,
            half_lives_days={},
            half_life_defaults={"perishable": 540, "durable": None},
        ),
        ontology=_ontology(),
    )


def test_perishable_edge_decays_via_class_default() -> None:
    # The bug: this scored 0.6 (freshness 1.0, eternal). Now it decays at the 540d perishable default.
    out = score_claims([claim("c1", "s", predicate="based-at", event=_OLD)], {"s": source("s", "text")}, _cfg())
    assert 0.0 < out["c1"] < 0.6  # reliability alone is 0.6; anything below it proves decay fired


def test_durable_edge_still_eternal() -> None:
    # A 16y-old durable fact must NOT decay — the class default is null for durable/n-a.
    out = score_claims([claim("c1", "s", predicate="manufactures", event="2010-01-01")],
                       {"s": source("s", "text")}, _cfg())
    assert out["c1"] == approx(0.6)  # freshness 1.0 despite age → still eternal by design


def test_assertion_freshness_stamps_stale_aging_and_the_honesty_flag() -> None:
    c = claim("c1", "s", predicate="based-at", event=_OLD)
    summary, flags = assertion_freshness(["c1"], {"c1": c}, _NOW, _cfg())
    assert "stale" in flags
    assert "aging" in flags
    assert "freshness-variant-assumed:perishable" in flags  # honest: variant untagged, class-rate decay
    assert summary.half_life_days == 540


def test_stale_status_flows_once_the_half_life_is_reachable() -> None:
    # An otherwise-strong assertion (two independent looks, conf ≈ 0.99) demotes to STALE because its
    # freshest look is past one half-life — the STALE gate was correct all along, it just needed a
    # non-None half-life to flow (which the class default now provides).
    c = claim("c1", "s", predicate="based-at", event=_OLD)
    _, flags = assertion_freshness(["c1"], {"c1": c}, _NOW, _cfg())
    a = assertion(
        "edge1",
        per_claim={"c1": 0.9, "c2": 0.9},
        groups=[group("g1", ["c1"]), group("g2", ["c2"])],
        gate_flags=flags,
    )
    out = assign_status([a], _cfg())
    assert out["edge1"].status == "stale"
    assert "stale-demotion" in out["edge1"].gate_vector


def test_no_class_default_still_means_no_decay() -> None:
    # A perishable edge with neither a bare key nor a class default stays eternal (fail-safe: no fabricated
    # half-life) — and the unreachable-half-life lint is what turns that config gap into a loud finding.
    cfg = bundle(
        credibility=cred_config(as_of=_NOW, half_lives_days={}, half_life_defaults={}),
        ontology=_ontology(),
    )
    out = score_claims([claim("c1", "s", predicate="based-at", event=_OLD)], {"s": source("s", "text")}, cfg)
    assert out["c1"] == approx(0.6)  # no reachable half-life → durable fallback (the pre-fix behaviour)
