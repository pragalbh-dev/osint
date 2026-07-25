"""The shared canned answer for extraction **pass 2** (in-document coreference) — one definition.

Lives beside the suite rather than inside ``conftest.py`` because two different extraction doubles need it:
the shared :class:`~chanakya.ingest.client.ScriptedExtractionClient` (patched by the ingest conftest) and
``test_pdf_multimodal``'s bespoke recording client. Two copies of a canned model response is exactly the
drift class this repo keeps paying for, so there is one.

See ``tests/ingest/conftest.py`` for *why* pass 2 is answered off-queue at all. The short version of why the
answer is **not** empty: an empty ``{}`` would leave the producer's parsing untested on every document in
the suite. :data:`NO_COREF` is a fully-formed proposal on both carriers — a two-member
``EXPLICIT_EQUIVALENCE`` cluster and a contrast — whose licensing span occurs in no document, so each run
drives the real chain (shape → evidence category → per-span verbatim check → member resolution → type rail)
and is refused at the rail that carries the most weight: **an unquotable licence is not a licence.** Nothing
is emitted, so the claims every caller asserts on are identical to the flag-off run.
"""

from __future__ import annotations

import copy
from typing import Any

from chanakya.ingest import coref

#: A licensing span no document can contain. The quote check is whitespace-collapsed substring matching, so
#: the guillemets plus the self-describing wording make an accidental match impossible.
UNLICENSED_SPAN = "⟪ coref side channel: this span occurs in no document ⟫"

#: The canned pass-2 proposal — well-formed, licensed by nothing.
NO_COREF: dict[str, Any] = {
    "clusters": [
        {
            "member_ids": [1, 2],
            "evidence": coref.EXPLICIT_EQUIVALENCE,
            "licensing_quotes": [UNLICENSED_SPAN],
        }
    ],
    "contrasts": [{"left_id": 1, "right_id": 2, "licensing_quote": UNLICENSED_SPAN}],
}

#: The forced-tool schema pass 2 forwards.
_COREF_SCHEMA = coref.CoreferenceClusters.model_json_schema()


def is_coref_call(tool_name: str, input_schema: dict[str, Any]) -> bool:
    """Is this unmistakably pass 2's call? Both the tool name *and* the forwarded schema must match.

    Deliberately narrow. A double that answered on the tool name alone would quietly swallow any other call
    that came to share it, and a swallowed call is an assertion that stopped being made.
    """
    return tool_name == coref.TOOL_NAME and input_schema == _COREF_SCHEMA


def no_coref() -> dict[str, Any]:
    """A fresh copy of :data:`NO_COREF` — callers must never be able to mutate the shared answer."""
    return copy.deepcopy(NO_COREF)
