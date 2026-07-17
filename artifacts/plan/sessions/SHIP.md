# Session SHIP — Production Packaging & Deploy

**Wave 2 · depends on `API` merged (+ `X0`, `DATA-C`, `INGEST`) · NO LLM.**
Read `../00-master-plan.md` §7 (deployment-readiness standards — SHIP *is* the "final image" end of that
section; honour it, don't re-derive) and §4.8 (the API surface the image serves), plus §8 (worktree/PR
workflow). SHIP is the last mile: it **reconciles X0's walking-skeleton `Dockerfile`/`compose`/`deploy/`
into the production image** (master §3: `Dockerfile,compose X0(skeleton) → SHIP(production)`) and fills in
F0's stubbed `Makefile` with real targets (`Makefile F0(skeleton) → SHIP(real targets)`). It is plumbing +
packaging — no module logic, no acceptance assertions.

## Goal

Produce **one multi-stage image** that bakes the whole app — built SPA + seeded SQLite baseline + `config/`
+ corpus + pre-extracted claim bundles — so `docker run` locally is byte-identical to the always-on EC2
box (dev == prod by construction). Publish it to a **public GHCR repo**, run it on EC2 via `docker compose`
+ `cloudflared`, and make **both reviewer paths** work: `docker run ghcr.io/<you>/osint:latest` and
`git clone && make run`. The image **boots keyless**, `GET /health` gates readiness, and rollback is a
previous-GHCR-tag pin.

## Design docs to read first
`md/07-stack` (**Packaging** row, **Hosting** row + "Hosting architecture", **Deploy/distribution** row,
**Secrets** row, "Clean-deploy strategy", the full "Build-stage sequencing" — SHIP is the Stage-5 final
image on that ladder — and "Risks & mitigations") · `md/06-preflight-audit` (the deploy/live-demo items:
M-TIMELINE-1 drop ladder, L-DEMO-1 recorded-fallback) · master `00-master-plan` §7 (deployment-readiness
standards) + §4.8 (API/`/health`). Skim only; SHIP honours these, it does not restate design.

## Scope (build these)

1. **Production multi-stage `Dockerfile`** (extends X0's shape in place). **Node stage** builds the *real*
   SPA seam → static: build `frontend/` to `frontend/dist` **if the frontend track has produced it, else
   fall back to X0's placeholder SPA** — SHIP bakes whatever `dist` exists, never authors the SPA. Pin the
   Node version (build-break risk, `md/07`). **Python stage** installs the **full F0 `pyproject.toml`** (not
   X0's minimal deps) and copies into one image: the built SPA (served by FastAPI `StaticFiles`, §4.8),
   the **seeded SQLite baseline** (INGEST's committed offline-extraction log), `config/*.yaml` (DATA-C),
   the frozen `corpus/**`, and the **pre-extracted claim bundles** (`corpus/scenarios/*/claims/**`, INGEST).
   Runtime writes (ingest/HITL/config) append to a **container-local** copy, resetting to clean baseline on
   restart *by design* (`md/07` "Runtime writes / config"). No managed DB, no volume, no VPC.
2. **Real `Makefile` targets** (fill F0's stubs): `make extract` (extraction over the **raw corpus** → the
   seeded baseline — **the reviewer's optional "extract-from-raw at initial run" mode, keyed** (master §7
   mode 2); also refreshes the committed baseline) · `make build` (rebuild the view) · `make ingest DOC=…`
   (live extract → append → `rebuild()` → observable-eval — the running-app ingest, master §7 mode 3) ·
   `make ask Q="…"` (run the agent) · `make run` (docker build + `docker run --env-file .env -p 8000:8000` —
   boots **keyless from the seeded baseline** by default, the byte-identical image the EC2 box serves) ·
   keep `test`/`lint` working.
3. **GHCR publish** — build + push to a **public** GHCR repo; document the exact `docker run ghcr.io/<you>/
   osint:latest` and `docker compose pull && up -d` commands in `deploy/`.
4. **Production `docker-compose.yml`** (extends X0's) — `image:` from GHCR; `restart: unless-stopped`; port
   **8000 bound to localhost** (no public inbound); `ANTHROPIC_API_KEY` (+ optional `GEMINI_API_KEY`) from
   `.env`/compose env; `cloudflared` as a compose service (or documented host daemon) dialling out.
5. **Keyless boot + secrets** — the seeded baseline + pre-extracted bundles let the app boot and run the
   hero query with **no key**; live extraction is the optional keyed lane. Secrets via `.env`/compose env,
   **never baked into the image, never committed** (rely on the committed `.gitignore`; don't own it).
   Scaffold **Bedrock-via-EC2-instance-role** (`bedrock:InvokeModel` on the inference-profile ARNs, no
   stored secret) as the *design-note prod path* — document it in `deploy/`, don't make it Day-of load-bearing.
6. **Readiness, rollback, fallback ladder** — `GET /health` returns `200` only after `rebuild()` (§4.8);
   `restart: unless-stopped`; **rollback = pin the previous GHCR tag**; keep the fallback ladder (Caddy+domain
   → bare-IP → SSH tunnel; `md/07` "Hosting architecture") **one command away — the image is unchanged in
   every case** (record it in `deploy/`, don't build it).
7. **Recorded demo fallback** — commit a recorded end-to-end **screencast of the scripted worked query on
   the deployed https URL** (under `deploy/`) as the true demo fallback (`md/06` L-DEMO-1; brief-sanctioned).

## Contracts implemented
Master **§7** (deployment-readiness standards) in full, serving the **§4.8** API surface (esp. `/health`
gated on `rebuild()` + the `StaticFiles` SPA seam). SHIP freezes **no** code contract; it takes ownership of
the `Dockerfile`/`compose`/`deploy/` X0 stubbed and the `Makefile` targets F0 stubbed (a sequential handoff,
not a parallel-conflict — those Wave-0 sessions are long merged). No F0-frozen surface is edited (a new
runtime dep would be an F0-amendment PR, master §2 Rule 3).

## Acceptance criteria
- [ ] The **production image builds** (both stages) and bakes the built SPA + seeded SQLite baseline +
      `config/` + corpus + pre-extracted claim bundles into one artifact.
- [ ] `docker run` boots the image **KEYLESS** and `GET /health` returns **`200`** only after `rebuild()`.
- [ ] The **hero query runs end-to-end on the deployed https Cloudflare Tunnel URL**.
- [ ] `make run` produces the **byte-identical image the EC2 box serves** (dev == prod).
- [ ] **Both reviewer paths work:** `docker run ghcr.io/<you>/osint:latest` and `git clone && make run`.
- [ ] **Rollback to a previous GHCR tag is verified** (pull the prior tag → serves cleanly).
- [ ] `ANTHROPIC_API_KEY` (+ optional `GEMINI_API_KEY`) stays gitignored and out of the image/logs.
- [ ] A recorded end-to-end screencast of the scripted worked query on the deployed URL is committed.

## Owned paths (nothing else)
`Dockerfile`, `docker-compose.yml` (extend X0's → production), `Makefile` (real targets, over F0's skeleton),
`deploy/**` (GHCR/EC2/`cloudflared` commands, Bedrock-instance-role note, fallback ladder, recorded
screencast). **Depends on:** `API` (merged) + `X0`, `DATA-C`, `INGEST`. **LLM:** no.

## Out of scope
The **SPA implementation** (frontend track — SHIP only bakes whatever `frontend/dist` exists, else X0's
placeholder). The **module logic** (Wave 1 — RESOLVE/SCORE/MONITOR/ASK/HITL/INGEST fill their own dirs).
The **acceptance assertions** (EVAL owns the spine-gate + demo-flex harness). The API app body (`API`).
Authoring config *content* (DATA-C) or seed bundles (INGEST).

## Worktree lifecycle
`git worktree add ../wt-SHIP -b feat/ship` → implement → PR `[SHIP]` → **you review & merge** → you update
`PROGRESS.md` → `git worktree remove ../wt-SHIP`. Starts only after `API` is on `main` (with `X0`, `DATA-C`,
`INGEST` merged); rebase onto `main` on every sibling merge (clean given disjoint ownership).
