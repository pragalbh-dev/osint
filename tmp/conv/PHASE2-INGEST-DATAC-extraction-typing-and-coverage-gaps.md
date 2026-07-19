# Handoff → PHASE 2 (INGEST + DATA-C): extraction typing bugs + coverage gaps

**Source:** surfaced by the Phase-1 entity-registry compilation pass. Full detail (per-item evidence,
doc/claim ids) is in `tmp/conv/eval-rca/phase1-entity-registry-draft.md` §3 (ambiguities) and §4
(coverage note). Do NOT fix the frozen corpus/answer_key unilaterally — these are for the owning phase.

## Extraction typing bugs (INGEST — Phase 2)
- **Pakistan Army / PAF entities mistyped as `manufacturer`.** They are `unit`s. This fragments the
  unit entities (`unit_paad`, `unit_hq9b`) and pollutes the manufacturer set. Root fix rides with the
  ontology domain/range + enum work (Phase 1/2): type must come from the constrained schema, not free text.
- **The single `contract_import_event` node is the wrong event.** The real `import_2021`
  (China→Pakistan HQ-9/P transfer) is not correctly captured; a different/incidental event was typed as
  the contract node instead. Needs the deterministic supply-chain transform (ING-2) to emit the right
  `contract_import_event` + `exported-by`/`imported-by` edges.

## Coverage gaps — oracle ids with ZERO corpus surface forms (DATA-C + INGEST — Phase 2)
- `gap_ht233_maker`, `sustain_techdata`, `import_2021`, `comp_interceptor` — no surface form found in the
  extracted claims. Decide per-id: is it a corpus gap (doc doesn't support it → DATA-C seeds/annotates)
  or an extraction drop (doc supports it but LLM missed it → INGEST transform/prompt)?

## Out-of-scope-but-relevant clusters (DATA-C note)
- CPMIEC and the front-company shells surfaced but sit outside the current registry scope; note for
  the export-agent / trading-org typing (ING-2 "type customs consignee as trading-org").

**Action:** Phase-2 agents read the draft §3/§4, decide corpus-vs-extraction per item, and resolve there.
