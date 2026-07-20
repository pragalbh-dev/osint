# T3a — the review queue: 40 identical rows → a triageable queue

Branch `qa/t3a-review-queue` (off `origin/main`). Frontend only. No backend, no config, no API change.
Design basis: `artifacts/spine/05-hitl-and-triage.md` (the adjudication service, the ★ control points,
recall-biased triage) + `artifacts/product/00-ux-brief.md`.

---

## 1. The diagnosis

Three separate faults stacked on the same surface.

**(a) The rows carried no subject.** `viewToReviewQueue` gave every derived item a *per-review-type*
title — `'Same system, or two?'` for every merge, `'Is this really confirmed?'` for every override. The
rail rendered kicker + badge + title, so 40 merge proposals rendered as 40 byte-identical cards. The
entity names were sitting in the item's `context.left/right` and were simply never shown.

**(b) The rail had no ordering and no grouping.** The queue was rendered in view order — same-as edges
in whatever order `sorted(partition.candidates)` emitted them. `hitl/triage.py` already defines the
deterministic order (★ pinned by `star_priority`, then rank) and the client ignored it entirely.

**(c) The card under-read the item.** In LIVE mode the panel *does* route to `LiveCard` (not the demo
`MergeCard` — that branch is `!live`), so the "clicking any row shows the demo HQ-9/P card" hypothesis
was wrong. The real fault was thinner but the same in effect: `LiveCard`'s merge branch showed only two
names, one dots row and a one-line summary. The card's actual argument — matched-on (long, quiet) vs
differs-on (short, loud), and the consequence — existed **only** in the demo constant. So the ★ marquee
control point degraded to a name pair in live mode.

## 2. What is wired now

### Rows identify themselves
Every row is built from the records it is about:

| type | kicker | title | second line |
|---|---|---|---|
| merge | `Merge · basing site` (both types when they differ) | `Army Air Defence Centre, Karachi ↔ Sargodha` | `identity match 0.63 · 3 of 4 signals` |
| status-override | `Status override · unit` | the element's own name | `reads contradicted — credible sources disagree` |
| alert-disposition | `Alert · basing relocation` | `Basing relocation · HQ-9B fire unit` | `occupied @ Rawalpindi → occupied @ Rahwali` |

The badge is no longer the constant `'Close call'`: it is banded off the recorded `merge_confidence`
through the app's existing `credibilityToDots` tiers (Strong match / Close call / Weak match / Very weak),
plus a `Touches a chokepoint` chip when either endpoint carries a candidate/confirmed chokepoint. The
question ("Same system, or two?") moved to the card headline, where it belongs — it was never what
distinguished one row from another.

### The card is data-driven in BOTH modes
`MergeCard.tsx` now exports a pure `MergeCardView({ data, onBack, onDecide })` over a `MergeCardData`
model, plus a thin `MergeCard()` demo wrapper that feeds it the frozen scenario constant. `LiveCard`'s
merge branch feeds the **same component** with `mergeCardDataFromItem(item)` — the item the analyst
clicked. The authored design intent is preserved verbatim: matched-on long and quiet, differs-on short
and loud in the problem-coloured box, and **THE NO-HINT RULE** (three identically styled options, no
default, no highlight, no implied order).

Where the live content comes from — all of it already on `GET /view`, nothing invented:

* **Matched on** — `attrs.breakdown` on the candidate `same-as` edge: the resolver's own per-signal
  merge score (`attribute`, `relational`, `temporal_consistency`, `source_asserted`), rendered in analyst
  language with the raw 0..1 value beside the dots. Only signals scoring **> 0** appear here.
* **Differs on** — computed from the two records: type mismatch, differing `location.raw`, great-circle
  distance when both sides have coordinates, any conflicting scalar attribute (`site_type`, `role`,
  `family`…), **plus every merge signal that scored exactly 0**, stated as an absence ("No source states
  they are the same."). That last part is the ACH inversion done with the resolver's own numbers. If
  nothing separates them the card says so instead of manufacturing a doubt.
* **If you merge** — counted off the graph: claims joined (union of both nodes' `claim_ids`, with the
  per-side split named) and how many assertional edges re-point at the merged record (identity/version
  links excluded — merging does not re-point a `same-as`). A chokepoint line is added when one is involved.
* **Not known from here** — the status change is **not** predicted. `rebuild()` recomputes status from
  the joined claim set; the demo card's "changes 2 node statuses" is authored fixture copy and printing
  anything like it beside live data would be exactly the fabricated consequence the brief disqualifies.
  The card prints the admitted unknown instead.

Status-override and alert-disposition cards gained the same two blocks ("If you override" / "If you
decide" + the unknown), and now show all their badges rather than one.

### The queue is triageable
Two moves, in `adapters.ts`, both pure and deterministic (no LLM, no clock — the demo replays identically):

1. **`orderReviewQueue`** — ★ priority mirrored from `hitl/triage.TriageConfig.star_priority`
   (status-override → merge → alert), then materiality (chokepoint first), then the most confident
   identity claim. An **unknown** confidence sorts as *more* urgent, never less — recall-biased, unknown
   is never treated as safe.
2. **`groupReviewQueue`** — union-find over the merge proposals' endpoints. A connected run of ≥ 3
   proposals collapses into one **identity cluster** header that states the shape of the problem, counted:
   `8 records, 28 merge proposals · every one of the 28 possible pairs is proposed — these are not
   independent proposals`. Members expand underneath, each still individually decidable, and each carries
   the cluster onto its card so the analyst sees while deciding that the proposal is not independent
   evidence.

On the current corpus the wall of **40 items becomes 7 decisions**: three clusters (28 basing sites, 5
components, 3 contract-import events) and four isolated pairs — and the four isolated pairs are the
genuinely interesting ones (`CPMIEC ↔ China National Precision Machinery Import & Export Corporation`,
`SINO-GALAXY IMP/EXP CO. LTD ↔ SINO-GALAXY IMPEX CO, LTD`, `HQ-16 ↔ LY-80`), which the flat list had
buried among 28 near-duplicates.

**Nothing is dropped, filtered or auto-decided.** `groups.flatMap(g => g.items)` is a permutation of the
queue (asserted in a test); the Review badge still shows the true escalation count (40), with
`40 items · 7 decisions — 3 identity clusters` beneath it. Clustering is a lens on the queue, never a
filter over it — escalation recall stays where spine/05 puts it.

## 3. Verified in a browser (live mode)

Backend `:8011` + Vite `:5311`, `?mode=live`, headless Chromium. Screenshots (gitignored by
`.gitignore:41`, so they live on disk only):

* `tmp/qa/t3a-before-queue-41-identical.png` — the fault, captured on this branch with the change stashed.
* `tmp/qa/t3a-after-queue-grouped.png` — the queue now.
* `tmp/qa/t3a-after-cluster-expanded.png` — a cluster expanded to its members (`KPQA-HC-2020-118834 ↔
  KPQA-HC-2020-118835 · Strong match`).
* `tmp/qa/t3a-after-card-single.png` — CPMIEC card: real signals, real differs-on, counted consequence.
* `tmp/qa/t3a-after-card-cluster-member.png` — a cluster member's card, carrying the non-independence line.
* `tmp/qa/t3a-after-demo-card.png` — demo mode unchanged, through the shared component.

Round-trip checked live: opening a cluster member → **Keep separate** → `POST /hitl/merge` → rebuilt view
→ badge 40 → 39, groups re-derived, no console errors. Demo mode: 3 rows, entity-named, demo merge card
renders the frozen copy exactly as before.

## 4. Shared files / API

* **No API change.** Everything the rows and card need was already on `GET /view`. Nothing was added to
  `frontend/src/api/client.ts` or the store.
* **New load-bearing consumption:** the frontend now reads `attrs.breakdown` (and `merge_confidence`) off
  candidate `same-as` edges to render the merge case. Logged as a consumer note in
  `tmp/conv/API-to-FRONTEND-contract-log.md` so it is not dropped as "resolver-internal".
* **`frontend/src/demo/scenario.ts`** — `QueueItem` gains `detail` (the records each demo row is about),
  taken from the card that row opens. Additive; demo card copy untouched.
* **Not touched:** `backend/chanakya/resolve/`, `config/`, `GraphView.tsx`, `MapView.tsx`,
  `components/drawer/`, `store/workbench.ts`, `api/client.ts`.

## 5. Deliberately left

* **The 40 proposals themselves.** T2 owns the resolver gate. This surface is built to read correctly at
  40 items or 6 — the cluster header degrades to ordinary rows below 3 connected proposals.
* **The demo merge card's authored consequence** ("Joins 4 claims, changes 2 node statuses") stays, because
  demo mode is entirely fixture — there is no real data beside it to mislead about. Live never renders it.
* **Cluster-level decisions** (one "keep all 8 separate" action). Tempting, but it would let one click
  dispose of 28 escalations — a bulk auto-decide is precisely what spine/05 forbids, and it is the kind of
  scope call that belongs to the user, not to me. The cluster today *frames* the decision; it does not make it.
* **Server-side ordering.** `hitl/triage.order_queue` already exists with a `frozen_rank` seam for the
  config-versioned NL rubric, but no GET route exposes the queue (it is derived client-side by design).
  The client order mirrors `star_priority` rather than re-deriving a second policy; if the queue ever moves
  server-side, `orderReviewQueue` should be deleted, not duplicated.
* **Confidence-band thresholds** are the app's existing `credibilityToDots` quartiles, deliberately reused
  rather than inventing a second private set of numbers. The resolver's real bands live in
  `config/resolution.yaml`, which the client cannot read (there is no `GET /config` — already filed by
  FRONTEND). When that route lands, the band labels should read from it.

## 6. Decisions that leaned on a guiding principle

| Decision | Principle | Alternative rejected |
|---|---|---|
| Cluster the blob instead of hiding/collapsing duplicates | *escalate the ambiguous; recall ≈ 1.0* | de-duplicating near-identical proposals (silently drops escalations) |
| Print "status is recomputed at rebuild" instead of a predicted status count | *no fabricated assessment; name what is missing* | reusing the demo's "changes 2 node statuses" line |
| One `MergeCardView` fed by both modes | *demo determinism + live truth from one component* | a second live-only merge card that would drift from the authored design |
| Client ordering mirrors `star_priority` verbatim | *config-driven, no divergent second policy* | a private frontend ranking heuristic |
| Reuse `credibilityToDots` tiers for the badge band | *no magic numbers buried in code* | new hardcoded 0.75/0.5 thresholds in the rail |
