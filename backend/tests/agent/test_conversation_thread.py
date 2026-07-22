"""Conversational threading (feat/ask-conversation-thread).

Within one browser session a user asks follow-ups that should carry the prior turns as context, so the
planner can resolve references ("who else supplies *that*?") to an entity named in an earlier answer. The
thread is held by the CLIENT and replayed on each request; the backend stays **stateless per request**.

What this suite proves — deterministically, without the live model API:
* empty/omitted history builds the message list EXACTLY as the single-question path did (regression guard);
* prior answered turns seed as ordered ``user``/``assistant`` pairs BEFORE the current question;
* a prior refused turn (``answer=None``) seeds the honest refusal MARKER, never an empty/None assistant turn;
* the thread flows through ``ask()`` → ``run_react_loop`` (end-to-end plumbing).

A ``RecordingClient`` captures the ``messages`` list the loop hands the client on its first turn, then
stops the loop immediately (an ``end_turn`` reply, no tool use) — so the captured list is exactly the
seeded thread, observed before any tool call mutates the history.
"""

from __future__ import annotations

from typing import Any

from chanakya.agent import ask
from chanakya.agent.client import LLMResponse
from chanakya.agent.context import ToolContext
from chanakya.agent.loop import REFUSED_TURN_MARKER, run_react_loop
from chanakya.schemas import PriorTurn


class RecordingClient:
    """An offline client that snapshots the ``messages`` it is handed each turn, then replays a script.

    Mirrors the ``ScriptedClient`` protocol (``run_turn`` ignores nothing it needs to answer) but records
    a shallow copy of ``messages`` per turn into ``seen_messages`` so a test can assert on the exact seed.
    """

    def __init__(self, script: list[LLMResponse]) -> None:
        self._script = list(script)
        self._i = 0
        self.seen_messages: list[list[dict[str, Any]]] = []

    def run_turn(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        self.seen_messages.append(list(messages))  # snapshot before any downstream mutation
        resp = self._script[self._i]
        self._i += 1
        return resp


def _stop_now() -> RecordingClient:
    """A recording client that terminates the loop on the first turn (no tool use), so the captured
    messages are exactly the seeded thread — nothing appended by tool results."""
    return RecordingClient([LLMResponse(text="done", stop_reason="end_turn")])


# ── (a) empty history → byte-identical to the single-question path ────────────────────────────────

def test_empty_history_builds_exactly_the_single_question_message_list(view, claims, config) -> None:
    ctx = ToolContext.build(view, claims, config)
    llm = _stop_now()
    run_react_loop(ctx, "Who supplies HT-233?", llm)  # history omitted ⇒ defaults to empty
    assert llm.seen_messages[0] == [{"role": "user", "content": "Who supplies HT-233?"}]


def test_explicit_empty_history_is_identical_to_omitting_it(view, claims, config) -> None:
    """Passing ``history=[]`` must be indistinguishable from omitting the argument (regression guard)."""
    ctx = ToolContext.build(view, claims, config)
    omitted, explicit = _stop_now(), _stop_now()
    run_react_loop(ctx, "q", omitted)
    run_react_loop(ctx, "q", explicit, history=[])
    assert omitted.seen_messages[0] == explicit.seen_messages[0] == [{"role": "user", "content": "q"}]


# ── (b) two answered prior turns → seeded in order before the current question ────────────────────

def test_two_prior_answered_turns_seed_before_the_current_question(view, claims, config) -> None:
    ctx = ToolContext.build(view, claims, config)
    history = [
        PriorTurn(question="Who makes the HQ-9/P?", answer="CASIC makes the HQ-9/P."),
        PriorTurn(question="What is its seeker?", answer="The HT-233 engagement radar."),
    ]
    llm = _stop_now()
    run_react_loop(ctx, "Who else supplies that radar?", llm, history=history)
    assert llm.seen_messages[0] == [
        {"role": "user", "content": "Who makes the HQ-9/P?"},
        {"role": "assistant", "content": "CASIC makes the HQ-9/P."},
        {"role": "user", "content": "What is its seeker?"},
        {"role": "assistant", "content": "The HT-233 engagement radar."},
        {"role": "user", "content": "Who else supplies that radar?"},
    ]


# ── (c) a refused prior turn → the marker text, never empty/None ──────────────────────────────────

def test_refused_prior_turn_seeds_the_refusal_marker(view, claims, config) -> None:
    ctx = ToolContext.build(view, claims, config)
    history = [PriorTurn(question="Who supplies the Rahwali SAM regiment?", answer=None)]
    llm = _stop_now()
    run_react_loop(ctx, "What about the Malir site?", llm, history=history)
    seeded = llm.seen_messages[0]
    assert seeded == [
        {"role": "user", "content": "Who supplies the Rahwali SAM regiment?"},
        {"role": "assistant", "content": REFUSED_TURN_MARKER},
        {"role": "user", "content": "What about the Malir site?"},
    ]
    # the assistant half of a refused turn is real, non-empty text — never "" or None.
    assistant_turn = seeded[1]["content"]
    assert isinstance(assistant_turn, str) and assistant_turn.strip()
    assert "insufficient evidence" in assistant_turn.lower()


def test_mixed_answered_and_refused_turns_seed_correctly(view, claims, config) -> None:
    ctx = ToolContext.build(view, claims, config)
    history = [
        PriorTurn(question="q1", answer="a1"),
        PriorTurn(question="q2", answer=None),  # refused
    ]
    llm = _stop_now()
    run_react_loop(ctx, "q3", llm, history=history)
    assert llm.seen_messages[0] == [
        {"role": "user", "content": "q1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "q2"},
        {"role": "assistant", "content": REFUSED_TURN_MARKER},
        {"role": "user", "content": "q3"},
    ]


# ── end-to-end: the thread flows through ask() → run_react_loop ───────────────────────────────────

def test_ask_threads_history_into_the_loop(view, claims, config) -> None:
    """The plumbing: ``ask(..., history=...)`` seeds the same prior turns into the loop's message list."""
    history = [PriorTurn(question="Who makes the HT-233?", answer="CASIC.")]
    llm = _stop_now()
    ask("Who else?", view, config, llm=llm, claims=claims, history=history)
    assert llm.seen_messages[0] == [
        {"role": "user", "content": "Who makes the HT-233?"},
        {"role": "assistant", "content": "CASIC."},
        {"role": "user", "content": "Who else?"},
    ]


def test_ask_without_history_is_the_single_question_seed(view, claims, config) -> None:
    llm = _stop_now()
    ask("What is HT-233?", view, config, llm=llm, claims=claims)  # no history arg
    assert llm.seen_messages[0] == [{"role": "user", "content": "What is HT-233?"}]
