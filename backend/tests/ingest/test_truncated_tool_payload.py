"""The silent-truncation defect: a typed list field returned as text must be a *recorded* failure.

This pins a defect that shipped and cost real evidence. In a recorded extraction run, 2 of 81 forced
coreference calls came back with ``clusters`` filled as a **truncated JSON string** rather than a list.
``AnthropicExtractionClient._call`` did ``dict(block.input)`` with no validation; ``valid_clusters`` did
``for entry in raw.get("clusters") or []``, iterated the *characters*, dropped every one of them on its
``isinstance(entry, dict)`` guard, and returned nothing. No exception, no log, and the recorded ``error``
was ``null`` — an extraction that had the right answer became indistinguishable from one that found
nothing, which is precisely the confusion this system's one non-negotiable forbids.

The payload below is the real one, verbatim from that run (``anthropic-opus-5/run-01`` on
``d05_customs_manifest``): 265 characters that stop mid-token, carrying the cluster the gold's own note
calls "the ONLY identifier-backed equivalence in the slice".

Two behaviours are pinned:

* the **old silent path** still demonstrably swallows it — so the test states the harm rather than
  asserting the fix in a vacuum;
* the **client** now refuses it, on both live providers and on the scripted replay, naming the field and
  the truncation instead of returning an empty extraction.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
import respx

from chanakya.ingest import coref
from chanakya.ingest.client import MAX_TOKENS, AnthropicExtractionClient, ScriptedExtractionClient
from chanakya.toolargs import MalformedToolPayload, structural_violations, validate_tool_arguments

# The client streams the Messages call (a 32000-token ceiling makes a non-streaming request unsafe), so
# the Anthropic mock has to be Server-Sent Events rather than one JSON body. The event sequence lives in
# one place — ``test_client`` — so there is a single definition to correct if the SDK's shape moves.
from tests.ingest.test_client import _tool_use_stream

# ── the real recorded payload ─────────────────────────────────────────────────────────────────────

#: Verbatim from bundles/anthropic-opus-5/run-01/_resume/d05_customs_manifest.json — the ``clusters``
#: value as the provider returned it. It ends mid-string; ``json.loads`` raises "Unterminated string".
TRUNCATED_CLUSTERS = (
    '[{"member_ids": [1, 7, 10], "evidence": "EXPLICIT_EQUIVALENCE", "licensing_quotes": '
    # NB ``\\n`` — the provider emitted a literal backslash-n *inside* the string, which is part of what
    # makes this fragment unparseable. Kept byte-exact rather than tidied.
    '["ORIENT ELECTRO TRADING PVT LTD (formerly ORIENT ELECTRONIC\\n                 TRADING CO -- '
    'name change ref SECP CUIN 0087762, 2019)", "Consignee ORIENT ELECTRO TRADING (PVT) LTD /'
)
RECORDED_PAYLOAD: dict[str, Any] = {"clusters": TRUNCATED_CLUSTERS}

COREF_SCHEMA = coref.CoreferenceClusters.model_json_schema()
_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

#: This module scripts the coreference call itself, so it opts out of the ingest conftest's side channel
#: (which would otherwise answer the call off-queue and never let the recorded payload through).
pytestmark = pytest.mark.scripts_coref


def test_the_recorded_payload_is_what_we_think_it_is() -> None:
    """The fixture is the real defect, not a hand-made approximation of it."""
    assert len(TRUNCATED_CLUSTERS) == 265
    assert COREF_SCHEMA["properties"]["clusters"]["type"] == "array"
    with pytest.raises(json.JSONDecodeError, match="Unterminated string"):
        json.loads(TRUNCATED_CLUSTERS)


def test_the_silent_path_still_swallows_it_whole(caplog: pytest.LogCaptureFixture) -> None:
    """The harm, stated: the downstream consumer iterates characters and reports nothing at all.

    This is why validation has to live at the client. Every rail below it is written to drop what it
    cannot verify — correct behaviour on a per-entry basis, and total silence when the container itself
    is the wrong type.
    """
    with caplog.at_level("DEBUG"):
        assert coref.valid_clusters(RECORDED_PAYLOAD, [], "document text", []) == []
    assert caplog.records == [], "the drop is completely silent — nothing is logged"


# ── the fix: the payload never reaches the consumer ───────────────────────────────────────────────

def test_validator_names_the_field_and_the_truncation() -> None:
    with pytest.raises(MalformedToolPayload) as exc:
        validate_tool_arguments(RECORDED_PAYLOAD, input_schema=COREF_SCHEMA,
                                tool_name="cluster_coreferences", provider="Anthropic")
    message = str(exc.value)
    assert "clusters" in message and "array" in message and "string" in message
    assert "cut off mid-token" in message
    violation = exc.value.violations[0]
    assert violation.path == "clusters" and violation.truncated and violation.length == 265


@respx.mock
def test_anthropic_client_refuses_the_recorded_payload() -> None:
    """The production seam, end to end: the same bytes off the wire now raise instead of returning.

    ``stop_reason`` is the benign ``tool_use`` on purpose — the payload is refused on its own evidence,
    with no help from the provider's stop signal. The arguments reach the client as ``input_json_delta``
    fragments that reassemble into exactly ``RECORDED_PAYLOAD``: the truncation that matters here is
    *inside* the ``clusters`` value, which the provider serialised as a string and cut mid-token.
    """
    respx.post(_ANTHROPIC_URL).mock(
        return_value=_tool_use_stream("cluster_coreferences", RECORDED_PAYLOAD))
    client = AnthropicExtractionClient(api_key="sk-test")
    with pytest.raises(MalformedToolPayload, match="clusters"):
        client.extract(tool_name="cluster_coreferences", input_schema=COREF_SCHEMA,
                       system="s", text="doc")


@respx.mock
def test_anthropic_client_rejects_a_call_stopped_at_the_token_budget() -> None:
    """A tool call cut off *between* two complete list entries leaves a payload whose shape is fine.

    Only the provider's own ``stop_reason`` reveals it, so that signal is a rejection on its own — a
    forced call that ran out of budget returned an incomplete answer, not a short one. The budget it ran
    out of is ``MAX_TOKENS``, read from the module so this stays honest when the ceiling next moves.
    """
    respx.post(_ANTHROPIC_URL).mock(return_value=_tool_use_stream(
        "cluster_coreferences",
        {"clusters": [{"member_ids": [1, 2], "evidence": "NAME_VARIANT",
                       "licensing_quotes": ["q"]}]},
        stop_reason="max_tokens", output_tokens=MAX_TOKENS,
    ))
    client = AnthropicExtractionClient(api_key="sk-test")
    with pytest.raises(MalformedToolPayload, match="truncated the forced tool call"):
        client.extract(tool_name="cluster_coreferences", input_schema=COREF_SCHEMA,
                       system="s", text="doc")


#: The same generation, cut where it actually stopped: valid JSON right up to the point the budget ran
#: out, ending inside the ``clusters`` string with nothing closed. This is what a mid-token cut looks
#: like *on the wire*, as opposed to the reassembled dict the recorded bundle preserved.
CUT_MID_TOKEN_JSON = json.dumps(RECORDED_PAYLOAD)[:-2]  # drop the closing quote and brace


@respx.mock
def test_a_stream_cut_mid_string_arrives_as_an_empty_payload() -> None:
    """Why the test above puts *complete* JSON on the wire, and why ``stop_reason`` has to stand alone.

    The SDK reassembles ``input_json_delta`` fragments by partial-parsing the buffer, and partial parsing
    **discards a trailing unfinished string**. So a call cut mid-token does not reach the client as a
    ragged payload the validator can name — it reaches it as ``{}``: structurally spotless, and
    indistinguishable from a truthful "found nothing". That is the same silent-loss shape this module
    exists to forbid, and nothing in the arguments can catch it. ``stop_reason`` is the only surviving
    evidence, which is exactly why the budget signal is a rejection in its own right.
    """
    with pytest.raises(json.JSONDecodeError):
        json.loads(CUT_MID_TOKEN_JSON)  # genuinely unfinished, not a tidied stand-in

    # stop_reason is the benign one here, isolating what the *payload* alone can be held to.
    respx.post(_ANTHROPIC_URL).mock(return_value=_tool_use_stream(
        "cluster_coreferences", {}, raw_json=CUT_MID_TOKEN_JSON))
    client = AnthropicExtractionClient(api_key="sk-test")
    assert client.extract(tool_name="cluster_coreferences", input_schema=COREF_SCHEMA,
                          system="s", text="doc") == {}, "the cut field is dropped, not surfaced"


def test_scripted_replay_refuses_a_malformed_recorded_payload() -> None:
    """A frozen bundle is a provider answer we kept; replaying a broken one must fail the same way."""
    client = ScriptedExtractionClient([RECORDED_PAYLOAD])
    with pytest.raises(MalformedToolPayload, match="clusters"):
        client.extract(tool_name="cluster_coreferences", input_schema=COREF_SCHEMA, system="", text="d")


# ── the boundary: what must NOT be rejected ───────────────────────────────────────────────────────

@pytest.mark.parametrize("payload", [
    {},
    {"clusters": [], "contrasts": []},
    {"clusters": None, "contrasts": None},  # absence is a first-class answer, never an error
    {"clusters": [{"member_ids": [1, 7], "evidence": "EXPLICIT_EQUIVALENCE",
                   "licensing_quotes": ["a quote"]}]},
    # a content-level mismatch: the *flavour* of a scalar is the downstream rails' business, not ours
    {"clusters": [{"member_ids": ["1", "7"], "evidence": 42, "licensing_quotes": ["q"]}]},
    # an undeclared top-level key is an "invented field", measured elsewhere — not a structural defect
    {"clusters": [], "notes": "chatter"},
])
def test_well_formed_payloads_pass_untouched(payload: dict[str, Any]) -> None:
    assert validate_tool_arguments(payload, input_schema=COREF_SCHEMA, tool_name="t",
                                   provider="p") is payload


def test_a_structure_serialised_as_text_is_caught_at_depth() -> None:
    """The class is closed at every level, not just the top — the defect is a serialisation defect."""
    payload = {"clusters": [{"member_ids": "[1, 7, 10", "evidence": "NAME_VARIANT",
                             "licensing_quotes": ["q"]}]}
    violations = structural_violations(payload, COREF_SCHEMA)
    assert [v.path for v in violations] == ["clusters[0].member_ids"]


def test_a_whole_object_returned_as_json_text_is_caught() -> None:
    with pytest.raises(MalformedToolPayload, match="non-object arguments"):
        validate_tool_arguments('{"clusters": []}', input_schema=COREF_SCHEMA, tool_name="t",
                                provider="p")
