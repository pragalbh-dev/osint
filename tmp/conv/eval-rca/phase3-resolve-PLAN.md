# Phase-3 (RESOLVE) — implementation plan

**Refines** `handoff-resolve.md` (RES-1…RES-5). Where this plan and the handoff disagree, **this plan wins** —
it folds in the orchestrator design review of 2026-07-19 that reframed the master fix and settled four
open calls the handoff left implicit. Read `handoff-resolve.md` for the original evidence/probes; read this
for *what to build and why*.

**Owner:** RESOLVE. **Branch off** `fix/phase2-ingest-extraction` (which sits on the Phase-1 fix) — Phase 3
needs the registry (`config/entities.yaml`) + `ontology.py` domain/range (Phase 1) **and** the Phase-2
extraction rework (structural edges, identity-as-source-weighted-claims, denials/gaps no longer emitting
nodes). See §0 for the one caveat (the frozen bundles are pre-re-record).

---

## 0. State of the world (so nobody re-derives it)

- **Phase 1 = DONE.** `config/entities.yaml` (14 entities / ~76 aliases + entity-id `distinct_from` traps),
  `backend/chanakya/ontology.py` `EdgeLaneIndex` (per-edge domain/range + extractor enum + re-lane),
  `ConfigBundle.entities: EntitiesConfig` (declared, schema comment literally says *"RESOLVE consumes at
  rebuild"*). **But nothing in RESOLVE reads `config/entities.yaml` yet** — `ResolveConfig.from_bundle`
  only takes `config.resolution` + `config.places`. Wiring that is step P3.0.
- **Phase 2 (INGEST) = CODE-COMPLETE** on `fix/phase2-ingest-extraction` (edge re-lane + extraction enum,
  provenance, structural transforms — customs `contract_import_event` + `exported-by`/`imported-by` +
  `trading_org`, tender `interceptor_stockpile`/`techdata_authority`; denials/gap-sentences no longer emit
  nodes/edges). **One gate remains: a keyed re-record of `claims/*.json`.** Until that runs, the frozen
  bundles under `corpus/scenarios/hq9p_primary/claims/` are the *pre-Phase-2* extraction — so build/verify
  RES-1/3/5 against them now (the 109 `unknown` still collapse), and re-verify once the bundles are
  re-recorded. **Phase 2 deliberately deferred identity handling to Phase 3 (decision D-2.5)** — see P3.2.
- **Oracle is being re-grounded in parallel** (answer-key grounding audit, merged PR #30): D-G1 removes the
  un-sourced `mfr_casic→comp_ht233` edge, D-G2 softens the 3× `based-at` to observed+derived. Verify Phase-3
  fragmentation/edge expectations against the *updated* `answer_key.json`, not the RCA-era snapshot.
- **What works, do not touch:** union-find + collapse + finalise, the distinct-from traps, SCORE's
  credibility/status machinery (`credibility.yaml` stays frozen). This plan adds *inputs* to the resolver
  and *outputs* to the partition; it does not rewrite the fixpoint.

---

## 1. The one idea (RES-1, reframed)

The whole Phase-3 master fix is a single reframe, and every sub-item hangs off it:

> **An edge endpoint is a *mention*, and resolution is one attach-or-mint process. RESOLVE is the id-minting
> authority. The registry is accumulated resolved-state, not a name-lookup oracle.**

Concretely:

- Entity-form claims already go through resolution (normalize → candidate-gen → scoring → union-find → mint
  id / attach via `entity_canonical`). **Triple endpoints never did** — `entities.build()` stores
  `Edge(subject=p.subject, object=p.object)` as raw LLM strings, so they were never inducted as mentions.
  That is the *entire* source of the 109 `unknown` nodes and the dead relational/source-asserted scores.
- The fix is to run endpoints through the *same* process: each endpoint becomes a mention, scored against
  the current entity set (which now includes the seeded registry), and it either **attaches** to an existing
  minted entity (its edge endpoint is rewritten to that id) or **mints a new node**.
- **Do it at the graph-construction layer, not as a view-only remap.** If you only populate the view's
  `to_canonical` map at the end, the *view* connects but the *resolver's own* `relational_score` /
  `source_asserted_score` stay 0 (they read `graph.edges` endpoints and compare to `eid`). Reviving those is
  what makes RES-2 mostly evaporate — so endpoints must carry entity ids *inside* `EntityGraph`, before
  `merge_score` runs.

Two refinements that make it airtight (both only possible because Phase 1 landed):

1. **Type each endpoint from the edge.** An endpoint has a name but no type. Phase-1's domain/range gives
   the type from the predicate (an `equips` subject *is* a `component`). So a *minted* endpoint node is a
   **typed** node, not `unknown`. Use `OntologyConfig.edge_types[...].from_types()/to_types()` (or a small
   `EdgeLaneIndex` helper exposing predicate → (from_types, to_types)). If only one endpoint is typable, the
   existing `edge_direction.py` net is the fallback.
2. **The registry seeds candidates, it never fabricates nodes.** Seed the registry entries into the
   resolver's candidate space (stable id + type + aliases) so mentions can attach and clusters adopt the
   stable id (`var_hq9p`). But a registry entry becomes a *view node* **only if a real claim resolves onto
   it** (contributing its `claim_id` as provenance). Never draw a node the corpus didn't attest — gate G4 /
   the traceability non-negotiable holds.

**Settled call — id lifetime: re-derive, do not persist.** Ids are a deterministic function of the claim
set each rebuild: a cluster containing a registry entry adopts its stable id; a brand-new cluster derives
`ent:<type>:<name>` from its preferred member. Nothing is written back to `entities.yaml` by the pipeline.
The register "grows" only through (a) the append-only decision log replayed each rebuild and (b) analyst
promotion (below) — never a live mutate-during-rebuild. Keeps gate G2 determinism intact; the persistent-
register / incremental-resolution variant is explicitly *out of scope* (bigger architectural commitment than
the demo needs; revisit as an adaptation feature).

---

## 2. Work items (in build order)

### P3.0 — Plumb the registry into RESOLVE  *(prereq for everything)*
- Add `ResolveConfig` access to `config.entities` (mirror the `places` accessor).
- Seed registry entries into the entity graph as **candidate** entities: `entity_id` → stable id, `type`,
  `canonical_name`, `aliases` (fold aliases into `AliasIndex` so a surface form that equals a registry alias
  is alias-equivalent → bootstraps at confidence 1.0), and `distinct_from` → veto pairs (entity-id level).
- **Verify:** existing 5 merges still fire; the golden/empty-config path is unchanged (gate G2).

### P3.1 — RES-1 endpoint-as-mention  *(the master fix)*
- In `entities.build()` (or a dedicated pass right after), for every triple: synthesize `subject`/`object`
  as mentions typed via domain/range; resolve each through candidate-gen + scoring; rewrite `Edge.subject`/
  `Edge.object` to the resolved **entity id** (attach) or a freshly minted **typed** id.
- Consequences that fall out for free: `relational_score` + `source_asserted_score` revive (endpoints now
  match `eid`); `view/pipeline.py`'s `to_canonical` attaches edges to real typed nodes; the `unknown`
  fallback (`pipeline.py:283-286`) stops firing.
- **Guards (non-negotiable):** a no-match endpoint mints a typed node — **never force-link** to the nearest
  name (honest "we don't have this entity"). An endpoint with >1 type-compatible match is **ambiguous** →
  emit a HITL candidate, do not auto-pick. Endpoints the ontology can't type in either order stay a
  tier-3/undtyped mention (do not invent a type).
- **Verify:** `unknown` node count in `view_full.json` 109 → ~0 (modulo genuinely un-typable mentions);
  `relational_score`/`source_asserted_score` non-zero for `unit_paad` / `comp_ht233` variants; the
  FRAGMENTED-N counts (evidence-summary lines 77-133) shrink toward 1.

### P3.2 — RES-4 consume identity assertions  *(per Phase-2 decision D-2.5 — read this, it overrides the handoff)*
Phase 2 ratified **D-2.5**, which changes the RES-4 design from the original handoff. The handoff (and the
P1 handoff) said "route identity into the `merge_proposal` decision channel `_llm_pairs` reads." **That was
rejected** — flattening identity into decision records loses the asserting source's credibility weighting.
The ratified design:

- **RESOLVE reads `same-as`/`distinct-from` from the *claim stream*, weighted by the asserting source's
  grade** — they still emit as ordinary source-weighted evidence claims (bi-level model: identity is
  evidence-layer, the *merge* is knowledge-layer). RESOLVE already receives `claims` + `config`, so it has
  each claim's `source_id` and can look up its grade via the credibility/sources config.
- **`same-as` → a raise-only merge *signal*, source-weighted, NEVER auto-merge.** Make
  `source_asserted_score` **source-weighted** (a high-grade source's identity assertion raises more) instead
  of the current binary 1.0/0.0, and keep it raise-only-to-HITL (reuse the `_band(..., has_llm=True)` path).
  Never auto — the corpus plants false identities (Army↔PAF variant cross-wiring across a distinct-from
  trap). Gate on type + namespace compatibility.
- **`distinct-from` → hard veto *and* drawn** (fold into `veto`; keep it visible as a trap edge).
- **View change (part of this item): stop drawing `same-as` as a knowledge edge.** Today the 42 `same-as`
  edges render as graph edges; once they're consumed as merge signals they must be suppressed in
  `view/pipeline.py` (a `same-as` is a signal, not a relationship). `distinct-from` stays drawn.
- **Verify:** `same-as` pairs carry `merge_confidence`/`merge_band` (went through scoring), reflect source
  grade, and no longer appear as drawn edges; distinct-from traps still separate *and* still render.

### P3.3 — RES-2 band geometry + containment signal
- **Add a high-precision bootstrap trigger:** containment / shared-head-token / acronym-expansion within the
  same type + namespace (e.g. `HT-233` ⊂ `HT-233 engagement radar`; `PAAD` ⇄ `Pakistan Army Air Defence`).
  Sits alongside `_shared_unique_id` / `alias_equivalent` in the Phase-1 bootstrap; **veto-gated** (a
  head-token match that would fuse a distinct-from pair is blocked by the existing hard veto).
- **Re-tune the geometry to a stated invariant, not to examples:** *"a strong/exact name match alone must
  reach at least `hitl_low`."* Today name-only caps at `0.30·attr + 0.15 = 0.45 < 0.55`. Raise the attribute
  weight and/or lower `hitl_low`, and reconsider the dead `temporal_consistency` constant-1.0 weight (either
  make it a real discriminator or redistribute its 0.15). The weights were never tuned — this *is* the
  tuning step, so it is not a magic-number hack; the discipline is to validate against the FT-2000 / HQ-9BE
  and 4th-Academy / 23rd-RI(BIRM) **distinct-from traps**, not against a list of cited pairs. Numbers live in
  `config/resolution.yaml` (DATA-C-owned) — **coordinate the final values with DATA-C.**
- **Note:** consuming the registry (P3.0) already turns most cited fragmentation (HT-233 spellings, PAAD
  spellings, TEL chassis) into *alias-equivalent* → confidence-1 bootstrap merges. RES-2's residual scope is
  the **open-world tail** (surface forms the registry has never seen) — keep the re-tune proportionate to
  that, don't over-fit.
- **Verify:** HITL merge queue non-empty (was 0 across 26 docs); cited pairs land ≥ `hitl_low` (or auto via
  registry); traps still separate.

### P3.4 — RES-3 place-ref write-back  *(no gazetteer minting)*
- `resolve_place` already computes a `PlaceMatch(place_id, band, distance_m, via)` and throws it away.
  **Persist it onto the entity:** add a place-ref channel to `Partition` (mirror how `entity_canonical`
  flows) carrying `{eid → (place_id, distance_m, band)}`; `rebuild()`/`_assemble` stamps
  `NodeView.resolved_place_ref` (+ distance/band as attrs) so downstream (`observe/dsl.py:32`, map) reads it.
- **Match to *existing curated anchors only*. Do NOT auto-mint into `config/places.yaml`.** The gazetteer is
  the analyst's curated set — it is what distinguishes a **main, named anchor** from an **incidental pin**;
  machine-writing to it destroys that curation (and mutates a human-owned config, breaking reproducibility).
  A mention that matches no anchor keeps its own raw coord and stands as an honest pin — no ref, not merged,
  not written. Type-scaled radius (pad 500m … city 15km) absorbs the Nominatim jitter *for curated places*,
  which are the ones the reasoning depends on.
- **Gazetteer growth = analyst promotion only** (a HITL/config action: name it, class it, add it), not a
  machine mint. That is the adaptation seam; it is not P3.4 code.
- **Product consequence (handoff to ARCH/frontend, not RESOLVE code):** the map renders two tiers — curated
  anchors (big, named markers) vs. incidental pins (raw dots). RESOLVE only has to expose "matched a curated
  anchor (ref+distance+band)" vs. "unmatched (raw coord only)"; the frontend does the visual tiering.
- **Verify:** the 3 known matches (Malir→`pl_karachi_ad`, Rahwali→`pl_rahwali`, Army-AD-Centre→…) carry a
  non-empty `resolved_place_ref` with a distance; the relocation observable reads populated basing edges.

### P3.5 — RES-5 place gates  *(minor; ride on P3.4)*
- Match on a **frozen toponym slot** (`attrs.toponym`) rather than the raw entity display name
  (`_location_of` already prefers `toponym` then falls back to `ent.name` — tighten so the descriptive
  display name isn't the toponym).
- **Gate proximity on two things** or jitter-absorption becomes garbage-absorption: (a) place-type /
  precision-class compatibility (a `basing_site` may match pad/site-class places, never a `terminal`) via a
  small config map `entity_type → allowed place classes` (extensible, not hardcoded); (b) the mention's own
  geocode confidence — a vague low-confidence geocode ("central Punjab") must not snap into a precise pad; it
  stays an honest pin. The INGEST-side companion (flagging low-confidence Nominatim geocodes) is out of
  RESOLVE scope — flag to INGEST if not already covered.
- **Verify:** `Army Air Defence Centre` no longer proximity-matches `pl_karachi_port` (matches nothing, or a
  compatible class).

---

## 3. Contract / config touches (flag for review)

- **RESOLVE becomes a consumer of `config/entities.yaml`** (new). Non-breaking — the surface already exists;
  this is the intended wiring. `resolution.yaml` weights/bands get re-tuned (DATA-C-owned — coordinate).
- **`Partition` gains a place-ref channel**; **`entity_canonical` semantics broaden** from "merged refs only"
  to "canonical id for any ref (merged member *or* raw endpoint mention)" — update the doc comment at
  `schemas/stage_io.py:48`. Small `EdgeLaneIndex` addition to expose predicate → endpoint types.
- **`source_asserted_score` goes from binary → source-grade-weighted** (D-2.5); **`view/pipeline.py` stops
  drawing `same-as` edges** (consumed as a signal, not a relationship) while still drawing `distinct-from`.
- None of these break the F0 contract beyond what Phase 1 already ratified; the two review points are the
  `entity_canonical` broadening and the `Partition` place-ref field. Flag in the PR.

---

## 4. Decisions log  *(append to `RCA-FIX-DECISIONS.md` / DECISIONS.md §6 at PR time)*

- **D-P3.1 — endpoint-as-mention at the graph layer** (not a view-only remap). *Principle:* build the
  mechanism fully + provenance/traceability. *Rejected:* view-only `to_canonical` patch (leaves resolver
  scoring dead → RES-2 stays broken).
- **D-P3.2 — re-derive ids each rebuild; register grows via decision log + analyst promotion.** *Principle:*
  determinism / reproducibility (gate G2). *Rejected:* persistent mutable register (mutate-during-rebuild
  fights replay determinism; out of scope).
- **D-P3.3 — no auto-mint into the gazetteer; match existing curated anchors, analyst promotes.**
  *Principle:* HITL curation + human-owned config + reproducibility. *Rejected:* open-world place minting
  into `places.yaml` (erases the main-anchor vs. incidental-pin distinction the analyst owns).
- **D-P3.4 — identity read from the claim stream, source-grade-weighted (aligns with Phase-2 D-2.5):
  `same-as` = raise-only merge signal, never auto, not drawn; `distinct-from` = hard veto, drawn.**
  *Principle:* the fabrication non-negotiable + recall-biased triage + the bi-level model (identity is
  evidence-layer, the merge is knowledge-layer). *Rejected:* flattening identity into `merge_proposal`
  decision records (loses source-credibility weighting — the P1-handoff route Phase 2 overturned).
- **D-P3.5 — band re-tune to the invariant "strong name alone ≥ HITL," validated against the traps; add a
  containment/acronym bootstrap signal.** *Principle:* config-driven tuning, not magic numbers (the weights
  were never tuned — this is the tuning step). *Rejected:* nudging thresholds to pass cited examples
  (over-fit).

---

## 5. Reproduce / verify

```bash
export CHANAKYA_ROOT=<this worktree>
backend/.venv/bin/python tmp/conv/eval-rca/rca_evidence.py   # regenerates view_full.json + evidence-summary
```
Run once before (baseline symptom), once after each item. Headline acceptance for Phase 3: `unknown` nodes
≈ 0 · non-zero relational/source-asserted for known pairs · HITL merge queue non-empty · `resolved_place_ref`
populated on the 3 known place matches · the FT-2000 / HQ-9BE / BIRM distinct-from traps still separate.
```
