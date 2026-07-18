"""Extraction-seam tests — the forced-single-tool contract, offline + deterministic (INGEST gate G10).

The scripted client and the builder are exercised with zero network. The two live providers are covered
two ways: a ``respx``-mocked Anthropic round-trip that asserts the *request* shape (forced tool_choice,
no sampling params, the image block on ``read_image``) and parses a canned tool_use response, plus opt-in
``@pytest.mark.live`` smoke tests that hit the real API only when a key is present.
"""

from __future__ import annotations

import base64
import dataclasses
import json
import os

import httpx
import pytest
import respx

from chanakya.ingest.client import (
    MODEL,
    AnthropicExtractionClient,
    ExtractionCall,
    ExtractionClient,
    GeminiExtractionClient,
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
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert build_extraction_client() is None


def test_build_client_prefers_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic")
    client = build_extraction_client()
    assert isinstance(client, GeminiExtractionClient)
    assert client.model_id == "gemini-2.5-flash"


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


# ── AnthropicExtractionClient (respx-mocked round-trip, offline) ──────────────────────────────────

_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


def _tool_use_response(tool_name: str, tool_input: dict[str, object]) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "model": "claude-opus-4-8",
            "content": [
                {"type": "tool_use", "id": "toolu_test", "name": tool_name, "input": tool_input}
            ],
            "stop_reason": "tool_use",
            "stop_sequence": None,
            "usage": {"input_tokens": 12, "output_tokens": 7},
        },
    )


@respx.mock
def test_anthropic_extract_forces_tool_and_omits_sampling() -> None:
    route = respx.post(_ANTHROPIC_URL).mock(
        return_value=_tool_use_response("emit_prose_claim", {"claims": []})
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
    # No sampling params ever (400 on Opus 4.8; G7).
    for banned in ("temperature", "top_p", "top_k"):
        assert banned not in body


@respx.mock
def test_anthropic_read_image_attaches_base64_block() -> None:
    route = respx.post(_ANTHROPIC_URL).mock(
        return_value=_tool_use_response("emit_imagery_observation", {"features": []})
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
    respx.post(_ANTHROPIC_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "msg_x",
                "type": "message",
                "role": "assistant",
                "model": "claude-opus-4-8",
                "content": [{"type": "text", "text": "no tool"}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {"input_tokens": 3, "output_tokens": 2},
            },
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
