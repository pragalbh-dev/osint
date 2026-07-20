"""Entailment citation validator (spine/09; master §4.5) — "correctness ≠ faithfulness".

A mandatory post-hoc check with two parts:

* **deterministic** — every content sentence carries ≥1 citation; every cited claim ID exists; a hop
  sentence's citation actually supports that hop (is in the hop's claim set); and any count/metric in the
  answer matches the tool's returned evidence set (a fabricated count is rejected).
* **LLM-judge / NLI** — the cited claim(s) *entail* the sentence they back (a cheap yes/no judge over the
  claim's asserted content). A sentence that is uncited, cites a non-supporting/absent claim, or is
  cited-but-not-entailed is **rejected**.

The judge is an :class:`~chanakya.agent.client.LLMClient` (the same seam; mocked offline). With no judge
(keyless), only the deterministic part runs — documented, never silently skipped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from chanakya.schemas import AskAnswer, ClaimRecord, EntityDescriptor, EventDescriptor, Triple

from .client import LLMClient
from .context import ToolContext
from .loop import AgentTrace

_CITE_RE = re.compile(r"\[([^\]]+)\]")
# A COUNT is a standalone number before a counted noun ("3 components"). The lookbehind excludes the tail
# of a designator — "HT-233 matches the criteria" asserts no count of 233, and "Type 305B" none of 305 —
# which would otherwise be checked against the tool's count ceiling and rejected as fabricated. Narrows
# what counts as a count; it does not narrow the check applied to a real one.
_COUNT_RE = re.compile(r"(?<![\w-])(\d+)\s+(chokepoints?|components?|suppliers?|sources?|units?|matches?)\b")

JUDGE_SYSTEM = (
    "You are a strict entailment judge for cited intelligence claims. Given a source CLAIM and a "
    "SENTENCE, answer only 'yes' if the claim's asserted content directly supports (entails) the "
    "sentence, or 'no' otherwise. Default to 'no' if unsure. Answer with a single word."
)


@dataclass
class Finding:
    """One rejected sentence and why."""

    sentence: str
    problem: str  # uncited | citation_missing | not_supporting_hop | count_mismatch | not_entailed
    detail: str = ""


@dataclass
class ValidationResult:
    ok: bool
    findings: list[Finding] = field(default_factory=list)


def _cites(sentence: str) -> list[str]:
    out: list[str] = []
    for m in _CITE_RE.findall(sentence):
        out.extend(part.strip() for part in m.split(",") if part.strip())
    return out


def _claim_text(claim: ClaimRecord) -> str:
    """A plain-language rendering of the claim's asserted content, for the judge."""
    p = claim.payload
    if isinstance(p, Triple):
        body = f"{p.subject} {p.predicate} {p.object}"
    elif isinstance(p, EntityDescriptor):
        body = f"{p.entity_type} '{p.name}' with attributes {p.attrs}"
    elif isinstance(p, EventDescriptor):
        body = f"event {p.event_type} involving {p.participants}"
    else:  # pragma: no cover - discriminated union is exhaustive
        body = "unknown"
    return f"[{claim.kind}] source {claim.source_id}: {body}"


def _count_ceiling(trace: AgentTrace) -> set[int]:
    """Every count the tools actually returned — the only integers a count sentence may assert."""
    seen: set[int] = set()
    for c in trace.all_of("query_graph"):
        r = c.result
        for key in ("match_count", "indeterminate_count"):
            if isinstance(r.get(key), int):
                seen.add(r[key])
        agg = r.get("aggregate") or {}
        if isinstance(agg.get("result"), int):
            seen.add(agg["result"])
    for c in trace.all_of("neighbors"):
        if isinstance(c.result.get("total"), int):
            seen.add(c.result["total"])
    for c in trace.all_of("find_paths"):
        if isinstance(c.result.get("hop_count"), int):
            seen.add(c.result["hop_count"])
    return seen


def _judge_entails(judge: LLMClient, ctx: ToolContext, sentence: str, cites: list[str]) -> bool:
    claims = [ctx.claims[c] for c in cites if c in ctx.claims]
    if not claims:
        return False
    joined = " ; ".join(_claim_text(c) for c in claims)
    prompt = f"CLAIM: {joined}\nSENTENCE: {sentence}\nDoes the claim entail the sentence?"
    resp = judge.run_turn(system=JUDGE_SYSTEM, messages=[{"role": "user", "content": prompt}])
    return resp.text.strip().lower().startswith("y")


def validate_answer(
    answer: AskAnswer,
    trace: AgentTrace,
    ctx: ToolContext,
    judge: LLMClient | None = None,
) -> ValidationResult:
    """Validate a *positive* answer. Refusals carry a templated reason (not free prose) → nothing to entail."""
    if answer.answer is None:
        return ValidationResult(ok=True)

    findings: list[Finding] = []
    sentences = [s for s in answer.answer.split("\n") if s.strip()]
    count_ceiling = _count_ceiling(trace)

    for idx, sent in enumerate(sentences):
        cites = _cites(sent)
        if not cites:
            findings.append(Finding(sent, "uncited"))
            continue
        for cid in cites:
            if cid not in ctx.claims:
                findings.append(Finding(sent, "citation_missing", detail=cid))
        # a hop sentence's citation must be in that hop's own claim set (supports its hop).
        if idx < len(answer.hops):
            hop_claims = set(answer.hops[idx].claim_ids)
            if not (set(cites) & hop_claims):
                findings.append(Finding(sent, "not_supporting_hop", detail=f"hop {answer.hops[idx].step}"))
        # every count in the sentence must be one the tools actually returned.
        for num, _noun in _COUNT_RE.findall(sent):
            if int(num) not in count_ceiling:
                findings.append(Finding(sent, "count_mismatch", detail=num))
        # entailment (only when a judge is available).
        if judge is not None and not _judge_entails(judge, ctx, sent, cites):
            findings.append(Finding(sent, "not_entailed"))

    return ValidationResult(ok=not findings, findings=findings)
