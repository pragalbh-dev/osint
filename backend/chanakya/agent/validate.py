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

from .assemble import DERIVED_METRIC_PREFIX, WEIGHED_NOT_CARRIED_PREFIX
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
    "sentence, or 'no' otherwise. Default to 'no' if unsure. "
    "When an IDENTITY line is present, it states entity equivalences the analysis graph already "
    "resolved (e.g. an export designator and its system are one entity): treat a name the CLAIM uses "
    "and its resolved equivalent in the SENTENCE as the SAME entity — an alias is not a mismatch. "
    "Answer with a single word."
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


def _judge_entails(
    judge: LLMClient,
    ctx: ToolContext,
    sentence: str,
    cites: list[str],
    resolved_entities: list[str] | None = None,
) -> bool:
    """Ask the judge whether the cited claims entail the sentence.

    The sentence is written at the RESOLVED-knowledge layer (canonical entity names), while a cited claim
    carries the RAW surface form a document used ("CASIC manufactures FD-2000" vs "…manufactures HQ-9/P").
    Without the resolver's identity bindings the judge is comparing two altitudes and correctly says "no"
    to a faithful sentence. So for a hop sentence we hand it the sentence's resolved entities (the hop's
    own endpoints — the exact merge the resolver made): the equivalence is auditable graph state, not a
    hint we invent. A genuinely unfaithful sentence still fails, because only the identity is bridged,
    never the assertion.
    """
    claims = [ctx.claims[c] for c in cites if c in ctx.claims]
    if not claims:
        return False
    joined = " ; ".join(_claim_text(c) for c in claims)
    identity = ""
    resolved = list(dict.fromkeys(e for e in (resolved_entities or []) if e))
    if resolved:
        # The claim carries RAW surface terms (an export designator, a document's own wording); the
        # sentence carries the RESOLVED entities the graph merged them into. Give the judge that
        # equivalence — the resolver's own recorded merge, not a hint we invent — so it judges the
        # RELATION, not the identity. Pairing is by meaning; the equivalence set is what is asserted.
        raw_terms = list(
            dict.fromkeys(
                t
                for c in claims
                if isinstance(c.payload, Triple)
                for t in (c.payload.subject, c.payload.object)
            )
        )
        raw_str = "; ".join(f'"{t}"' for t in raw_terms) if raw_terms else "the source's raw names"
        identity = (
            f"IDENTITY: the analysis graph resolved the source's raw names [{raw_str}] to these "
            f"entities: [{'; '.join(resolved)}]. A raw name and its resolved entity are the SAME "
            f"entity — judge only whether the asserted RELATION holds between them.\n"
        )
    prompt = f"CLAIM: {joined}\n{identity}SENTENCE: {sentence}\nDoes the claim entail the sentence?"
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
        resolved_entities: list[str] = []
        if idx < len(answer.hops):
            hop = answer.hops[idx]
            if not (set(cites) & set(hop.claim_ids)):
                findings.append(Finding(sent, "not_supporting_hop", detail=f"hop {hop.step}"))
            # the sentence's resolved endpoints — the identity bridge for the entailment judge.
            resolved_entities = [ctx.display_name(hop.src), ctx.display_name(hop.dst)]
        # every count in the sentence must be one the tools actually returned.
        for num, _noun in _COUNT_RE.findall(sent):
            if int(num) not in count_ceiling:
                findings.append(Finding(sent, "count_mismatch", detail=num))
        # Entailment (only when a judge is available) — but NOT for the two sentence classes that no
        # single claim can entail by construction (a rebuild-derived metric; a link reported as REJECTED).
        # Those keep the deterministic checks above; sending them to the NLI judge would reject a faithful
        # answer for asserting something citations were never meant to entail. (assemble.py owns the prefixes.)
        nli_exempt = sent.startswith(DERIVED_METRIC_PREFIX) or sent.startswith(WEIGHED_NOT_CARRIED_PREFIX)
        if judge is not None and not nli_exempt and not _judge_entails(judge, ctx, sent, cites, resolved_entities):
            findings.append(Finding(sent, "not_entailed"))

    return ValidationResult(ok=not findings, findings=findings)
