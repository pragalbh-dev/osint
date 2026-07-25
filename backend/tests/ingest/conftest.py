"""Ingest-suite fixtures — the pass-2 coreference side channel for the scripted extraction double.

**The debt this pays.** :class:`~chanakya.ingest.client.ScriptedExtractionClient` is a positional FIFO: a
test declares the exact list of tool-argument dicts its document should draw, and an over-draw raises. That
is the point — the queue length *is* an assertion about how many model calls extraction makes. But the
RK-COREF (S3) stage flag turns on a **second** extraction call per document (``coref.propose_coreference``),
and thirty-odd tests across this suite were written before that call existed. With the flag on they died at
``ScriptedExtractionClient exhausted`` — 32 tests, not one of which is about coreference. Until that is paid
the flag-ON state cannot be measured at all, and for S2/S3/S4 an unmeasurable stage is an unverifiable one
(the stage rule: an *unchanged* graph is a failure signal, so the run has to actually happen).

**Why a side channel and not thirty-two padded queues.** Pass 2 fires *last* within a document but a queue
is shared across every document a test ingests, so a positional pad would have to be interleaved per-doc —
fragile, and it would have to be re-done for every future test. Instead the coreference call is answered
**off-queue**, and only when it is unmistakably that call: the tool name must be
:data:`~chanakya.ingest.coref.TOOL_NAME` *and* the forwarded ``input_schema`` must be exactly the
``CoreferenceClusters`` schema. Anything else — every pass-1 fill, every image read — still draws the FIFO
and still raises on over-draw. So the double is not made lenient: the assertion each of those tests makes
about how many *extraction* calls its document costs is fully intact, and a genuinely unexpected call still
errors. What it stops catching is a runaway in pass 2 itself (a second coref call for one document would be
served rather than flagged) — which is why ``tests/ingest/test_coref.py``, the suite that owns pass 2's call
contract, opts out with ``pytest.mark.scripts_coref`` and keeps scripting the call positionally.

**The canned answer is deliberately not empty** — it is a fully-formed proposal with an unquotable licence,
so every run drives the producer's real parse-and-refuse chain rather than skipping it. It lives in
``tests/ingest/_coref_double.py``, which explains the choice; the bespoke recording client in
``test_pdf_multimodal`` answers from the same definition.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pytest

from chanakya.ingest.client import ScriptedExtractionClient
from tests.ingest._coref_double import is_coref_call, no_coref


@pytest.fixture(autouse=True)
def coref_side_channel(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Answer pass 2's extraction call off-queue, so a pre-S3 test's FIFO is not drained by it.

    Inert while the stage flag is off (the producer makes no call at all), so the flag-OFF suite is
    byte-identical to its pre-existing baseline. Opt out with ``@pytest.mark.scripts_coref`` when the test
    scripts the coreference response itself.
    """
    if "scripts_coref" in request.keywords:
        return

    queued = ScriptedExtractionClient.extract

    def extract(
        self: ScriptedExtractionClient, *, tool_name: str, input_schema: dict[str, Any],
        system: str, text: str, images: Sequence[tuple[bytes, str]] = (),
    ) -> dict[str, Any]:
        if is_coref_call(tool_name, input_schema):
            return no_coref()
        return queued(
            self, tool_name=tool_name, input_schema=input_schema, system=system, text=text, images=images,
        )

    monkeypatch.setattr(ScriptedExtractionClient, "extract", extract)
