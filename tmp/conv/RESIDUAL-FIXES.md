# Residual fixes — known, logged, deliberately deferred

**What this is.** Every defect and gap we found, understood, and chose *not* to fix before the
deadline. Each entry says what it is, whether it touches the demo, why we deferred it, and what the
fix actually is. Nothing here is a surprise — if one of these surfaces on the call, we can describe
it precisely rather than discover it live.

**Status key:** 🟢 no demo impact · 🟡 visible only if a reviewer goes looking · 🔴 demo-affecting.

---

## 1. 🟡 Mis-laned `equips` edge on hop 2 of the worked query — ✅ STAGE 1 DONE (diagnosed, not fixed)

**Diagnosis (2026-07-20, QA-T7). `relane()` is not broken — it never saw a `unit → variant` fact.**
The offending claim is `d06-spares-tender-l15-5`, and its own provenance says what happened:
`_relane_reason: "'equips' reoriented (variant->?)"`. That reason string is emitted by the
**partial-typing** branch of `_Emitter.relation()`, not by `relane()`. The model asserted
*"LR-SAM system —equips→ Pakistan Air Force"*; at write time `_entity_types` (the types **this
document** declared) knew `Long Range Surface-to-Air Missile (LR-SAM) system` = `variant`, but had
nothing for the string `Pakistan Air Force`. With one endpoint untyped, the both-typed branch — the
only one that may change the *label* — is skipped by design, and the partial branch fixes
**orientation only**, keeping the as-stated predicate. `edge_direction` correctly flipped it so the
variant sat in the `to` slot, which is how a `unit → variant` fact ended up wearing the `equips` label.

`relane("equips", "unit", "variant")` returns `inducted-into` reversed, correctly, today. The gap is in
the *producer's inputs*, not its logic: **the endpoint that makes this fact fully typed is only typed
downstream, by RESOLVE at rebuild.** Note the near-miss — d06 *does* declare a `unit` entity, but for
the string *"AIR HEADQUARTERS PROCUREMENT DIRECTORATE"*; the model reached for *"Pakistan Air Force"* in
the triple. Had the two strings matched, the re-lane would have fired. So the fix is not "fix relane" but
one of: (a) type relationship endpoints against the **entity registry + alias table** as well as the
current document's own entities, or (b) re-lane **after** resolution, where both endpoint types exist.

**Invariant test: none exists.** There is no re-lane analogue of
`test_shipped_corpus_is_already_fully_normalized` — every re-lane test
(`backend/tests/ingest/test_phase2_relane.py`, `test_edge_direction.py`) runs on synthetic input, and
`ingest/renormalize.py` is scoped to five *location* fields and may not touch a predicate. So a
logic-only fix would **not** turn a test red — but equally, nothing guards the frozen bundles against
drifting from the current lane logic. That cuts both ways and is worth stating on the call.

**Safe stage 2, if we ever want it:** `renormalize.py` is the precedent for editing frozen bundles
**deterministically and offline** — no LLM, no network, additive only, dry-run by default. A re-lane pass
in that mould would fix the label without a keyed re-record, i.e. **without putting the LR-SAM alias
binding at risk at all.** It would have to reproduce the endpoint typing RESOLVE does, which is exactly
the work the write-time path could not do. Still not worth doing before the deadline.

### Original entry, for the record

**What.** `e:unit_hq9b:equips:var_hq9p` — a `unit → variant` edge on the `equips` lane, but
`config/ontology.yaml:106` declares `equips` as `component → variant`. The correct lane for a
unit↔variant fact is `inducted-into` (reversed), which is what the fixture chain uses.

**Exactly one edge in the graph is affected**, and it is hop 2 of the flagship demo.

**Verified impact — contained everywhere except one surface:**
- Prose: **no effect.** Renders "The PAF HQ-9B fire unit fields HQ-9/P" via a `by_from_type`
  override in `config/templates.yaml`. Reads correctly.
- Materiality/chokepoint: **no effect.** 0 bogus nominations — the read-time endpoint-type guard
  added by the SC-1 fix already rejects this edge from supply-tier reasoning.
- The asserted fact: **correct and sourced** (d06, probable). Only the lane *label* is wrong.
- **The one exposure:** the API payload lists hops as `['based-at','equips','equips']`. A reviewer
  comparing that against the ontology sees the inconsistency.

**Why deferred — the fix is riskier than the defect.** d06 is the spares tender, and its alias
binding (*"Long Range Surface-to-Air Missile (LR-SAM) system"* → HQ-9/P) is the **only** reason
hop 2 resolves at all — it is the designator-free-tender trap the corpus was built around. A keyed
re-record re-runs the model over that document; if the binding comes back differently, **hop 2
breaks and the flagship demo stops tracing.**

**The fix, when we want it.** Two-stage, and stage 1 is safe on its own:
1. Diagnose why the write-time re-lane didn't catch a fully-typed `unit → variant` fact
   (`backend/chanakya/ontology.py` `relane()`, called from `ingest/extract.py`). Fix the producer.
   Check first whether a "frozen bundles agree with current code" invariant test exists for
   re-laning the way `test_shipped_corpus_is_already_fully_normalized` does for coordinates — if it
   does, a logic-only fix turns it red.
2. Only then decide on a re-record. If you do: **copy the bundle first**, re-record `--only
   d06_spares_tender`, diff before/after (claim count, claim ids, and specifically whether the
   LR-SAM alias binding survives), and keep the new one only if hop 2 still traces.

---

## 2. ✅ RESOLVED (2026-07-20) — Alert → provenance click-through, verified in a browser

**Walked end to end for the first time, and it holds. No code changes were needed** — the alert's
evidence chips already routed through the same `GET /evidence/{id}` drawer that node selection uses,
so there was never a second drill-down path to drift.

Verified: cold boot 171/105/0-alerts → reviewer clicks **Ingest** on a withheld document in the
Awaiting-ingest panel → "13 claims appended · 1 tripwire fired" → Watch renders the alert with
`based-at: site_rawalpindi → based-at: site_rahwali` → clicking the after-side claim chip opens the
**correct** element (`e:unit_hq9b:based-at:site_rahwali`, Probable) showing the **verbatim quote**
with file, line and character span. The before-side chip independently opens the Rawalpindi edge as
**Stale**, with its own quote and a *"To raise this"* block naming what is missing and a dated next
coverage. Both sides of "what changed" are separately checkable, which is the point. Ingesting the
second document appended 29 claims and correctly fired nothing. Zero console errors.

**One nuance worth knowing on the call:** the UI-fired alert carries **2** claim ids (the before and
the arriving after) where `make beat` shows **3**, because a reviewer ingests the two documents as
separate arrivals while `make beat` stages both as one delta. Both are correct — the alert records
what was on the table when it fired, and the second document then strengthens the edge without
re-firing. Only if we wanted the UI to reproduce `make beat` byte-for-byte would both bundles need
to go in a single POST.

Screenshots: `tmp/qa/fixshots/01..05` (gitignored, local only).

### Original entry, for the record

**What.** A fired alert has never been clicked through to its evidence in a browser. The served
cold-boot view legitimately has **0 alerts**, and the staged ingest that produces one exists only
inside `eval.harness` — there is no API flag or env var to boot the app with documents held back.

**Impact.** P0-class by our own ladder: one-click-to-source is the non-negotiable, and the alert was
the one artifact that lacked provenance until MON-4. The *data* contract is proven (`make beat`
emits the alert with before=Rawalpindi, after=Rahwali and 3 claim ids) and the rendering code is
unit-tested — but the path from a rendered alert to the drawer has not been exercised end-to-end.

**Why deferred.** Not really deferred — it is blocked on the same work as the reviewer-facing live
ingest (task #6). Solving that solves this: hold the two 2025 Rahwali documents out of the seed,
ship their pre-extracted bundles, let a reviewer ingest one, and the alert appears. Then click it.

**Do this immediately after SHIP.** It is the highest-value open item.

---

## 3. 🟢 `sustained-by` rollup not built

Its inputs genuinely do not exist: 0 `replenishes` edges, 0 `interceptor_stockpile`, 0
`techdata_authority` nodes. Building the rollup would fabricate the path it claims to summarise.
Deliberate boundary, stated at `ingest/extract.py:340`, not an oversight. See `tmp/conv/EVAL-DATAC-sustainment-nodes-dropped.md`.

## 4. 🟢 `techdata_authority` never extracted — a real, mundane bug

The corpus **does** state it (d21: radar software/calibration "routed through a Chinese state
technical-data authority… retains configuration control"). We do not capture it because the schema
slot exists on the procurement-tender form but **not** the analytic-prose form, so the model had
nowhere to record it. Three-step fix + a scoped re-record documented in
`tmp/conv/EVAL-DATAC-sustainment-nodes-dropped.md`. Deferred because it needs a keyed re-record.
Note the source scopes control to the *radar*, while our edge is typed authority→system — recording
it faithfully needs a component-scoped lane.

## 5. ✅ RESOLVED (2026-07-20) — Supersede ordering now compares intervals, not upper-bound strings

`_latest_iso` is replaced by `_interval` + `_relation` (`backend/chanakya/view/supersede.py`). A target's
time is now the **union interval** across its claims, and two targets are compared as intervals:
disjoint-and-strictly-earlier → ordered pair; identical exact instants → contradiction; identical *vague*
intervals → unorderable → `candidate_supersede` (the branch the string compare could never reach); any
other overlap → contradiction. A missing *either* bound stays unorderable rather than guessed. Both named
defects are now covered by tests that fail on the pre-fix module: a vague `"2025"` can no longer outrank a
precise `2025-03-27`, and a late restatement of an old fact can no longer reverse the arrow (it widens the
old fact into overlap → HITL). **The Rahwali beat is unchanged** — Rawalpindi (2021-10-09) and Rahwali
(2025-01-01 … 2025-12-31) are disjoint, `site_rahwali supersedes site_rawalpindi` still promotes, the
retired edge still reads *stale*, and `make beat` still fires with 3 claim ids. The garrison/field xfail
(#6) is unaffected and stays xfailed.

### Original entry, for the record

`view/supersede.py` `_latest_iso` takes only the upper bound of a date interval and compares with
string equality, and takes `max` over a target's claims. Two consequences: a vague `"2025"` can
outrank a precise `2025-03-27`, and a late *restatement* of an old fact can reverse the arrow.
**Correct on the current corpus** (Rahwali genuinely resolves newest) and contained because
everything routes through `candidate_supersede` + the post-status floor. The fix is ~8 lines using
the existing `canonical_iso_bounds` — compare intervals, treat overlap as contradiction, treat
indistinguishable as unorderable. Was specified in D-P4.4(iii) and only half-built.

## 6. 🟢 Garrison + field basing would mint a false supersede

`based-at` is keyed single-valued per subject, but is genuinely single-valued per
`(unit, site_type)` — a unit at a garrison *and* a forward site simultaneously would falsely
supersede. Captured as a **strict xfail** in `backend/tests/view/test_supersede.py` with the fix
described; it XPASSes when the derivation stamps `site_type`. Does not occur in this corpus.

## 7. 🟢 Node-level perishability is not read

`freshness_class` is consumed for **edges only**. `interceptor_stockpile` and `techdata_authority`
declare one as node types and would not decay. Moot while both are unpopulated.

## 8. ✅ PARTLY RESOLVED (2026-07-20) — sustainment items removed from the spec; the key was NOT regenerated

The two nodes, the two edges and the stale `single_source` flex are gone from
`tools/generate/scenarios/hq9p_primary.yaml` (the flex is re-pointed onto d17, matching the key
verbatim), and the stale prose in `artifacts/plan/sessions/EVAL.md` and `config/entities.yaml` is fixed.
**The answer key was deliberately left alone**, because regenerating it is far more dangerous than the
four items suggested: `generate.py` writes the key as a straight copy of the spec, and the spec has
drifted from the hand-curated key in six further ways — the Phase-1 lane renames revert, `mfr_taian` /
`comp_tel_chassis` and their edges vanish, the `deep_tier_confirmed` flex vanishes, d24/d25 vanish from
the document registry, the whole `attribution_inference` block vanishes (`answer_key()` cannot emit it at
all), and `adversary_denial_bypass` reverts. Full diff + the two ways out are in
`tmp/conv/QA-T7-answer-key-generator-drift.md`, and a warning block now sits above `ground_truth:` in the
spec. **Until DATA-C reconciles them: regenerate documents only and restore the key from git.**

## 9. ✅ RESOLVED (2026-07-20) — the refusal body now names entities, not Python objects

The "lens has no basing site" refusal in `agent/loop.py` renders unresolved anchors through a new
`_names()` helper (node names, comma-joined; an id with no node falls back to itself rather than being
dressed up as a name), and the internal lens id is gone from the prose. The two failure shapes now read
differently and honestly — *anchors absent from the rebuilt view* vs *anchors that resolve but none is a
basing site*. Machine-readable ids still travel in `missing`, which the SPA already resolves to display
names of its own accord. Two tests exercise both branches and assert no `[` / `'` / lens id appears.

## 10. ✅ RESOLVED — already hermetic on `main`; verified both ways (2026-07-20)

Fixed upstream by SHIP (commit `6e6d8a3`) before this register was written: the test monkeypatches the
SPA seam at a non-existent dist directory instead of reading the real `frontend/dist`. **Verified
deliberately**, since the failure is environment-dependent in both directions: the suite is green with no
`frontend/dist` at all *and* with a stub `frontend/dist/index.html` present. No change needed. The
register entry was stale.

## 11. 🟢 D-P4.14 — the independence weight is applied twice — ✅ DECIDED (2026-07-20): KEEP, AND DISCLOSE

**User's call, 2026-07-20: keep the current behaviour, and keep it stated here.** This is no longer an
open question — it is a *deliberate, disclosed conservatism*, and it should be said out loud on the call
and in the design note rather than quietly corrected:

> The credibility layer applies the independence weight twice — once to the magnitude of a group's
> contribution and once to the count of independent looks — which makes it **stricter** than `spine/04`
> as written. It therefore **under-claims** confidence and never over-claims.

Given the brief treats fabricated or inflated assessment as disqualifying, strict is the right direction
to err, and saying so is stronger than a silent fix. The correction, if ever made, is a credibility
retune that must land as **its own change with a before/after status table** — never folded into a QA
sweep, which is exactly why it was not folded into one.

Diagnosis, verified and retained as the record of what is being disclosed: `group_confidence()`
multiplies the strongest claim credibility by `group.weight` (magnitude) and `_effective_looks()` sums
the same weights against `min_independent_groups` = 2 (count), while `spine/04` defines `c_g` as the max
credibility with no weight factor and the gate as *≥2 groups*. Quantified: 86 of 334 groups weigh 0.5;
**26 of 294 assessed elements** would move confidence if corrected, and some sit near the 0.80 cut, so
statuses could flip. **The flagship path is untouched either way** — both Rahwali groups weigh 1.0. The
four options and the reasoning are preserved in `tmp/conv/QA-T7-independence-weight-decision.md`.

## 12. 🟢 DATA-C / answer-key items

`mfr_taian` → probable (single-doc justification for a `confirmed` grade); the now-unsatisfiable
`FD-2000 same-as` oracle assertion (Phase 3 stopped drawing `same-as`); `import_2021` naming
mismatch; full id unification (eval still matches by name+type). None block the demo, but they
block anyone trusting the fragmentation/MISSING counts — which per the standing caveat come from a
probe that ignores edge endpoints and **should not be quoted as a score**.

## 13. 🟢 In-document coreference is built but gated off — ✅ MEASURED & DECIDED (2026-07-20): KEEP GATED

Both halves shipped (`ingest/coref.py` + the RESOLVE honor policy); `config/resolution.yaml`
`coref_authoritative_evidence: []` keeps it inert by choice.

**Now measured rather than assumed** (branch `qa/t1-coref-gate`, full analysis in
`tmp/conv/T1-coref-gate-evaluation.md`). Three findings, each sufficient on its own:

1. **Flipping the consumer flag is a provable no-op, not a null result** — the 29 frozen bundles contain
   **zero** `coref-same-as` claims, so the consumer's loop body never executes.
2. **Turning the producer on breaks the build today** — it needs a *second* extraction call per document;
   every recorded fixture holds one response, so the scripted client exhausts and **31 tests fail**. That
   is the concrete shape of "needs a re-record": 29 bundles + ~31 fixtures + a keyed re-run.
3. **Even after a perfect re-record the trade is bad** — only **11 of 40** duplicate candidates are
   in-document, and **9 of those 11 are pairs a human would call clearly different** (`Punjab ↔ Sindh`;
   the three *distinct* KPQA bills of lading; HT-233 array ↔ support vehicles), with **none of the four
   demotion rails firing on any of them**. Payoff: ~**one** reliable merge (`LY-80 ↔ HQ-16`).

**Not deleted, deliberately.** The code is sound, fully inert, and is a good answer to a real design
question — defensible on the call *as a gated capability*: "we built the in-document discourse channel,
measured its reach at 11 of 40 with 9 of those unguarded, and left it raise-only until veto coverage
earns it."

**Its own pre-conditions for revisiting are now all met** (T3b landed the identical-string resolve fix,
the `basing_site`-absorbing-areas retyping, and the `contract_import_event` identifier rail), so a future
re-record would be measured against a much cleaner baseline than the one that produced this verdict.

## 14. ✅ RESOLVED (2026-07-20) — the `deep_tier_confirmed` flex no longer claims corroboration it lacks

The `expect` text in `answer_key.json` said the Taian/Wanshan chassis link was "multiply attested"; it
appears in exactly one bundle (d24). Reworded to say what is actually true — the grade rests on the
**directness** of a single source that names supplier + component + relationship explicitly, *not* on
corroboration count — and the single-bundle fact is now stated in the flex itself so nobody re-derives
the overclaim. The `confirmed` status is unchanged (it was always the evidence-gate argument, and that
argument survives). Prose only: no ground-truth node, edge or status moved. One stale echo of the old
wording remains in the historical audit note `tmp/conv/eval-rca/ANSWER-KEY-GROUNDING-AUDIT.md` — left as
written because it is a dated record of an audit, not a live artifact.

## 15. 🔴 No node ever becomes a CONFIRMED chokepoint — `substitutable-by` is never populated

**The assignment asks for supply-chain chokepoint identification. Today the system produces 10
`candidate` chokepoints and *zero* confirmed ones, and it is structurally incapable of producing one.**

Measured on the integrated graph (`qa/live-fixes`, 166 nodes):

* `chokepoint_status`: **156 `none`, 10 `candidate`, 0 confirmed/sole-source**
* `substitutability_state`: **`UNKNOWN` on all 166 nodes** — without exception
* `chokepoint_count`: **0** on every candidate
* **`substitutable-by` edges in the graph: 0.** `supplies-component` edges: 2.

**The mechanism.** `materiality/precompute.py::_substitutability` derives its three-state value purely
from a node's `substitutable-by` edges. With none in the graph every node is `UNKNOWN`, and the
classifier then applies its own (correct, conservative) rule — *"UNKNOWN substitutability / inferred →
candidate, never sole-source"*. So the promotion path is closed by construction, not by evidence.

**This was scoped, not overlooked.** `config/ontology.yaml:169` declares the predicate and its own comment
says *"three-state on the edge; only UNKNOWN seeded (roadmap)"*. The materiality layer, the three-state
model, the candidate classification, the `contributing_refs` and the Known-Gap template (`missing
named_supplier, substitutability`) are all built and working — the **evidence layer underneath them is
empty**.

**The corpus is NOT silent on this, which is what makes it worth fixing rather than merely disclosing.**
`d16_adversary_denial` is *entirely* an argument about sole-sourcing — a claim that the HT-233 is "a fully
indigenised product… no dependency on Chinese technical data packages", pushed back on in the same
document, against earlier reporting that tied HT-233 sustainment to "CASIC-supplied documentation and
periodic Chinese technician visits". That is substitutability evidence, *and* it is contested
substitutability evidence — precisely the adversary-denial case the credibility layer exists to weigh.
`d21` (technical-data authority / configuration control) and `d24` (Taian/Wanshan chassis) bear on it too.
Related: **#4** (`techdata_authority` never extracted — same root, a schema slot the extractor had nowhere
to record).

**Impact.** The graded ask is "an auditable order-of-battle **+ supply-chain map**". We can nominate what
*might* be a chokepoint and state exactly what is missing — which is the non-negotiable behaving correctly
— but we cannot currently answer "name the chokepoint" with anything better than *candidate, UNKNOWN*. The
worked query's close reads *"Chokepoint: HT-233 — candidate, substitutability UNKNOWN. Insufficient
evidence to assess…"*. Defensible, and honest, but thin against the brief.

**Do not fix silently.** The fix needs an extraction slot for substitutability plus a keyed re-record, and
it changes what the flagship answer says — so it is a scoped piece of work with a user decision attached,
not a patch. Options, cheapest first:
1. **Disclose only** — state on the call that substitutability is modelled end-to-end but unpopulated, and
   that every chokepoint is therefore a candidate. Zero risk, zero build.
2. **Seed `substitutable-by` from `config/` for the two or three components the corpus actually argues
   about**, provenance-tagged as analyst-curated, so at least one node completes the ladder and the demo
   can show a *confirmed* chokepoint with its contested evidence.
3. **Extract it properly** — add the schema slot, re-record d16/d21/d24, and let the credibility layer
   adjudicate the denial. Best story (an adversary-denial claim *lowering* confidence in a sole-source
   read is exactly the graded axis), highest cost and highest risk this close to the deadline.

## 16. 🟡 `rebuild()` emits some edge ids on several rows, and only one row is ever scored

Found by T9 while wiring the new hero query (`tmp/conv/T9-to-DATA-graph-gaps.md`); **filed, not fixed —
it changes graph shape everywhere.**

The same edge id can appear on **multiple rows**, each holding a *different slice* of that edge's claims,
and only one of those rows is assessed. `e:var_hq9p:inducted-into:unit_paad` appears **four times**: the
ISPR official induction announcement is stranded on an unassessed row, while the row that *is* scored
carries only imagery plus the planted `d23` false attribution — hence its "missing official_announcement".
**7 ids duplicated, 9 surplus rows.**

**Why it matters more than it looks.** This is very likely the reason **nothing on the corpus reaches
`confirmed`** and why every induction edge reads `insufficient`: corroboration is being split across rows
so no single row ever accumulates enough independent looks. It is also why the new hero query runs its
ORBAT hop on `equips` rather than the better-sourced `inducted-into`. Suspect a shared root with the
`edge_instance` keying issue noted in the Phase-4 audit.

No edge in the current worked-query chain is affected, so the demo is not at risk — but any claim we make
about corroboration counts or status distribution is suspect until this is understood. Fix it *before*
re-running any evaluation numbers.

## 17. 🔴 DEMO MODE IS A SECOND, UNQA'd APPLICATION — and it is what the app boots into

**The single most demo-critical thing the 2026-07-20 QA sweep found.** Discovered the hard way: the user
was handed a running instance, and three of the four defects they reported back were **demo-mode
artifacts**, not real ones.

**Why it bites.** `frontend/src/store/workbench.ts` ships `mode: 'demo'` as the default, and
`ModeToggle.tsx` renders **only under `import.meta.env.DEV`** — deliberately, so the graded build stays
pixel-clean. In a **production** build (i.e. `make run`, i.e. the hosted URL a reviewer opens) there is
therefore **no visible way to reach live mode**; the only route is the undocumented **`?mode=live`** URL
param. A reviewer will never guess it. So the default experience of the shipped app is the frozen
scripted scenario, and **every improvement this sweep made lives behind a param they cannot discover.**

Confirmed defects **in demo mode**, all verified in code, none of which exist in live mode:

* **Every map pin opens the same drawer.** `DrawerHost` routes `mode !== 'live'` to `Drawer.tsx`, which
  subscribes to `drawerOpen` / `expanded` / `ingested.d20` / three Rahwali selectors and **never reads
  which node is selected** — there is no selection binding in it at all. It is one hardcoded Rahwali
  panel. Clicking Rawalpindi, Sargodha or Karachi all render *"HQ-9B fire-unit occupied at Rahwali"*.
* **Review cards do not open.** The three scripted queue rows do not route to a card, so the ★ HITL
  control point — the thing the brief grades — cannot be exercised at all in the default mode.
* **The hero question now contradicts its own scripted answer** (see #18).
* **Only the 4 scripted pins render**, so the map looks as sparse as it did before the map work.

**Why it went unnoticed:** every agent in the sweep verified in `?mode=live`, correctly, because that is
where the real data is. Nobody was asked to look at the mode the app actually starts in. That is a
briefing failure, not an agent failure.

**Options, and this needs a call before the demo:**
1. **Default the production build to `live`** and keep demo behind `?mode=demo`. Smallest change, biggest
   effect; risk is that the cold-boot refusal (D1) then greets the reviewer.
2. **Render the toggle in production** so both modes are reachable and labelled.
3. **Fix demo mode's drawer + review routing** to be selection-aware. Most work, and duplicates in the
   scripted path what the live path already does properly.
4. **Drop demo mode from the graded build.** Cleanest story ("what you see is the real system"), but
   forfeits the deterministic scripted walk that exists precisely because the live one can vary.

## 18. 🔴 The demo's scripted hero answer contradicts the new hero question

Introduced by the hero-query change (#T9) and **left deliberately unfixed — the demo narrative is
hand-authored graded content and rewriting it is the user's call, not an integrator's.**

`TARGET_QUERIES.hero` is a **single shared string** rendered as the first affordance in `ZeroView` in
*both* modes. It now reads *"Trace the long-range SAM battery now based at **Rahwali**…"*, while the
frozen `HERO_HOPS` walk still answers **step 1: "Where is the battery based?" → "Karachi — HQ-9/P pad
signature"**. In demo mode the question and its answer openly disagree on the first hop.

Partial alignment worth knowing before choosing a fix: the demo's **step 3** already answers *"CASIC —
export agent CPMIEC"*, which **matches** the new query's real terminal answer, and its **step 4** ("Are
there alternate suppliers? Unknown…") is exactly the substitutability gap in **#15**. Only step 1's
premise is wrong. Options: re-author step 1 to Rahwali; or give demo its own question constant so each
mode shows a question consistent with its own walk (they are currently coupled through one export).

## 19. 🟡 A vetoed pair can still be offered as a merge candidate

Found while integrating the QA branches (`tmp/conv/QA-INTEGRATION.md` §"Still open"). A
`places.place_geo_conflict_pairs()` sibling to `place_distinct_pairs()` — vetoing when two *resolved
gazetteer anchors* exceed `entity_geo_conflict_max_km` — computes the right **73 pairs**, but folding
them into the `veto` set **did not suppress the candidate `same-as` edges**: it only drew 22 additional
`distinct-from` edges, leaving the graph simultaneously asserting *"these are distinct"* and *"these might
be the same"* about one pair. **The candidate-emission path does not consult `veto` the way the merge path
does.** The change was reverted rather than shipped half-working.

**Live consequence:** the user's original complaint class survives — `Army Air Defence Centre, Karachi` ↔
`fenced compound near a PAF airbase in central Punjab` is still an open merge card at `merge_confidence`
0.519, ~800 km apart. `scoring.geo_conflict_km` cannot catch it because it reads coordinates a *claim*
states, and after toponym geocoding these entities are positioned from a gazetteer **anchor** instead
(T5 closed six such pairs by hand with config `distinct_from` rows; this one was not among them).

Fix properly: make candidate emission honour the same veto set the merge path uses, then re-add the
anchor-distance rail. The other seven surviving candidates are genuinely good questions and must stay.

## 20. 🟡 The map's honest area rendering is nearly invisible

The user looked at a map carrying **12 plotted entities** and reported it as showing "only selected
places". They were not wrong about what they could see: only ~4 nodes are point-precision and get a sharp
reticle; the other 8 are area-precision and render as a **faint dashed ring** — and a ±150 km province
envelope is so large against the dark basemap that it reads as background, not as a marker.

The rendering is *correct* and the honesty is the point (#T5: never draw a province as a sharp dot). But
a reviewer who cannot see that 12 things are located will conclude the map is empty — the same wrong
conclusion the original "the whole map looks so empty" complaint came from. **Correct-but-illegible is
still a demo problem.** Cheap fixes exist that cost no honesty: a count ("12 located · 4 point fixes · 8
area-only"), a stronger area stroke, or a list beside the map. Not a data change.

---

## Open decisions and not-yet-done (as of the Phase-4 PR)

**D1. 🔴 What should a reviewer's FIRST query do?** Raised by SHIP. With the 2025 evidence
withheld from the boot seed (so the beat can fire on demand), a reviewer's first `/ask` is an honest
refusal until they ingest. That is the designed beat, but **the flagship demo looks broken on
arrival unless the UI leads them to the ingest.** The Awaiting-ingest panel in the left rail does
this, but nobody has watched a cold reviewer use it. Two verified options, both seams exist:
(a) keep it withheld and make the SPA prompt the ingest more loudly; (b) ship full-corpus by setting
`CHANAKYA_SEED_WITHHOLD=` in compose, and treat the beat as a separate deliberate action.
**Needs a call before the demo.**

*Re-confirmed 2026-07-20 (T9):* the replacement hero query — *"Trace the long-range SAM battery now based
at Rahwali back to the organisation that builds its missile system, and name the fire-control
chokepoint"* — **also refuses on a cold boot**, for the same structural reason: its anchor is Rahwali,
which does not exist until the two withheld 2025 passes are ingested. Changing the query did not and could
not dissolve this decision. T9 also notes the refusal wording is **engineer-shaped rather than
analyst-shaped**, which makes the cold-boot first impression worse than it needs to be under either
option — worth fixing regardless of which is chosen.

**D6. 🔴 How do we answer "name the chokepoint" on the call?** New, 2026-07-20 — see **#15**. Every
chokepoint in the graph is a `candidate` with `UNKNOWN` substitutability, because no `substitutable-by`
edge is ever produced. Three options (disclose only / seed a curated few / extract properly) are in #15,
cheapest first. This is a **graded ask of the brief**, so it needs a deliberate answer even if the answer
is "we disclose the limitation".

**D2. Not exercised in SHIP** (stated, not hidden): the GHCR **push** (no credentials assumed — the
pull path was proven by running the tag from outside the repo, i.e. everything but the network hop);
**EC2 + Cloudflare Tunnel** deploy to `ec2-3-142-96-102.us-east-2.compute.amazonaws.com`; the
**rollback drill** (needs two pushed tags); and the recorded **screencast** (needs the live URL).

**D3. `make run` defaults to PORT=8000**, which on the dev box is the user's company vLLM server.
Fine for reviewers and EC2; always pass `PORT=…` locally.

**D4. Still to write:** the README (now writable — the commands exist and are verified by both
paths), the ledger reconciliation (D-P4.1…D-P4.14 are in NO decision ledger; `artifacts/plan/PROGRESS.md`
shows six merged sessions as in-review and EVAL as not-started), and the design note (the user's
`artifacts/design-note-v2.md` is in progress and deliberately untracked).

**D5. The two design notes are untracked on purpose** — `artifacts/design-note.md` (agent-written,
fact-checked against the running system) and `artifacts/design-note-v2.md` (the user's, still being
edited). Neither is committed; the merge of the two is the last graded deliverable.

---

## Also worth knowing (not defects)

- **The evaluation numbers are not a score.** The fragmentation/MISSING counts come from a probe
  that ignores edge endpoints. Do not present them as an accuracy figure.
- **Five mechanisms reached a green test suite while wired to nothing** — supersession, the
  freshness-class layer, the refusal templates, the tripwire grouping key, the alert feed. In every
  case the tests asserted against a data shape production never emitted. This is a real lesson about
  integrating parallel work late, and it belongs in the design note as one, stated plainly.
