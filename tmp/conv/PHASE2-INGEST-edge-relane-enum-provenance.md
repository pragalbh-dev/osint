# Handoff → PHASE 2 (INGEST): wire the edge re-lane + extraction enum (with the provenance rule)

**From:** Phase-1 fix (`fix/phase1-edge-vocab-and-entity-registry`). **Owns:** INGEST.
**Decisions:** DECISIONS §6 "EVAL" D-A; full sub-decisions in `tmp/conv/eval-rca/RCA-FIX-DECISIONS.md`.

## What Phase 1 delivered (ready to consume)
- `config/ontology.yaml` — every edge now declares `from`/`to` (domain/range) + `symmetric` + `extractor`.
  `manufactures` is **tightened** to Manufacturer→Variant, so Manufacturer→Component is unambiguously
  `supplies-component`. Every `extractor: true` edge has a unique `(from → to)` pair (no collisions).
- `backend/chanakya/ontology.py` — `EdgeLaneIndex(ontology)`:
  - `.extractor_edges()` → the 10 relationship edges the LLM may assert (the **enum**).
  - `.canonical_edge(subj_type, obj_type)` → the single edge those endpoints imply, or None.
  - `.relane(predicate, subj_type, obj_type)` → `RelaneResult{edge, action(kept|relaned|rejected),
    reversed, reason}`. Handles backwards-written facts (`reversed=True` ⇒ swap endpoints too).

## INGEST to do
1. **Narrow the extraction enum.** `extract.py`'s `EdgeTypeName` currently lists all 19 edges. Drive it
   from `EdgeLaneIndex.extractor_edges()` (the 10). `same-as`/`distinct-from`/`substitutable-by`/evidence/
   derived edges are **not** extractor edges — the LLM must not assert them as knowledge triples.
2. **Re-lane at write time.** After typing a triple's endpoints (use the co-extracted entity types for its
   subject/object), call `relane(predicate, subj_type, obj_type)`:
   - `kept`/`relaned` → use `result.edge`; if `reversed`, swap subject/object as well.
   - `rejected` → do **not** emit a first-class edge. Flag it as a tier-3 attribute (mirror
     `imagery.py:_flag_offontology` — e.g. `_rejected_predicate`/`_offontology`). Never invent a predicate.
3. **PROVENANCE RULE (non-negotiable — do not skip).** The claim appended to the immutable log MUST
   preserve the **as-stated predicate** (e.g. `_as_stated_predicate`) and the **verbatim source_quote**, and
   record the re-lane `reason`. Re-lane normalizes the *label* (so two sources of one fact land on one edge
   and corroborate); it must never silently overwrite what the source said. One click must still show:
   source quote → extractor label → canonical edge + why. (This is what makes re-lane a normalization, not
   an evidence rewrite — see RCA-FIX-DECISIONS D-A.2.)
4. **Order vs `edge_direction.py`.** `relane` handles **fully-typed** triples (name + orientation).
   `edge_direction.py` (the uncommitted INGEST module — see risk note below) handles the **partial-typing**
   residue (only one endpoint typable) via its scoring. Run `relane` first; fall back to `edge_direction`.
   Both read the same ontology `from`/`to` — one source of truth.
5. **Route identity to the merge channel.** Stated aliases / `distinct-from` (`OrgMention.aka`,
   `VariantMention.designators`, denials) go to the **merge-proposal channel RESOLVE reads**, not as
   `same-as`/`distinct-from` knowledge triples.
6. **Reconcile the ontology.** Your uncommitted branch left `manufactures` as `from`-only (polymorphic).
   Adopt Phase-1's tightened `manufactures` (from+to=variant) + the `extractor:` flags — the ratified D-A
   makes Manufacturer→Component always `supplies-component`. Resolve the `config/ontology.yaml` merge in
   favor of the Phase-1 superset.

## Also
- The frozen `claims/*.json` were extracted before this — re-record via
  `python -m chanakya.ingest extract --scenario hq9p_primary` (keyed) once wired.
- Extraction typing bugs + coverage gaps: `tmp/conv/PHASE2-INGEST-DATAC-extraction-typing-and-coverage-gaps.md`.
- The uncommitted `edge_direction.py` work: `tmp/conv/INGEST-edge-direction-UNCOMMITTED-risk.md`.
