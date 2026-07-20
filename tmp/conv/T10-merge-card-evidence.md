# T10 — the merge card: from "trust the number" to "read the source"

Branch `qa/t10-merge-card-evidence`, off the integrated `qa/live-fixes`. Backend + frontend.
Design basis: `artifacts/spine/05-hitl-and-triage.md` (the adjudication service, the ★ control points),
`artifacts/spine/03-resolution.md` (the merge signals), and T3a's own note (`tmp/conv/T3a-review-queue.md`),
whose design ethics are preserved verbatim.

---

## 1. The fault

T3a made the live merge card argue its case properly: the resolver's per-signal breakdown as the quiet
case FOR, a loud short case AGAINST, a counted consequence, and an honest refusal to predict the
post-merge status. It was a good card. **It was also unfalsifiable.**

The only clickable things on it were the back arrow and the three decision buttons. So the analyst was
asked to make an identity call on:

* **"A source calls them the same · 0.70"** — which source? saying what? when? how credible? Unreachable.
  The resolver weights that signal by the *asserting source's* grade (D-2.5), which is precisely the
  thing the analyst has to second-guess — and the card showed only the output of that weighting.
* **"HT-233 · confirmed · 8 claims" / "Type 120 · probable · 2 claims"** — ten sourced claims named on
  screen, none openable.
* **"Differs on: functional role — engagement radar vs acquisition radar"** — decisive, unattributed.

That is the project's non-negotiable broken (*every claim is one-click traceable to its exact source*)
on the one screen where a human is being asked to override the machine.

## 2. Why there was nothing to link to (the real root cause)

The gap was not a missing button. **An identity assertion is consumed, not drawn.** `view/pipeline.
_assemble` deliberately suppresses `same-as` claims as edges (D-2.5/P3.2 — drawing them produced twin
nodes and self-loops for the very designators resolution had just reconciled). The knowledge layer
expresses the answer by merging, or by leaving a candidate edge for an analyst.

Correct — but it meant the sentence a source actually wrote had **no surviving pointer anywhere**. The
`source_asserted` score rode the candidate edge; the claim behind it rode nothing. `resolve.Edge` did not
even carry its own `claim_id`.

## 3. What was built

### Backend — the candidate edge now cites its own evidence (no new route)

One thread, four small links, so the existing `GET /evidence/{element_id}` does all the serving:

| file | change |
|---|---|
| `resolve/entities.py` | `Edge.claim_id` — a triple now remembers which claim it came from |
| `resolve/scoring.py` | `identity_claim_ids(graph, a, b)` — the claims behind `source_asserted_score`, using the **same** pair/predicate test, so the list and the number can never disagree |
| `schemas/stage_io.py` | `Partition.identity_claims: {pair_key → [claim_id]}` |
| `resolve/__init__.py` | populated for candidates + accepted merges, only where a source really spoke |
| `view/pipeline.py` | `_resolution_edges` stamps them onto the candidate `same-as` edge's `claim_ids` |

`GET /evidence/same-as:<a>|<b>` then returns the asserting claims with their **verbatim quotes**, exact
locators, and `sources` registry cards — all machinery T6 already built. **No API route was added or
touched** (T11's territory), and node/edge counts are unchanged (166 / 84).

On the frozen corpus this lights up exactly the four pairs a source spoke about, and leaves the other
four dark:

| pair | `source_asserted` | claims now cited |
|---|---|---|
| HQ-16 ↔ LY-80 | 0.85 | 3 (`d01_sipri_transfer`, `d14_stale_holding`, `d23_cpmiec_false_attribution`) |
| HT-233 ↔ Type 120 / YLC | 0.70 | 1 (`d15_globaltimes_aligned`) |
| CPMIEC ↔ China National Precision Machinery | 0.635 | 1 (`d14_stale_holding`) |
| SINO-GALAXY IMP/EXP ↔ SINO-GALAXY IMPEX | 0.61 | 1 (`d05_customs_manifest`) |
| the other 4 candidates | 0.0 | **none — and the card offers no link** |

### Frontend — three doors, all into the SAME drawer

Nothing new was built to display evidence; every affordance calls `store.openProvenance(id)`, which is
the identical path node selection and the alert feed already use.

1. **Each record panel is a button into its own claims.** The claim count is the visible handle
   (`see the 8 claims →`, dotted underline, hover border). The panel subtitle drops to `component ·
   confirmed` so the count is not printed twice.
2. **The "a source calls them the same" row is a real `CitationChip`** — the app's established citation
   language — labelled with what it opens (`A source calls them the same · 1 claim`) and pointing at the
   candidate edge id. **Only that row.** The other three signals are the resolver's own arithmetic over
   the two records and stay plain text; a quiet footnote says so out loud
   (*"Only the cited row is a source's assertion — the rest the resolver computed from the two records."*,
   and its converse when nothing is cited).
3. **Every "differs on" line declares its standing.** Lines read off the records' stated values carry
   `read from HT-233 · Type 120 / YLC series`, each name a link into that record's claims. Lines the
   machine computed say so instead — *"the resolver's own signal, scored at zero — an absence, not a
   quoted claim"*, *"computed from both records' stated coordinates — not a quoted claim"*, *"counted over
   the review queue"*. **A computation is never dressed as a citation**; that is the exact failure this
   card exists to prevent.

### The judgement call: the drawer opens *beside* the decision, not over it

The drawer is a right-anchored 560px overlay and the panel is the rightmost 400px — so opening it would
have **hidden the very decision the analyst went looking for evidence about**. While a live review card
is up, `LiveDrawer` now offsets itself by the panel width. The record pair, the signals, the differs-on
box and the three options all stay on screen the whole time the analyst is reading the claims. It still
*overlays* (the stage) and never pushes, and everywhere else the drawer is exactly where it always was.
When a decision lands, the drawer that was opened for it is dismissed with it.

### Two copy fixes the new route made reachable

Clicking a `same-as` edge now happens routinely, and T6's status-less copy was written for `supersedes`:

* verdict block: an identity link now reads *"it is a question about identity, not a fact about the
  world… anything below is a source asserting they are one thing, and it is for you to weigh"* rather
  than "it records a change of state".
* the residual claim bucket reads **"Who asserts it"** instead of "Also cited · not counted as an
  independent look" — independent looks are not counted for a status-less link at all.

## 4. What is preserved, deliberately

* **THE NO-HINT RULE.** The three options are untouched: identical styling, no default, no highlight, no
  implied order. Verified in the browser with the drawer open.
* **Matched-on long and quiet, differs-on short and loud** — the ACH inversion is intact. The one chip
  in the quiet block is not decoration: it marks the only row with a source behind it.
* **No predicted status.** The "Not known from here" admission is unchanged.
* **Demo mode is byte-identical.** The demo model carries no ids and no `onOpenEvidence` handler, so every
  affordance is *structurally absent* rather than disabled. Verified by text-diffing the demo card
  against the reference instance: **identical**. A link into the demo drawer's frozen fixture — which is
  about a different node entirely — would have been a lie dressed as provenance.

## 5. What the data could NOT support (stated, not faked)

* **A "differs on" line cannot be pinned to the exact claim that asserts it.** Node `attrs` are merged
  from a node's claims first-write-wins, and the view does not record which claim supplied which key. So
  the attribution is to the **record** ("read from HT-233"), which lands the analyst in that record's
  drawer where the claim is visible — in practice the first claim row of HT-233 literally reads
  `functional role — engagement radar`. Pinning per-attribute would need per-key claim provenance in
  `resolve.entities.build`; **filed here rather than invented.**
* **Coreference-raised pairs get no chip.** `coref-same-as` is a separate raise-only lane that does not
  feed `source_asserted`; citing it on that row would over-claim what the score counted. (Coref is off on
  this build in any case.) If it is ever turned on, it wants its own row and its own licensing quote.
* **Accepted (auto-merged) pairs still cite nothing.** `_merge_provenance` stamps `resolved_from` with the
  breakdown on the surviving node; `Partition.identity_claims` now carries the claim ids for those pairs
  too, but nothing renders them yet. Cheap follow-up, deliberately out of this scope.
* **`GET /evidence/{claim_id}` still 404s** — element ids only. Every affordance here passes an element id.

## 6. Verified in a browser (production build, `?mode=live`)

Backend + built SPA same-origin on `:8042` (reference instance on `:8080` untouched). Headless Chromium,
1440×900. Screenshots under `tmp/qa/` (gitignored, on disk only):

| file | what it shows |
|---|---|
| `t10-before-card-live.png` | **the fault**, captured on the reference `:8080` (integrated branch): same pair, nothing clickable |
| `t10-after-02-card.png` | the card now — both records openable, the source-asserted row a chip, the differs-on line attributed |
| `t10-after-03-chip-drawer.png` | chip → drawer **beside** the card; the pair, the signals and all three options still on screen |
| `t10-after-03b-chip-drawer-expanded.png` | the claim expanded: *"the associated engagement radar has been referred to in various reports as both Type 120 and HT-233"* → `d15_globaltimes_aligned.txt · L17 · 3625–3724`, source graded **reliability C, exporter-state interest** |
| `t10-after-04-back-on-card.png` | drawer dismissed, decision still in front of the analyst |
| `t10-after-05-record-drawer.png` | record panel → HT-233's own drawer (7 sources · 7 independent looks · 8 claims) |
| `t10-after-06-card-no-source.png` | a pair **no source spoke about**: no chip, footnote inverted, "No source states they are the same." marked as the resolver's own signal |
| `t10-after-07-after-decision.png` | after **Keep separate** → `POST /hitl/merge` **200**, view rebuilt, drawer dismissed with the decision |
| `t10-after-demo-card.png` | demo mode, unchanged |

Round-trip proof (the one T3a used): `POST /hitl/merge → 200`, badge re-derived, **zero console errors**
across the whole pass.

## 7. Gates

| check | baseline | now |
|---|---|---|
| `make test` | 843 passed, 6 skipped, 1 xfailed | **850 passed, 6 skipped, 1 xfailed** (+7) |
| ruff | clean | clean |
| mypy | clean (96 files) | clean (96 files) |
| `tsc --noEmit` | clean | clean |
| vitest | *(note said 134; measured baseline on this branch is 155)* | **163** (+8) |
| nodes / edges | 166 / 84 | **166 / 84** |

## 8. Shared files touched (exact list)

* `frontend/src/api/adapters.ts` — **additive only**, four spots: `MergeSignalRow` +2 optional fields;
  new `MergeDiffRow` type; `LiveMergeEvidence.differs`; `LiveReviewSide.evidenceId`;
  `LiveDrawerSubject.edgeType`; `mergeDifferences()` added with `mergeDiffersOn()` kept as its exact
  plain-text projection (no existing signature or return shape changed); one `MERGE_SIGNAL_SOURCE_ASSERTED`
  constant; the merge branch of `viewToReviewQueue` sets the handles. **No existing function was rewritten.**
* `frontend/src/api/adapters.test.ts` — two appended `describe` blocks (+8 tests), nothing edited.
* `frontend/src/store/workbench.ts` — one const + `decideLive` also clears the drawer.
* `frontend/src/components/drawer/LiveDrawer.tsx` — the beside-the-card offset, the identity-link copy,
  the "Who asserts it" kicker.
* `frontend/src/components/panel/views/MergeCard.tsx`, `LiveCard.tsx` — the card itself.
* `backend/chanakya/resolve/{entities,scoring,__init__}.py`, `schemas/stage_io.py`, `view/pipeline.py`.
* `backend/tests/{view/test_resolution_edges,resolve/test_entity_resolution}.py` + new
  `tests/acceptance/test_merge_candidate_provenance.py`.
* `tmp/conv/API-to-FRONTEND-contract-log.md` — T10 entry appended.

**Not touched:** `backend/chanakya/api/routes/` (T11), `backend/chanakya/agent/loop.py` and the
worked-query config/tests (T9), `frontend/src/components/rail/Rail.tsx`, `src/api/client.ts`,
`src/api/hooks.ts` (T11), `frontend/src/demo/scenario.ts`, `config/`, `corpus/`.

## 9. Decisions that leaned on a guiding principle

| Decision | Principle | Alternative rejected |
|---|---|---|
| Thread the asserting claim ids onto the candidate edge and reuse `GET /evidence/{id}` | *one-click to source; no second provenance surface* | a new identity-evidence route, or a bespoke evidence panel inside the card |
| Cite **only** the predicates that feed `source_asserted` | *never assert more than the evidence supports* | folding in coref claims, which would make the citation over-claim the score |
| No handle at all when no source asserted the identity | *an admitted absence beats a plausible link* | a chip that opens an empty drawer |
| Mark computed differs-on lines as computed | *a fabricated citation next to real data is disqualifying* | letting the km figure and the zero-signal lines read as quotations |
| Attribute differs-on to the **record**, not to a claim | *don't assert what the data does not record* | guessing which claim supplied a merged attribute |
| Drawer opens beside the card, not over it | *keep the human in the loop — the decision must stay in view* | the default full-right overlay, which hides the decision behind the evidence |
| Demo affordances structurally absent, not disabled | *demo determinism; never a link that opens the wrong thing* | wiring demo into the frozen drawer fixture |
| Split `mergeDifferences` / keep `mergeDiffersOn` as its projection | *`adapters.ts` is the repo's worst merge hotspot — additive only* | changing `differsOn`'s type in place and touching every caller |
