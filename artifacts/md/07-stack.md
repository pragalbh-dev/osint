# Stack Recommendation & AWS Deployment Plan

**What this is.** The recommended stack for the Chanakya OSINT demo, the AWS hosting architecture (you
have an AWS account), a clean-deploy strategy, and a build-stage sequencing where **each stage ends
independently deployable** — so the final submission deploy is a non-event, not a big-bang integration.
Produced by two independent stack proposals (minimize-moving-parts vs most-credible) reconciled through a
deployment-focused critique. *As of 2026-07-16. Deadline 20 Jul 2026, 12:00.*

**The one idea that makes everything else clean.** A **single Docker image** — FastAPI serving both the
JSON API *and* the built React SPA as static files, with a seeded SQLite baseline baked in — run with
`docker compose` on **one always-on EC2 instance**, reached via a **Cloudflare Tunnel** (free TLS + a real
https URL, no domain, no open inbound ports). All state is file-based in-image, so there is deliberately
**no managed database and no VPC wiring** — that absence is the whole design. `docker run` locally is
byte-identical to what the EC2 box runs, so a deploy is a pure image pull/swap — and the same image is what
reviewers run (prebuilt from GHCR, or built locally via `make run`).

> **Corrections & updates (2026-07-17):**
> - **Env var is `ANTHROPIC_API_KEY`** (reverted to the SDK default — the earlier `CLAUDE_API_KEY` note is
>   dropped). An optional **`GEMINI_API_KEY`** enables Gemini as a secondary extraction provider.
> - **Determinism is de-prioritised** (per `spine/09`): Opus 4.8 rejects `temperature`/`top_p`/`top_k`
>   (HTTP 400), so we simply don't send sampling params — but we no longer *lean* on determinism to cut
>   capability. The frozen baseline + tested queries reproduce; the live-ingestion lane is fresh by design;
>   a tight extraction prompt is "deterministic enough"; a recorded hero-trace is the network-safety
>   fallback for the graded Ask beat.
> - **Extraction is no longer frozen-only** — it's a **live runtime capability** (see the Extraction row);
>   the seeded SQLite baseline still ships so the app boots keyless.
> - **Hosting is EC2 + Cloudflare Tunnel, not App Runner** (user's call) — see the Hosting row.
> - *(Already fixed: the missing `.gitignore` that made `.env` committable.)*

---

## Recommended stack (one choice per layer)

| Layer | Choice | Why | Main alternative |
|---|---|---|---|
| **Evidence + decision logs** (source of truth) | **SQLite**, two append-only tables, baked read-only into the image; runtime HITL writes append to a container-local copy | `spine/08` §1 makes the knowledge layer a pure function of the logs; append-only SQLite gives traceability, reversible merges, retraction, HITL propagation for free, zero ops, travels inside the one artifact | Postgres/RDS — only for durable multi-user writes, which the UX brief §8 rules out; adds VPC/subnet/SG/secret surface |
| **Knowledge view / graph** | **NetworkX in-memory**, rebuilt from the logs via `rebuild()` on every change, serialized to JSON for the frontend | At ~15–25 entities a full rebuild is ms; free multi-hop traversal for the agent, trivial Cytoscape export, nodes carry claim IDs so traceability is structural | Neo4j/KùzuDB — the documented >10⁶-edge scale path behind the same view interface; a second service for zero graded benefit at n=25. Design-note only |
| **Extraction / ingestion** | **LLM-only, available BOTH offline (seeded baseline) AND live at ingest** (Claude function-calling → the one claim schema for every source; Gemini optional; vision only if real images added). No per-source parsers (`spine/02`). **Extract-raw guardrail:** extracts *stated* claims incl. stated alias/`same-as`, never resolves/normalizes the unstated (anti-circularity/messiness). **Live ingestion is always available** — `make ingest` / a UI action runs extract → append → `rebuild()` → observable-eval; keyless reviewers ingest **pre-extracted claim bundles** instead (corpus ships raw + pre-extracted) | Makes the *monitoring* axis real (ingest a doc → an observable fires live) and lets reviewers run extraction themselves; the seeded baseline still gives a keyless boot + reproducible graded beats. The LLM runs *upstream* of the append, so the **`rebuild()` invariant (no LLM inside rebuild) holds** and the view stays deterministic | Frozen-only extraction — rejected (can't demonstrate live ingest→alert; was the old plan). Deterministic per-source parsers = production/roadmap |
| **Embeddings / search** | **None in the runtime.** Entity lookup = alias table + **BM25 + fuzzy (`rapidfuzz`)**; the agent navigates by graph traversal (`spine/09`) | The reason is **scale + signal, not determinism** (embeddings are deterministic): at hundreds of curated nodes there's nothing to fuzzily recall that alias+BM25+fuzzy miss, and the discriminating OSINT signal is **relational**, not semantic (a front company is designed not to look like its parent) | A local sentence-transformer as one *offline* resolution candidate-gen signal; build-time only, never in the runtime image (roadmap) |
| **LLM + VLM provider** | **Anthropic Claude API direct**, `claude-opus-4-8`, for the runtime Ask agent (+ offline extraction). Scaffold a Bedrock (instance-role → `bedrock:InvokeModel`, no stored key) switch as the *ratified prod* path | The repo key unblocks Day-0 with no approval you don't control; Bedrock's no-secret / data-in-account story is the defence-appropriate design-note narrative — present it as prod, don't make it Day-0 load-bearing | Bedrock-via-IAM as Day-0 provider — cleaner secret story but gated on per-account/per-region model-access approval that can lag; request access Day 0 but don't block on it |
| **Agent loop / retrieval** | **Bounded ReAct tool-calling loop** in Python, no framework; **~7 namespaced `graph_*` tools** + materiality precomputed in `rebuild()` + a mandatory **entailment-based** citation validator + first-class refusal. Full design in `spine/09`; research basis in `md/14`. Live loop primary, recorded hero-trace as network-safety fallback | The graded thing is citation-validated no-naked-assertions discipline + honest refusal, not orchestration. Bounds (hop≤4, top-k≈3, sufficiency-termination) keep it reproducible; **no `temperature` param** (400 on Opus 4.8) | LangGraph/LlamaIndex — opaque control flow, heavy deps, harder to defend line-by-line. Microsoft GraphRAG / vector RAG / embeddings — provenance-corrosive or unneeded at our scale (`md/14`). Rejected |
| **Backend API** | **FastAPI, single Uvicorn process** — serves the rebuilt view as JSON, provenance lookups, the 3 HITL writeback endpoints, the Ask endpoint, `/health` gated on `rebuild()` completion, AND the built SPA via `StaticFiles` | `tools/` is already Python → one language end to end; one process = one artifact, one port, same-origin (**CORS is a non-issue**); `/health` after `rebuild()` gives the tunnel/health check a real readiness gate. This same-origin single-process choice is what makes the clean deploy possible | Separate Node/Express API or S3+CloudFront static host — splits the deploy into two artifacts, reintroduces CORS + build coordination. Avoid |
| **Frontend** | **React + Vite + TypeScript SPA** built to static assets; **Tailwind + shadcn/ui** (copy-in Radix primitives) for the dense analyst-terminal aesthetic; light state via TanStack Query + Zustand | UX brief locks React/Vite and asks for a calm, dense "finance-terminal" feel; Tailwind tokens are the fastest route to the status × freshness × source-tier visual language (the brief's #1 deliverable); shadcn is copy-in (no heavy runtime dep); static build folds into the one Python image | Headless primitives + hand-rolled CSS (lower build-break risk, slower to polish) or MUI/Ant (heavier, fights the aesthetic). Next.js rejected — a second Node runtime for SSR the demo doesn't need |
| **Map** | **Leaflet with tiles VENDORED locally** (bundled raster/mbtiles for the Pakistan AOI, or a single georeferenced static basemap via `ImageOverlay`); pins absolutely placed, status-coded, with the scripted relocation animation | Map is explicitly ungraded (`08` §4) → optimize purely for zero live-demo risk: vendoring removes the external-network/CSP dependency so a slow/blocked tile host can't break a hero beat over conference wifi | Live Carto/OSM tiles — a conference-wifi dependency on the graded call for no benefit. A muted static SVG region is an even simpler fallback |
| **Graph-viz** | **Cytoscape.js** (via `react-cytoscapejs`) | Named in `08` §5; purpose-built for node-link at this scale, automatic dagre/cose layout, click-through selection, path-highlight for the multi-hop answer, data-driven stylesheet encoding status→fill / freshness→border / tier→icon + chokepoint emphasis | React Flow — nicer bespoke node visuals but you hand-manage layout; d3-force — most code |
| **Packaging** | **One multi-stage Dockerfile** — Node stage builds the Vite SPA to static; Python stage installs FastAPI + copies the built SPA + seeded SQLite logs + `config/` + corpus into one image. Identical image runs locally and on the EC2 box | A single deployable artifact with dev/prod parity is the core of the clean deploy — `docker run` locally is byte-identical to the EC2 box, eliminating integration risk; view rebuilt in-memory at boot → no DB migration, no volume coordination | Separate FE/BE images or a non-containerized zip — reintroduces multi-artifact coordination + env drift |
| **Hosting** | **One always-on EC2 instance** (e.g. t3.small/medium), Docker + **`docker compose`** with `restart: unless-stopped`; reached via a **Cloudflare Tunnel** (`cloudflared`) → free TLS + a real https URL, no domain, no open inbound ports | User's call. Always-on → no cold start on the graded call; single analyst → the in-image SQLite write model is safe; the tunnel removes DNS/cert setup and keeps the box's ports closed. All state in-image → no managed DB, no VPC | App Runner / Lightsail (managed URL, but adds ECR/IAM Day-0 setup); Caddy auto-TLS (needs a domain); bare HTTP on the public IP (no TLS). EC2 keeps the deploy under our control and byte-identical to what reviewers run |
| **Deploy / distribution** | **Both reviewer paths.** (1) fast — `docker run ghcr.io/<you>/osint:latest` from a **prebuilt public GHCR image**; (2) transparent — `git clone && make run` (local multi-stage build). Our EC2: `docker compose pull && up -d` (image from GHCR) + `cloudflared`. `make run` = build + `docker run --env-file .env -p 8000:8000` | It's a code submission, so reviewers get the source *and* a one-command image; `make {extract,build,ingest,ask,run}` exposes each stage on their end | A thin Terraform/CI layer (GitHub Actions → GHCR on tag push) is a nice bonus if time — design-note by default |
| **Secrets** | **`ANTHROPIC_API_KEY`** (+ optional **`GEMINI_API_KEY`**), via `.env` on the box (gitignored) or a `docker compose` env var; never baked into the image or client bundle. `.gitignore` with `.env` committed FIRST *(done)*. Keyless still boots (frozen baseline + pre-extracted ingest) | One credential path per environment; image stays clean and shareable. **Bedrock via an EC2 instance-role → `bedrock:InvokeModel`** is the no-stored-secret prod endgame for the design note (cleaner on EC2 than SSM) | Hardcoding/baking the key or committing `.env` (disqualifying); SSM/Secrets Manager (unneeded off App Runner) |
| **Runtime writes / config** | **Live in-process state, no restart ever.** Boot reads the baked baseline → `rebuild()` → serves; runtime **ingests, HITL adjudications, and config edits (observables, credibility weights, thresholds, ontology types)** append/write to a **container-local live config+log store** the process reads on each `rebuild()`; a restart resets to the clean baseline (an intended feature for repeatable demos) | The product rule (`spine/09`): **nothing a user does in-app requires a restart** — `rebuild()` is a live in-process op (ms at demo scale), config lives in a store the UI writes to, not a baked file. Always-on EC2 keeps the session warm | A durable multi-user store (Postgres/EFS) — reintroduces DB/VPC surface; single-analyst demo doesn't need it. Design-note |

---

## Hosting architecture (concrete)

Build one multi-stage Docker image (Node builds the React/Vite SPA to static; a Python stage runs FastAPI
+ Uvicorn serving the static bundle, the JSON view API, the HITL writeback endpoints, the **ingest
endpoint**, the Ask agent endpoint, and `/health`, with the seeded SQLite baseline + `config/` + corpus
baked in). Publish it to a **public GHCR repo** and run it on **one always-on EC2 instance** via
`docker compose` (`restart: unless-stopped`, port 8000 bound to localhost). A **Cloudflare Tunnel**
(`cloudflared`, run as a second compose service or host daemon) exposes it as a real `https://…` URL with
managed TLS — **no domain, no DNS, no open inbound security-group ports** (the tunnel dials out). Reviewers
reach the same URL; the box's only inbound rule is SSH (or SSM Session Manager).

Because all state is file-based SQLite baked into the image + a container-local live store, there is
deliberately **no managed database and no VPC wiring** — that absence is the design. The secret
`ANTHROPIC_API_KEY` (+ optional `GEMINI_API_KEY`) is injected via `.env` / a compose env var; the ratified
production path swaps the key for an **EC2 instance-role** granted `bedrock:InvokeModel` on the Claude
cross-region inference-profile ARNs (no stored secret, data in-account).

**Fallback ladder if the tunnel snags:** Caddy reverse-proxy with auto-TLS (needs a domain) → bare HTTP on
the EC2 public IP for the call → an SSH tunnel. The image is unchanged in every case.

---

## Clean-deploy strategy

The single container is the unit of deploy and **dev == prod by construction**: `make run` runs the
byte-identical image the EC2 box serves, so a deploy is a pure image pull/swap, never a first-time
integration.

**The one rule that makes the final deploy clean:** on **Day 0, before any feature work**, build the
multi-stage image with a trivial FastAPI route + a placeholder SPA, push to **GHCR**, run it on the EC2 box
via `docker compose` + `cloudflared`, and confirm the public https URL loads. This pays down the entire
image/registry/tunnel/TLS/secret cost while failures are cheap; from then on the deploy is fixed and
identical at every stage.

Specifics:
- **SQLite persistence** — the knowledge view is rebuilt in-memory from the baked baseline at boot, so
  there is no DB migration and no persistent volume; runtime ingests / HITL writes / config edits go to a
  container-local live store and reset-to-clean on restart *by design* (always-on EC2 keeps it warm) → no
  EFS/VPC.
- **Secrets** — `.gitignore` with `.env` committed first *(done)*; `ANTHROPIC_API_KEY` (+ optional
  `GEMINI_API_KEY`) stays out of the image and git, injected via `.env` / a compose env var; EC2
  instance-role → Bedrock no-secret path scaffolded.
- **HTTPS** — the Cloudflare Tunnel terminates TLS and issues the public URL automatically; nothing to
  configure, no open inbound ports.
- **CORS** — a non-issue: FastAPI serves the SPA same-origin, so there's no cross-origin call and no second
  static host.
- **Static frontend** — the Vite build is baked into the image and served by FastAPI `StaticFiles`; no Node
  at runtime, no S3/CloudFront.
- **Readiness** — `/health` returns 200 only after `rebuild()` completes, gating post-deploy verification.

The final submission deploy is just the last image push + `docker compose pull && up -d` of a fully-featured
image — a non-event, because the pipeline has carried real weight since Day 0. Rollback = pin the previous
GHCR tag.

---

## Build-stage sequencing (each stage ends independently deployable)

- **Stage 0 (Day 0, ~½ day) — Walking skeleton.** Commit `.gitignore` *(done)*, a multi-stage Dockerfile
  with a trivial FastAPI route + `/health` + placeholder SPA, push to **GHCR**, run on the **EC2 box via
  `docker compose` + `cloudflared`** with `ANTHROPIC_API_KEY` from `.env`. **Deployable:** a hosted "it
  boots" page on an https tunnel URL. Proves the entire image/registry/tunnel/TLS/secret pipeline while
  failures are cheap. *(Highest-leverage schedule insurance — the one real risk is NOT doing this first.)*
- **Stage 1 (Day 1) — Store + live `rebuild()` + JSON view API + ingest lane.** Seed the baseline SQLite
  claims (offline extraction, baked in); implement `rebuild()` (resolution → credibility → status →
  **materiality precompute** → NetworkX) as a **live in-process op** triggered by ingest/decision/config
  writes (not boot-only), reading from a **live config store**; expose the view as JSON + an **ingest
  endpoint/CLI** + a post-`rebuild()` **observable evaluator**. SPA renders the scored graph read-only.
  **Test `rebuild()` reproducibility (same logs+config → identical view) before any UI sits on top.**
  **Deployable:** a hosted app serving the real, scored graph that already accepts a live ingest.
  *(Architectural note: live `rebuild()` + the config store + the observable evaluator are Stage-1 plumbing
  — the hot-config / no-restart / user-defined-observable model of `spine/09` depends on them, even though
  the hero observable's content lands at Stage 5.)*
- **Stage 2 (Day 1–2) — The three read surfaces + visual language.** Cytoscape graph explorer, Leaflet map
  (vendored tiles), provenance drawer with one-click-to-source and the "5 sources / 2 independent looks"
  grouping; wire the status × freshness × source-tier visual language (**timebox this — top schedule risk
  after `rebuild()`**). **Deployable:** demonstrates traceability, confirmed-vs-probable, and stale.
- **Stage 3 (Day 2–3) — The Ask view (graded centerpiece).** Deterministic tool-calling agent (**NO
  `temperature` param; `effort: low`**) + citation validator + sufficiency templates + first-class Known
  Gap, running the worked query end-to-end with observed-vs-inferred rendering and the explicit "insufficient
  evidence to assess" refusal on the planted gap. **The disqualifying line (explicit insufficient-evidence +
  zero fabrication, enforced by the citation validator) is the Stage-3 acceptance test, not polish.** Live
  loop primary, recorded known-good trace as fallback. **Deployable:** the centerpiece works.
- **Stage 4 (Day 3) — HITL review queue.** The 3 wired control points (merge adjudication, confirmed↔probable
  override, alert disposition) with writeback that appends to the decision log and re-runs `rebuild()`, so a
  decision visibly changes the graph and the next answer; plus the M4 recycled-photo integrity penalty.
  **Deployable:** human-in-the-loop is real and propagating.
- **Stage 5 (Day 4) — The relocation observable + choreography.** The Rawalpindi→Rahwali occupancy
  state-change beat, now **driven live by `make ingest` / a UI ingest** (not a scripted reveal) — single
  pass → probable via decoy cap, second independent look → confirmed, `supersedes` retires the old position
  which greys to stale, pin moves — the alert firing + disposition, and visual-language polish for the full
  hero flow. Reviewers can also define their own observable (`spine/09`). **Deployable:** the complete hero
  flow + a live ingest→alert loop.

**If time runs out, the last deployed stage is always a coherent hosted demo — never a broken integration.**

---

## Risks & mitigations

- **[CORRECTNESS]** Opus 4.8 rejects `temperature`/`top_p`/`top_k` (HTTP 400) → don't send sampling params.
  Determinism is de-prioritised (`spine/09`); the frozen baseline + tested queries reproduce and a recorded
  hero-trace is the network-safety fallback for the graded Ask beat. (`08` §1 property 5 / §4 doc-07 row
  still to be reconciled to this.)
- **[SECRETS, blocking — FIXED]** No `.gitignore` meant `.env` was only untracked → `git add -A` would
  commit the API key. `.gitignore` added this session; inject `ANTHROPIC_API_KEY` via `.env` / a compose
  env var (never committed).
- **[BUILDABILITY]** Use `ANTHROPIC_API_KEY` (the SDK default) — the zero-arg `Anthropic()` client reads it
  automatically. Optional `GEMINI_API_KEY` for the secondary provider. Keep both out of git/image.
- **[SCHEDULE, highest-leverage]** First-time GHCR/EC2/`cloudflared` setup can eat time → do the entire
  Stage-0 deploy (image → GHCR → compose on EC2 → tunnel URL loads) before any feature work, when failures
  are cheap.
- **[LIVE-DEMO, EC2]** The box or tunnel could drop → `docker compose` `restart: unless-stopped` + run
  `cloudflared` as a managed service; keep the fallback ladder (Caddy+domain / bare-IP / SSH tunnel) one
  command away — the image is identical in every case.
- **[CRITICAL PATH]** `rebuild()`-on-write is the load-bearing demo mechanism (HITL propagation,
  supersedes-vs-contradicts) → front-load it; test frozen-logs→identical-view before building UI on top.
- **[GRADED-AXIS]** A purely cached hero answer reads as canned if a grader asks a live follow-up → keep the
  real tool-calling loop as the primary path with the recorded trace only as a fallback.
- **[IF BEDROCK]** Model-access approval is per-account/per-region and can lag (request Day 0); current-gen
  Claude on Bedrock is invoked via cross-region inference profiles, so the instance-role IAM must permit the
  inference-profile ARNs — a policy scoped to a single model ARN silently 403s at runtime. Bedrock also
  lacks automatic prompt caching / Batches / Files / Models APIs — keep the runtime to core Messages +
  tool-use + vision.
- **[SCHEDULE]** The status × freshness × source-tier visual language is design-hard ("Christmas tree" risk)
  and the top schedule risk after `rebuild()` → legend-tile-first; encode in fill+border+icon (not color
  alone — colorblind + washed-out projector); timebox it.
- **[BUILD]** React/Vite is a Node toolchain that can break the image build (dep/lockfile drift) → pin Node
  in the multi-stage Dockerfile, keep FE deps lean, rely on the SPA being static at runtime.
- **[LIVE-DEMO]** Any external network call on the graded call is a failure mode → vendored/static map
  basemap (zero runtime tile fetch); never put a live LLM round-trip on a graded beat's critical path
  without the recorded-trace fallback.
- **[COST]** An always-on EC2 (t3.small/medium) bills continuously for the ~4-day window (small); token cost
  is modest now that extraction can run live on ingest (still bounded — only ingested docs + Ask); no RDS =
  no VPC/NAT surprise. Accept the instance charge — it's the intended cost of no cold-start.

---

## Open stack choices

**Resolved this session (2026-07-17):**
- **Hosting** → always-on **EC2 + Cloudflare Tunnel** (was App Runner).
- **Reviewer deploy** → **both** — prebuilt GHCR image (`docker run …`) *and* `git clone && make run`.
- **Provider** → direct **`ANTHROPIC_API_KEY`** for the demo (+ optional `GEMINI_API_KEY`); **Bedrock via
  EC2 instance-role** = the no-secret prod path in the design note.
- **Extraction / determinism** → LLM-only, **live ingestion available** (not frozen-only); determinism
  de-prioritised (`spine/09`).
- **Embeddings** → none in runtime (alias + BM25 + fuzzy).
- **Retrieval / agent** → bounded ReAct tool-calling loop, ~7 tools, `spine/09`.

**Still open (your call):**
1. **Frontend component strategy** — Tailwind + shadcn/ui copy-in (best hits the dense analyst-terminal
   aesthetic; slightly larger Node build surface) vs headless primitives + hand-rolled CSS (lowest
   build-break risk, slower to polish). A taste-and-time call; both fold into the one static image.
   *Default: shadcn.*
2. **Map fallback depth** (all zero-network; map is ungraded) — vendored raster/mbtiles vs a single
   georeferenced static basemap (`ImageOverlay`) vs a muted static SVG region. Pick by how much map polish
   is worth against the relocation animation.
3. **Thin CI layer** (a GitHub Actions job that builds + pushes to GHCR on a tag) as a discipline bonus —
   only if Stage-0 is solid with time to spare. Roadmap / design-note by default.
