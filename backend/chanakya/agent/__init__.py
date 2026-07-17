"""AGENT stage — the bounded ReAct multi-hop QnA loop + citation validator (owned by session ASK).

F0 ships a **trivial stub** that returns a first-class *refusal* (never a fabricated answer — the
disqualifying line, principle 4). ASK fills the ~7 ``graph_*`` tools, the bounded loop, and the
entailment citation validator (spine/09, master §4.5). Runtime LLM lives here, **outside** the rebuild
call-path (gate G1).

Frozen signature: ``ask(question, view, config) -> AskAnswer``.
"""

from __future__ import annotations

from chanakya.schemas import AskAnswer, ConfigBundle, GraphView, RefusalPayload


def ask(question: str, view: GraphView, config: ConfigBundle) -> AskAnswer:
    """STUB: refuse cleanly (the agent is not built yet). ASK implements the real cited loop."""
    return AskAnswer(
        question=question,
        answer=None,
        refusal=RefusalPayload(reason="agent not implemented in F0 (skeleton stub)"),
    )
