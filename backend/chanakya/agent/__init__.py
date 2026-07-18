"""AGENT stage — the bounded ReAct multi-hop QnA loop + entailment citation validator (session ASK).

Runtime LLM lives here, **outside** the rebuild call-path (gate G1). The one load-bearing principle
(spine/09): the LLM plans and orchestrates tool calls; the seven deterministic ``graph_*`` tools do every
set operation / count / filter / materiality lookup; the answer is assembled from the tool results and
every sentence is validated to be cited *and entailed*. Where evidence is absent/ambiguous the agent
returns a first-class refusal (Known Gap + missing slots + next coverage due) — **never a fabrication**
(the disqualifying line).

Frozen signature (F0-amendment 2026-07-18): ``ask(question, view, config, llm=None, claims=None) -> AskAnswer``.
Two *optional* query-time inputs the F0 stub lacked (both additive — the existing/planned caller
``ask(question, view, config)`` in the API session is unaffected):

* ``llm`` — the query-time :class:`~chanakya.agent.client.LLMClient` seam (planner + entailment judge).
  ``None`` → build the default client from settings (keyless → the deterministic fixed hero path / refusal).
* ``claims`` — a ``claim_id → ClaimRecord`` lookup. ``rebuild()`` emits a view that references claims by ID
  only; the record bodies (``kind``, ``doc_ref``, source, dates) stay in the evidence log, but
  ``get_evidence`` (source/date/span) and observed-vs-inferred (from ``kind``) need them. The API passes
  ``{c.claim_id: c for c in store.replay()}``; tests pass the fixture's claims.

See ``artifacts/plan/PROGRESS.md`` → Contract amendments and ``DECISIONS.md`` §6 (ASK).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from chanakya.schemas import AskAnswer, ConfigBundle, GraphView, RefusalPayload

from .assemble import assemble_answer
from .client import ScriptedClient, build_default_client
from .context import ToolContext, normalize
from .loop import run_fixed_hero_path, run_react_loop
from .validate import validate_answer

if TYPE_CHECKING:
    from chanakya.agent.client import LLMClient
    from chanakya.schemas import ClaimRecord

__all__ = ["ask", "ToolContext"]

# Keyword signature of the flagship trace — routes it to the deterministic fixed hero path (primary +
# reproducible), independent of whether a key is present. Kept narrow so only the flagship query triggers.
_HERO_KEYWORDS = ("trace", "chokepoint")
_HERO_ALT = ("weak link",)


def _is_hero_query(question: str, config: ConfigBundle) -> bool:
    q = normalize(question)
    for lens in config.subjects.subjects:
        for tq in lens.target_queries:
            if normalize(tq) == q:
                return True
    has_trace = "trace" in q and ("chokepoint" in q or "weak link" in q)
    return has_trace and ("hq-9" in q or "battery" in q or "supplier" in q)


def ask(
    question: str,
    view: GraphView,
    config: ConfigBundle,
    llm: LLMClient | None = None,
    claims: Mapping[str, ClaimRecord] | None = None,
) -> AskAnswer:
    """Answer a question over an already-rebuilt view with per-hop citations, or refuse honestly."""
    ctx = ToolContext.build(view, claims or {}, config)
    resolved_llm = llm if llm is not None else build_default_client()

    if _is_hero_query(question, config):
        trace = run_fixed_hero_path(ctx, question)
    elif resolved_llm is not None:
        trace = run_react_loop(ctx, question, resolved_llm)
    else:
        # Keyless, non-flagship, no recorded trace: refuse honestly — never fabricate an answer.
        return AskAnswer(
            question=question,
            answer=None,
            refusal=RefusalPayload(
                missing=["live_llm_or_recorded_trace"],
                reason=(
                    "Insufficient capability to plan this query offline: no LLM key and no recorded "
                    "trace. Set ANTHROPIC_API_KEY for a live answer, or use the reproducible hero query."
                ),
            ),
        )

    answer = assemble_answer(trace, ctx)
    # Entailment judge runs only for a live client; a ScriptedClient (offline/recorded transcript) is a
    # fixed replay, not an interactive judge, so those paths use the deterministic validation only.
    judge = None if isinstance(resolved_llm, ScriptedClient) else resolved_llm
    verdict = validate_answer(answer, trace, ctx, judge=judge)
    if not verdict.ok:
        # A positive answer that fails citation/entailment validation is withheld — the non-negotiable
        # forbids emitting unbacked prose. Downgrade to a transparent refusal.
        return AskAnswer(
            question=question,
            sub_questions=answer.sub_questions,
            answer=None,
            refusal=RefusalPayload(
                missing=[f"{f.problem}" for f in verdict.findings][:5],
                reason="Answer withheld: one or more sentences were uncited, unsupported, or not entailed by their evidence.",
            ),
        )
    return answer
