"""The extraction LLM/VLM seam — a thin, provider-agnostic surface for *one forced tool call*.

INGEST pulls structured claims out of a source by handing the model a single strict extraction
tool and *forcing* it to fill that tool's arguments (provider-native function-calling — never free-text
parsing, never DSPy/litellm). This module is the seam the transformer (``extract.py``) and the imagery
reader (``imagery.py``) are written against, so those layers never import ``anthropic`` / ``google-genai``
directly. That indirection buys the same three things the ASK seam (``agent.client``) does — but the
shape is different, so this is a *separate* seam, not a reuse of that one:

* **offline, deterministic tests + byte-stable bundles** — inject a :class:`ScriptedExtractionClient`
  that replays queued tool-argument dicts in order (gate G10 / determinism);
* **keyless boot** — :func:`build_extraction_client` returns ``None`` when no key is present, and the
  caller falls back to the frozen bundle-append path (never a fabricated extraction);
* **an optional second provider** — Gemini is PRIMARY (master §1: native function-calling), Anthropic is
  the optional second impl; either slots behind the one :class:`ExtractionClient` protocol.

Rules honoured here (master §, spine/08–09, INGEST contract):

* **No sampling params.** Neither the Gemini nor the Anthropic call passes ``temperature`` / ``top_p`` /
  ``top_k`` (400 on Opus 4.8; deliberately omitted for Gemini too) — ``model_conf`` is held at 1.0.
* **Forced single tool.** Exactly one tool is offered per call and the model is *required* to call it
  (Anthropic ``tool_choice={"type":"tool",...}``; Gemini ``FunctionCallingConfig(mode=ANY, ...)``).
* **Subject-blind.** This seam never sees a subject/anchor — it forwards the generic, ontology-TYPE-keyed
  ``input_schema`` its caller built (gates G9/G11). It is a pure transport; it does not build schemas,
  map fields, or resolve anything.
* **Upstream of ``rebuild()`` (G1).** Every call here runs at *extraction* time; its output is frozen onto
  a ``ClaimRecord`` before ``store.append``. Nothing in this module ever runs inside ``rebuild()``.

Provider SDKs are imported **lazily** (inside the client constructors), so importing this module never
requires ``anthropic`` or ``google-genai`` to be installed or configured.
"""

from __future__ import annotations

import base64
import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

# ── model + call defaults (config-adjacent constants, no magic numbers buried in logic) ───────────

MODEL = "claude-opus-4-8"  # Anthropic extraction model (md/07); forced tool_use, no sampling params
# PRIMARY extractor: native function-calling + multimodal, fast, keyed. The floating ``-latest`` alias
# tracks the current Gemini flash so a pinned id going "no longer available to new users" (which is what
# happened to gemini-2.5-flash) never dead-ends live extraction; overridable via ``build_extraction_client``.
DEFAULT_GEMINI_MODEL = "gemini-flash-latest"
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
        self.model_id = model_id

    def _sdk_client(self) -> Any:
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._api_key) if self._api_key else genai.Client()
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


# ── client resolution (keyed → live; keyless → None → bundles path) ───────────────────────────────

def build_extraction_client(model_id: str | None = None) -> ExtractionClient | None:
    """Resolve the extraction client from the environment: Gemini if keyed, else Anthropic, else ``None``.

    Gemini is PRIMARY (``GEMINI_API_KEY``); Anthropic is the optional second (``ANTHROPIC_API_KEY``).
    ``None`` means "no live extractor" — the caller falls back to the keyless frozen-bundle append path,
    never a fabricated extraction. ``model_id`` overrides the chosen provider's default model.
    """
    if os.environ.get("GEMINI_API_KEY"):
        return GeminiExtractionClient(model_id=model_id or DEFAULT_GEMINI_MODEL)
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicExtractionClient(model_id=model_id or MODEL)
    return None
