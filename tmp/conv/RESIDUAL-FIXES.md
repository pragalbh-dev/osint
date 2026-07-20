# Residual fixes — known, logged, deliberately deferred

**What this is.** Every defect and gap we found, understood, and chose *not* to fix before the
deadline. Each entry says what it is, whether it touches the demo, why we deferred it, and what the
fix actually is. Nothing here is a surprise — if one of these surfaces on the call, we can describe
it precisely rather than discover it live.

**Status key:** 🟢 no demo impact · 🟡 visible only if a reviewer goes looking · 🔴 demo-affecting.

---

## 1. 🟡 Mis-laned `equips` edge on hop 2 of the worked query

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

## 5. 🟡 Supersede date ordering compares upper bounds as strings

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

## 8. 🟡 The answer-key generator still contains the dropped sustainment items

`tools/generate/scenarios/hq9p_primary.yaml` (lines ~57/59/80/99/456) still declares
`sustain_spares` / `sustain_techdata` and the old flex. **Regenerating the answer key would
reintroduce all four removed items.** Trap, not a live defect. Also stale: `artifacts/plan/sessions/EVAL.md:61`, `config/entities.yaml:49`.

## 9. 🟡 Refusal body can print a Python list repr and a raw lens id

`backend/chanakya/agent/loop.py:183` builds a string that can render `['unit_paad','site_karachi']`
and `lens-hq9p-pk` into analyst-facing text. **Not currently reachable** — the new worked query
resolves — but it resurfaces on any lens with a missing anchor. Fix: render unresolved anchors as
node names, comma-joined; drop or humanise the lens id.

## 10. 🟢 `test_spa.py::test_placeholder_when_no_spa_build` fails locally

Asserts the placeholder appears when no SPA build exists; a stale `frontend/dist` (built by agents)
makes that case unreachable. **The only failing test.** SHIP must confirm the test's intent still
holds once the image bakes the build in — do not silently accept it red.

## 11. 🟢 D-P4.14 — the independence weight is applied twice

Once in `group_confidence` (magnitude) and again in `_effective_looks` (count) — stricter than
`spine/04:167-171` describes. **RAISED, NOT RATIFIED.** It is a credibility retune, so it needs an
explicit decision and must not be folded into another change.

## 12. 🟢 DATA-C / answer-key items

`mfr_taian` → probable (single-doc justification for a `confirmed` grade); the now-unsatisfiable
`FD-2000 same-as` oracle assertion (Phase 3 stopped drawing `same-as`); `import_2021` naming
mismatch; full id unification (eval still matches by name+type). None block the demo, but they
block anyone trusting the fragmentation/MISSING counts — which per the standing caveat come from a
probe that ignores edge endpoints and **should not be quoted as a score**.

## 13. 🟢 In-document coreference is built but gated off

Both halves shipped (`ingest/coref.py` + the RESOLVE honor policy); `config/resolution.yaml`
`coref_authoritative_evidence: []` keeps it inert by choice. Phase 3 shrank its value
(`unknown` 109→3). Turning it on needs an EVAL re-record.

## 14. 🟢 `deep_tier_confirmed` flex says "multiply attested" but it is single-bundle

The Taian/Wanshan chassis link appears in exactly one bundle (d24). The `confirmed` status is
defensible on the evidence-gate argument; the *wording* is not supported by the claim data.

---

## Also worth knowing (not defects)

- **The evaluation numbers are not a score.** The fragmentation/MISSING counts come from a probe
  that ignores edge endpoints. Do not present them as an accuracy figure.
- **Five mechanisms reached a green test suite while wired to nothing** — supersession, the
  freshness-class layer, the refusal templates, the tripwire grouping key, the alert feed. In every
  case the tests asserted against a data shape production never emitted. This is a real lesson about
  integrating parallel work late, and it belongs in the design note as one, stated plainly.
