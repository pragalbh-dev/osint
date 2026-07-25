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
#: ``max_completion_tokens`` (the newer parameter; ``max_tokens`` is rejected by reasoning models).
MAX_COMPLETION_TOKENS = 8192


class OpenAIExtractionClient:
    """Live extractor on the OpenAI Chat Completions API with a forced function call.

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
        """A base64 data-URI image part (the Chat Completions ``image_url`` shape)."""
        encoded = base64.standard_b64encode(image).decode("ascii")
        return {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{encoded}"}}

    @staticmethod
    def _text_block(text: str) -> dict[str, Any]:
        return {"type": "text", "text": text}

    # ── the one call ──────────────────────────────────────────────────────────────────────────────

    def _call(
        self, *, tool_name: str, input_schema: dict[str, Any], system: str, content: Any
    ) -> dict[str, Any]:
        """Force exactly one function call and return its parsed arguments as a plain dict."""
        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": content})

        tool = {
            "type": "function",
            "function": {"name": tool_name, "parameters": input_schema},
        }
        response = self._client.chat.completions.create(
            model=self.model_id,
            messages=messages,
            tools=[tool],
            tool_choice={"type": "function", "function": {"name": tool_name}},
            max_completion_tokens=MAX_COMPLETION_TOKENS,
        )
        self.last_usage = _usage_dict(getattr(response, "usage", None))

        for choice in getattr(response, "choices", None) or []:
            message = getattr(choice, "message", None)
            for call in getattr(message, "tool_calls", None) or []:
                fn = getattr(call, "function", None)
                if fn is None or getattr(fn, "name", None) != tool_name:
                    continue
                args = getattr(fn, "arguments", None)
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

        Text-only sends a bare string (the unchanged wire shape); with page images the user turn becomes
        a text part plus one image part per page, so prose, tables and figures are read together — the
        PDF-multimodal path the shipped clients implement.
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

    Returns ``None`` rather than zeros when the API reports nothing: a zero token count would price a run
    at zero dollars, which is a fabricated benchmark line.
    """
    if usage is None:
        return None
    prompt = getattr(usage, "prompt_tokens", None)
    completion = getattr(usage, "completion_tokens", None)
    if prompt is None and completion is None:
        return None
    return {"input_tokens": int(prompt or 0), "output_tokens": int(completion or 0)}


__all__ = ["MAX_COMPLETION_TOKENS", "OpenAIExtractionClient"]
