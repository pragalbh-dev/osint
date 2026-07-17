"""G8 — insufficient-evidence is first-class. A planted gap yields a Known Gap node with
``missing_slots`` + ``next_coverage_due``, **off the confidence scale**, and the refusal prose is a
rendered template, not regenerated (master §1 non-negotiable, §5; the disqualifying line).

F0 checks: the Known Gap shape is off-scale (no status/confidence fields); the refusal is a
deterministic template render; and ``rebuild()`` actually *emits* a Known Gap when sufficiency fails
(behavioural — exercises F0's emission path without depending on SCORE's real templates).
"""

from __future__ import annotations

from chanakya.schemas import KnownGap, SufficiencyEval
from chanakya.view import rebuild
from tests.fixtures import loaders


def test_known_gap_is_off_the_confidence_scale() -> None:
    gap = KnownGap.model_validate(loaders.per_stage("known_gap")["known_gap"])
    assert gap.missing_slots and gap.next_coverage_due
    assert gap.observability_ceiling in ("confirmable", "probable-max", "never-observable")
    # A refusal is NOT a confidence value: the Known Gap carries no status/confidence fields.
    assert "status" not in KnownGap.model_fields
    assert "assertion_confidence" not in KnownGap.model_fields
    assert "confidence" not in KnownGap.model_fields


def test_refusal_prose_is_a_rendered_template() -> None:
    fx = loaders.per_stage("known_gap")
    rendered = fx["refusal_template"].format(**fx["refusal_slots"])
    assert rendered == fx["expected_refusal"]  # deterministic template, never regenerated prose


def test_rebuild_emits_known_gap_when_sufficiency_fails(monkeypatch) -> None:
    def failing_check(assertion, claims, config) -> SufficiencyEval:
        return SufficiencyEval(
            satisfied=False, missing_slots=["imagery_confirmation"],
            next_coverage_due="2026-10-01", ceiling="confirmable",
        )

    # rebuild binds `check` at import; patch it in the pipeline module's namespace.
    monkeypatch.setattr("chanakya.view.pipeline.check", failing_check)
    view = rebuild(loaders.golden_evidence_log(), [], loaders.golden_config_store().snapshot())

    assert view.known_gaps, "sufficiency failure must emit a first-class Known Gap"
    for gap in view.known_gaps:
        assert gap.missing_slots == ["imagery_confirmation"]
        assert gap.next_coverage_due == "2026-10-01"
        assert gap.observability_ceiling == "confirmable"
        assert gap.related_ref  # hangs off the assertion that failed
