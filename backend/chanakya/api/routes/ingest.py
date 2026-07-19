"""``POST /ingest`` — the live ingest lane, delegated to INGEST (API.md scope 5).

Two paths, one endpoint:

* **keyless** — append a pre-extracted claim ``bundle`` (no key, no LLM: a frozen bundle is byte-for-byte
  the output of live extraction over the same doc). This is the reviewer / public-demo default.
* **keyed** — extract a raw doc live (``extract → append``), then rebuild. Guarded behind
  ``CHANAKYA_ENABLE_EXTRACTION`` (default **off**) so a public deployment doesn't burn model quota /
  rate limits on every visitor; when off, a raw-doc submission is turned away toward the bundle path.

Either way the append is followed by :meth:`AppState.rebuild_and_swap`, so the held view + alert feed
update in-process with **no restart** (§1 invariant 3), and any observables fired on the post-ingest
delta come back in the response. **This route is a plain ``def`` on purpose**: the lane runs its own
``asyncio`` extraction fan-out internally, so an ``async def`` route would call ``asyncio.run`` from
inside the running loop and crash — FastAPI runs a ``def`` route in a threadpool, preserving concurrency.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError

from chanakya.api.routes.deps import get_state
from chanakya.api.state import AppState
from chanakya.ingest import build_extraction_client, ingest_bundle, ingest_document
from chanakya.schemas import IngestRequest, IngestResult

router = APIRouter()

_TRUTHY = {"1", "true", "yes", "on"}


def _extraction_enabled() -> bool:
    return os.environ.get("CHANAKYA_ENABLE_EXTRACTION", "").strip().lower() in _TRUTHY


@router.post("/ingest", response_model=IngestResult)
def post_ingest(req: IngestRequest, state: AppState = Depends(get_state)) -> IngestResult:
    has_bundle = bool(req.bundle)
    has_raw = bool(req.raw_text) or bool(req.doc_path)
    if has_bundle and has_raw:
        raise HTTPException(400, detail="provide either `bundle` (keyless) or a raw doc, not both")
    if not has_bundle and not has_raw:
        raise HTTPException(
            400,
            detail="provide `bundle` (keyless) or `raw_text` + `source_id` + `source_type` (keyed)",
        )

    # ── keyless: append a pre-extracted bundle ──────────────────────────────────────────────────
    if has_bundle:
        try:
            claims = ingest_bundle(req.bundle or [])
        except ValidationError as exc:
            raise HTTPException(422, detail=f"invalid claim bundle: {exc.error_count()} error(s)") from exc
        state.evidence.append_many(claims)
        fired = state.rebuild_and_swap()
        return IngestResult(
            appended_claim_ids=[c.claim_id for c in claims],
            rebuilt=True,
            alerts_fired=[alert.observable_id for alert in fired],
        )

    # ── keyed: extract a raw doc live (guarded) ─────────────────────────────────────────────────
    if req.doc_path:
        raise HTTPException(
            400, detail="`doc_path` ingestion is a CLI/SHIP concern; submit `raw_text` or a `bundle`"
        )
    if not _extraction_enabled():
        raise HTTPException(
            403,
            detail=(
                "live extraction is disabled on this deployment; submit a pre-extracted `bundle`, "
                "or set CHANAKYA_ENABLE_EXTRACTION=1 to enable keyed extraction"
            ),
        )
    if not (req.source_id and req.source_type):
        raise HTTPException(400, detail="keyed ingest needs both `source_id` and `source_type`")
    client = build_extraction_client()
    if client is None:
        raise HTTPException(
            400,
            detail="no extraction key configured (set GEMINI_API_KEY or ANTHROPIC_API_KEY), or submit a `bundle`",
        )

    # live_rebuild=False: AppState owns the single rebuild + alert-feed swap (avoids a double rebuild).
    result = ingest_document(
        req.raw_text or "",
        source_id=req.source_id,
        source_type=req.source_type,
        config=state.config.snapshot(),
        client=client,
        store=state.evidence,
        file=req.source_id,
        live_rebuild=False,
    )
    fired = state.rebuild_and_swap()
    return IngestResult(
        appended_claim_ids=result.appended_claim_ids,
        rebuilt=True,
        alerts_fired=[alert.observable_id for alert in fired],
    )
