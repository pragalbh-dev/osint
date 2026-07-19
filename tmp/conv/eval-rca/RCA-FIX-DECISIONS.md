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

## Phase-3 (RESOLVE) — `fix/phase3-resolve`

Plan: `phase3-resolve-PLAN.md`. Master defect: the edge/entity id-namespace split (RES-1).

- **D-3.1 — Endpoint-as-mention, resolved at the graph-construction layer.** A triple's subject/object is a
  *mention*, not a string: it is inducted through the same normalize + `AliasIndex` + scoring machinery as an
  entity-form claim, and `Edge.subject`/`Edge.object` are rewritten to entity ids **before** the fixpoint
  runs. *Only this ordering revives `relational_score`/`source_asserted_score` inside the resolver — a
  view-layer remap fixes the picture but leaves the scoring dead.* *Rejected:* populating the view's
  `to_canonical` map only (the original handoff's framing); it would have left RES-2 permanently broken.
- **D-3.2 — The registry is a resolution *prior*, not a lookup oracle; ids are re-derived, never persisted.**
  `config/entities.yaml` entries seed the candidate space as **claim-less** stable-id entities, so a registry
  entry becomes a view node only when a real claim resolves onto it and supplies the provenance (G4 holds: 0
  nodes without a `claim_id`). Resolution is one attach-or-mint pass; a cluster containing a registry entry
  adopts its stable oracle id, a new cluster mints a deterministic `ent:<type>:<name>`. *Determinism (G2):
  ids are a pure function of the claim set; the register grows via the append-only decision log and analyst
  promotion, not a mutate-during-rebuild.* *Rejected:* a persistent mutable register (makes rebuild N+1
  depend on rebuild N's writes).
- **D-3.3 — An endpoint's type comes from the entity it matches first, the edge's domain/range second.** An
  entity-form claim or registry entry is authoritative about what a surface form *is*; the ontology range is
  the fallback. *A mis-laned edge would otherwise re-type a known entity — it typed `HQ-9/P` as a
  `contract_import_event`.* Un-typable endpoints stay untyped tier-3 mentions; a match spanning a veto becomes
  an adjudication candidate, never a silent pick. *Rejected:* domain/range-only typing.
- **D-3.4 — The customs front-company shells stay unresolved; no oracle id invented.**
  `PHASE2-VERIFY-DELTA-AND-HANDOFF.md` instructed Phase 3 to resolve shell→`mfr_casic`/`unit_paad` so
  `import_2021` would form. **That instruction was refused.** The scenario's D7 design
  (`phase1-entity-registry-draft.md` §4) states the cluster is deliberately unresolved-to-any-subject-entity
  and that no id should be invented; there is no corpus signal (no alias, no `same-as`, no shared neighbour)
  linking them, and the types are incompatible. *Forcing it would assert an attribution the corpus never
  states — the disqualifying failure mode.* `import_2021` remains `[MISSING]` for an unrelated reason (oracle
  name vs corpus designator) — a DATA-C/EVAL id-unification matter, written up in
  `../RESOLVE-to-DATAC-EVAL-import-event-and-shells.md`. **Strike that line from the Phase-2 handoff.**
- **D-3.5 — Identity read from the claim stream, source-grade-weighted; `same-as` raise-only and undrawn,
  `distinct-from` veto and drawn.** Implements D-2.5. `source_asserted_score` is now the max asserting
  source's grade rather than binary. **Raise-only is enforced structurally** — `_band` tests auto-merge
  against a total that *excludes* the source-asserted term, so no future re-tune can let an asserted identity
  auto-merge (property-tested at weight 1.0). *The one planted false identity comes from a credible B-grade
  source, so credibility weighting can never be the safeguard — the hard veto is; grading re-ranks the queue,
  it does not re-decide it.* *Rejected:* flattening identity into `merge_proposal` records; relying on the
  `has_llm` flag alone (the source-asserted score could itself cross the auto line).
- **D-3.6 — Band geometry tuned to a stated symmetric invariant, not to examples.** `attribute 0.40 /
  relational 0.40 / temporal 0.05 / source_asserted 0.15`; `hitl_low 0.45`, `auto_merge 0.85` (unchanged):
  name-alone = neighbourhood-alone = `hitl_low` (always queued); deterministic ceiling = `auto_merge`, so the
  fuzzy path effectively cannot auto-merge and every auto-merge comes from a bootstrap rule.
  `temporal_consistency` was not dead but was a constant `+0.15` floor that made a printed `hitl_low` of 0.55
  behave like 0.40 — kept live at 0.05 with effective strictness unchanged, so *the numbers now mean what they
  say*. Added a containment / head-token / acronym-expansion bootstrap (veto-gated, min-2-token hook — a
  one-word hook bridged `China`→CASIC and walked at the PAAD/PAF trap). *Rejected:* every geometry raising the
  deterministic ceiling — each auto-merges customs contracts `KPQA-HC-2020-118834` and `-118835` (0.98
  name-similar, identical neighbourhood); scoring cannot tell a serial-number difference from a spelling
  variant, so that pair must stay a candidate (it now sits at 0.8416, just under the line).
- **D-3.7 — Places: match curated anchors only; never auto-mint the gazetteer.** `Partition.place_refs` +
  `NodeView.resolved_place_ref` finally give the computed match a writer, carrying `distance_m`/`band` as the
  *evidence* for the snap ("380 m" is a confident bind; "2.8 km" is one an analyst should eyeball). Proximity
  is gated on place-type/precision compatibility and geocode confidence (RES-5). A mention matching no anchor
  keeps its raw coord and stands as an honest pin. An exact match on a **seeded** `canonical_name`/alias may
  bind without a coordinate (config knob) — this anchors `site_rawalpindi`→`pl_nurkhan`; the withheld
  earned-merge traps (Chaklala; Rahwali's relative-bearing form) stay unreachable by string lookup, pinned by
  test. *`config/places.yaml` is the analyst's curated set — it is what distinguishes a main named anchor from
  an incidental pin; machine-writing to it destroys that curation and mutates a human-owned config. The
  gazetteer grows by analyst promotion.* *Rejected:* open-world place minting; back-filling an anchor's
  coordinate onto the node (that coordinate is the anchor's provenance, not the document's — copying it would
  launder a fix the source never asserted; the honest close is INGEST's MGRS parse).
