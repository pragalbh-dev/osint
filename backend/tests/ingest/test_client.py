"""Extraction-seam tests — the forced-single-tool contract, offline + deterministic (INGEST gate G10).

The scripted client and the builder are exercised with zero network. The two live providers are covered
two ways: a ``respx``-mocked Anthropic round-trip that asserts the *request* shape (forced tool_choice,
no sampling params, the image block on ``read_image``) and parses a canned tool_use response, plus opt-in
``@pytest.mark.live`` smoke tests that hit the real API only when a key is present.

That canned response is a **stream**, not a JSON body — see the note above ``_sse_response`` for why.
"""

from __future__ import annotations

import base64
import dataclasses
import json
import os
import sys
from collections.abc import Sequence

import httpx
import pytest
import respx

import chanakya.ingest.client as client_mod
from chanakya.ingest.client import (
    DEFAULT_OPENAI_MODEL,
    MAX_TOKENS,
    MODEL,
    AnthropicExtractionClient,
    ExtractionCall,
    ExtractionClient,
    GeminiExtractionClient,
    OpenAIExtractionClient,
    ScriptedExtractionClient,
    build_extraction_client,
)

_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {"summary": {"type": "string"}},
    "additionalProperties": False,
}


# ── ExtractionCall descriptor ──────────────────────────────────────────────────────────────────────

def test_extraction_call_is_frozen_with_defaults() -> None:
    call = ExtractionCall(tool_name="emit_prose_claim")
    assert call.tool_name == "emit_prose_claim"
    assert call.input_schema == {} and call.system == "" and call.text == ""
    with pytest.raises(dataclasses.FrozenInstanceError):
        call.tool_name = "other"  # type: ignore[misc]


def test_extraction_call_holds_fields() -> None:
    call = ExtractionCall(tool_name="t", input_schema=_SCHEMA, system="sys", text="doc")
    assert call.input_schema is _SCHEMA and call.system == "sys" and call.text == "doc"


# ── ScriptedExtractionClient (offline replay) ──────────────────────────────────────────────────────

def test_scripted_client_satisfies_protocol() -> None:
    client = ScriptedExtractionClient([{"a": 1}])
    assert isinstance(client, ExtractionClient)
    assert client.model_id == "scripted"


def test_scripted_client_replays_in_order_across_both_methods() -> None:
    client = ScriptedExtractionClient([{"n": 1}, {"n": 2}, {"n": 3}], model_id="rec-1")
    # text then image then text — one shared FIFO queue, inputs are ignored (pure replay).
    assert client.extract(tool_name="t", input_schema={}, system="", text="x") == {"n": 1}
    assert client.read_image(
        tool_name="t", input_schema={}, system="", image=b"\x89PNG", media_type="image/png"
    ) == {"n": 2}
    assert client.extract(tool_name="t", input_schema={}, system="", text="y") == {"n": 3}
    assert client.model_id == "rec-1"


def test_scripted_client_raises_when_exhausted() -> None:
    client = ScriptedExtractionClient([{"only": True}])
    client.extract(tool_name="t", input_schema={}, system="", text="x")
    with pytest.raises(RuntimeError, match="exhausted"):
        client.extract(tool_name="t", input_schema={}, system="", text="x")


# ── build_extraction_client (keyed → live client; keyless → None) ─────────────────────────────────

def test_build_client_keyless_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keyless means *no* provider key, so every one of the three has to be cleared here.

    Missing ``OPENAI_API_KEY`` from this list would leave the keyless-boot claim untested on a machine that
    happens to carry an OpenAI key — the claim being that a reviewer with no key falls through to the
    frozen bundles rather than to a live extractor."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert build_extraction_client() is None


def test_build_client_prefers_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic")
    client = build_extraction_client()
    assert isinstance(client, GeminiExtractionClient)
    # Assert against the CONSTANT, not a copy of its value: what this test is for is that the builder
    # honours the declared default, and a literal here re-asserts the pin in a second place that has to be
    # edited in lockstep. The pin's own justification (keyless == live) lives on the constant.
    assert client.model_id == client_mod.DEFAULT_GEMINI_MODEL


def test_build_client_falls_back_to_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic")
    client = build_extraction_client()
    assert isinstance(client, AnthropicExtractionClient)
    assert client.model_id == MODEL


def test_build_client_model_id_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic")
    client = build_extraction_client(model_id="claude-opus-4-8-custom")
    assert isinstance(client, AnthropicExtractionClient)
    assert client.model_id == "claude-opus-4-8-custom"


def test_build_client_falls_through_to_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    """Third in precedence, and third on purpose: appending rather than inserting leaves every existing
    keyed deployment resolving to exactly the client it resolved to before."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    client = build_extraction_client()
    assert isinstance(client, OpenAIExtractionClient)
    assert client.model_id == DEFAULT_OPENAI_MODEL


def test_the_openai_default_model_is_a_pinned_id_not_a_floating_alias() -> None:
    """A ``-latest`` style id would let the frozen seed silently stop equalling what live produces, which
    is the failure KEYLESS==LIVE exists to prevent. There is deliberately nothing here to fall back to."""
    assert not DEFAULT_OPENAI_MODEL.endswith(("-latest", ":latest", "@latest", "latest"))


# ── AnthropicExtractionClient (respx-mocked round-trip, offline) ──────────────────────────────────

_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


# ── why these mocks are streams, not one JSON body ────────────────────────────────────────────────
#
# ``AnthropicExtractionClient._call`` calls ``messages.stream(...)``, not ``messages.create(...)``: with
# ``MAX_TOKENS`` at 32000 the SDK *refuses* a non-streaming request outright (it estimates the call could
# outlive the HTTP timeout), so streaming is not a preference here, it is the only way the call is made.
# The wire response therefore has to be Server-Sent Events. Everything below builds the event sequence
# the SDK's accumulator expects:
#
#     message_start → content_block_start → content_block_delta* → content_block_stop
#                   → message_delta (stop_reason + usage) → message_stop
#
# The *request* is still fully inspectable through the respx route exactly as before — it now simply also
# carries ``"stream": true``.


def _sse_response(events: Sequence[tuple[str, dict[str, object]]]) -> httpx.Response:
    """Render ``(event-name, payload)`` pairs as a ``text/event-stream`` body.

    The SDK's decoder dispatches on the ``event:`` name and JSON-parses the ``data:`` line, so both are
    required; a plain JSON body is simply never parsed on this path.
    """
    body = "".join(f"event: {name}\ndata: {json.dumps(payload)}\n\n" for name, payload in events)
    return httpx.Response(200, content=body.encode(), headers={"content-type": "text/event-stream"})


def _message_stream(
    content_block: dict[str, object],
    deltas: Sequence[dict[str, object]],
    *,
    stop_reason: str,
    output_tokens: int = 7,
) -> httpx.Response:
    """A one-content-block assistant message, streamed the way the Messages API sends it."""
    events: list[tuple[str, dict[str, object]]] = [
        ("message_start", {"type": "message_start", "message": {
            "id": "msg_test", "type": "message", "role": "assistant", "model": MODEL,
            "content": [], "stop_reason": None, "stop_sequence": None,
            "usage": {"input_tokens": 12, "output_tokens": 0}}}),
        ("content_block_start",
         {"type": "content_block_start", "index": 0, "content_block": content_block}),
        *(("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": d})
          for d in deltas),
        ("content_block_stop", {"type": "content_block_stop", "index": 0}),
        # stop_reason arrives here, on message_delta — never on message_start.
        ("message_delta", {"type": "message_delta",
                           "delta": {"stop_reason": stop_reason, "stop_sequence": None},
                           "usage": {"output_tokens": output_tokens}}),
        ("message_stop", {"type": "message_stop"}),
    ]
    return _sse_response(events)


def _tool_use_stream(
    tool_name: str,
    tool_input: dict[str, object],
    *,
    raw_json: str | None = None,
    stop_reason: str = "tool_use",
    output_tokens: int = 7,
) -> httpx.Response:
    """A forced ``tool_use`` call carrying ``tool_input`` — the streaming twin of a canned tool_use body.

    The block opens with an empty ``input`` and the arguments arrive as ``input_json_delta`` fragments
    that are each invalid JSON on their own; the SDK re-parses the accumulated buffer after every delta
    and the client reads the reassembled result. Chopping the payload up rather than sending it whole is
    the point — it is the accumulator, not a pre-parsed dict, that the production code now consumes.

    ``raw_json`` overrides the serialised arguments with a literal string, so a caller can put genuinely
    unfinished JSON on the wire — a generation that stopped mid-token — instead of a serialisable dict.
    """
    raw = json.dumps(tool_input) if raw_json is None else raw_json
    fragments = [raw[i:i + 24] for i in range(0, len(raw), 24)]
    return _message_stream(
        {"type": "tool_use", "id": "toolu_test", "name": tool_name, "input": {}},
        [{"type": "input_json_delta", "partial_json": fragment} for fragment in fragments],
        stop_reason=stop_reason,
        output_tokens=output_tokens,
    )


@respx.mock
def test_anthropic_extract_forces_tool_and_omits_sampling() -> None:
    route = respx.post(_ANTHROPIC_URL).mock(
        return_value=_tool_use_stream("emit_prose_claim", {"claims": []})
    )
    client = AnthropicExtractionClient(api_key="sk-test")
    out = client.extract(
        tool_name="emit_prose_claim", input_schema=_SCHEMA, system="sys prompt", text="doc text"
    )
    assert out == {"claims": []}

    body = json.loads(route.calls.last.request.content)
    assert body["model"] == MODEL
    assert body["tool_choice"] == {"type": "tool", "name": "emit_prose_claim"}
    assert body["tools"][0]["name"] == "emit_prose_claim"
    assert body["system"] == "sys prompt"
    assert body["messages"][0]["content"] == "doc text"
    # The ceiling is read from the module so it cannot rot here, and the two travel together: a budget
    # this large is exactly why the request has to be streamed.
    assert body["max_tokens"] == MAX_TOKENS
    assert body["stream"] is True
    # No sampling params ever (400 on Opus 4.8; G7).
    for banned in ("temperature", "top_p", "top_k"):
        assert banned not in body


@respx.mock
def test_anthropic_read_image_attaches_base64_block() -> None:
    route = respx.post(_ANTHROPIC_URL).mock(
        return_value=_tool_use_stream("emit_imagery_observation", {"features": []})
    )
    client = AnthropicExtractionClient(api_key="sk-test")
    out = client.read_image(
        tool_name="emit_imagery_observation",
        input_schema=_SCHEMA,
        system="read the imagery",
        image=b"\x89PNG\r\n\x1a\n",
        media_type="image/png",
    )
    assert out == {"features": []}

    body = json.loads(route.calls.last.request.content)
    assert body["tool_choice"] == {"type": "tool", "name": "emit_imagery_observation"}
    block = body["messages"][0]["content"][0]
    assert block["type"] == "image"
    assert block["source"]["type"] == "base64"
    assert block["source"]["media_type"] == "image/png"
    # round-trips to the original bytes
    assert base64.standard_b64decode(block["source"]["data"]) == b"\x89PNG\r\n\x1a\n"


@respx.mock
def test_anthropic_raises_when_no_tool_use_block() -> None:
    # A prose answer to a forced-tool request: the stream carries a text block and no tool_use at all.
    respx.post(_ANTHROPIC_URL).mock(
        return_value=_message_stream(
            {"type": "text", "text": ""},
            [{"type": "text_delta", "text": "no tool"}],
            stop_reason="end_turn",
            output_tokens=2,
        )
    )
    client = AnthropicExtractionClient(api_key="sk-test")
    with pytest.raises(RuntimeError, match="no forced tool_use"):
        client.extract(tool_name="emit_prose_claim", input_schema=_SCHEMA, system="s", text="t")


# ── live smoke tests (opt-in; need a real key) ─────────────────────────────────────────────────────

@pytest.mark.live
@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="no ANTHROPIC_API_KEY")
def test_anthropic_live_forced_extraction() -> None:
    client = AnthropicExtractionClient()
    out = client.extract(
        tool_name="emit_summary",
        input_schema=_SCHEMA,
        system="Extract a one-line summary of the text into the tool.",
        text="An HQ-9/P battery was reported near Gujranwala in 2021.",
    )
    assert isinstance(out, dict)


@pytest.mark.live
@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="no GEMINI_API_KEY")
def test_gemini_live_forced_extraction() -> None:
    client = GeminiExtractionClient()
    out = client.extract(
        tool_name="emit_summary",
        input_schema=_SCHEMA,
        system="Extract a one-line summary of the text into the tool.",
        text="An HQ-9/P battery was reported near Gujranwala in 2021.",
    )
    assert isinstance(out, dict)


# ── extract with page images (the PDF multimodal path) ────────────────────────────────────────────

def test_scripted_client_extract_ignores_images() -> None:
    client = ScriptedExtractionClient([{"n": 1}, {"n": 2}])
    # images is a pure passthrough on the scripted client (replay is input-blind).
    assert client.extract(tool_name="t", input_schema={}, system="", text="x",
                          images=[(b"\x89PNG", "image/png")]) == {"n": 1}
    assert client.extract(tool_name="t", input_schema={}, system="", text="y") == {"n": 2}


@respx.mock
def test_anthropic_extract_attaches_page_images() -> None:
    route = respx.post(_ANTHROPIC_URL).mock(
        return_value=_tool_use_stream("extract_prose_claim", {"sources": []})
    )
    client = AnthropicExtractionClient(api_key="sk-test")
    out = client.extract(
        tool_name="extract_prose_claim", input_schema=_SCHEMA, system="sys",
        text="page text", images=[(b"\x89PNG\r\n\x1a\n", "image/png")],
    )
    assert out == {"sources": []}

    body = json.loads(route.calls.last.request.content)
    content = body["messages"][0]["content"]
    # a text block followed by the image block — prose + figure read together
    assert content[0] == {"type": "text", "text": "page text"}
    assert content[1]["type"] == "image" and content[1]["source"]["media_type"] == "image/png"
    assert base64.standard_b64decode(content[1]["source"]["data"]) == b"\x89PNG\r\n\x1a\n"
    # still no sampling params, still the forced tool
    assert body["tool_choice"] == {"type": "tool", "name": "extract_prose_claim"}
    for banned in ("temperature", "top_p", "top_k"):
        assert banned not in body


@respx.mock
def test_anthropic_extract_text_only_stays_bare_string() -> None:
    route = respx.post(_ANTHROPIC_URL).mock(
        return_value=_tool_use_stream("extract_prose_claim", {"sources": []})
    )
    client = AnthropicExtractionClient(api_key="sk-test")
    client.extract(tool_name="extract_prose_claim", input_schema=_SCHEMA, system="s", text="only text")
    body = json.loads(route.calls.last.request.content)
    # no images → the content is a plain string (unchanged wire shape, back-compatible)
    assert body["messages"][0]["content"] == "only text"



# ── the lazy-init race (found by RK-BAKEOFF, 2026-07-26) ──────────────────────────────────────────

def test_gemini_builds_exactly_one_sdk_client_under_concurrency(monkeypatch: pytest.MonkeyPatch) -> None:
    """`_sdk_client` must build one client even when many threads reach it cold, simultaneously.

    `lane.extract_many` fans extraction across threads, so an unguarded lazy init lets every thread build
    its own `genai.Client`. All but one are then unreachable, and google-genai's httpx wrapper closes its
    transport in `__del__` — so the orphans tear down sockets that sibling threads are still using. This
    killed two paid RK-BAKEOFF runs, in the two shapes the race produces:
    `httpx.ReadError: [SSL: DECRYPTION_FAILED_OR_BAD_RECORD_MAC]` and
    `RuntimeError: Cannot send a request, as the client has been closed`.

    The constructor sleeps so the window is wide and the assertion does not depend on scheduler luck:
    unguarded, all eight threads are inside it at once and eight clients are built.
    """
    import threading as _threading
    import time as _time
    import types as _types

    built: list[object] = []
    lock = _threading.Lock()

    def _fake_client(**_: object) -> object:
        _time.sleep(0.05)  # hold the window open
        sdk = object()
        with lock:
            built.append(sdk)
        return sdk

    google_mod = _types.ModuleType("google")
    genai_mod = _types.ModuleType("google.genai")
    genai_mod.Client = _fake_client  # type: ignore[attr-defined]
    google_mod.genai = genai_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "google", google_mod)
    monkeypatch.setitem(sys.modules, "google.genai", genai_mod)

    client = GeminiExtractionClient(api_key="k", model_id="gemini-3.6-flash")
    seen: list[object] = []

    def worker() -> None:
        seen.append(client._sdk_client())

    threads = [_threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    assert len(built) == 1, f"built {len(built)} SDK clients — the lazy init is racing"
    assert len(seen) == 8
    assert len({id(s) for s in seen}) == 1, "threads received different SDK client objects"
