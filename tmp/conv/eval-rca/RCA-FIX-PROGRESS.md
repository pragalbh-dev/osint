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
- **Phase 3 — resolution (RESOLVE): PLANNED (ready to build).** `phase3-resolve-PLAN.md` — the build plan
  (refines `handoff-resolve.md`; folds in the 2026-07-19 design review + Phase-2 D-2.5: endpoint-as-mention
  at the graph layer, register consumed as candidates, re-derive-not-persist ids, no gazetteer auto-mint,
  identity read source-weighted from the claim stream / same-as raise-only + not-drawn, band re-tune to an
  invariant). Supporting: `handoff-resolve.md` (evidence/probes) ·
  `PHASE3-RESOLVE-alias-candidates-and-ambiguities.md` (candidates + ambiguities to adjudicate).
- **Phase 4 — derived + surfaces: PENDING.** `handoff-score.md` · `handoff-arch.md` (lens anchors via
  registry; materiality-filter schema) · `handoff-monitor.md` · `handoff-ask.md` (crash-guard + honest refusal).
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
    (SC-G1..G4). **NEW coupling:** ASK hero-path code (`agent/loop.py`) embeds the same false narrative →
    ASK fix (overlaps `handoff-ask.md`; does NOT block this PR — fixture-based tests untouched).
  - Still open (separate): `PHASE1-DATAC-EVAL-answer_key-reconciliation.md` (id unification only — grounding
    part superseded by D-G1); `EVAL-RCA-corpus-grounding-basing-and-materiality.md` (subsumed by the audit).

## Handoff index
| Doc | Owner | Phase | Status |
|---|---|---|---|
| `phase3-resolve-PLAN.md` | RESOLVE | 3 | 📋 **build plan ready** (refines handoff-resolve; folds in D-2.5) |
| `handoff-resolve.md` | RESOLVE | 3 | superseded-by-plan (evidence/probes still valid) |
| `handoff-ingest.md` | INGEST | 2 | ✅ DONE (80a8702 + 02ad5aa + e597891 + re-record) |
| `PHASE2-VERIFY-DELTA-AND-HANDOFF.md` | INGEST→P3/P4 | 2 | ✅ delta verified; downstream inheritance + repro gotcha |
| `handoff-data-c.md` | DATA-C | 1/2 | Phase-1 parts DONE |
| `handoff-score.md` | SCORE | 4 | pending |
| `handoff-arch.md` | ARCH | 1/4 | contract DONE; lens code pending |
| `handoff-ask.md` | ASK | 4 | pending |
| `handoff-monitor.md` | MONITOR | 4 | pending |
| `../PHASE2-INGEST-edge-relane-enum-provenance.md` | INGEST | 2 | ✅ done (80a8702) |
| `../PHASE2-INGEST-DATAC-extraction-typing-and-coverage-gaps.md` | INGEST/DATA-C | 2 | pending |
| `../PHASE3-RESOLVE-alias-candidates-and-ambiguities.md` | RESOLVE | 3 | pending |
| `../PHASE1-DATAC-EVAL-answer_key-reconciliation.md` | DATA-C/EVAL | 1→x | pending (id-unification part only; grounding part superseded by D-G1) |
| `../INGEST-edge-direction-UNCOMMITTED-risk.md` | INGEST | 2 | pending |
| `../EVAL-RCA-corpus-grounding-basing-and-materiality.md` | DATA-C/EVAL | 2/3 | subsumed by `ANSWER-KEY-GROUNDING-AUDIT.md` |
| `handoff-answer-key-grounding.md` | DATA-C/EVAL | x | **answer_key edits ✅ APPLIED (fix/answer-key-grounding-apply)** |
| `ANSWER-KEY-GROUNDING-AUDIT.md` | DATA-C/EVAL | x | reference (full node/edge grounding sweep) |
| `handoff-resolve-score-grounding.md` | RESOLVE/SCORE (+ASK note) | 3/4 | **pending — derive the softened oracle** |

## Verify after each phase
`export CHANAKYA_ROOT=<worktree>; backend/.venv/bin/python tmp/conv/eval-rca/rca_evidence.py` — regenerates
`view_full.json` / `view_lens.json` / `00-evidence-summary.md`. NB: Phase 1 alone does not move the graph
numbers (it's the contract/mechanism); reconnection lands in Phase 3.
