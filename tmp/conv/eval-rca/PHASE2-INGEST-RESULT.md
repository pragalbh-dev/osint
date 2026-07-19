# PHASE-2 INGEST extraction rework — result

**Branch:** `fix/phase2-ingest-extraction` (stacks on Phase-1 edge-vocab/entity-registry + C edge_direction).
**Scope:** the seven tasks in the ratified handoff, with the two corrections (denials → drop, identity →
leave as-is) applied exactly.

## What changed (files)

- **`backend/chanakya/ingest/extract.py`** — the bulk of the work:
  - **Enum narrowing (task 1).** `RelationMention.relation` is now a plain `str`; the allowed values are
    injected into the tool schema at build time from `EdgeLaneIndex.extractor_edges()` via the new
    `_constrain_relation_enum()` (called in `extract_document`). The hardcoded 19-value `EdgeTypeName`
    literal + its dead `_EDGE_TYPE_SET` are removed. Identity/evidence/derived edges are no longer
    assertable through the `relations` slot.
  - **Write-time re-lane + endpoint recovery (task 2) + provenance rule (task 3).** New `_Emitter.relation()`
    method. The emitter now tracks a per-document `name -> entity_type` map (populated by `entity()`), so a
    relation's endpoints are typed from the entities the same document emitted; structural transforms pass
    types directly. Both-typed → `relane()` (name + orientation); one-typed → `edge_direction.reversed_for_types()`
    (orientation only, as-stated predicate kept); neither-typed → keep as-stated + tier-3 `_endpoint_typing`
    flag. Rejected endpoints → a tier-3 `_rejected_relation` note on the subject node, never an edge.
    Re-laned claims carry `_as_stated_predicate` + verbatim `source_quote` + `_relane_reason`.
  - **Denials dropped (task 4).** The prose `denials` loop and the social `negations` loop no longer emit
    triples. Zero denial-derived edges / `unknown` nodes.
  - **Identity untouched (task 5).** `same-as`/`distinct-from` from `aka`/`designators`/`aliases`/`distinctions`
    still emit verbatim via `triple()` (the raw path — never re-laned).
  - **Imagery gaps (task 6).** `transform_imagery_geoint` mints a `known_gap` node **only** when a
    `missing_slot` is stated, keyed by the slot (never the verbose sentence). No slot ⇒ no node.
  - **Structural transforms (task 7).** Customs types consignee/shipper as `trading_org` (not
    `manufacturer`), and mints a `contract_import_event` node + `exported-by`→shipper / `imported-by`→consignee
    edges (deterministic role projection, emitted verbatim). Tender mints `interceptor_stockpile` /
    `techdata_authority` nodes from two new optional schema fields — **nodes only, no `sustained-by`**.
- **`backend/chanakya/edge_direction.py`** — added the public `reversed_for_types(predicate, subj_type,
  obj_type, rules)` (the partial-typing orientation helper), refactored to share `_orientation_score`.
- **`config/ontology.yaml`** — added the `trading_org` node type (ING-3). No edge references it → no
  domain/range collision.
- **Tests** — `backend/tests/ingest/test_extract.py` updated (customs → `trading_org` + import node/edges;
  social negation → no edge). New `backend/tests/ingest/test_phase2_relane.py` (12 tests) covering enum
  narrowing, re-lane + provenance, backwards/rejected/untypable relations, denials, identity, imagery gaps,
  and the tender sustainment nodes.

## Decisions that leaned on a guiding principle

1. **Denials are dropped, not retained as negative-polarity claims.** *Principle:* the graph must not be
   polluted with junk (RCA ING-1); "record it, drawn nowhere" is preferred but only if possible.
   *Rejected alternative:* keep the negation as a negative Triple. *Why rejected:* `view/pipeline.py` draws
   **every** triple as an edge (no polarity filter) and mints `unknown` nodes from edge endpoints, so a
   retained negation would still create junk. The task's sanctioned fallback ("drop entirely if retaining
   would create a junk node") applies. No consumer reads denials, so nothing is lost downstream.
2. **Customs role-edges (`exported-by`/`imported-by`) are emitted verbatim, NOT re-laned.** *Principle:*
   re-lane normalizes unreliable *LLM verbs*; a deterministic structural projection is not an LLM assertion.
   *Rejected alternative:* route them through `relane()` with `trading_org` endpoints. *Why rejected:* the
   ontology ranges these edges at contract→manufacturer / contract→unit, so `relane(contract, trading_org)`
   would **reject** them; and broadening both edges' `to` to include `trading_org` would create a
   `(contract, trading_org)` **collision** in `EdgeLaneIndex` (breaks `test_no_endpoint_collisions`). The
   role *is* the edge; the generic `trading_org` endpoint is intentional (shell→end-user linking is RESOLVE's).
3. **A rejected relation is recorded as a tier-3 note on the subject node.** *Principle:* provenance is not
   optional — "do not drop the provenance." *Rejected alternative:* emit the rejected triple flagged (mirror
   the old `_offontology` flag-but-emit). *Why rejected:* that still draws an ad-hoc-predicate edge, which the
   task forbids. Known limitation: the note rides in the tier-3 bag, which `dedup` excludes from its
   signature, so through the full lane it can merge into an un-noted restatement of the same subject. The
   primary guarantee (no ad-hoc edge, no `unknown` node) holds regardless; rejected relations are rare.
4. **`trading_org` added as a config node type, not hardcoded.** *Principle:* config-driven & extensible.
   Reserves `manufacturer` for real OEMs; gives RESOLVE a clean shell-org starting type (ING-3).
5. **Tender sustainment captured via two new all-optional schema fields.** *Principle:* schema-flexible,
   extract-what-is-stated, transform-by-fixed-table (never keyword-inference over raw strings). Maps cleanly
   to the declared `interceptor_stockpile` / `techdata_authority` node types.

## Deliberately deferred (out of this task's lane)

- **Identity rendering / consumption → Phase 3.** View-side "don't draw `same-as` as a knowledge edge" and
  RESOLVE-side "consume aliases as source-weighted merge/veto" are Phase-3. INGEST keeps emitting the
  sourced identity claims (verified they still emit).
- **`sustained-by` and `based-at` → derived, not INGEST.** `sustained-by` is SCORE's Phase-4 rollup (nodes
  only here). No `based-at` transform added: no corpus doc states a unit stationed at a site, so a
  deterministic `based-at` would require inventing the unit (that edge is RESOLVE-derived, Phase 3).
- **VLM co-load (ING-8) + real per-doc date-stamping (ING-7)** are separate tasks, untouched.
- **Re-recording the frozen `claims/*.json`** — needs API keys + is non-deterministic; a separate follow-up.
  All validation here is via unit tests over synthetic filled-dicts (the transforms are pure functions).

## Test results

- `backend/tests/ingest` + `backend/tests/test_ontology.py`: **247 passed, 4 skipped**.
- Full backend suite: **568 passed, 6 skipped** (1 pre-existing httpx deprecation warning, unrelated).
- `ruff check` clean on the changed files; `mypy` shows only pre-existing errors (third-party stub gaps +
  the pre-existing `_emit` `str`→`Literal` args, untouched by this change).
