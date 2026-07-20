# RCA-fix — progress hub (the whole eval-RCA fixing effort)

Single place to track the four-phase RCA fix. Root cause + plan: `00-RCA-index.md`. Decisions:
`RCA-FIX-DECISIONS.md`. Master board points here (`artifacts/plan/PROGRESS.md`).

## Phase status
- **Phase 1 — foundation (DATA-C + ARCH): edge vocab + entity registry — ✅ DONE.**
  Branch `fix/phase1-edge-vocab-and-entity-registry` (off main). Delivered:
  - `config/ontology.yaml` — per-edge domain/range (`from`/`to`) + `symmetric`/`extractor`; `manufactures`
    tightened → every extractor edge endpoint-unique (D-A, D-A.1).
  - `backend/chanakya/ontology.py` — `EdgeLaneIndex`: extraction enum + endpoint→edge re-lane (D-A.2).
  - `config/entities.yaml` (new 9th surface) + `EntityEntry`/`EntitiesConfig` schema + store/exports — the
    entity canonical-id registry, 14 entities / ~76 aliases, distinct-from traps, earned-merges withheld,
    foreign_control seeds removed (D-B, D-B.1, D-C.1).
  - Tests: `backend/tests/test_ontology.py`, `backend/tests/config/test_entities_config.py` (green).
- **Phase 2 — extraction (INGEST): ✅ DONE + re-record verified.**
  Branch `fix/phase2-ingest-extraction`. Commits: **80a8702** (core rework — enum + write-time re-lane +
  provenance rule + denials-drop + gap slot-keying + customs/tender structural transforms + `trading_org`)
  · **02ad5aa** (ING-8 image co-load, 9 sources; ING-7 real per-doc dates, 24 stamped / honesty-verified)
  · **e597891** (chaff image pointers) · keyed re-record of all 26 `hq9p_primary` bundles (pymupdf PDF
  path, D-2.9). **Verified delta** (`PHASE2-VERIFY-DELTA-AND-HANDOFF.md`): ad-hoc edge predicates
  **~22→0**; `exported-by` 0→5, `supplies-component` 0→1, `imported-by` 2→7, `contract_import_event` 1→4,
  `trading_org` 0→4; VLM claims 0→9 bundles; `known_gap` sentence-nodes 14→6; view 294n/101e→258n/100e.
  **Unchanged by design → downstream:** fragmentation (P3 RES-1), lens `0/0` (P4 ARCH AR-2), hero crash
  (P4 ASK AS-1), `as_of=2021` rewind empty (P4 MONITOR MON-2 valid-time) — see the handoff. Decisions
  D-2.1…D-2.9; full backend suite 571✓/6-skip.
- **Phase 3 — resolution (RESOLVE): ✅ DONE.** Branch `fix/phase3-resolve` (off main @ ea392c6). Plan:
  `phase3-resolve-PLAN.md`; decisions **D-3.1…D-3.7**. Delivered in 4 waves: registry plumbing +
  **endpoint-as-mention at the graph layer** (the master fix — edges carry entity ids *before* the fixpoint,
  which is what revives the relational/source-asserted terms) · identity read source-weighted from the claim
  stream (`same-as` raise-only + **undrawn**, `distinct-from` veto + drawn; raise-only enforced structurally)
  · band geometry re-tuned to a symmetric invariant + containment/acronym bootstrap · place-ref write-back
  with the two RES-5 gates and exact curated-alias binding (no gazetteer auto-mint).
  **Verified delta** (RCA baseline → Phase-2 → Phase-3): nodes 294→258→**162**; `unknown` 109→86→**3**;
  lens **0/0 → 23n/34e**; merges 5→5→**53**; HITL queue 0→0→**20**; `entity_canonical` 5→**120**;
  `resolved_place_ref` `{}` → **3 anchors bound** (`pl_karachi_ad`, `pl_rahwali`, `pl_nurkhan`); relational
  score >0 on 51 pairs and source-asserted on 30 (both were uniformly 0). All flagship distinct-from traps
  still separate **and** render, now under stable registry ids. Suite **595 pass / 6 skip / 0 fail**; G2
  determinism byte-identical across `PYTHONHASHSEED` 0/1/7/42/12345; G4 clean (0 nodes without a claim_id);
  ruff + mypy clean.
  **Refused by design (D-3.4):** the customs shell→real-entity link the Phase-2 handoff asked for — the D7
  scenario design says those stay unresolved and no id should be invented; forcing it would fabricate an
  attribution. **Open for DATA-C/EVAL** (neither self-fixed): `../RESOLVE-to-DATAC-EVAL-import-event-and-shells.md`
  (import-event naming) · `../RESOLVE-to-DATA-EVAL-same-as-no-longer-drawn.md` (the oracle's now-unsatisfiable
  `same-as` edge assertion). **Open for INGEST:** `../RESOLVE-to-INGEST-mislaned-edge-endpoints.md` ·
  `../RESOLVE-to-INGEST-frozen-location-gaps.md` (MGRS frozen as toponym — fix in flight on
  `fix/ingest-mgrs-surface-format`).
- **Phase 4 — derived + surfaces: AUDITED + REPLANNED + IN PROGRESS. Build from `PHASE4-CORRECTED-PLAN.md`,
  NOT the four handoffs** (4 of their recommended fixes are hacks; 3 findings mis-attributed; 3 structural
  holes nobody scoped are the real blockers — see the plan, decisions D-P4.1…D-P4.14).
  **Re-verified against the live post-Phase-3 view (2026-07-19):** all Phase-4 *code* findings stand
  (Phase 3 touched none of agent/observe/materiality/supersede/lens/credibility — `git diff d96f077..HEAD`
  empty for those). Phase 3 only improved the *inputs*: nodes 258→**162**, unknown 86→**3**, lens
  0/0→**23n/34e** (so AR-2's blocking symptom is FIXED → demoted to defensive). Still broken as verified live:
  `edge_instance` still embeds the object → **supersede/contradiction still 0**; based-at still **2
  wrong-shaped edges, no relocation pair**; chokepoint still nominates variants/units; `var_hq9p` is named
  `HQ-9P` with no aliases stamped → `find_entity("HQ-9/P")` still misses; **0 stale** nodes.
  **Demo-impact ranking + build order (ratified with orchestrator, branch `fix/phase4-derived-and-surfaces`):**
  1. ⏳ **ASK worked-query bundle** (AS-1/2/3/4/5/6) — the demo centrepiece; currently crashes → fabricates a
     refusal about a non-existent node (disqualifying). Independent, fixable now. **IN PROGRESS.**
  2. **SC-1 chokepoint direction** — visibly wrong output; cheap; independent.
  3. **SC-2 basing-stale wiring** — freshness invisible; cheap; also relocation-beat prereq.
  4. **Relocation beat** (all-or-nothing chain: edge_instance key + INGEST occupancy lane/dated derivation +
     SCORE supersede-floor/stale + MONITOR grouping/de-pin + staged-ingest harness + frontend live feed).
  5. Hardening/honesty polish (AR-2 defensive, AR-3, AS-3/4, MON-4).
  6. → DATA-C: `mfr_taian`→probable (SC-3), supersedes node-edge shape reconciliation.
- **Cross-cutting (DATA + EVAL): answer_key edits ✅ APPLIED; downstream (RESOLVE/SCORE/ASK) PENDING.**
  - **Audit + handoff DONE (PR #30, merged).** Full node/edge sweep: `ANSWER-KEY-GROUNDING-AUDIT.md`;
    analyst handoff + edit spec: `handoff-answer-key-grounding.md`. Verdict: ~85% cleanly sourced.
  - **answer_key edits ✅ APPLIED (2026-07-19, branch `fix/answer-key-grounding-apply`, own PR)** at the
    user's direction (ratified DATA/EVAL reconciliation). D-G1 = **A1 remove** the un-sourced
    `mfr_casic→comp_ht233` edge (A2 rejected: ontology locks `design-authority-for` to techdata→variant) +
    re-lane 23rd_ri → `supplies-component` + worked-query terminates at `comp_ht233`; D-G2 = 3× `based-at`
    now `basis:derived` with `observed_layer`/`attribution_layer`; D-G3 = cosmetics; D-G4 = no change
    (chokepoint stays `candidate`; verified no `foreign_control` seed). Chaff scenario: 0 edges, untouched.
  - **Downstream PENDING:** `handoff-resolve-score-grounding.md` — RESOLVE derives the two-layer `based-at`
    + CASIC-via-program (RES-G1); SCORE basing-stale / supersede-floor / 2-signal gate / candidate-chokepoint
    (SC-G1..G4). **NEW coupling:** ASK hero-path code (`agent/loop.py:170-171`) still *speaks* the removed
    claim — it looks up the maker via `manufactures` (never matches a component post-D-A) then falls back to
    the literal `"mfr_casic"`. Written up as `handoff-ask-grounding.md` (D-G5); **bundle post-Phase-4** with
    `handoff-ask.md`. Does NOT block any PR — ASK's tests are fixture-based, so they stay green.
  - Still open (separate): `PHASE1-DATAC-EVAL-answer_key-reconciliation.md` (id unification only — grounding
    part superseded by D-G1); `EVAL-RCA-corpus-grounding-basing-and-materiality.md` (subsumed by the audit).

## Handoff index
| Doc | Owner | Phase | Status |
|---|---|---|---|
| `phase3-resolve-PLAN.md` | RESOLVE | 3 | ✅ **DONE** — built in 4 waves on `fix/phase3-resolve` (D-3.1…D-3.7) |
| `handoff-resolve.md` | RESOLVE | 3 | ✅ superseded-by-plan; RES-1…RES-5 all addressed |
| `../RESOLVE-to-DATAC-EVAL-import-event-and-shells.md` | DATA-C/EVAL | 3→x | **open** — import-event naming; shells stay unresolved (D-3.4) |
| `../RESOLVE-to-DATA-EVAL-same-as-no-longer-drawn.md` | DATA-C/EVAL | 3→x | **open** — oracle asserts a `same-as` edge that is now unsatisfiable |
| `../RESOLVE-to-INGEST-mislaned-edge-endpoints.md` | INGEST | 3→2 | **open** — variant→country mis-lane mints wrong-typed nodes |
| `../RESOLVE-to-INGEST-frozen-location-gaps.md` | INGEST | 3→2 | 🟨 MGRS-as-toponym fix in flight (`fix/ingest-mgrs-surface-format`) |
| `handoff-ingest.md` | INGEST | 2 | ✅ DONE (80a8702 + 02ad5aa + e597891 + re-record) |
| `PHASE2-VERIFY-DELTA-AND-HANDOFF.md` | INGEST→P3/P4 | 2 | ✅ delta verified; downstream inheritance + repro gotcha |
| `handoff-data-c.md` | DATA-C | 1/2 | Phase-1 parts DONE |
| `PHASE4-CORRECTED-PLAN.md` | ALL P4 | 4 | 📋 **BUILD FROM THIS** (D-P4.1…D-P4.14; supersedes the 4 handoffs below) |
| `handoff-score.md` | SCORE | 4 | ⚠️ superseded — SC-1/2 fixes are hacks as written; SC-3 = answer-key defect; SC-4a mis-attributed |
| `handoff-arch.md` | ARCH | 1/4 | ⚠️ superseded — AR-1 done (P3 consumes); AR-2 symptom fixed by P3; AR-3 `exclude_off_subject` is oracle-only |
| `handoff-ask.md` | ASK | 4 | ⏳ IN PROGRESS on `fix/phase4-derived-and-surfaces` — corrected plan + AS-5/AS-6 (new) |
| `handoff-monitor.md` | MONITOR | 4 | ⚠️ superseded — MON-3 fix aimed at wrong layer; + MON-4/5 (no alert provenance; dead feed) |
| `../PHASE2-INGEST-edge-relane-enum-provenance.md` | INGEST | 2 | ✅ done (80a8702) |
| `../PHASE2-INGEST-DATAC-extraction-typing-and-coverage-gaps.md` | INGEST/DATA-C | 2 | pending |
| `../PHASE3-RESOLVE-alias-candidates-and-ambiguities.md` | RESOLVE | 3 | pending |
| `../PHASE1-DATAC-EVAL-answer_key-reconciliation.md` | DATA-C/EVAL | 1→x | pending (id-unification part only; grounding part superseded by D-G1) |
| `../INGEST-edge-direction-UNCOMMITTED-risk.md` | INGEST | 2 | pending |
| `../EVAL-RCA-corpus-grounding-basing-and-materiality.md` | DATA-C/EVAL | 2/3 | subsumed by `ANSWER-KEY-GROUNDING-AUDIT.md` |
| `handoff-answer-key-grounding.md` | DATA-C/EVAL | x | **answer_key edits ✅ APPLIED (fix/answer-key-grounding-apply)** |
| `ANSWER-KEY-GROUNDING-AUDIT.md` | DATA-C/EVAL | x | reference (full node/edge grounding sweep) |
| `handoff-resolve-score-grounding.md` | RESOLVE/SCORE (+ASK note) | 3/4 | **pending — derive the softened oracle** |
| `handoff-ask-grounding.md` | ASK | post-4 | **pending — bundle with `handoff-ask.md` (D-G5)** |

## Verify after each phase
`export CHANAKYA_ROOT=<worktree>; backend/.venv/bin/python tmp/conv/eval-rca/rca_evidence.py` — regenerates
`view_full.json` / `view_lens.json` / `00-evidence-summary.md`. NB: Phase 1 alone does not move the graph
numbers (it's the contract/mechanism); reconnection lands in Phase 3.
