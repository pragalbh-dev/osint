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
from .context import ToolContext
from .loop import run_react_loop
from .propose import ObservableProposal, propose_observable_from_text
from .validate import validate_answer

if TYPE_CHECKING:
    from chanakya.agent.client import LLMClient
    from chanakya.schemas import ClaimRecord

__all__ = ["ask", "ToolContext", "propose_observable_from_text", "ObservableProposal"]


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

    if resolved_llm is not None:
        # The LLM plans; the deterministic graph_* tools compute. No query is special-cased — a judgement
        # needing many hops (an origin/supply trace, a single-point-of-failure scan) is reached via the
        # general graph_analyze tool, not a hardcoded path.
        trace = run_react_loop(ctx, question, resolved_llm)
    else:
        # Keyless, no recorded trace: refuse honestly — never fabricate an answer.
        # This is a CAPABILITY outage, not an evidence gap: nothing was consulted, so we must not
        # report a shortfall in the world's evidence. `missing` names the capability in the words an
        # analyst can act on, not an internal token.
        return AskAnswer(
            question=question,
            answer=None,
            refusal=RefusalPayload(
                kind="capability",
                missing=["a model key (ANTHROPIC_API_KEY)", "or a recorded trace for this question"],
                reason=(
                    "The system could not run this query: the reasoning agent needs a model key and "
                    "none is configured, and there is no recorded trace to replay. No evidence was "
                    "consulted, so nothing is being asserted about the graph. Set ANTHROPIC_API_KEY "
                    "and ask again, or use the reproducible worked query, which runs without a key."
                ),
            ),
        )

    answer = assemble_answer(trace, ctx)
    # Entailment judge is an OPT-IN belt on top of the always-on deterministic citation checks
    # (config.credibility.entailment_judge_enabled, default OFF). It runs only when explicitly enabled AND
    # for a live client — a ScriptedClient (offline/recorded transcript) is a fixed replay, not an
    # interactive judge, so those paths always use deterministic validation only. Off ⇒ answers rest on the
    # deterministic grounding that already forbids naked/fabricated sentences.
    judge_on = getattr(config.credibility, "entailment_judge_enabled", False)
    judge = resolved_llm if (judge_on and not isinstance(resolved_llm, ScriptedClient)) else None
    verdict = validate_answer(answer, trace, ctx, judge=judge)
    if not verdict.ok:
        # A positive answer that fails citation/entailment validation is withheld — the non-negotiable
        # forbids emitting unbacked prose. Downgrade to a transparent refusal.
        return AskAnswer(
            question=question,
            sub_questions=answer.sub_questions,
            answer=None,
            refusal=RefusalPayload(
                kind="withheld",
                missing=[f"{f.problem}" for f in verdict.findings][:5],
                reason="Answer withheld: one or more sentences were uncited, unsupported, or not entailed by their evidence.",
            ),
        )
    return answer
