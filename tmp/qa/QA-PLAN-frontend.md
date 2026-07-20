# QA Plan — Chanakya Frontend (demo-mode SPA)

**For use with `/qa-only`.** This is a *scoped* plan: it tests each distinct code path **once**
and deliberately skips overlapping flows. Follow the SKIP list and the SCOPE-NOTES list as
strictly as the test cases — reporting a deliberately-inert element as a "bug" is the failure
mode this plan exists to prevent.

---

## 0. Context & constraints (read before testing)

- **App under test:** React/Vite SPA, single fixed shell, **no router** — "screens" are
  state-driven panel swaps, not routes.
- **Run it:** `cd frontend && npm install && npm run dev` → **http://localhost:5173**
  (worktree: **`wt-EVAL`**, branch `fix/phase4-derived-and-surfaces` — the frontend merged to main
  in PR #31 and now lives alongside the backend). Port 5173 per `vite.config.ts`.
- **TWO passes, both reachable.** ⚠️ *This section was rewritten 2026-07-20 — the previous version
  said live mode was unreachable dead code. That is no longer true and following it would skip the
  newest work entirely.*
  - **Pass A — demo mode (default).** App boots `mode='demo'` and renders from a frozen scenario
    (`src/demo/scenario.ts`) + local state. Deterministic; no backend required.
  - **Pass B — live mode (NEW, must be tested).** Reachable via the **`?mode=live`** deep-link
    (`main.tsx:42`); live sync is wired through `store/workbench.ts`, `App.tsx`, `Rail.tsx`,
    `api/viewmodel.ts`, `api/hooks.ts`. **The backend has 8 implemented routes**
    (`view`, `ask`, `ingest`, `hitl`, `config`, `node`, `lookup`, `health`), so live mode needs a
    running backend — see §2B for how to start it.
- **Demo and live legitimately DIVERGE, and that is not a bug.** The frozen demo scenario shows the
  intended end-state; live mode shows the real rebuilt graph, which is honestly weaker in places
  (see T5/T5L). Do not file a live-vs-demo difference as a defect unless §4 says so.
- **Deep-link params are your main efficiency lever.** `main.tsx` applies URL params once
  before first render, so you can jump straight to any state instead of replaying clicks:
  `?panel=<hero|gaps|cred|watch>`, `?card=<merge|override|alert>`, `?stage=<map|graph>`,
  `?ingest=d18,d19`, `?drawer=1`, `?merge=1`, `?expanded=<chip>`. Use these to isolate each
  test. (Confirm exact names against `main.tsx:8-41` on first load.)

## 1. Testing philosophy for this run

**Cover distinct code paths, not user flows.** Many flows re-run the same logic; testing the
flow list end-to-end would burn compute re-verifying shared code. The cases below are chosen so
that together they touch every distinct path with near-zero repetition. Each case names what it
covers and what it therefore makes redundant.

**Priority ladder (report findings tagged with these):**
- **P0 — the non-negotiables.** One-click-to-source (**including from a fired alert** — new),
  "insufficient evidence" refusal, the confirmed-vs-probable visual separation, and
  **`stale` reading differently from `insufficient`** (new). A failure here is disqualifying for the
  product's purpose — treat as blocker.
- **P1 — core interactions.** Ingest choreography + status transitions, hero cited answer,
  review-queue decision + propagation, credibility recompute.
- **P2 — polish.** Back-navigation, read-only views, double-click idempotency, canvas/pixel drift.

---

## 2. Test cases (run in this order; each is scoped to a distinct path)

### T1 — Boot & shell integrity  · P1
- **Goal:** app loads clean; the 4-zone shell (Rail / Stage / Panel=Zero / AskBar) renders; Map
  is the default Stage view; **zero console errors** on load.
- **Steps:** open `/`. Capture console. Screenshot full shell.
- **Expect:** Rail (240px) with Subject / Review (badge=3) / Watching / Documents / Credibility;
  Stage on Map with AOI=Pakistan + 5 pins; ZeroView showing 3 target-query affordances; AskBar
  present with one "Ask" button.
- **Covers baseline render for every later case** (shell never unmounts).

### T2 — Ingest choreography → status transitions (Map **and** Graph together)  · P1
> This one sequence is the backbone. It validates the ingest overlay, **both** Map and Graph
> transitions (they read the *same* derived state), the Drawer's evolving content, and the
> confirmed/probable *transitions* — so none of those need separate flow tests.
- **Steps:**
  1. From clean state, Rail → Documents → click **d18** (or deep-link `?ingest=d18`). **Wait for
     the end-state (~3.3s of scripted timers) before asserting** — do not assert immediately.
  2. Assert: Rawalpindi → **stale**, Rahwali → **probable**, on **both** Map and Graph. A
     "moved →"/"replaced by →" dashed supersede link appears (supersede, not contradict).
  3. Ingest **d19** → Rahwali → **confirmed** (second, discipline-independent ELINT look lifts it);
     Drawer (if open) gains "Look 2".
  4. Ingest **d20** → Drawer gains a "Since then" spoof note.
- **Observe:** Map pins are real DOM — assert via `data-ring` / `data-core` / `data-caption`
  attributes on the `L.divIcon` markers. Graph is **canvas** — assert via **screenshot** at each
  step (or `cy.$id(...)` through `page.evaluate`), never DOM selectors.
- **Also (P2):** double-click d18 / drop a second doc while a trace is in flight → **must be a
  no-op** (`startIngest` is guarded). Confirm state doesn't corrupt.
- **Makes redundant:** any separate "test Map status" vs "test Graph status" flow; any separate
  relocation/freshness flow.

### T3 — Provenance drawer / one-click-to-source  · **P0 (non-negotiable #1)**
- **Goal:** a claim traces in one click to its **exact** source (dates + verbatim quote), and the
  M4 integrity guard blocks fabricated-but-corroborated material.
- **Steps:**
  1. From clean state, click the **Rahwali** map pin → Drawer opens.
  2. Verify headline "N sources · M looks", verdict + reason, Look 1 (imagery, expandable).
  3. Click a citation chip (**d18** or **d11**) → it expands **in place** to the L2 view: **three
     dates + the exact quote**. This is the one-click-to-source assertion.
  4. **M4 check:** the "Social imagery" section is **integrity-flagged** (recycled/parade photo,
     reshares) and **does not** promote the node to confirmed despite the corroboration count —
     it collapses to "adds no look".
  5. Smoke-only: confirm the **Graph node tap** and the **ZeroView provenance affordance** open
     the *same* Drawer (they call the same `select('rahwali')`). One click each — **do not**
     re-verify drawer contents (identical path).
- **Observe:** Drawer is DOM — use selectors for text/quote assertions.
- **Makes redundant:** testing provenance from all three entry points in full.

### T4 — Honest refusal / "insufficient evidence"  · **P0 (non-negotiable #2)**
- **Goal:** where evidence is absent, the system **refuses explicitly** and names the gap.
- **Steps:** ZeroView/AskBar → "What do we not know here?" (or deep-link `?panel=gaps`).
- **Expect:** GapsView renders **three** refusal blocks; the first shows the literal verdict
  **"Insufficient evidence to assess."** and names *what is missing + when next coverage is due*;
  the others show the "probable-max ceiling" and the "never-observable boundary" (hatch). Confirm
  the same gap appears structurally as the **TEL pin** (hollow dashed rect) on Map / `.gap` node
  on Graph.
- **This is the disqualifying-if-broken case — verify the wording literally.**

### T5 — Hero cited answer  · P1
- **Steps:** AskBar → "Ask" (fires the frozen hero query), or `?panel=hero`. **Wait for the
  staggered reveal to finish** (~120ms/step × hops) before asserting.
- **Expect:** the 4-hop numbered walk (based-at → inducted-into → imported-by →
  supplies-component/manufactures → chokepoint), a dashed **"Inferred"** wall, and citation chips
  present per hop.
- **Scope note:** the chips here are **display-only (no onClick) in this build** — see SCOPE NOTES;
  do **not** file "chip does nothing" as a bug.
- **⚠️ Demo-mode only.** This 4-hop answer is the *frozen* scenario. In live mode the same query
  **refuses** — see **T5L**. That is correct behaviour, not a regression.

### T6 — Review queue: decision plumbing (once) + Merge fan-out (unique)  · P1
> All three review cards share one decision mechanism; test it **once**, on Merge, because Merge
> is the *only* card whose decision has a second, cross-screen effect.
- **Steps (Merge — full):** Rail → Review (badge=3) → expand → open **Merge** card (HQ-9/P vs
  HQ-9BE; shows matched-on / differs-on). Pick any option →
  - badge **3 → 2**; ZeroView shows the **"resolved · reversible"** banner;
  - **cross-screen:** next visit to HeroAnswer shows the hop-2 **"Revised"** box (this is Merge's
    unique fan-out via `selHeroRevised`).
- **Steps (Override, Alert — payload-only):** open each card; verify its **unique content**
  renders (Override = Karachi-East contradiction, against-lines; Alert = relocation triage
  severity ramp) and that a decision produces the ZeroView banner. **Do not** re-verify the
  badge/reset/banner plumbing — T6-Merge already covered it.
- **Makes redundant:** running all three review flows end-to-end.

### T7 — Credibility rubric (self-contained)  · P1
- **Steps:** Rail → Credibility (or `?panel=cred`). Drag a weight slider.
- **Expect:** the Karachi-East verdict and the two source score bars **live-recompute** as the
  weights change. Fully isolated — nothing else feeds it.

### T8 — Confirmed-vs-probable visual grammar  · **P0 (non-negotiable #3)**
- **Goal:** "dashed = probable/provisional · solid = confirmed/settled" is applied consistently.
- **Steps:**
  1. Best single regression point: verify the rule once on a **DOM** consumer (StatusSwatch in
     Drawer or CredView) — this is the shared `util.ts`/`StatusSwatch` implementation.
  2. **Drift check:** separately screenshot the **Graph** (canvas `cyStyle()`) and **Map** (pin
     `pinHtml()`) — these re-implement the same rule in parallel style objects and can drift.
     Confirm dashed/solid matches the DOM rule in all three.
- **Reason for the split:** the canvas surfaces don't share the DOM component, so one check can't
  cover them — but you still only need *one* DOM check + *two* screenshots, not per-component.

### T9 — Read-only view + back-navigation trap  · P2
- **Watching (demo):** Rail → Watching (or `?panel=watch`) → the tripwire cards render, **no actions**.
  **⚠️ Changed 2026-07-20:** the "armed" badge used to be a hardcoded string on every card; it now
  reflects real state. In demo mode assert the cards render; the badge's *correctness* is a live
  assertion — see **T10L**.
- **Back-button trap:** each panel view defines its **own inline copy** of the back-arrow (not a
  shared component). Fold this in: at the **end of T3–T8**, click "back" and confirm it returns to
  ZeroView. A regression in one copy won't show in another — one back-press per visited panel.

---

## 2B. PASS B — live mode (NEW, 2026-07-20). Run after Pass A.

**Why this exists:** the relocation beat, the alert feed, and the honest refusal are now real
backend behaviour. The previous plan skipped all of it as "dead code". These cases are the whole
reason for this QA run.

**Start the stack** (from the repo root, worktree `wt-EVAL`):
```
CHANAKYA_ROOT=$PWD backend/.venv/bin/python -m uvicorn chanakya.api.app:app --port 8000
cd frontend && npm run dev        # then open http://localhost:5173/?mode=live
```
*(Confirm the exact app path/port from `backend/chanakya/api/app.py` + the Makefile on first run.
If the SPA is served same-origin by the backend, use that instead and note which you used.)*
**Sanity-gate first:** hit `/health` and `/view`. If `/view` returns no nodes, STOP and report —
every case below would fail for one upstream reason and the findings would be noise.

### T5L — Honest refusal in live mode  · **P0**
- **Steps:** `?mode=live`, run the hero query from the AskBar.
- **Expect:** it **refuses** rather than answering, and the refusal **names the actual unresolved
  input** (the Karachi site anchor). Verify the wording literally.
- **Expect NOT:** a fabricated chain, or a refusal that names an entity absent from the graph.
  Either is **disqualifying** — file P0.
- This is the counterpart to T4: T4 checks a *declared evidence gap*; T5L checks the system
  refusing honestly when its own retrieval could not ground the question.

### T10L — Live alert feed + tripwire state  · P1
- **Steps:** `?mode=live&panel=watch`.
- **Expect:** cards render from the **live** view's `alerts`, not the frozen demo constants; the
  armed/state badge reflects real state (it was hardcoded before).
- **Expect the relocation alert:** subject = the watched unit, **before = Rawalpindi**,
  **after = Rahwali**. The sites must appear **only here, in the fired alert** — if the tripwire
  *definition* names them, that is a demo-integrity finding (P0), because a wire that names its own
  destination is confirming, not detecting.
- If no alert is present, check whether the running view was built from the staged ingest
  (`make beat`) — a backend built without the staged delta legitimately shows none. Report which.

### T11L — Alert provenance / one-click-to-source from an alert  · **P0 (non-negotiable #1)**
- **Goal:** alerts were the one artifact carrying **no** provenance. They now carry claim ids.
- **Steps:** open the relocation alert → click through to its evidence.
- **Expect:** it reaches the **same** provenance drawer as T3 (one drawer, not a second bespoke
  one), showing the before-claim (2021 Rawalpindi imagery) and the two after-claims (the 2025
  Rahwali pass + its confirmation) — 3 claims total, each to an exact source.
- A fired alert that cannot be traced to source is a **P0**.

### T12L — `stale` vs `insufficient` visual grammar  · **P0**
- **Goal:** these mean opposite things and must not look alike. **stale** = we know the unit *left*
  (history, well-evidenced). **insufficient** = we do *not know* (an evidence gap).
- **Steps:** in the live graph/map, find the Rawalpindi basing edge (now `stale`, superseded) and
  any `insufficient` element.
- **Expect:** visually distinguishable, and the stale one legible as *superseded/history* rather
  than as a gap. Conflating them is a **correctness** bug in the trust language, not a style nit.

### T13L — Drawn `supersedes` edge renders safely  · P1
- **Steps:** locate the site→site `supersedes` edge (Rahwali → Rawalpindi) in the live graph.
- **Expect:** it renders (it is the visible relocation link) and, critically, **carries no status** —
  confirm no status chip is invented for it and **no console error** from a missing-status path.
- If a `supersede_hold_reason` appears anywhere (a supersession held for review), it should read as
  a human-readable "held because…" explanation, not a raw token dump.

---

## 3. SKIP list — do NOT test (with reasons)

- ~~Any live/backend/API path~~ — **REMOVED 2026-07-20.** This was based on "no backend routes
  exist", which is false: 8 routes are implemented and live mode is reachable via `?mode=live`.
  Live mode is now **Pass B** and is the priority of this run.
- **Mode-switching *as a UI affordance*.** There is still no in-app toggle; `?mode=live` is a
  deep-link. Test each mode by loading it directly — don't hunt for a switch.
- **Map status logic separately from Graph** (and vice-versa). Same derived state — T2 covers both.
- **Provenance drawer from all three entry points in full.** Same `select()` path — T3 verifies
  content once + smoke-clicks the other two entries.
- **Review plumbing on all three cards.** Same mechanism — T6 tests it once (Merge) + payload-only
  on Override/Alert.
- **Status grammar per-component.** T8's one DOM check + two canvas screenshots is sufficient.
- **AskBar per panel.** It's one persistent mounted instance — one "Ask" test is representative.

## 4. SCOPE NOTES — report as *scope gaps*, not *bugs*

These are current-build limitations vs. the product brief, **not defects**. Note them once in a
"scope" section of the report; do not file them as failures or re-report per element:

- **Only Rahwali is a live provenance target.** The other 8 of 9 graph nodes and the non-Rahwali
  map pins only highlight — no drawer content exists for them by design in this build.
- **Citation chips in HeroAnswer and GapsView are display-only** (no `onClick`). Present, inert,
  intended for this build.
- **Override and Alert decisions have no downstream propagation.** They set the banner only; no
  node status changes elsewhere (unlike the data-contract's aspiration §D-2). Expect no
  confirmed→probable change from these cards.
- **No in-app live/demo toggle.** The seam is reachable by deep-link (`?mode=live`) but there is no
  UI switch. Testable (Pass B), just not discoverable — note once, don't file per element.
- **Live mode is honestly weaker than the demo scenario in places.** The frozen demo shows the
  intended end-state; live shows the real graph. Known, expected divergences: the hero query
  refuses (T5L); some entities are fragmented across surface forms; only part of the graph is
  richly provenance-backed. Report these as *scope*, not defects — **except** the P0 cases in §2B,
  which are real assertions.
- **The relocation spoof's silence is structural, not a scoring win.** If the run touches the d20
  spoof: it fires no alert because the extractor read those social posts as sightings, so it never
  produces a competing basing claim. Do not describe this as the credibility gate defeating it.

## 5. Execution notes (avoid false failures)

- **Wait for end-states, not clicks.** Ingest choreography runs on wall-clock timers
  (~600/1250/1900/3300ms); the hero answer staggers ~120ms/hop. Assert on the final state, or
  you'll capture half-rendered UI and file phantom bugs.
- **Canvas vs DOM:** Cytoscape graph = canvas, no per-node DOM → screenshot or `cy` JS API.
  Leaflet pins = real DOM with `data-*` attrs → selectors are fine. Basemap tiles/reticle/lines
  are SVG/canvas layers (not text).
- **StrictMode is deliberately off** — do not force-remount the app in a harness; it would
  double-init Leaflet/Cytoscape and produce artificial breakage.
- **Deep-links for isolation:** prefer `?panel=`/`?card=`/`?stage=`/`?ingest=`/`?drawer=1` to jump
  to a state rather than replaying the whole sequence — faster and less flaky.

## 6. What "ship-ready" means for this run

Green = **all P0 cases pass, in both passes** — T3 (one-click-to-source), T4 (declared refusal),
T8 (confirmed-vs-probable), **T5L** (honest refusal live), **T11L** (alert traceable to source),
**T12L** (stale ≠ insufficient) — plus **T2** transitions on both surfaces and **T6** Merge
propagation. P1/P2 issues are notes, not blockers, for the take-home demo; a P0 failure is a
stop-ship.

**Run order:** Pass A (T1-T9, demo) → Pass B (T5L, T10L-T13L, live). Pass A first because it needs
no backend and will surface any pure-frontend breakage cheaply, so Pass B's failures can be
attributed to the integration rather than to the UI.

## 7. Change log

- **2026-07-20** — Rewrote §0's premise: the plan previously declared the backend routeless and live
  mode "unreachable dead code", and its SKIP list forbade testing any live path. Both are false as
  of the Phase-4 work; following the old plan would have skipped the alert feed, the live honest
  refusal, and the stale/supersede rendering — i.e. everything this run exists to check. Added
  **Pass B (§2B)** with five live cases (two new P0s: alert provenance, stale-vs-insufficient),
  updated T5/T9 for demo-vs-live divergence, corrected the worktree to `wt-EVAL`, and added the
  scope notes covering live's honest weaknesses and the spoof's structural (not scored) silence.
