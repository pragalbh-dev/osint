# Session API — FastAPI Layer (JSON view · provenance · HITL writeback · ingest · ask · hot-config · `/health` · SPA seam)

**Wave 2 · depends on RESOLVE, SCORE, ASK, HITL, MONITOR, INGEST (all merged) · no LLM of its own — delegates to ASK/INGEST.**
Read `../00-master-plan.md` §4.8 (endpoints + view-JSON shapes — the contract this session *implements*), §4.3
(rebuild + lens), §4.5 (agent/ask), §4.6 (observables), §4.7 (HITL writeback), §1 invariant 3 (hot-config /
live-`rebuild()`). This session is **THIN**: it exposes the already-merged Wave-1 modules over HTTP. It
re-derives no schema, owns no module logic, and calls no LLM directly — the two LLM-touching endpoints
(`/ask`, `/ingest`) delegate to ASK / INGEST.

## Goal

Stand up the **single deployable artifact**: one FastAPI + Uvicorn process, same-origin, that wires the F0
store + config store + `rebuild()` view to the merged Wave-1 modules and serves the whole system over HTTP —
the rebuilt graph JSON, the provenance drawer, the three HITL writebacks, live ingest, the cited multi-hop
answer, hot-config writes, `/health`, and the built SPA. Because FastAPI serves the SPA same-origin, **CORS
is a non-issue** (`md/07` Backend-API row). Every write path (ingest / HITL / config) runs through the same
in-process `rebuild()` so **nothing requires a restart** (§1 invariant 3). Implements master §4.8 exactly.

## Design docs to read first
`../00-master-plan.md` §4.8 (endpoints + view-JSON models — frozen in F0), §4.3 (`rebuild()` + `apply_lens`),
§4.5 (ask), §4.6 (observable define/arm), §4.7 (HITL `enqueue`/writeback), §1 (invariant 3 hot-config) ·
`../../spine/09-retrieval-and-tools.md` (hot-config / live-`rebuild()` table — no restart; live-ingest vs
extraction) · `../../product/03-data-contracts.md` (**ALL A–H shapes the API serves**: A Claim, B Node/Edge,
C Provenance drawer, D Review-queue item, E Ask answer, F Observable/Alert, G Known Gap, H Config surfaces) ·
`../../md/07-stack.md` (Backend-API row: FastAPI single process serving JSON + built SPA same-origin;
`/health` gated on `rebuild()`; keyless boot).

## Scope (build these)

1. **App factory (single process)** — a `create_app()` in `chanakya/api/` that instantiates the F0 store
   (baked baseline → container-local copy) + live config store, runs the boot `rebuild()`, and holds the
   resulting view. Wire the merged Wave-1 stage functions through F0's `rebuild()` (never re-implement a
   stage). One Uvicorn process; same-origin, so no CORS middleware. Any write endpoint calls `rebuild()`
   in-process and swaps the held view atomically. Response models are **F0's frozen API models** (§4.8,
   `product/03` A–H) — import them, do not define new ones.
2. **`GET /view`** — the rebuilt graph JSON per master §4.2 node/edge shapes (`product/03` **B**): nodes with
   `id+type`, computed `status`, confidence breakdown, freshness, supporting-claims-grouped-by-independence,
   opposing claims, sufficiency, per-type/materiality attrs; edges likewise. Optional `subject`/`lens` query
   param → F0's `apply_lens(view, subject)` scoping (N-hops-from-anchors + materiality filter) so distractors
   don't leak. No LLM, no mutation.
3. **`GET /node/{id}` + `GET /evidence/{id}`** — the node inspector (`product/03` **B**) and the provenance
   drawer (`product/03` **C**): claim clusters **grouped by independence** ("5 sources · 2 independent
   looks"), per-source tier/reliability/bias, integrity flags & penalties, freshness factor, resulting status
   + contradicting evidence. Every listed claim carries its `doc_ref` (file + span/row/frame) so the drawer
   is **one-click-to-exact-source** (claim → `doc_ref`). 404 with an actionable body on unknown id.
4. **`POST /ask`** — delegate to the merged ASK agent; return its cited multi-hop answer (`product/03` **E**):
   the decomposed sub-questions, the ordered per-hop path with **per-hop citations** (real claim IDs), the
   observed-vs-inferred tags (read from each claim's `kind`), and — on the planted gap — the **first-class
   refusal payload** (what's-missing list + `next_coverage_due` + the surfaced Known Gap **G**). The API adds
   no reasoning; it forwards ASK's validated output verbatim.
5. **`POST /ingest`** — delegate to the merged INGEST live lane: `extract → append → rebuild → observable-eval`
   for a raw doc (keyed), **or** append a **pre-extracted claim bundle keyless** (no `ANTHROPIC_API_KEY`
   needed — the reviewer path). Returns the appended claim IDs + any alerts fired on the post-ingest
   `rebuild()`. This and `/ask` are the only LLM-touching endpoints, and only by delegation.
6. **`POST /hitl/{merge|status|alert}`** — call the merged HITL `enqueue(...) → decision → writeback`. The
   writeback appends a decision-log entry; the endpoint then runs `rebuild()` so `effects` apply (propagation
   is structural). Payloads = the three deep cards (`product/03` **D**): merge (accept/reject/split),
   status-override (promote/demote/reject), alert-disposition (real/noise/needs-more). No status is ever set
   directly by the API (G5) — only via the appended decision + `rebuild()`.
7. **`POST /config/*`** — hot-config writes to the live config store, each followed by an in-process
   `rebuild()`, **NO restart** (§1 invariant 3, `spine/09` table): `POST /config/observable` (define/arm an
   observable, §4.6), `POST /config/credibility` (weights / thresholds / half-lives), `POST /config/ontology`
   (extend node/edge/event types). Config surfaces per `product/03` **H**. The write goes to the store, never
   a baked file.
8. **`GET /health`** — returns 200 **only after** the boot `rebuild()` has completed (the readiness gate for
   the tunnel/health check, `md/07`); before that, 503. Cheap, no LLM, no rebuild-on-call.
9. **SPA static seam** — mount `StaticFiles` from `frontend/dist/` if it exists (SPA fallback to `index.html`
   for client routes), else serve a minimal placeholder page. **This is the ONLY seam to the excluded
   frontend track** — the API ships the mount; the SPA build lands via SHIP's Docker Node stage.

## Contracts you IMPLEMENT AGAINST (do not change — an edit here is an F0-amendment PR)
Master §4.8 (endpoint names + request/response models — **frozen in F0's `chanakya/schemas/` API models**),
§4.2 (record + derived-view shapes the JSON carries), §4.3 (`rebuild()` order + `apply_lens`), §4.5 (ASK's
answer/refusal contract), §4.6 (observable declarative spec), §4.7 (HITL `enqueue`/writeback signature), §1
invariant 3 (hot-config). All A–H shapes: `product/03`. Field **names** are whatever F0's API models froze —
reconcile to those, not to `product/03`'s prose.

## Acceptance criteria
Tested with `httpx` against the app (via FastAPI's test client / ASGI transport) over the **seeded baseline +
F0 golden fixtures**, offline (ASK/INGEST LLM calls mocked per §6 recorded transcripts):
- [ ] `GET /health` returns **503 before** the boot `rebuild()` completes and **200 only after** it does.
- [ ] `GET /view` returns the master §4.2 node/edge shapes; body conforms to `product/03` **B**; a
      `?subject=` lens scopes the graph (N-hops + materiality) and drops distractors.
- [ ] `GET /evidence/{id}` renders the provenance drawer (**C**) with independence-grouped clusters, and
      **every claim one-click resolves to a `doc_ref` (claim → doc_ref)**; unknown id → actionable 404.
- [ ] `POST /ask` returns a cited answer (**E**) with per-hop citations and observed-vs-inferred tags on a
      normal query, and the **refusal payload + Known Gap on the planted-gap query** (never a fabricated
      assessment — the non-negotiable).
- [ ] `POST /hitl/status` (demote a confirmed edge) **then** `GET /view` reflects the propagated change with
      **no restart** — status drops, and a re-`POST /ask` changes accordingly (**G12** behaviour over HTTP).
- [ ] `POST /config/observable` to define an observable, **then** `POST /ingest` (pre-extracted bundle)
      **fires it live** in the response — hot-config, **no restart** (§1 invariant 3).
- [ ] All response bodies validate against F0's frozen API models (which realise `product/03` **A–H**).
- [ ] The process boots **keyless** (seeded baseline + pre-extracted bundles) and answers the hero query.
- [ ] `ruff` + `mypy` + `pytest` (incl. all §5 gates) green; the app **imports cleanly** and leaves the build
      deployable; no frozen/shared file edited (or: an F0-amendment PR is filed).

## Owned paths (nothing else)
`chanakya/api/**`, `tests/api/**`.

## Out of scope
The module logic itself — RESOLVE / SCORE / ASK / HITL / MONITOR / INGEST are merged Wave-1 code the API only
*calls*. Docker / compose / GHCR / EC2 / `make` targets (**SHIP**). The React/Vite SPA and its Cytoscape/
Leaflet surfaces (**frontend track**) — the API provides only the `StaticFiles` mount seam. New schemas or
config content (F0 / DATA-C). No LLM logic of the API's own (delegated to ASK/INGEST).

## Worktree lifecycle
`git worktree add ../wt-API -b feat/api` (off latest `main`, after RESOLVE/SCORE/ASK/HITL/MONITOR/INGEST are
merged) → onboard (`CLAUDE.md` → `PROGRESS.md` → this file → the §4.8/§4.3/§4.5/§4.6/§4.7 contracts +
`product/03`) → implement e2e inside owned paths only → PR `[API]` (template in master §8; check G1–G12 +
`ruff`/`mypy`/`pytest`) → **you review & merge** (sole merge authority; the agent does not self-merge) →
`git worktree remove ../wt-API` and delete the branch.
