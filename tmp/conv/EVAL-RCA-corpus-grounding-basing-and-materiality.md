# EVAL RCA → DATA agent + EVAL agent: oracle expectations not grounded in the corpus

**Author:** EVAL RCA / Phase-2 analysis session (`feat/eval`). **Date:** 2026-07-19.
**Scope boundary:** These are **data / expectation issues** — the frozen corpus does not state facts the
`answer_key.json` grades for. Per working rule, the **data agent** (corpus/answer_key) and the **eval
agent** (oracle assertions) resolve them; the analysis session does **not** edit the corpus or answer_key.
Grounding below was verified by direct read of the `hq9p_primary` docs (verbatim quotes + line refs).

**Why this matters:** two Phase-2 fixes in the RCA (ING-2 `based-at` transform; DC-3 materiality seeding)
look like extraction/config bugs, but the real blocker is that **the source documents never assert the
graded fact**. Trying to make the pipeline emit them would mean either fabricating a value or hand-seeding
config to hit the oracle — which violates the traceability non-negotiable (every node/edge one-click
traceable to a source that actually says it). So this is a corpus-vs-oracle reconciliation, not a code fix.

---

## Item 1 — Unit→Site `based-at` edges are not stated by any document  [DATA + EVAL, P0]

**Oracle expects** (see `00-evidence-summary.md` lines 174-176):
- `unit_paad --based-at--> site_karachi` (want **confirmed**)
- `unit_hq9b --based-at--> site_rawalpindi` (want **stale**)
- `unit_hq9b --based-at--> site_rahwali` (want **confirmed**)

**Corpus reality:** no document names a *unit* stationed at a *site*. Every occupancy/imagery/relocation
doc states **equipment at a place** (a sighting) and, at most, a **hedged association** to a formation —
never a unit-designator-to-site basing fact:
- `d07_sat_confirm_karachi` — "…reportedly part of **Pakistan Army Air Defence Command's** continuing
  long-range SAM buildout" (loose, "reportedly"; the site is equipment-defined, no unit named).
- `d17_rawalpindi_2021` — "assessed … as an **HQ-9B battery element** occupied through the reporting
  period at the former Chaklala airfield site, now PAF Base Nur Khan" (a generic "battery element" — an
  equipment read, no unit designator).
- `d19_rahwali_confirm` — "first collection cycle to **associate** a … HQ-9BE … battery **with** the
  location" ("associate", not "based at").
- `d09_official_routine` — "training activity … in the general area east of Karachi" (no unit ID, no site).
- `d20_supersede_spoof` — the Rahwali→Rawalpindi relocation is an **unverified social rumor** ("sources
  telling me…", "cannot confirm", "single unverified source").

**Consequence for the pipeline:** the `unit --based-at--> site` edge is a **derived/resolved** fact
(resolve a battery-sighting + a hedged formation reference into a unit, then attach it to a site), not a
**stated** fact. INGEST (whose contract is *extract only what is literally stated, never infer*) cannot
honestly emit it. RCA finding ING-2 mis-assigns `based-at` to INGEST; it belongs to RESOLVE/SCORE as a
derived edge, at **probable** confidence, not a confirmed stated edge.

**Decision needed (pick one, or split by edge):**
- **(a) DATA enriches the corpus** — add/adjust a doc that actually states a named unit at a named site
  (then it extracts honestly and lands at the confidence the source supports). Only do this if a
  real-world OSINT product would plausibly state it; a fabricated ORBAT line is worse than a soft oracle.
- **(b) EVAL softens the oracle** — model `based-at` as *equipment@site sighting* (stated, high
  confidence) + *unit↔equipment↔site association* **derived** by RESOLVE/SCORE at **probable** (not
  confirmed). This matches what open sources actually support and is the more honest demo.
- **Recommendation:** (b) as the primary, with the `based-at` edge owned by RESOLVE/SCORE (derived), and
  the oracle's expected status set to what the hedged evidence supports. Keep the *relocation* (d20) as a
  **rumor-grade** input that must NOT flip a confirmed basing — that's a credibility-triage flex, not a
  bug.

---

## Item 2 — Chokepoint / materiality inputs are not stated by any document  [DATA, P0 · reconciles DC-3]

**Oracle/materiality expects** `comp_ht233` to surface as the **single point of failure** (chokepoint);
DC-3 wants `foreign_control` attrs + `substitutable-by` edges seeded so it confirms. CONFIRMED-chokepoint
requires a `SOLE_SOURCE` / evidence-backed `foreign_control` input (see `handoff-data-c.md` DC-3).

**Corpus reality:** the documents do **not** state that the HT-233 (or the interceptor) is sole-sourced,
foreign-controlled, or non-substitutable. In fact they state the opposite about its maker:
- `d22_deep_tier_supplier` — "The **manufacturer of the HT-233** should therefore be treated as
  **unconfirmed/unknown** pending better sourcing." (This is exactly the oracle's own `gap_ht233_maker`.)
- The only supports are **hedged** and are about *sustainment control*, not *manufacturing sole-source*:
  - `d21_techdata_authority` — re-certification is "**said to** be routed through a Chinese state
    technical-data authority … which retains **configuration control** over the underlying software
    baseline" ("said to", "would imply").
  - `d24_tel_chassis_attribution` — "there is **no open indication of a substitute chassis**; the launcher
    platform is therefore a **confirmed Taian/Wanshan supply relationship**" (absence of open reporting on
    a substitute ≠ an assertion that no substitute exists).

**Consequence:** hand-seeding `foreign_control: true` on `comp_ht233` in config to force CONFIRMED would be
teaching-to-the-test and un-traceable (no source says it). There is also an **internal oracle tension**:
HT-233's maker is graded as an *unknown* (`gap_ht233_maker`) while HT-233 is simultaneously graded as a
*confirmed* chokepoint — reconcile which axis the chokepoint rests on.

**Decision needed:**
- **(a) Ground the chokepoint on the axis the corpus supports** — the durable/force-revalidated
  **techdata-authority configuration-control** (d21) and the **no-open-substitute chassis** (d24), *with
  their hedges preserved*, so materiality lands at the confidence the evidence supports (likely
  **probable**, not confirmed). If EVAL wants "confirmed", the oracle's expected status must move to match
  the hedged evidence — or —
- **(b) DATA authors corpus text** that actually states a sole-source / no-domestic-substitute fact for a
  component that plausibly has one (then it extracts honestly). Prefer the *techdata-authority* angle over
  a fabricated manufacturing sole-source, since the former is already hedged-present in d21.
- **Do NOT** seed a bare `foreign_control` attr with no source behind it. The DATA-owned honest move is to
  make the corpus/answer_key agree on a *stated, hedged* dependency and let SCORE's (already-correct)
  materiality precompute derive the status.

---

## Cross-refs
- Corpus grounding: verbatim reads of `corpus/scenarios/hq9p_primary/docs/{d07,d09,d17,d19,d20,d21,d22,d24}.txt`.
- RCA: `handoff-ingest.md` (ING-2), `handoff-data-c.md` (DC-3), `00-evidence-summary.md` lines 156-178
  (oracle-edge→view table), 68-113 (fragmentation), 250-253 (relocation observable).
- Related open punch-list: `PHASE2-INGEST-DATAC-extraction-typing-and-coverage-gaps.md` (coverage-gap
  section already flags `gap_ht233_maker`, `import_2021`, `sustain_techdata`, `comp_interceptor` as
  "no surface form — decide corpus-vs-extraction"; Item 2 here resolves the HT-233 side of that).
