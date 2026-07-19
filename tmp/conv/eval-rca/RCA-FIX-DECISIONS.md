# RCA-fix — decision hub (the whole eval-RCA fixing effort)

Consolidated decision ledger for the end-to-end RCA fix. The master ledger (`DECISIONS.md` §6 "EVAL")
carries the headline ratifications D-A/D-B/D-C and points here for the build-time sub-decisions. Progress +
handoff index: `RCA-FIX-PROGRESS.md` (same folder). RCA root: `00-RCA-index.md`.

Format: **choice · principle invoked · alternative rejected**.

## Headline ratifications (full text in DECISIONS.md §6 "EVAL")
- **D-A — Edge-vocabulary collision fix.** Keep ratified edge names; add domain/range (`from`/`to`) +
  `symmetric`/`extractor`; constrain extraction to the enum; deterministic write-time re-lane by endpoint
  types; reject (don't invent) when endpoints fit no edge. *Extensible-not-hardcoded; model to queries.*
  *Rejected:* renaming edges (ambiguity is in the words, not the names; needless oracle/doc churn).
- **D-B — Entity canonical-id registry.** New 9th surface `config/entities.yaml` mirroring `places.yaml`;
  extractor emits surface+type, RESOLVE maps surface→id; alias table grows from HITL/auto merges.
  *Standardization; HITL learning loop.* *Rejected:* surface-form-only ids (the id-namespace split).
- **D-C — Eval-match bridge + id-unification target.** Eval matches by name+type now (bridge); target is one
  unified id namespace so id-exact falls out; answer_key reconciliation is a separate task.

## Build-time sub-decisions (this session)
- **D-A.1 — `manufactures` tightened to Manufacturer→Variant.** So Manufacturer→Component is uniquely
  `supplies-component` (what lets the chokepoint fire) and every extractor edge is endpoint-unique (zero
  collisions). *Model to queries; deterministic.* *Rejected:* leaving `manufactures` polymorphic
  (`from`-only, as INGEST's uncommitted branch had it) — re-introduces the collision. **Consequence:** the
  oracle's two `manufactures`→component edges get reconciled to `supplies-component` — a **separate
  DATA/EVAL task** (`../PHASE1-DATAC-EVAL-answer_key-reconciliation.md`), per D-C's "answer_key its own thing".
- **D-A.2 — Re-lane is order-agnostic + provenance-preserving.** It fixes name *and* orientation for
  fully-typed triples (`reversed` swaps endpoints); `edge_direction.py` is the partial-typing fallback. The
  appended claim MUST keep the as-stated predicate + verbatim quote + the re-lane reason — re-lane
  normalizes the *label* for corroboration, it never silently overwrites evidence. *Traceability
  non-negotiable; corroboration needs one canonical edge.* *Rejected:* rewriting the predicate in the
  immutable log with no trace (would corrupt the audit trail).
- **D-B.1 — Registry is an open-world prior, confirmed-aliases-only.** Seeds only corpus-attested/oracle
  aliases; withholds the earned-merge traps (Chaklala, relative-bearing forms) mirroring `places.yaml`;
  candidates-to-verify + ambiguities go to RESOLVE, not the seed. *Extensible; earn merges, don't hand them.*
- **D-C.1 — foreign_control / materiality NOT seeded in Phase 1 (the catch).** A registry-authoring pass
  seeded `foreign_control: true` on HT-233 et al.; **removed**, because the corpus never states sole-source/
  foreign-control (HT-233's maker is graded UNKNOWN) — seeding it to force a CONFIRMED chokepoint is
  un-sourced and violates the **disqualifying** traceability non-negotiable. Deferred to a Phase-2/3
  DATA+EVAL grounding on the hedged techdata-authority/no-substitute axis at PROBABLE.
  *No fabricated assessments in evidence-sparse cases (the non-negotiable).* *Rejected:* keeping the seeds
  (teaching-to-the-test). See `../EVAL-RCA-corpus-grounding-basing-and-materiality.md`.
- **RD — Reconciliation: Phase 1 kept self-contained.** Landed as its own branch/PR; INGEST's uncommitted
  `edge_direction.py` (complementary — direction vs name) is reconciled via handoff, not folded, so Phase 1
  doesn't couple to INGEST's larger in-flight work. *Clean ownership; keep the tested contract independent.*
  See `../INGEST-edge-direction-UNCOMMITTED-risk.md`.

## Answer-key grounding sub-decisions (session 2026-07-19, branch `fix/answer-key-grounding` off main)
Full analyst reasoning + exact edits: `handoff-answer-key-grounding.md`; complete node/edge sweep:
`ANSWER-KEY-GROUNDING-AUDIT.md`. Trigger: the complaint that the oracle asserts things "not makeable from
the data." Finding: ~85% of the key is cleanly sourced; the issues are one un-sourced edge + an
over-flattened basing cluster + cosmetics. These are DATA-C/EVAL edits (not a code agent's) — this session
produced the audit + handoff, did **not** touch `answer_key.json`.
- **D-G1 — Remove the `mfr_casic --manufactures--> comp_ht233 (confirmed)` edge.** The corpus (d22 IISS,
  d24 CSIS) states the HT-233 maker is **unknown** and explicitly warns against the export-agent/integrator
  → maker conflation; the key itself grades the maker `unknown` + mints `gap_ht233_maker`, so the edge
  self-contradicts. CASIC is reachable as *program design authority* via `var_hq9p`; HT-233's maker stays
  gap/possible (23rd RI). *Confirmed=sourcing-not-plausibility; export-agent≠manufacturer; no fabricated
  assessments (the non-negotiable).* *Rejected:* the prior Item-1 re-lane-only (`manufactures`→
  `supplies-component`) — relabelling leaves a *confirmed* CASIC→HT-233 supply edge that is still
  un-sourced. **This supersedes `../PHASE1-DATAC-EVAL-answer_key-reconciliation.md` Item 1.**
- **D-G2 — Soften the three `based-at` unit→site edges to observed-occupancy + derived unit-attribution.**
  No doc states a named unit at a named site; each is equipment@site (imagery) + a hedged formation
  reference. Model both layers at their own confidence (Karachi confirmed-occupancy/strong-attribution;
  Rawalpindi confirmed-2021→derived-stale; Rahwali probable→confirmed via 2 independent signals); keep d20
  rumor-grade. *Observed≠inferred; basing is earned-not-stated in this target set.* *Rejected:* enriching
  the corpus to state basing outright — it would contradict the scenario's own "Pakistan never discloses
  ORBAT" backbone (d01/d02/d03/d17/d19) and re-introduce teaching-to-the-test. RESOLVE/SCORE own the
  derivation (RES-1, SC-2/SC-4).
- **D-G3 — Hedge cosmetic over-resolutions.** `unit_paad` "regiment"→"unit/formation" (d02 says unit);
  `unit_hq9b` branch is Army-leaning/ambiguous in sources, not cleanly PAF; `sustained-by` should hang off
  the PAF spares tender (d06), not the Army unit. *State only what the source states.*
- **D-G4 — Materiality: no answer_key change.** The key already grades the chokepoint `candidate` (honest);
  do **not** seed `foreign_control`/`SOLE_SOURCE` to force CONFIRMED (upholds D-C.1). If material at all,
  rest it on the hedged techdata-authority (d21) + no-open-substitute-chassis (d24) axis at **probable**.
  *Absence of evidence ≠ evidence of absence.* Config-side owner: SCORE (no credibility retune).
