"""The extraction LLM/VLM seam — a thin, provider-agnostic surface for *one forced tool call*.

INGEST pulls structured claims out of a source by handing the model a single strict extraction
tool and *forcing* it to fill that tool's arguments (provider-native function-calling — never free-text
parsing, never DSPy/litellm). This module is the seam the transformer (``extract.py``) and the imagery
reader (``imagery.py``) are written against, so those layers never import ``anthropic`` / ``google-genai`` /
``openai`` directly. That indirection buys the same three things the ASK seam (``agent.client``) does — but the
shape is different, so this is a *separate* seam, not a reuse of that one:

* **offline, deterministic tests + byte-stable bundles** — inject a :class:`ScriptedExtractionClient`
  that replays queued tool-argument dicts in order (gate G10 / determinism);
* **keyless boot** — :func:`build_extraction_client` returns ``None`` when no key is present, and the
  caller falls back to the frozen bundle-append path (never a fabricated extraction);
* **interchangeable providers** — Gemini is PRIMARY (master §1: native function-calling), Anthropic is the
  second impl, OpenAI the third; each slots behind the one :class:`ExtractionClient` protocol.

All three live *here*, on the shipped ingest path, and that placement is load-bearing rather than tidy.
KEYLESS==LIVE — a reviewer with no key gets the same graph the live system produces — holds only when the
frozen seed bundles were produced by the *same code* the live extractor runs. A client kept off this path
(RK-BAKEOFF's OpenAI candidate originally lived under ``backend/eval``) can be measured but can never be
the producer that freezes the seed, so it cannot win the bake-off however well it extracts. Adding a
provider is therefore a class here plus a :func:`build_extraction_client` branch plus its SDK in the
shipped image's dependencies — never a client parked beside the harness that measures it.

Rules honoured here (master §, spine/08–09, INGEST contract):

* **No sampling params.** No provider call passes ``temperature`` / ``top_p`` / ``top_k`` / ``seed`` (400
  on Opus 4.8; deliberately omitted for Gemini and OpenAI too) — ``model_conf`` is held at 1.0. Nor does
  the OpenAI call pass ``reasoning``/``reasoning_effort``: see :class:`OpenAIExtractionClient`.
* **Forced single tool.** Exactly one tool is offered per call and the model is *required* to call it
  (Anthropic ``tool_choice={"type":"tool",...}``; Gemini ``FunctionCallingConfig(mode=ANY, ...)``; OpenAI
  ``tool_choice={"type":"function","name":…}``).
* **Subject-blind.** This seam never sees a subject/anchor — it forwards the generic, ontology-TYPE-keyed
  ``input_schema`` its caller built (gates G9/G11). It is a pure transport; it does not build schemas,
  map fields, or resolve anything.
* **Upstream of ``rebuild()`` (G1).** Every call here runs at *extraction* time; its output is frozen onto
  a ``ClaimRecord`` before ``store.append``. Nothing in this module ever runs inside ``rebuild()``.

Provider SDKs are imported **lazily** (inside the client constructors), so importing this module never
requires ``anthropic``, ``google-genai`` or ``openai`` to be installed or configured.
"""

from __future__ import annotations

import base64
import json
import os
import threading
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

# ── model + call defaults (config-adjacent constants, no magic numbers buried in logic) ───────────

MODEL = "claude-opus-4-8"  # Anthropic extraction model (md/07); forced tool_use, no sampling params
# PRIMARY extractor: native function-calling + multimodal, fast, keyed. The floating ``-latest`` alias
# tracks the current Gemini flash so a pinned id going "no longer available to new users" (which is what
# happened to gemini-2.5-flash) never dead-ends live extraction; overridable via ``build_extraction_client``.
DEFAULT_GEMINI_MODEL = "gemini-flash-latest"
# Third provider. PINNED, and deliberately not an alias: the OpenAI models endpoint exposes no dated
# snapshot for the 5.6 family, so this IS the concrete id. There is no ``-latest`` fallback here on
# purpose — a floating id would let the frozen seed silently stop equalling what live produces.
DEFAULT_OPENAI_MODEL = "gpt-5.6-sol"
MAX_TOKENS = 8192  # a single doc's worth of tool arguments; well under the streaming/timeout threshold


# ── the call descriptor ──────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ExtractionCall:
    """One forced-tool extraction request — the inputs a client turns into a provider call.

    A convenience value type for callers that want to *describe* a call before dispatching it (e.g. to
    queue, log, or record it). The client methods take the same fields as keyword args directly; this
    record just names the bundle. Immutable — ``input_schema`` is shared by reference, never mutated.
    """

    tool_name: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    system: str = ""
    text: str = ""


# ── the provider-agnostic seam ─────────────────────────────────────────────────────────────────────

@runtime_checkable
class ExtractionClient(Protocol):
    """The single interface the transformer + VLM reader are written against (never a raw SDK).

    Two operations — a text extraction and an image read — each a *forced single tool call* returning the
    tool's filled ``input`` as a plain dict. ``model_id`` is the model-id string that gets stamped onto
    ``Extraction(method=…, version=model_id, model_conf=1.0)`` so provenance records *what produced* each
    claim.
    """

    model_id: str

    def extract(
        self, *, tool_name: str, input_schema: dict[str, Any], system: str, text: str,
        images: Sequence[tuple[bytes, str]] = (),
    ) -> dict[str, Any]:
        """Force one tool call over ``text`` (+ optional page ``images``) → the tool's filled ``input``.

        ``images`` is a sequence of ``(bytes, media_type)`` — the rendered PDF pages the multimodal read
        looks at alongside the prose (INGEST PDF-multimodal path). Empty for a pure-text source, so a
        text-only call is unchanged. This is a document read where the surrounding text is legitimate
        context — distinct from :meth:`read_image`, the *subject-blind* standalone-imagery lane.
        """
        ...

    def read_image(
        self,
        *,
        tool_name: str,
        input_schema: dict[str, Any],
        system: str,
        image: bytes,
        media_type: str,
    ) -> dict[str, Any]:
        """Force one tool call over a **standalone** ``image`` → the tool's filled ``input`` dict.

        The adversarial-imagery lane only (satellite / social ``.png``): the extraction instruction rides
        on ``system``; the image is attached to the user turn. The VLM is *never* told the subject (G11)
        and *never* geolocates from pixels (that is ``imagery.py``'s contract, upstream text coords stay
        authoritative) — this seam only carries the bytes. PDF page images ride on :meth:`extract`.
        """
        ...


# ── scripted / recorded client (offline tests + byte-stable bundles) ───────────────────────────────

class ScriptedExtractionClient:
    """Replays a fixed queue of tool-argument dicts in order — the offline + recorded-bundle client.

    Deterministic and network-free: the same script yields the same claims every run (INGEST gate G10 —
    "LLM/VLM paths tested with mocked/scripted clients"). ``extract`` and ``read_image`` draw from the
    *same* FIFO queue, so a doc that runs text-then-image dequeues in that order. Ignores the live inputs
    (it is a pure replay) and raises if the caller asks for more calls than were recorded.
    """

    def __init__(self, responses: Sequence[dict[str, Any]], *, model_id: str = "scripted") -> None:
        self._queue: list[dict[str, Any]] = list(responses)
        self._i = 0
        self.model_id = model_id

    def _next(self) -> dict[str, Any]:
        if self._i >= len(self._queue):
            raise RuntimeError(
                "ScriptedExtractionClient exhausted: more extraction calls were requested than recorded"
            )
        out = self._queue[self._i]
        self._i += 1
        return out

    def extract(
        self, *, tool_name: str, input_schema: dict[str, Any], system: str, text: str,
        images: Sequence[tuple[bytes, str]] = (),
    ) -> dict[str, Any]:
        return self._next()

    def read_image(
        self,
        *,
        tool_name: str,
        input_schema: dict[str, Any],
        system: str,
        image: bytes,
        media_type: str,
    ) -> dict[str, Any]:
        return self._next()


# ── Gemini client (PRIMARY, live) ──────────────────────────────────────────────────────────────────

class GeminiExtractionClient:
    """Live extractor on Google ``google-genai`` native function-calling — PRIMARY (master §1).

    Forces one function call (``FunctionCallingConfig(mode=ANY, allowed_function_names=[tool])``) and
    returns its arguments. No ``temperature``/``top_p``/``top_k`` is ever set. ``google-genai`` is
    imported lazily so importing this module never requires the SDK.
    """

    def __init__(self, api_key: str | None = None, *, model_id: str = DEFAULT_GEMINI_MODEL) -> None:
        # SDK import + client construction are deferred to first use, so *constructing* this client (and
        # thus `build_extraction_client`) never requires the optional `google-genai` dep — only an actual
        # `extract()`/`read_image()` call does. Keeps the keyless/CI path (no `[gemini]` extra) import-clean;
        # a missing SDK surfaces a clear ImportError at call time, not at build.
        self._api_key = api_key
        self._client: Any = None
        # The lazy init below runs under concurrency and MUST be guarded — see `_sdk_client`.
        self._client_lock = threading.Lock()
        self.model_id = model_id

    def _sdk_client(self) -> Any:
        """The SDK client, built once. The lock is load-bearing, not defensive.

        ``lane.extract_many`` fans extraction out across threads (``asyncio.to_thread`` under a
        semaphore), so several threads reach this method simultaneously on a cold client. Unguarded, each
        one sees ``self._client is None`` and builds its own ``genai.Client``; the last assignment wins and
        every other instance becomes unreachable. ``google-genai``'s httpx wrapper closes its transport in
        ``__del__``, so those orphans take their sockets down as they are collected — while sibling threads
        are still using them.

        That is not a hypothetical. It broke the RK-BAKEOFF live run twice on 2026-07-26, in the two shapes
        this race produces: ``httpx.ReadError: [SSL: DECRYPTION_FAILED_OR_BAD_RECORD_MAC]`` when a
        connection was torn down mid-response, and ``RuntimeError: Cannot send a request, as the client has
        been closed`` when a thread reached a client that had already been collected. Both look like
        network faults and neither is one. The Anthropic and OpenAI clients construct their SDK client in
        ``__init__`` and were never exposed to this.
        """
        if self._client is None:
            with self._client_lock:
                if self._client is None:  # re-checked under the lock: the first test is unsynchronised
                    from google import genai

                    self._client = (
                        genai.Client(api_key=self._api_key) if self._api_key else genai.Client()
                    )
        return self._client

    def _call(
        self, *, tool_name: str, input_schema: dict[str, Any], system: str, contents: Any
    ) -> dict[str, Any]:
        from google.genai import types

        declaration = types.FunctionDeclaration(name=tool_name, parameters_json_schema=input_schema)
        config = types.GenerateContentConfig(
            system_instruction=system or None,
            tools=[types.Tool(function_declarations=[declaration])],
            tool_config=types.ToolConfig(
                function_calling_config=types.FunctionCallingConfig(
                    mode=types.FunctionCallingConfigMode.ANY,
                    allowed_function_names=[tool_name],
                )
            ),
        )
        response = self._sdk_client().models.generate_content(
            model=self.model_id, contents=contents, config=config
        )
        for candidate in response.candidates or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", None) or []:
                fn_call = getattr(part, "function_call", None)
                if fn_call is not None and fn_call.name == tool_name:
                    return dict(fn_call.args or {})
        raise RuntimeError(f"Gemini returned no forced function call for tool {tool_name!r}")

    def extract(
        self, *, tool_name: str, input_schema: dict[str, Any], system: str, text: str,
        images: Sequence[tuple[bytes, str]] = (),
    ) -> dict[str, Any]:
        if images:
            from google.genai import types

            contents: Any = [text, *(types.Part.from_bytes(data=d, mime_type=m) for d, m in images)]
        else:
            contents = text
        return self._call(tool_name=tool_name, input_schema=input_schema, system=system,
                          contents=contents)

    def read_image(
        self,
        *,
        tool_name: str,
        input_schema: dict[str, Any],
        system: str,
        image: bytes,
        media_type: str,
    ) -> dict[str, Any]:
        from google.genai import types

        part = types.Part.from_bytes(data=image, mime_type=media_type)
        return self._call(tool_name=tool_name, input_schema=input_schema, system=system, contents=[part])


# ── Anthropic client (optional second, live) ───────────────────────────────────────────────────────

class AnthropicExtractionClient:
    """Live extractor on Anthropic ``claude-opus-4-8`` forced ``tool_use`` — the optional second impl.

    Offers the single extraction tool and forces it via ``tool_choice={"type":"tool","name":tool}``; the
    filled ``tool_use.input`` block is returned as a dict. No ``temperature``/``top_p``/``top_k`` (400 on
    Opus 4.8). ``anthropic`` is imported lazily so importing this module never requires the SDK.
    """

    def __init__(self, api_key: str | None = None, *, model_id: str = MODEL) -> None:
        import anthropic

        self._client: Any = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self.model_id = model_id

    def _call(
        self, *, tool_name: str, input_schema: dict[str, Any], system: str, content: Any
    ) -> dict[str, Any]:
        tool = {"name": tool_name, "input_schema": input_schema}
        response = self._client.messages.create(
            model=self.model_id,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": content}],
            tools=[tool],
            tool_choice={"type": "tool", "name": tool_name},
        )
        for block in response.content:
            if getattr(block, "type", None) == "tool_use" and block.name == tool_name:
                return dict(block.input)
        raise RuntimeError(f"Anthropic returned no forced tool_use for tool {tool_name!r}")

    @staticmethod
    def _image_block(image: bytes, media_type: str) -> dict[str, Any]:
        """A base64 image content block (the Anthropic Messages image shape)."""
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64.standard_b64encode(image).decode("ascii"),
            },
        }

    def extract(
        self, *, tool_name: str, input_schema: dict[str, Any], system: str, text: str,
        images: Sequence[tuple[bytes, str]] = (),
    ) -> dict[str, Any]:
        # Text-only stays a bare string (unchanged wire shape); page images become a text block + image
        # blocks so the model reads prose, tables and figures together.
        content: Any = text
        if images:
            content = [{"type": "text", "text": text},
                       *(self._image_block(d, m) for d, m in images)]
        return self._call(tool_name=tool_name, input_schema=input_schema, system=system, content=content)

    def read_image(
        self,
        *,
        tool_name: str,
        input_schema: dict[str, Any],
        system: str,
        image: bytes,
        media_type: str,
    ) -> dict[str, Any]:
        return self._call(
            tool_name=tool_name, input_schema=input_schema, system=system,
            content=[self._image_block(image, media_type)],
        )


# ── OpenAI client (third, live) ────────────────────────────────────────────────────────────────────

class OpenAIExtractionClient:
    """Live extractor on the OpenAI **Responses** API with a forced function call — the third impl.

    Carries the full surface the other two carry: the text lane, the PDF-page multimodal lane
    (``extract(images=…)``), and the subject-blind standalone-imagery lane (:meth:`read_image`). Dropping
    the imagery lane is a disqualifier, not a weakness, so a partial client would make this provider
    unusable rather than merely worse.

    **Why Responses and not Chat Completions.** The first cut used ``chat.completions.create`` and it does
    not work on ``gpt-5.6-sol``, which rejects the request outright: *"Function tools with
    reasoning_effort are not supported for gpt-5.6-sol in /v1/chat/completions. To use function tools, use
    /v1/responses or set reasoning_effort to 'none'."* The API offers two ways out and only one of them is
    honest — setting ``reasoning_effort='none'`` would run a *deliberately weakened* model under a pinned
    id, which is a rigged comparison in the bake-off and an undisclosed downgrade in production. So the
    client moved to ``/v1/responses`` and the model keeps its native reasoning. That is a transport
    change; nothing about what is asked of the model changed.

    ``model_id`` has **no default here**: it is supplied by the caller (``build_extraction_client`` passes
    :data:`DEFAULT_OPENAI_MODEL`, RK-BAKEOFF passes the pinned id from its candidate declaration) and is
    stamped onto every claim's ``Extraction.version``, so provenance records the exact version that
    produced the claim. A class-level default is what lets a wrong-but-plausible id ride along unnoticed.

    ``openai`` is imported lazily so importing this module never requires the SDK.
    """

    def __init__(self, api_key: str | None = None, *, model_id: str) -> None:
        import openai

        if not model_id:
            raise ValueError("OpenAIExtractionClient needs an explicit pinned model_id (no default)")
        self._client: Any = openai.OpenAI(api_key=api_key) if api_key else openai.OpenAI()
        self.model_id = model_id
        #: Token usage of the most recent call, or ``None`` when the API returned none. Callers that price
        #: a run read this; it is never invented when absent (see :func:`_openai_usage_dict`).
        self.last_usage: dict[str, int] | None = None

    @staticmethod
    def _image_block(image: bytes, media_type: str) -> dict[str, Any]:
        """A base64 data-URI image part (the Responses ``input_image`` shape)."""
        encoded = base64.standard_b64encode(image).decode("ascii")
        return {"type": "input_image", "image_url": f"data:{media_type};base64,{encoded}"}

    @staticmethod
    def _text_block(text: str) -> dict[str, Any]:
        return {"type": "input_text", "text": text}

    def _call(
        self, *, tool_name: str, input_schema: dict[str, Any], system: str, content: Any,
    ) -> dict[str, Any]:
        """Force exactly one function call and return its parsed arguments as a plain dict.

        ``strict`` is deliberately left off the tool: every extraction schema in this project is
        all-optional by construction (a required field is how a model is pushed into inventing an operator
        or a date the source never stated), and strict mode demands the opposite. Turning it on would
        trade the anti-fabrication property for a validation guarantee — exactly backwards here.

        Two things are *absent* on purpose, and both are honesty rules rather than style:

        * **No sampling parameter** — no ``temperature`` / ``top_p`` / ``seed``, the same rule the Gemini
          and Anthropic clients are held to.
        * **No ``reasoning`` / ``reasoning_effort``** — the model runs at its own default, for the reason
          given in the class docstring.

        An empty ``system`` sends **no** instructions key at all, rather than an explicit ``null``: the
        claim is that no system message was sent, and only omission states that unambiguously.
        """
        request: dict[str, Any] = {
            "model": self.model_id,
            "input": [{"role": "user", "content": content}],
            "tools": [{"type": "function", "name": tool_name, "parameters": input_schema}],
            "tool_choice": {"type": "function", "name": tool_name},
            "max_output_tokens": MAX_TOKENS,
        }
        if system:
            request["instructions"] = system
        response = self._client.responses.create(**request)
        self.last_usage = _openai_usage_dict(getattr(response, "usage", None))

        for item in getattr(response, "output", None) or []:
            if getattr(item, "type", None) != "function_call":
                continue  # reasoning items and message items ride the same list; skip them
            if getattr(item, "name", None) != tool_name:
                continue
            args = getattr(item, "arguments", None)
            if isinstance(args, dict):
                return dict(args)
            parsed = json.loads(args or "{}")
            if not isinstance(parsed, dict):
                raise RuntimeError(
                    f"OpenAI returned non-object arguments for tool {tool_name!r}: {type(parsed).__name__}"
                )
            return parsed
        raise RuntimeError(f"OpenAI returned no forced function call for tool {tool_name!r}")

    def extract(
        self, *, tool_name: str, input_schema: dict[str, Any], system: str, text: str,
        images: Sequence[tuple[bytes, str]] = (),
    ) -> dict[str, Any]:
        # Text-only sends the prose as a bare string, matching Anthropic (`content=text`) and Gemini
        # (`contents=text`): a parts array for one provider and a bare string for the others is a harness
        # difference that would read as a model difference. Page images become a text part plus one image
        # part per page, so prose, tables and figures are read together.
        content: Any = text
        if images:
            content = [self._text_block(text), *(self._image_block(d, m) for d, m in images)]
        return self._call(tool_name=tool_name, input_schema=input_schema, system=system, content=content)

    def read_image(
        self,
        *,
        tool_name: str,
        input_schema: dict[str, Any],
        system: str,
        image: bytes,
        media_type: str,
    ) -> dict[str, Any]:
        return self._call(
            tool_name=tool_name, input_schema=input_schema, system=system,
            content=[self._image_block(image, media_type)],
        )


def _openai_usage_dict(usage: Any) -> dict[str, int] | None:
    """Normalise the SDK usage object to ``{input_tokens, output_tokens}``, or ``None`` if absent.

    Reads the Responses API's own names first and falls back to the Chat Completions ones, so a mixed or
    older SDK still prices correctly. Returns ``None`` rather than zeros when the API reports nothing: a
    zero token count would price a run at zero dollars, which is a fabricated benchmark line.
    """
    if usage is None:
        return None
    prompt = getattr(usage, "input_tokens", None)
    if prompt is None:
        prompt = getattr(usage, "prompt_tokens", None)
    completion = getattr(usage, "output_tokens", None)
    if completion is None:
        completion = getattr(usage, "completion_tokens", None)
    if prompt is None and completion is None:
        return None
    return {"input_tokens": int(prompt or 0), "output_tokens": int(completion or 0)}


# ── client resolution (keyed → live; keyless → None → bundles path) ───────────────────────────────

def build_extraction_client(model_id: str | None = None) -> ExtractionClient | None:
    """Resolve the extraction client from the environment: Gemini → Anthropic → OpenAI → ``None``.

    Gemini is PRIMARY (``GEMINI_API_KEY``); Anthropic is second (``ANTHROPIC_API_KEY``); OpenAI is third
    (``OPENAI_API_KEY``). The order is precedence, not preference-of-the-day: it is the order the shipped
    system has always used, and appending rather than inserting keeps every existing keyed deployment
    resolving to exactly the client it resolved to before.

    ``None`` means "no live extractor" — the caller falls back to the keyless frozen-bundle append path,
    never a fabricated extraction. ``model_id`` overrides the chosen provider's default model.
    """
    if os.environ.get("GEMINI_API_KEY"):
        return GeminiExtractionClient(model_id=model_id or DEFAULT_GEMINI_MODEL)
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicExtractionClient(model_id=model_id or MODEL)
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAIExtractionClient(model_id=model_id or DEFAULT_OPENAI_MODEL)
    return None
