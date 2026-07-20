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


class _RecordingJudge:
    """A judge that always says 'no' and records the SENTENCE line of every prompt it is shown, so a
    test can assert which sentence classes were (and were NOT) put to the NLI judge."""

    def __init__(self) -> None:
        self.sentences: list[str] = []

    def run_turn(self, *, system, messages, tools=None):
        from chanakya.agent.client import LLMResponse

        for line in messages[0]["content"].splitlines():
            if line.startswith("SENTENCE:"):
                self.sentences.append(line[len("SENTENCE:") :].strip())
        return LLMResponse(text="no", stop_reason="end_turn")


def test_derived_and_weighed_sentences_are_not_sent_to_the_nli_judge(view, claims, config) -> None:
    # A rebuild-derived metric ("Chokepoint: …") and a rejected link ("Weighed and not carried: …") can
    # never be *entailed* by a single claim; they keep deterministic validation but must skip the judge —
    # otherwise a faithful answer is withheld. A hard-'no' judge that STILL passes them proves the exemption.
    from chanakya.agent.assemble import DERIVED_METRIC_PREFIX, WEIGHED_NOT_CARRIED_PREFIX

    a, trace, ctx = _hero(view, claims, config)
    exempt = [
        s
        for s in a.answer.split("\n")
        if s.startswith(DERIVED_METRIC_PREFIX) or s.startswith(WEIGHED_NOT_CARRIED_PREFIX)
    ]
    assert exempt, "hero answer should carry at least one derived/weighed sentence to exercise the exemption"

    judge = _RecordingJudge()
    res = validate_answer(a, trace, ctx, judge=judge)
    # The judge was never asked about an exempt sentence …
    assert not any(s in judge.sentences for s in exempt)
    # … and no exempt sentence was rejected as not_entailed (its deterministic checks pass).
    assert not any(f.problem == "not_entailed" and f.sentence in exempt for f in res.findings)


def test_identity_line_carries_the_resolved_endpoints_to_the_judge(view, claims, config) -> None:
    # The judge sees raw claim text but a resolved sentence; the fix hands it the hop's resolved endpoints
    # so an alias ("FD-2000") is not read as a mismatch. Assert the IDENTITY bridge reaches the prompt.
    a, trace, ctx = _hero(view, claims, config)
    seen: list[str] = []

    class _Spy:
        def run_turn(self, *, system, messages, tools=None):
            from chanakya.agent.client import LLMResponse

            seen.append(messages[0]["content"])
            return LLMResponse(text="yes", stop_reason="end_turn")

    validate_answer(a, trace, ctx, judge=_Spy())
    hop_prompts = [p for p in seen if "IDENTITY" in p]
    assert hop_prompts, "hop-sentence prompts must carry an IDENTITY line naming the resolved endpoints"
    # the resolved endpoint NAMES (not ids) are what the judge is given
    assert any(ctx.display_name(a.hops[0].dst) in p for p in hop_prompts)
