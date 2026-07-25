"""The OpenAI GPT extraction client — a third implementation of the one ``ExtractionClient`` seam.

Built so the GPT candidate can actually be *measured*: the bake-off's VLM-imagery gate is pass/fail to
win, so a client that cannot exercise :meth:`read_image` makes its candidate unmeasurable rather than
merely weaker. This one carries the full surface the shipped clients carry — the text lane, the
PDF-page multimodal lane (``extract(images=…)``), and the subject-blind standalone-imagery lane
(``read_image``).

It mirrors ``chanakya.ingest.client`` exactly where the rules bind:

* **Forced single tool.** One function is offered and ``tool_choice`` names it, so the model cannot
  answer in prose. Never free-text parsing.
* **No sampling params.** No ``temperature`` / ``top_p`` / ``top_k`` / ``seed`` is ever sent — the same
  rule every other provider in this project is held to.
* **Pinned model id.** The id is passed in from config; this module declares no default and offers no
  ``-latest`` fallback. A floating alias is a gate failure, so there is deliberately nothing here to
  fall back *to*.
* **Subject-blind.** Pure transport: it forwards the ontology-TYPE-keyed ``input_schema`` its caller
  built and returns the model's filled arguments verbatim. It builds no schema and resolves nothing.
* **Lazy SDK import.** ``openai`` is imported inside the constructor, so importing this module never
  requires the SDK.

**Where it lives matters.** This is under ``backend/eval`` because GPT is a *candidate*, not the shipped
extractor. Per plan §8 a production winner's client must live in ``chanakya/ingest`` — the seed-freezing
producer and the live extractor have to be the same code for KEYLESS==LIVE to hold by construction. The
KEYLESS==LIVE gate checks that, so as long as this client sits here the GPT candidate fails that gate.
Promoting it is a file move plus a ``build_extraction_client`` branch, not a rewrite.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Sequence
from typing import Any

#: Matches ``chanakya.ingest.client.MAX_TOKENS`` — one document's worth of tool arguments. Sent as
#: ``max_output_tokens`` (the Responses API's name for the output cap).
MAX_COMPLETION_TOKENS = 8192


class OpenAIExtractionClient:
    """Live extractor on the OpenAI **Responses** API with a forced function call.

    **Why Responses and not Chat Completions.** The first cut of this client used
    ``chat.completions.create`` and it does not work on the candidate under test: ``gpt-5.6-sol``
    rejects the request outright with *"Function tools with reasoning_effort are not supported for
    gpt-5.6-sol in /v1/chat/completions. To use function tools, use /v1/responses or set reasoning_effort
    to 'none'."* The API offers two ways out and only one of them is honest here — setting
    ``reasoning_effort='none'`` would silently benchmark a *deliberately weakened* GPT against two
    competitors running at their own defaults, which is a rigged comparison wearing a fixed model id. So
    the client moved to ``/v1/responses`` and the model keeps its native reasoning. This is a transport
    change; nothing about what is asked of the model changed.

    ``model_id`` has **no default**: it is supplied by the candidate declaration in ``config/bakeoff.yaml``
    and is stamped onto every claim's ``Extraction.version``, so provenance records the exact pinned
    version that produced the claim.
    """

    def __init__(self, api_key: str | None = None, *, model_id: str) -> None:
        import openai

        if not model_id:
            raise ValueError("OpenAIExtractionClient needs an explicit pinned model_id (no default)")
        self._client: Any = openai.OpenAI(api_key=api_key) if api_key else openai.OpenAI()
        self.model_id = model_id
        #: Token usage of the most recent call, or ``None`` when the API returned none. The recording
        #: wrapper reads this to price a run; it is never invented when absent.
        self.last_usage: dict[str, int] | None = None

    # ── content-block helpers ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def _image_block(image: bytes, media_type: str) -> dict[str, Any]:
        """A base64 data-URI image part (the Responses ``input_image`` shape)."""
        encoded = base64.standard_b64encode(image).decode("ascii")
        return {"type": "input_image", "image_url": f"data:{media_type};base64,{encoded}"}

    @staticmethod
    def _text_block(text: str) -> dict[str, Any]:
        return {"type": "input_text", "text": text}

    # ── the one call ──────────────────────────────────────────────────────────────────────────────

    def _call(
        self, *, tool_name: str, input_schema: dict[str, Any], system: str, content: Any,
    ) -> dict[str, Any]:
        """Force exactly one function call and return its parsed arguments as a plain dict.

        ``strict`` is deliberately left off the tool: every extraction schema in this project is
        all-optional by construction (a required field is how a model is pushed into inventing an
        operator or a date the source never stated), and strict mode demands the opposite. Turning it on
        would trade the anti-fabrication property for a validation guarantee — exactly backwards for the
        thing this bake-off exists to measure.

        Two things are *absent* on purpose, and both are honesty rules rather than style:

        * **No sampling parameter** — no ``temperature`` / ``top_p`` / ``seed``, the same rule the shipped
          Anthropic and Gemini clients are held to. A knob set on one candidate and not the others would
          make the bake-off a comparison of settings.
        * **No ``reasoning`` / ``reasoning_effort``** — the model runs at its own default. Turning
          reasoning down is the other way out of the Chat Completions rejection described above, and it
          would benchmark a deliberately weakened GPT under a fixed model id.

        An empty ``system`` sends **no** instructions key at all, rather than an explicit ``null``: the
        parity claim is that no system message was sent, and only omission states that unambiguously.
        """
        request: dict[str, Any] = {
            "model": self.model_id,
            "input": [{"role": "user", "content": content}],
            "tools": [{"type": "function", "name": tool_name, "parameters": input_schema}],
            "tool_choice": {"type": "function", "name": tool_name},
            "max_output_tokens": MAX_COMPLETION_TOKENS,
        }
        if system:
            request["instructions"] = system
        response = self._client.responses.create(**request)
        self.last_usage = _usage_dict(getattr(response, "usage", None))

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

    # ── the ExtractionClient surface ──────────────────────────────────────────────────────────────

    def extract(
        self, *, tool_name: str, input_schema: dict[str, Any], system: str, text: str,
        images: Sequence[tuple[bytes, str]] = (),
    ) -> dict[str, Any]:
        """Force one tool call over ``text`` (+ optional rendered page ``images``) → filled arguments.

        Text-only sends the prose as a **bare string**, which is what both shipped clients do (Anthropic
        passes ``content=text``, Gemini passes ``contents=text``). Keeping the three wire shapes identical
        on the common lane matters: the bake-off is meant to measure models, and a text-only document
        wrapped in a parts array for one candidate and not the others is a difference in the *harness*
        that would show up as a difference in the *model*.

        With page images the user turn becomes a text part plus one image part per page, so prose, tables
        and figures are read together — the PDF-multimodal path the shipped clients implement.
        """
        content: Any = text
        if images:
            content = [self._text_block(text), *(self._image_block(d, m) for d, m in images)]
        return self._call(tool_name=tool_name, input_schema=input_schema, system=system, content=content)

    def read_image(
        self, *, tool_name: str, input_schema: dict[str, Any], system: str, image: bytes,
        media_type: str,
    ) -> dict[str, Any]:
        """Force one tool call over a **standalone** image → filled arguments (the VLM imagery lane).

        The instruction rides on ``system`` and the frame is the whole user turn — subject-blind, exactly
        as the Gemini and Anthropic clients do it. This method existing and working is what makes the GPT
        candidate measurable against the VLM gate at all.
        """
        return self._call(
            tool_name=tool_name, input_schema=input_schema, system=system,
            content=[self._image_block(image, media_type)],
        )


def _usage_dict(usage: Any) -> dict[str, int] | None:
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


__all__ = ["MAX_COMPLETION_TOKENS", "OpenAIExtractionClient"]
