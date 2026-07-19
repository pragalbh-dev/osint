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
- **Phase 2 — extraction (INGEST): PENDING.** `PHASE2-INGEST-edge-relane-enum-provenance.md` (wire enum +
  re-lane + provenance rule; reconcile ontology) · `PHASE2-INGEST-DATAC-extraction-typing-and-coverage-gaps.md`
  (typing bugs + coverage) · `INGEST-edge-direction-UNCOMMITTED-risk.md` (rescue + reconcile edge_direction).
- **Phase 3 — resolution (RESOLVE): PENDING.** `handoff-resolve.md` (RES-1 endpoint-linking master fix;
  RES-2 band recalibration + containment bootstrap; consume the registry) ·
  `PHASE3-RESOLVE-alias-candidates-and-ambiguities.md`.
- **Phase 4 — derived + surfaces: PENDING.** `handoff-score.md` · `handoff-arch.md` (lens anchors via
  registry; materiality-filter schema) · `handoff-monitor.md` · `handoff-ask.md` (crash-guard + honest refusal).
- **Cross-cutting (DATA + EVAL): analysis DONE, answer_key edits PENDING.**
  - **Answer-key grounding — audit + handoff DONE (2026-07-19, branch `fix/answer-key-grounding`, own PR).**
    Full node/edge sweep of `answer_key.json` vs all 25 primary docs: `ANSWER-KEY-GROUNDING-AUDIT.md`;
    analyst-perspective owner handoff + exact edit spec: `handoff-answer-key-grounding.md`. Verdict: ~85%
    cleanly sourced. Ratified fixes: D-G1 (remove un-sourced `mfr_casic→comp_ht233`; **supersedes**
    `PHASE1-DATAC-EVAL-answer_key-reconciliation.md` Item 1), D-G2 (soften 3× `based-at` to observed +
    derived, per-edge confidence), D-G3 (cosmetics), D-G4 (materiality already honest — no key change).
    **The edits themselves are DATA-C/EVAL's to apply — this session produced the audit + handoff and did
    NOT touch `answer_key.json`.**
  - Still open: `PHASE1-DATAC-EVAL-answer_key-reconciliation.md` (id unification — separate from grounding) ·
    `EVAL-RCA-corpus-grounding-basing-and-materiality.md` (subsumed by the audit above; its Item-2 "confirmed
    chokepoint" wording is a slip — the key already grades it `candidate`).

## Handoff index
| Doc | Owner | Phase | Status |
|---|---|---|---|
| `handoff-resolve.md` | RESOLVE | 3 | pending |
| `handoff-ingest.md` | INGEST | 2 | pending |
| `handoff-data-c.md` | DATA-C | 1/2 | Phase-1 parts DONE |
| `handoff-score.md` | SCORE | 4 | pending |
| `handoff-arch.md` | ARCH | 1/4 | contract DONE; lens code pending |
| `handoff-ask.md` | ASK | 4 | pending |
| `handoff-monitor.md` | MONITOR | 4 | pending |
| `../PHASE2-INGEST-edge-relane-enum-provenance.md` | INGEST | 2 | pending |
| `../PHASE2-INGEST-DATAC-extraction-typing-and-coverage-gaps.md` | INGEST/DATA-C | 2 | pending |
| `../PHASE3-RESOLVE-alias-candidates-and-ambiguities.md` | RESOLVE | 3 | pending |
| `../PHASE1-DATAC-EVAL-answer_key-reconciliation.md` | DATA-C/EVAL | 1→x | pending (id-unification part only; grounding part superseded by D-G1) |
| `../INGEST-edge-direction-UNCOMMITTED-risk.md` | INGEST | 2 | pending |
| `../EVAL-RCA-corpus-grounding-basing-and-materiality.md` | DATA-C/EVAL | 2/3 | subsumed by `ANSWER-KEY-GROUNDING-AUDIT.md` |
| `handoff-answer-key-grounding.md` | DATA-C/EVAL | x | **audit+handoff DONE; answer_key edits pending** |
| `ANSWER-KEY-GROUNDING-AUDIT.md` | DATA-C/EVAL | x | reference (full node/edge grounding sweep) |

## Verify after each phase
`export CHANAKYA_ROOT=<worktree>; backend/.venv/bin/python tmp/conv/eval-rca/rca_evidence.py` — regenerates
`view_full.json` / `view_lens.json` / `00-evidence-summary.md`. NB: Phase 1 alone does not move the graph
numbers (it's the contract/mechanism); reconnection lands in Phase 3.
