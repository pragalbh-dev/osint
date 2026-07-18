"""The query-time LLM seam (owned by ASK; runtime LLM lives here, outside the rebuild call-path — G1).

The bounded ReAct loop and the entailment judge depend on this **provider-agnostic** ``LLMClient``
protocol, never on ``anthropic`` directly. That indirection buys three things the brief requires:

* **offline, deterministic tests** — inject a :class:`ScriptedClient` (master §6);
* **keyless boot** — with no ``ANTHROPIC_API_KEY`` the default client replays the frozen hero transcript
  (spine/09 "recorded hero-trace = network-safety fallback");
* **an optional second provider** — Gemini (master §1) slots in as another impl.

Model rules honoured (md/07, spine/09; verified against the current Anthropic API): model
``claude-opus-4-8``; **no ``temperature``/``top_p``/``top_k``** (400 on Opus 4.8); reasoning effort ``low``
via ``output_config={"effort": "low"}``; tools are ``strict`` with ``additionalProperties:false``; a plain
manual tool-use loop (``stop_reason == "tool_use"`` → run tools → feed ``tool_result`` back).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

MODEL = "claude-opus-4-8"
EFFORT = "low"  # spine/09: reasoning effort low for the planner
MAX_TOKENS = 4096  # planning turns are short; well under the streaming threshold


@dataclass(frozen=True)
class ToolCall:
    """One tool the model asked to run this turn (normalized across providers)."""

    id: str
    name: str
    input: dict[str, Any]


@dataclass(frozen=True)
class LLMResponse:
    """A normalized model turn: assistant text, any tool-use requests, and the stop reason."""

    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"  # "tool_use" | "end_turn" | …


@runtime_checkable
class LLMClient(Protocol):
    """Provider-agnostic single-turn interface the loop + entailment judge are written against."""

    def run_turn(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Execute one model turn and return the normalized response."""
        ...


# ── scripted / recorded client (tests + keyless replay) ────────────────────────────────────────

class ScriptedClient:
    """Replays a fixed list of :class:`LLMResponse`s in order — the offline + recorded-trace client.

    Deterministic and network-free: the same script yields the same trace every run (the acceptance
    "tool layer is deterministic … LLM paths tested with recorded/mocked responses"). Ignores the live
    ``messages`` (it is a pure transcript replay); raises if the loop asks for more turns than scripted.
    """

    def __init__(self, script: list[LLMResponse]) -> None:
        self._script = list(script)
        self._i = 0

    def run_turn(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        if self._i >= len(self._script):
            raise RuntimeError("ScriptedClient exhausted: the loop requested more turns than recorded")
        resp = self._script[self._i]
        self._i += 1
        return resp


# ── Anthropic client (live) ──────────────────────────────────────────────────────────────────

class AnthropicClient:
    """The live query-time client — Anthropic ``claude-opus-4-8``, effort low, no sampling params.

    Constructed only when a key is present (see :func:`build_default_client`); ``anthropic`` is imported
    lazily so importing this module never requires the SDK to be configured.
    """

    def __init__(self, api_key: str | None = None, model: str = MODEL, effort: str = EFFORT) -> None:
        import anthropic

        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self._model = model
        self._effort = effort

    def run_turn(
        self,
        *,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        # NB: no temperature/top_p/top_k (400 on Opus 4.8); effort via output_config. The SDK's
        # TypedDict params don't unify with our plain dict messages/tools — the shapes are correct at
        # runtime (this is the live-client boundary, exercised only under @live), so ignore the overload.
        resp = self._client.messages.create(  # type: ignore[call-overload]
            model=self._model,
            max_tokens=MAX_TOKENS,
            output_config={"effort": self._effort},
            system=system,
            messages=messages,
            tools=tools or [],
        )
        text_parts: list[str] = []
        calls: list[ToolCall] = []
        for block in resp.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                calls.append(ToolCall(id=block.id, name=block.name, input=dict(block.input)))
        return LLMResponse(text="".join(text_parts), tool_calls=calls, stop_reason=resp.stop_reason or "end_turn")


# ── default client resolution ────────────────────────────────────────────────────────────────

def has_api_key() -> bool:
    """True when a live LLM key is configured (Anthropic, or the optional Gemini)."""
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("GEMINI_API_KEY"))


def build_default_client(recorded_trace: list[LLMResponse] | None = None) -> LLMClient | None:
    """Resolve the runtime client: live Anthropic if keyed, else the recorded trace, else ``None``.

    ``None`` means "no live LLM and no recorded transcript" — the caller falls back to the deterministic
    fixed hero path (no LLM) or a first-class refusal, never a fabricated answer.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicClient()
    if recorded_trace is not None:
        return ScriptedClient(recorded_trace)
    return None
