"""The OpenAI extraction client — offline, against a fake SDK. No network, no key, no spend.

What is asserted is the *contract*, not the vendor: one forced tool call, **no sampling parameters ever**,
a pinned model id with no default to fall back to, and the full surface the shipped clients carry —
including both multimodal lanes, because dropping the VLM path is a disqualifier and a client that cannot
exercise it makes its candidate unmeasurable.

**The transport is the Responses API, and these tests were rewritten to match it.** The first cut of the
client used ``chat.completions``, and the candidate under test rejects a function tool there outright
(*"Function tools with reasoning_effort are not supported for gpt-5.6-sol in /v1/chat/completions. To use
function tools, use /v1/responses or set reasoning_effort to 'none'."* — reproduced live, verbatim). Of the
two ways out, turning reasoning off would benchmark a deliberately weakened GPT under a fixed model id, so
the client moved endpoint instead. Everything these tests are *for* survived that move: the forced single
tool, the verbatim schema, the absent sampling knobs, absent usage staying ``None``, and both raise paths.
Only the wire spelling changed.
"""

from __future__ import annotations

import base64
import json
from types import SimpleNamespace
from typing import Any

import pytest

from eval.extraction.gpt_client import MAX_COMPLETION_TOKENS, OpenAIExtractionClient

SCHEMA = {"type": "object", "properties": {"orgs": {"type": "array"}}}


class _FakeResponses:
    def __init__(self, sink: list[dict[str, Any]], response: Any) -> None:
        self._sink = sink
        self._response = response

    def create(self, **kwargs: Any) -> Any:
        self._sink.append(kwargs)
        return self._response


class _FakeClient:
    def __init__(self, sink: list[dict[str, Any]], response: Any) -> None:
        self.responses = _FakeResponses(sink, response)


def _tool_response(name: str, arguments: str, *, usage: Any = None) -> Any:
    """A Responses-API reply: a reasoning item the parser must skip, then the forced function call.

    The reasoning item is not decoration. ``gpt-5.6-sol`` runs at its native reasoning effort, so its
    ``output`` list really does carry non-call items ahead of the call, and a parser that read
    ``output[0]`` would find no tool call on a response that contains one.
    """
    return SimpleNamespace(
        output=[
            SimpleNamespace(type="reasoning", summary=[]),
            SimpleNamespace(type="function_call", name=name, arguments=arguments, call_id="c1"),
        ],
        usage=usage,
    )


class _EchoResponses(_FakeResponses):
    """Answers with a forced call to whatever tool the request named (the happy-path provider)."""

    def create(self, **kwargs: Any) -> Any:
        self._sink.append(kwargs)
        name = kwargs["tool_choice"]["name"]
        return _tool_response(name, json.dumps({"orgs": [{"name": "North Ridge Foundry"}]}),
                              usage=SimpleNamespace(input_tokens=120, output_tokens=34))


@pytest.fixture
def sink(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    import openai

    def _build(**kw: Any) -> Any:
        client = _FakeClient(calls, None)
        client.responses = _EchoResponses(calls, None)
        return client

    monkeypatch.setattr(openai, "OpenAI", _build)
    return calls


def _client() -> OpenAIExtractionClient:
    return OpenAIExtractionClient(api_key="test-key", model_id="gpt-5.6-sol")


def _user_content(kwargs: dict[str, Any]) -> Any:
    """The one user turn's content, whatever shape it took."""
    assert [m["role"] for m in kwargs["input"]] == ["user"]
    return kwargs["input"][0]["content"]


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
    assert kwargs["tool_choice"] == {"type": "function", "name": "extract_prose"}
    assert len(kwargs["tools"]) == 1
    assert kwargs["tools"][0]["name"] == "extract_prose"
    # identity, not equality: the caller's schema is forwarded verbatim, never rebuilt or "helped"
    assert kwargs["tools"][0]["parameters"] is SCHEMA
    assert kwargs["model"] == "gpt-5.6-sol"
    assert kwargs["max_output_tokens"] == MAX_COMPLETION_TOKENS


def test_the_all_optional_schema_is_never_sent_as_strict(sink) -> None:
    """Strict mode demands required fields; every schema here is all-optional so a model is never pushed
    into inventing an operator or a date the source did not state. That anti-fabrication property is not
    tradeable for a validation guarantee."""
    _client().extract(tool_name="extract_prose", input_schema=SCHEMA, system="sys", text="body")
    assert "strict" not in sink[0]["tools"][0]


def test_no_sampling_parameter_is_ever_sent(sink) -> None:
    """The project sets none on any provider; a bake-off that quietly set one would not be comparing
    the same thing across candidates.

    ``reasoning``/``reasoning_effort`` are in the same list for a sharper reason: turning reasoning down is
    the *other* way past the Chat Completions rejection, and it would silently measure a weakened model
    under a pinned id nobody would suspect."""
    _client().extract(tool_name="extract_prose", input_schema=SCHEMA, system="sys", text="body")
    _client().read_image(tool_name="read_image", input_schema=SCHEMA, system="sys",
                         image=b"\x89PNG", media_type="image/png")
    forbidden = {"temperature", "top_p", "top_k", "seed", "frequency_penalty", "presence_penalty",
                 "reasoning", "reasoning_effort"}
    for kwargs in sink:
        assert not forbidden & set(kwargs)


def test_a_text_only_call_sends_a_bare_string(sink) -> None:
    """The same wire shape both shipped clients use for text-only (Anthropic ``content=text``, Gemini
    ``contents=text``). A parts array for one candidate and a bare string for the others would be a
    harness difference that reads as a model difference."""
    _client().extract(tool_name="extract_prose", input_schema=SCHEMA, system="sys", text="body")
    assert sink[0]["instructions"] == "sys"
    assert _user_content(sink[0]) == "body"


def test_pdf_page_images_ride_alongside_the_prose(sink) -> None:
    """The PDF-multimodal lane: prose and rendered pages read together, in one call."""
    _client().extract(tool_name="extract_prose", input_schema=SCHEMA, system="sys", text="body",
                      images=[(b"\x89PNG-1", "image/png"), (b"\x89PNG-2", "image/png")])
    content = _user_content(sink[0])
    assert content[0] == {"type": "input_text", "text": "body"}
    assert len(content) == 3
    assert content[1]["type"] == "input_image"
    assert content[1]["image_url"].startswith("data:image/png;base64,")


def test_the_standalone_vlm_lane_sends_only_the_frame(sink) -> None:
    """The gate that disqualifies a text-only candidate is the one this method exists to satisfy."""
    raw = b"\x89PNG-standalone"
    _client().read_image(tool_name="read_image", input_schema=SCHEMA, system="look",
                         image=raw, media_type="image/png")
    content = _user_content(sink[0])
    assert len(content) == 1 and content[0]["type"] == "input_image"
    encoded = base64.standard_b64encode(raw).decode("ascii")
    assert content[0]["image_url"] == f"data:image/png;base64,{encoded}"
    assert sink[0]["instructions"] == "look"


def test_usage_is_recorded_when_the_api_reports_it(sink) -> None:
    client = _client()
    client.extract(tool_name="extract_prose", input_schema=SCHEMA, system="s", text="t")
    assert client.last_usage == {"input_tokens": 120, "output_tokens": 34}


def test_chat_completions_usage_names_still_price_a_run(monkeypatch) -> None:
    """A mixed or older SDK reporting ``prompt_tokens``/``completion_tokens`` must still price, because the
    alternative is a run that silently looks free."""
    import openai

    usage = SimpleNamespace(prompt_tokens=7, completion_tokens=3)
    monkeypatch.setattr(openai, "OpenAI",
                        lambda **kw: _FakeClient([], _tool_response("t", "{}", usage=usage)))
    client = OpenAIExtractionClient(api_key="k", model_id="pinned-1")
    client.extract(tool_name="t", input_schema=SCHEMA, system="", text="x")
    assert client.last_usage == {"input_tokens": 7, "output_tokens": 3}


def test_absent_usage_is_none_never_a_zero_that_prices_a_run_free(monkeypatch) -> None:
    import openai

    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(openai, "OpenAI",
                        lambda **kw: _FakeClient(calls, _tool_response("t", "{}", usage=None)))
    client = OpenAIExtractionClient(api_key="k", model_id="pinned-1")
    client.extract(tool_name="t", input_schema=SCHEMA, system="", text="x")
    assert client.last_usage is None


def test_a_response_without_the_forced_call_raises(monkeypatch) -> None:
    """A reply carrying reasoning and prose but no tool call is a refusal to answer in schema, and the
    harness must see it as an error — never as an empty extraction, which would score as "found nothing"."""
    import openai

    empty = SimpleNamespace(
        output=[SimpleNamespace(type="reasoning", summary=[]),
                SimpleNamespace(type="message", content=[])],
        usage=None,
    )
    monkeypatch.setattr(openai, "OpenAI", lambda **kw: _FakeClient([], empty))
    client = OpenAIExtractionClient(api_key="k", model_id="pinned-1")
    with pytest.raises(RuntimeError, match="no forced function call"):
        client.extract(tool_name="t", input_schema=SCHEMA, system="", text="x")


def test_a_call_to_a_different_tool_is_not_accepted_as_the_forced_one(monkeypatch) -> None:
    import openai

    monkeypatch.setattr(openai, "OpenAI",
                        lambda **kw: _FakeClient([], _tool_response("some_other_tool", "{}")))
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
    """Omitted, not ``null``: the claim is that no system instruction was sent, and only absence says so."""
    _client().extract(tool_name="t", input_schema=SCHEMA, system="", text="x")
    assert "instructions" not in sink[0]
