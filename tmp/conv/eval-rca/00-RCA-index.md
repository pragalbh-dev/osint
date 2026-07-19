# EVAL RCA — master index (read this first)

**What this is.** The first-ever end-to-end run of the *merged* pipeline over a *real* LLM-extracted corpus
(not the clean unit-test fixtures) revealed the assembled system produces a graph far from the curated oracle
(`answer_key.json`). This directory is the root-cause analysis + a self-contained fix handoff per service.
Produced by the EVAL session (`feat/eval`); the fixes are owned by each service's agent.

**Method.** 26 live Gemini extractions were frozen to `corpus/scenarios/hq9p_primary/claims/`, the whole
pipeline was run, and the actual output captured (`view_full.json` — 294 nodes / 101 edges vs the oracle's
20 / 22). Seven per-service investigators root-caused it against the code + evidence + live probes; every
finding was then adversarially re-checked for correctness **and attribution** (most symptoms are downstream
of another service's defect), then synthesised into the dependency-ordered plan below. 31 findings, all
verified.

## Evidence bundle (referenced by every handoff)
- `00-evidence-summary.md` — histograms, oracle→view fragmentation diff, fired merges, hero crash, observable, places.
- `view_full.json` / `view_lens.json` — the actual rebuilt view (+ the empty lens view).
- `corpus/scenarios/hq9p_primary/claims/*.json` — the frozen extraction output the pipeline consumed.
- Regenerate after any fix (portable — resolves whichever worktree it runs in):
  `backend/.venv/bin/python tmp/conv/eval-rca/rca_evidence.py`.

## The two master defects (everything else is downstream)

**Master A — RESOLVE id-namespace split.** Triple endpoints stay as bare LLM surface strings while entity
nodes are keyed `ent:<type>:<name>`, and `entity_canonical` is filled only for *merged* clusters — so the
edge graph and the entity graph are disjoint sets (0/109 endpoints match an entity id; 0/190 entities carry
an incident edge). This one defect mints all 109 `unknown` nodes, zeroes `relational_score` and
`source_asserted_score` for every pair, starves the merge fixpoint, and disconnects the graph so the lens,
multi-hop traversal, and ASK return nothing. **Fix: RESOLVE's endpoint-linking pass (RES-1).**

**Master B — extraction contract gaps (INGEST + DATA-C).** Extraction emits denials and identity as
free-text / knowledge triples (→ ~22 ad-hoc predicates, 34 junk endpoints, 42 phantom `same-as` edges), has
no deterministic transform for the supply-chain / ORBAT edges (`supplies-component`/`exported-by`/
`sustained-by`/`based-at`/`supersedes` all ≈0), and the ontology edge vocabulary collides with natural
language so even correct facts land on the wrong valid edge name (Component→Variant lands on `component-of`
not `equips`; Mfr→Component lands on `manufactures` not `supplies-component`).

**What already works (don't touch):** RESOLVE's union-find + collapse (5 merges fired cleanly: FD-2000,
Hongqi-9, Triumph, ORIENT…), the FT-2000 / HQ-9BE / 4th-Academy / 23rd-RI distinct-from traps, and — verified
by counterfactual — **SCORE's credibility/status machinery is sound** (18 nodes confirm today; merged
entities reach CONFIRMED through the *unchanged* gate). Do **not** retune `credibility.yaml`.

## Dependency-ordered fix plan

**Phase 1 — foundation (contract-level; ratify first).**
1. **DATA-C + ARCH:** redesign the edge-type vocabulary to remove synonym collisions + add per-edge
   domain/range; introduce an entity canonical-id registry (mirror `places.yaml`'s `place_id` pattern):
   stable ids (`unit_paad`, `mfr_casic`, `comp_ht233`…) ↔ alias surface forms + type. *(Contract change —
   likely an F0-amendment; your ratification needed.)*
2. **DATA-C:** build the registry / expand `alias_table` — components (HT-233 family), TEL/8×8 chassis,
   Taian(Wanshan), Pakistani formations (PAAD / Army Air Defence Command; PAF↔Pakistan Air Force); keep the
   distinct-from traps.

**Phase 2 — extraction (INGEST, needs the ontology/registry from Phase 1).**
3. Hard-constrain relation extraction to the ontology enum + domain/range; route denials → SCORE
   sufficiency and identity (`same-as`/`distinct-from`) → the merge-proposal channel RESOLVE reads (not
   knowledge triples).
4. Add deterministic structural transforms for the edges the LLM drops/mis-lanes: supply chain
   (`contract_import_event` + `exported-by`/`imported-by`/`supplies-component`/`sustained-by`) and ORBAT
   (`based-at`/`inducted-into`/supersedes inputs); type customs consignee as a trading-org; stop minting
   collection-gaps and spare-part line-items as first-class entities.
5. **DATA-C:** stamp real per-doc `report_time` **and** `ingest_time` (not one frozen 2026-07-19 — this is
   why the observable's time-rewind is empty); cite the `.png` artifacts for imagery docs; seed
   `foreign_control` attrs + `substitutable-by` edges materiality needs.

**Phase 3 — resolution (RESOLVE, the master fix).**
6. **Endpoint-linking pass (RES-1, THE master fix):** resolve every triple subject/object to its entity id
   via `normalize()`+`AliasIndex`, populate `entity_canonical` with surface-name→canonical-id so the view
   reconnects edges to real typed nodes instead of 109 `unknown` twins (revives relational/source-asserted scores).
7. Consume the registry for canonical ids; consume `same-as`/`distinct-from` as raise-only merge/veto;
   recalibrate merge bands/weights (attribute-only currently caps at **0.45 < hitl_low 0.55** → HITL queue is
   structurally empty) + add a containment/head-token bootstrap.
8. Write the computed `place_id` back to `Location.resolved_place_ref` (currently computed then discarded);
   gate place matching on toponym + place-type/precision compatibility.

**Phase 4 — derived + surfaces (parallel once Phase 3 lands; ASK/SCORE/MONITOR items partly independent).**
9. **SCORE** (independent parts, no credibility retune): `based-at` half-life fallback so basing goes stale;
   broaden discipline taxonomy; restrict chokepoint nomination to supply-tier types + correct direction;
   compute derived `supersedes` (with a confidence floor vs the d20 spoof) + `sustained-by` rollups.
10. **ARCH:** resolve lens anchors through the registry/alias index (not literal id); implement + validate the
    declared materiality-filter schema.
11. **MONITOR:** consume the dropped trigger keys (unit/from_site/to_site/window/match_on); key the occupancy
    crossing by edge **source** (resolved unit) per `match_on`, not by `edge_instance`; drive off the
    supersede-aware active-edge delta, not the availability rewind.
12. **ASK** (independent, do anytime): guard `_from_get_node` + all builders against error-shaped results
    (kills the `KeyError` crash); resolve hero anchors via `find_entity`/alias then refuse honestly naming the
    real missing input; pass an `edge_whitelist` to the hero `find_paths`.

## Per-service handoffs

| Service | Handoff | Findings | Highest severity | Owns / master |
|---|---|---|---|---|
| RESOLVE | `handoff-resolve.md` | 5 | blocks-demo ×2 | **Master A** (endpoint-linking, bands, place-ref) |
| INGEST | `handoff-ingest.md` | 8 | blocks-demo ×2 | **Master B** (ontology-constrain, structural transforms) |
| DATA-C | `handoff-data-c.md` | 4 | blocks-demo ×3 | **Master B** (registry, vocab, dates, .png, seeds) |
| SCORE | `handoff-score.md` | 4 | major ×3 | independent (stale/discipline/chokepoint/derived edges); **do not retune credibility** |
| ARCH | `handoff-arch.md` | 3 | blocks-demo ×2 | contract ratification + lens-anchor resolution |
| ASK | `handoff-ask.md` | 4 | blocks-demo | independent (crash-guard + honest refusal) |
| MONITOR | `handoff-monitor.md` | 3 | major ×3 | trigger keys + temporal axis (mostly waits on upstream) |

## Notes for the orchestrator
- **The generated bundles are a snapshot for RCA reproduction.** INGEST/DATA-C fixes (Phase 2) will
  re-record them via `python -m chanakya.ingest extract --scenario hq9p_primary` (keyed), so treat the
  committed `claims/*.json` as the frozen baseline to diff against, not the final artifact.
- **Fixing agents need this evidence + bundles.** Have them branch off `feat/eval` (or merge the
  bundles+evidence to `main` first) so `gen_evidence.py` reproduces the baseline.
- **Step 1 is a contract change** (ontology vocab + entity registry) — an F0-amendment touching a shared
  surface; ratify before INGEST/RESOLVE build on it.
- EVAL itself (the acceptance harness + oracle assertions) is built to consume the *fixed* graph; it goes
  green once Phases 1–4 land. The `answer_key`-separation guard already passes.
