# ⚠ Risk flag → INGEST: `edge_direction.py` work is UNCOMMITTED and un-PR'd

**From:** Phase-1 fix (found while reconciling the edge machinery). **Owns:** INGEST.

## What's at risk
In the `wt-INGEST` worktree (branch `feat/ingest-attribution`), the following is **uncommitted / untracked**
(`git status`): a real, working body of edge-direction work that is **in no PR and never committed**:
- `backend/chanakya/edge_direction.py` (untracked)
- `backend/tests/ingest/test_edge_direction.py` (untracked)
- `config/ontology.yaml` (modified — the `from`/`to`/`symmetric` additions)
- `backend/chanakya/ingest/lane.py`, `backend/chanakya/view/pipeline.py` (modified — write-side + read-side wiring)
- `DECISIONS.md` (modified)

PR #21 (the "attribution proposer") — the committed base of that branch — **already merged to main**. This
edge-direction work was done *after* and left on the bench. It is **not** on `main` and not lost to a wrong
branch — it simply was never captured. If that worktree is reset or cleaned, it's gone.

## Action
1. **Commit + PR it** (or fold the good parts into a follow-up), before it's lost.
2. **Reconcile with Phase 1.** `edge_direction.py` (canonical *direction* — flips backwards-written but
   correctly-*named* edges) is **complementary** to Phase-1's `chanakya/ontology.py` re-lane (canonical
   *name* — picks the right edge from endpoints). Keep both; run re-lane first (fully-typed), edge_direction
   as the partial-typing fallback (see `PHASE2-INGEST-edge-relane-enum-provenance.md`).
3. **Ontology merge.** Both edits touch `config/ontology.yaml`'s edge block. Take the Phase-1 superset:
   tightened `manufactures` (from+to=variant) + `extractor:` flags. Your branch left `manufactures`
   `from`-only; the ratified D-A tightens it.
