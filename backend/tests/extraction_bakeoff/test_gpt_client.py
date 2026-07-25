"""The OpenAI extraction client — offline, against a fake SDK. No network, no key, no spend.

What is asserted is the *contract*, not the vendor: one forced tool call, **no sampling parameters ever**,
a pinned model id with no default to fall back to, and the full surface the shipped clients carry —
including both multimodal lanes, because dropping the VLM path is a disqualifier and a client that cannot
exercise it makes its candidate unmeasurable.
"""

from __future__ import annotations

import base64
import json
from types import SimpleNamespace
from typing import Any

import pytest

from eval.extraction.gpt_client import MAX_COMPLETION_TOKENS, OpenAIExtractionClient

SCHEMA = {"type": "object", "properties": {"orgs": {"type": "array"}}}


class _FakeCompletions:
    def __init__(self, sink: list[dict[str, Any]], response: Any) -> None:
        self._sink = sink
        self._response = response

    def create(self, **kwargs: Any) -> Any:
        self._sink.append(kwargs)
        return self._response


class _FakeClient:
    def __init__(self, sink: list[dict[str, Any]], response: Any) -> None:
        self.chat = SimpleNamespace(completions=_FakeCompletions(sink, response))


def _tool_response(name: str, arguments: str, *, usage: Any = None) -> Any:
    call = SimpleNamespace(function=SimpleNamespace(name=name, arguments=arguments))
    message = SimpleNamespace(tool_calls=[call])
    return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)


class _EchoCompletions(_FakeCompletions):
    """Answers with a forced call to whatever tool the request named (the happy-path provider)."""

    def create(self, **kwargs: Any) -> Any:
        self._sink.append(kwargs)
        name = kwargs["tool_choice"]["function"]["name"]
        return _tool_response(name, json.dumps({"orgs": [{"name": "North Ridge Foundry"}]}),
                              usage=SimpleNamespace(prompt_tokens=120, completion_tokens=34))


@pytest.fixture
def sink(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    import openai

    def _build(**kw: Any) -> Any:
        client = _FakeClient(calls, None)
        client.chat = SimpleNamespace(completions=_EchoCompletions(calls, None))
        return client

    monkeypatch.setattr(openai, "OpenAI", _build)
    return calls


def _client() -> OpenAIExtractionClient:
    return OpenAIExtractionClient(api_key="test-key", model_id="gpt-5.6-sol-2026-04-01")


def test_it_satisfies_the_extraction_client_protocol(sink) -> None:
    from chanakya.ingest.client import ExtractionClient

    assert isinstance(_client(), ExtractionClient)


def test_a_pinned_model_id_is_required_and_has_no_default(sink) -> None:
    with pytest.raises(TypeError):
        OpenAIExtractionClient(api_key="k")            # type: ignore[call-arg]
    with pytest.raises(ValueError, match="pinned model_id"):
        OpenAIExtractionClient(api_key="k", model_id="")


def test_text_extraction_forces_exactly_one_named_tool(sink) -> None:
    out = _client().extract(tool_name="extract_prose", input_schema=SCHEMA, system="sys", text="body")
    assert out == {"orgs": [{"name": "North Ridge Foundry"}]}
    kwargs = sink[0]
    assert kwargs["tool_choice"] == {"type": "function", "function": {"name": "extract_prose"}}
    assert len(kwargs["tools"]) == 1
    assert kwargs["tools"][0]["function"]["parameters"] is SCHEMA
    assert kwargs["model"] == "gpt-5.6-sol-2026-04-01"
    assert kwargs["max_completion_tokens"] == MAX_COMPLETION_TOKENS


def test_no_sampling_parameter_is_ever_sent(sink) -> None:
    """The project sets none on any provider; a bake-off that quietly set one would not be comparing
    the same thing across candidates."""
    _client().extract(tool_name="extract_prose", input_schema=SCHEMA, system="sys", text="body")
    _client().read_image(tool_name="read_image", input_schema=SCHEMA, system="sys",
                         image=b"\x89PNG", media_type="image/png")
    forbidden = {"temperature", "top_p", "top_k", "seed", "frequency_penalty", "presence_penalty"}
    for kwargs in sink:
        assert not forbidden & set(kwargs)


def test_a_text_only_call_sends_a_bare_string(sink) -> None:
    _client().extract(tool_name="extract_prose", input_schema=SCHEMA, system="sys", text="body")
    messages = sink[0]["messages"]
    assert messages[0] == {"role": "system", "content": "sys"}
    assert messages[1] == {"role": "user", "content": "body"}


def test_pdf_page_images_ride_alongside_the_prose(sink) -> None:
    """The PDF-multimodal lane: prose and rendered pages read together, in one call."""
    _client().extract(tool_name="extract_prose", input_schema=SCHEMA, system="sys", text="body",
                      images=[(b"\x89PNG-1", "image/png"), (b"\x89PNG-2", "image/png")])
    content = sink[0]["messages"][1]["content"]
    assert content[0] == {"type": "text", "text": "body"}
    assert len(content) == 3
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_the_standalone_vlm_lane_sends_only_the_frame(sink) -> None:
    """The gate that disqualifies a text-only candidate is the one this method exists to satisfy."""
    raw = b"\x89PNG-standalone"
    _client().read_image(tool_name="read_image", input_schema=SCHEMA, system="look",
                         image=raw, media_type="image/png")
    content = sink[0]["messages"][1]["content"]
    assert len(content) == 1 and content[0]["type"] == "image_url"
    encoded = base64.standard_b64encode(raw).decode("ascii")
    assert content[0]["image_url"]["url"] == f"data:image/png;base64,{encoded}"
    assert sink[0]["messages"][0]["content"] == "look"


def test_usage_is_recorded_when_the_api_reports_it(sink) -> None:
    client = _client()
    client.extract(tool_name="extract_prose", input_schema=SCHEMA, system="s", text="t")
    assert client.last_usage == {"input_tokens": 120, "output_tokens": 34}


def test_absent_usage_is_none_never_a_zero_that_prices_a_run_free(monkeypatch) -> None:
    import openai

    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(openai, "OpenAI",
                        lambda **kw: _FakeClient(calls, _tool_response("t", "{}", usage=None)))
    client = OpenAIExtractionClient(api_key="k", model_id="pinned-1")
    client.extract(tool_name="t", input_schema=SCHEMA, system="", text="x")
    assert client.last_usage is None


def test_a_response_without_the_forced_call_raises(monkeypatch) -> None:
    import openai

    empty = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[]))],
                            usage=None)
    monkeypatch.setattr(openai, "OpenAI", lambda **kw: _FakeClient([], empty))
    client = OpenAIExtractionClient(api_key="k", model_id="pinned-1")
    with pytest.raises(RuntimeError, match="no forced function call"):
        client.extract(tool_name="t", input_schema=SCHEMA, system="", text="x")


def test_non_object_arguments_raise_rather_than_being_coerced(monkeypatch) -> None:
    import openai

    monkeypatch.setattr(openai, "OpenAI",
                        lambda **kw: _FakeClient([], _tool_response("t", json.dumps([1, 2, 3]))))
    client = OpenAIExtractionClient(api_key="k", model_id="pinned-1")
    with pytest.raises(RuntimeError, match="non-object arguments"):
        client.extract(tool_name="t", input_schema=SCHEMA, system="", text="x")


def test_an_empty_system_prompt_sends_no_system_message(sink) -> None:
    _client().extract(tool_name="t", input_schema=SCHEMA, system="", text="x")
    assert [m["role"] for m in sink[0]["messages"]] == ["user"]
