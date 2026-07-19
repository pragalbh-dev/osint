"""Evidence-requirement templates → satisfied / Known Gap fields (spine/04 §3.7; gate G8)."""

from __future__ import annotations

from chanakya.schemas.config_models import EvidenceTemplate, TemplatesConfig
from chanakya.sufficiency.checker import check
from tests.credibility.builders import assertion, bundle, claim, cred_config, group, source

BASED_AT = EvidenceTemplate(
    assertion_type="based-at",
    require={"any_of": [
        {"imagery_confirmation": {"within_days": 365}},
        {"independent_text_groups": {"min": 2, "within_days": 365}},
    ]},
    refusal_template="Cannot confirm basing of {subject}: missing {missing_slots}. Next coverage due {next_coverage_due}.",
)
NEVER = EvidenceTemplate(
    assertion_type="interceptor-depth",
    require={"never_observable": True},
    observability_ceiling="never-observable",
)


def test_planted_missing_kind_yields_known_gap_fields() -> None:
    cfg = bundle(
        cred_config(as_of="2025-01-01"),
        sources=[source("txt", "trade-media"), source("sat", "satellite", cadence="7d")],
        templates=TemplatesConfig(templates=[BASED_AT]),
    )
    a = assertion("e1", groups=[group("g1", ["c1"])])
    ev = check(a, {"c1": claim("c1", "txt", predicate="based-at")}, cfg)
    assert not ev.satisfied
    assert set(ev.missing_slots) == {"imagery_confirmation", "independent_text_groups"}
    assert ev.next_coverage_due == "2025-01-08"  # as_of + satellite cadence (7d) — generated, not authored
    assert ev.template_id == "based-at"


def test_imagery_within_window_satisfies() -> None:
    cfg = bundle(
        cred_config(as_of="2025-01-01"),
        sources=[source("sat", "satellite", cadence="7d")],
        templates=TemplatesConfig(templates=[BASED_AT]),
    )
    img = claim("c1", "sat", predicate="based-at", event="2024-06-01")  # IMINT, within 365d
    ev = check(assertion("e1", groups=[group("g1", ["c1"])]), {"c1": img}, cfg)
    assert ev.satisfied and ev.missing_slots == []


def test_never_observable_is_unsatisfied_with_ceiling_and_no_schedule() -> None:
    cfg = bundle(templates=TemplatesConfig(templates=[NEVER]))
    c = claim("c1", "s", predicate="interceptor-depth")
    ev = check(assertion("e1", groups=[group("g1", ["c1"])]), {"c1": c}, cfg)
    assert not ev.satisfied
    assert ev.ceiling == "never-observable"
    assert ev.next_coverage_due is None  # a structural limit, nothing to schedule


def test_no_template_is_assessable() -> None:
    cfg = bundle()  # no templates
    ev = check(assertion("e1", groups=[group("g1", ["c1"])]),
               {"c1": claim("c1", "s", predicate="manufactures")}, cfg)
    assert ev.satisfied and ev.missing_slots == []
