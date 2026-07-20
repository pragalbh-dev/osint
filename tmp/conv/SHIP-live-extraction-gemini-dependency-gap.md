# SHIP: shipped image is missing `google-genai` — live extraction 500s if GEMINI_API_KEY is set

**From:** README + EC2 shipping task (docs/readme-and-deploy), 2026-07-20. Not fixed here —
this session was scoped to docs + deploy, explicitly no logic changes.

**What.** `chanakya/ingest/client.py` tries Gemini first whenever `GEMINI_API_KEY` is
present (Anthropic is the fallback), but `google-genai` is an optional extra
(`backend/pyproject.toml` → `[project.optional-dependencies] gemini = ["google-genai>=0.3"]`)
that the production `Dockerfile` never installs. Confirmed against the real built image
(`ghcr.io/pragalbh-dev/osint:latest`): booting with both keys set and
`CHANAKYA_ENABLE_EXTRACTION=1`, then POSTing a document to `/ingest {raw_text, source_id,
source_type}`, 500s with `ModuleNotFoundError: No module named 'google'`.

**Blast radius.** Only the *live, in-app* keyed-extraction path (the "or extract a
document" box in the Documents rail, LIVE mode). `make extract` (dev target, own venv) hits
the same gap — `make install` doesn't pull the `[gemini]` extra either — but that target
should never be run against the graded corpus anyway (see
`tmp/keyed-verification/SUMMARY.md` §2: two independent re-extractions of the same three
documents produced different bundles and broke hop 2 of the flagship query — a separate,
more serious finding).

**Workaround (no code change, verified working):** don't set `GEMINI_API_KEY` for
instructors — only `ANTHROPIC_API_KEY`. With Gemini's key absent, the client falls back to
Anthropic and live extraction works (200, claims appended). `GEMINI_API_KEY` has no
instructor-relevant purpose per `deploy/README.md`'s own secrets table (dev-only, for
`make extract`), so this is a clean, no-tradeoff fix for the README, not a compromise.

**Real fix, whenever someone owns `Dockerfile`/`pyproject.toml` again:** either bundle
`google-genai` in the image's base install, or reorder `client.py` to prefer Anthropic when
both keys are present (arguably better regardless, since Anthropic is the key path that's
actually tested end-to-end).

**The README for this task documents the workaround** (hand out `ANTHROPIC_API_KEY` only)
rather than waiting on this fix.
