"""The entailment citation validator (spine/09 "correctness ≠ faithfulness")."""

from __future__ import annotations

from chanakya.agent.assemble import assemble_answer
from chanakya.agent.context import ToolContext
from chanakya.agent.loop import run_fixed_hero_path
from chanakya.agent.validate import validate_answer

from .mock_llm import YesNoJudge


def _hero(view, claims, config):
    ctx = ToolContext.build(view, claims, config)
    trace = run_fixed_hero_path(ctx, "trace ... chokepoint")
    return assemble_answer(trace, ctx), trace, ctx


def test_passes_well_cited_answer_with_entailing_judge(view, claims, config) -> None:
    a, trace, ctx = _hero(view, claims, config)
    res = validate_answer(a, trace, ctx, judge=YesNoJudge([True] * 50))
    assert res.ok, [f.problem for f in res.findings]


def test_deterministic_part_passes_without_a_judge(view, claims, config) -> None:
    a, trace, ctx = _hero(view, claims, config)
    res = validate_answer(a, trace, ctx, judge=None)
    assert res.ok, [f.problem for f in res.findings]


def test_rejects_uncited_sentence(view, claims, config) -> None:
    a, trace, ctx = _hero(view, claims, config)
    tampered = a.model_copy(update={"answer": a.answer + "\nHT-233 is a confirmed sole-source."})
    res = validate_answer(tampered, trace, ctx, judge=None)
    assert not res.ok and any(f.problem == "uncited" for f in res.findings)


def test_rejects_cited_but_not_entailed_sentence(view, claims, config) -> None:
    a, trace, ctx = _hero(view, claims, config)
    res = validate_answer(a, trace, ctx, judge=YesNoJudge([False] * 50))  # judge: nothing entails
    assert not res.ok and any(f.problem == "not_entailed" for f in res.findings)


def test_rejects_count_that_does_not_match_evidence(view, claims, config) -> None:
    a, trace, ctx = _hero(view, claims, config)
    tampered = a.model_copy(update={"answer": a.answer + "\nThere are 99 chokepoints here. [d09-l7]"})
    res = validate_answer(tampered, trace, ctx, judge=None)
    assert not res.ok and any(f.problem == "count_mismatch" for f in res.findings)


def test_rejects_citation_that_does_not_exist(view, claims, config) -> None:
    a, trace, ctx = _hero(view, claims, config)
    tampered = a.model_copy(update={"answer": "Something is asserted here. [d99-fake]", "hops": []})
    res = validate_answer(tampered, trace, ctx, judge=None)
    assert not res.ok and any(f.problem == "citation_missing" for f in res.findings)
