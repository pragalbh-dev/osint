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

## Answer-key grounding sub-decisions (session 2026-07-19)
Full analyst reasoning + exact edits: `handoff-answer-key-grounding.md`; complete node/edge sweep:
`ANSWER-KEY-GROUNDING-AUDIT.md`; downstream derivation: `handoff-resolve-score-grounding.md`. Trigger: the
complaint that the oracle asserts things "not makeable from the data." Finding: ~85% of the key is cleanly
sourced; the issues are one un-sourced edge + an over-flattened basing cluster + cosmetics.

**STATUS: APPLIED to `answer_key.json` on branch `fix/answer-key-grounding-apply` (2026-07-19), at the
user's direction** — the ratified DATA/EVAL reconciliation (no *code* agent touched the oracle). The audit
+ handoff landed first on `fix/answer-key-grounding` (PR #30, merged). D-G1 resolved to **A1 (remove)**
after checking the ontology; RESOLVE/SCORE (+ a newly-found ASK coupling) are handed off, not applied here.
- **D-G1 — Remove the `mfr_casic --manufactures--> comp_ht233 (confirmed)` edge.** The corpus (d22 IISS,
  d24 CSIS) states the HT-233 maker is **unknown** and explicitly warns against the export-agent/integrator
  → maker conflation; the key itself grades the maker `unknown` + mints `gap_ht233_maker`, so the edge
  self-contradicts. CASIC is reachable as *program design authority* via `var_hq9p`; HT-233's maker stays
  gap/possible (23rd RI). *Confirmed=sourcing-not-plausibility; export-agent≠manufacturer; no fabricated
  assessments (the non-negotiable).* *Rejected:* the prior Item-1 re-lane-only (`manufactures`→
  `supplies-component`) — relabelling leaves a *confirmed* CASIC→HT-233 supply edge that is still
  un-sourced. **This supersedes `../PHASE1-DATAC-EVAL-answer_key-reconciliation.md` Item 1.**
  **Resolution = A1 (remove), APPLIED.** *A2 (re-type to `design-authority-for`) rejected on inspection:*
  the ontology locks `design-authority-for` to `techdata_authority → variant`, so a manufacturer→component
  design-authority edge would be an ontology contract change (widening domain/range, re-opening Phase-1
  edge-uniqueness, pulling in INGEST) — bigger blast radius, not smaller. A1 is ontology-clean: a
  manufacturer reaches a *component* only via `supplies-component` (a maker claim), which CASIC can't
  confirmably make, so it correctly has no direct radar edge. Also **applied:** re-laned
  `mfr_23rd_ri manufactures comp_ht233 (possible)` → `supplies-component (possible)`; `worked_query`
  expected_path now **terminates at `comp_ht233`** (chokepoint), CASIC reached as program prime via
  `var_hq9p`; `expected_answer` already honest (unchanged). **Coupling found:** ASK's hero-path code
  (`agent/loop.py`) embeds the same false narrative (defaults the chokepoint maker to `mfr_casic`) — ASK
  fix needed (does not break this PR; fixture-based tests untouched). See `handoff-resolve-score-grounding.md`
  §ASK-coupling + `handoff-ask.md`.
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
- **D-G5 — ASK grounding follow-on kept as its own handoff, bundled post-Phase-4.** D-G1 removed the
  un-sourced CASIC→HT-233 maker edge from the oracle, but ASK's deterministic hero path still *speaks* it:
  `agent/loop.py:170-171` looks up the maker via `manufactures` (which post-D-A can never match a component)
  and then falls back to the literal `"mfr_casic"` — an unconditional, un-sourced attribution. Written up as
  `handoff-ask-grounding.md` (ASK-G1 blocks-demo, ASK-G2/G3 major) rather than fixed here.
  *An honest store + a confabulating answer layer is still a fabricated assessment (the non-negotiable);
  clean ownership — ASK owns its surface.* *Rejected:* folding the ASK fix into the answer_key PR (would mix
  a DATA/EVAL oracle change with ASK code + 4 coupled test files, and ASK's tests are fixture-based so they
  stay green either way — no urgency to couple them). **Bundle into the post-Phase-4 ASK work alongside
  `handoff-ask.md`**, whose "honest refusal" machinery is the same mechanism ASK-G1 needs.
  NB: D-2.7 (INGEST) independently reached the same conclusion for `based-at` — "no doc states unit→site;
  it is derived" — which corroborates D-G2 from the extraction side.

## Phase-2 build-time sub-decisions (INGEST — extraction rework, commit 80a8702)
- **D-2.1 — Extraction enum driven from `EdgeLaneIndex.extractor_edges()`, injected at tool-schema build.**
  `RelationMention.relation` is now a plain `str`; the allowed edge set comes from the live ontology, not a
  hardcoded literal. *Config-driven/extensible; single source of truth.* *Rejected:* keeping the 19-value
  `EdgeTypeName` literal (drifts from the ontology; re-introduces off-vocab predicates).
- **D-2.2 — Re-lane at write time, endpoints authoritative.** Endpoint types are recovered from the
  entities the *same document* emitted (an `_Emitter` name→type map); both-typed → `relane()` (name +
  orientation); one-typed → `edge_direction.reversed_for_types()` (orientation only, predicate kept);
  neither-typed → keep as-stated + tier-3 flag. Rejected endpoints → tier-3 note, **never** an ad-hoc-
  predicate edge. *Deterministic; model-to-queries.* *Rejected:* trusting the LLM's verb.
- **D-2.3 — Provenance rule (non-negotiable).** A re-laned claim preserves `_as_stated_predicate` + verbatim
  `source_quote` + `_relane_reason`. *Traceability non-negotiable — normalize the label, never overwrite the
  source.* *Rejected:* silently rewriting the predicate.
- **D-2.4 — Denials/negations DROPPED (not routed to the merge channel).** The edge-relane handoff's
  "denials → merge-proposal channel" is a **category error** (a denial is not an identity assertion) and is
  overridden. Denials no longer emit any edge or `unknown` node; because `view/pipeline` draws *every*
  triple, even a retained non-rendered negative triple would still pollute, and nothing consumes denials
  today, so they are dropped outright. *Minimal correct path; kill the junk.* *Consequence:* the "X denied Y"
  text is fully removed from the evidence log — the **richer contradiction-scoring path (roadmap / design
  note)** would need to re-enable a proper negative-evidence channel. *Rejected:* misrouting to merge; or a
  new non-triple negative-claim type now (deferred to the richer path).
- **D-2.5 — Identity kept as source-weighted evidence claims; view/RESOLVE handling deferred to Phase 3.**
  `same-as`/`distinct-from` (incl. `aka`/`designators`) still emit verbatim as claims (they carry the
  asserting source's grade). Target design (Phase 3): `same-as` → a merge signal, **not drawn**;
  `distinct-from` → veto **and** drawn; RESOLVE reads them from the *claim stream* weighted by source.
  *Bi-level model: identity is evidence-layer, the merge is knowledge-layer.* *Rejected:* flattening identity
  into decision-log `merge_proposal` records (loses source credibility weighting — refines the P1 handoff);
  ripping identity out of extraction.
- **D-2.6 — Customs role-edges emitted verbatim, NOT re-laned.** `exported-by`(→shipper)/`imported-by`
  (→consignee) come from the *document field* the value sat in — the role IS the edge. Endpoint types
  cannot disambiguate them (both ends are `trading_org`); broadening both edges' ranges to include
  `trading_org` would create an `EdgeLaneIndex` collision. INGEST emits contract→shell only; the transient
  range mismatch (shell vs the ontology's manufacturer/unit range) resolves in Phase-3 when RESOLVE maps
  shell→real entity. *Structural transforms are document-determined, not endpoint-determined; extract-raw
  guardrail.* *Rejected:* routing role-edges through `relane()` (rejects them); range-broadening (collision).
- **D-2.7 — `trading_org` node type added; `based-at`/`sustained-by` NOT emitted by INGEST.** Customs
  consignee/shipper are typed `trading_org` (new ontology node type), reserving `manufacturer` for OEMs.
  `based-at` is **not** extracted (no doc states unit→site; it is derived — Phase 3) and the `sustained-by`
  edge is **not** emitted (SCORE-derived rollup — Phase 4); INGEST mints the `interceptor_stockpile` /
  `techdata_authority` **nodes** only. *Extract only what is stated; keep derivations in the deriving layer.*
  See `../EVAL-RCA-corpus-grounding-basing-and-materiality.md`.
- **D-2.8 — Collection gaps: no verbose-sentence nodes.** `known_gap` entity nodes are minted only when a
  `missing_slot` is stated, keyed by the slot — never the raw sentence. The SCORE sufficiency-template engine
  already emits the correctly-shaped `gap:*` items. *One mechanism, not a duplicate.* *Rejected:* keying a
  node by the full `GapMention.description`.
- **Known minor limitation:** a *rejected* relation's tier-3 note lives in `ClaimRecord.attributes`, which
  `dedup` excludes from its signature, so through the full lane the note can be absorbed into a restatement.
  Primary guarantees (no ad-hoc edge, no `unknown` node) hold; rejected relations are rare. Logged, not fixed.
- **D-2.9 — Keyed re-record takes the pymupdf PDF path (withhold `AZURE_*`).** The re-record crashes on the
  one corpus PDF (d25) when Azure OCR creds are in-env but `azure-ai-documentintelligence` is not installed
  (the loader selects the Azure path → `ModuleNotFoundError`). d25 is **born-digital**, so withholding
  `AZURE_*` takes the keyless pymupdf text path (pages still render for the VLM lane). Re-record with only
  `GEMINI_API_KEY`/`ANTHROPIC_API_KEY` exported. *Keyless≡live reproducibility; no optional-dep coupling on
  the extract path.* *Rejected:* installing the Azure extra just to read a born-digital PDF. See
  `PHASE2-VERIFY-DELTA-AND-HANDOFF.md`.
