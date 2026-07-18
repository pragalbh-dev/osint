"""Offline LLM doubles for the agent suite (master §6): a scripted planner and a yes/no entailment judge.

Not a test module — imported by the agent tests to drive the loop deterministically without the network.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from chanakya.agent.client import LLMResponse, ScriptedClient, ToolCall


def tool_turn(name: str, params: dict[str, Any], call_id: str = "t1") -> LLMResponse:
    """A scripted assistant turn that calls one tool."""
    return LLMResponse(tool_calls=[ToolCall(id=call_id, name=name, input=params)], stop_reason="tool_use")


def final(text: str = "done") -> LLMResponse:
    """A scripted terminal assistant turn."""
    return LLMResponse(text=text, stop_reason="end_turn")


def planner(*responses: LLMResponse) -> ScriptedClient:
    """A ScriptedClient replaying the given turns in order (the recorded/mocked planner)."""
    return ScriptedClient(list(responses))


class YesNoJudge:
    """An entailment judge that answers a scripted sequence of yes/no verdicts (True → 'yes')."""

    def __init__(self, verdicts: Iterable[bool]) -> None:
        self._verdicts = list(verdicts)
        self._i = 0

    def run_turn(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        verdict = self._verdicts[self._i] if self._i < len(self._verdicts) else True
        self._i += 1
        return LLMResponse(text="yes" if verdict else "no", stop_reason="end_turn")
