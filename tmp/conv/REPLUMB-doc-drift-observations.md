# Observations for the user — three doc statements that mislead a continuing agent

**Written 2026-07-25 by the orchestrating session.** These are *observations*, not edits: two of the three
fixes belong in files an agent should not rewrite unilaterally (`CLAUDE.md` is boot instructions; the handoff
reads as agent instructions). Both edits were attempted and correctly refused by the harness. Recording them
here — the project's own channel for this — so the fix is a user decision with the reasoning already done.

---

## 1. `CLAUDE.md`'s endgame section reads as a veto on this entire branch

**What it says.** Deliverable *"Due 20 Jul 2026, 12:00"*; *"Operating mode — endgame (from 2026-07-20)…
finishing, fixing… not designing"*; *"Don't start new capability"*; re-architecting what works *"is now a
cost, not depth."*

**Why it misleads.** `CLAUDE.md` instructs every agent to read it first, every session. An agent that obeys
that and then finds a 111-commit substrate rework in flight has to choose between the boot doc and the work.
It may reject the replumb as forbidden, or — worse and more likely — quietly under-scope it into
demo-finishing, which is precisely how a multi-stage chain dies mid-way.

**What is actually true** (citations only — *no file records the deadline as met, missed or moved, and this
note does not claim it was*):

- `artifacts/plan/01-replumb-implementation-plan.md` §0 — *"This is post-deadline, multi-week substrate work
  — the real-system build, not a demo fix. There is no wall-clock pressure to jam it in; correctness and
  reversibility win over speed."*
- `artifacts/spine/13-…-replumb.md` §12 — *"**Cost accepted (per the user):** node ids, the partition, the
  golden view and the answer key all change → full regen… This is a multi-week substrate rework,
  post-deadline — the real-system build, not a demo fix."*
- `artifacts/working-principles.md` (2026-07-23) — method set *during* this build; **`CLAUDE.md` never links
  it**.
- Dated user rulings threaded through the plan (2026-07-25): no-backward-compatibility (§5a), C8-to-roadmap
  (§5b), the synthetic coref sandbox (§7), the bake-off candidate set.

**Suggested fix** (one paragraph, under the endgame heading): the endgame mode governs the **demo** on
`main`; on `design/resolution-redesign` the pacing rule is plan §0's *correctness and reversibility over
speed*. **The non-negotiable is unchanged and unchangeable everywhere** — the replumb exists to *strengthen*
it, since individuated instances are what let the system say *whose* dependency is missing.

## 2. Both handoff docs claim S3 is on the branch. It is not.

`HANDOFF-REPLUMB.md` §1 and `RK-COREF-CONTINUATION.md` line 3 both say *"everything described here is
committed on `design/resolution-redesign` = PR #63."* **False for S3, verified twice independently:**
`backend/chanakya/coref_gate.py` does not exist on that branch and `config/resolution.yaml` there has no
`earned_identity` block. What merged were S3's *governance* commits — the M1–M15 rulings, the continuation
note, a commit whose subject records "S3 at 1324/4" — which read as if the stage landed. Its ~8,300 lines of
code sit on `s3/rk-impl` alone.

An agent trusting either sentence concludes S3 was never built and may rebuild it.

**Suggested fix.** Say "the *governance* is on #63; S3's code is on `s3/rk-impl` pending review." Correct in
both files. *(Fixed on the handoff as part of the S3 landing, if that lands.)*

## 3. `PROGRESS.md` is stale in both halves

The board's RK-COREF row reads "not-started" (S3 is at 1324/4), and the 12-session board still shows seven
sessions "in-review" with EVAL/SHIP "not-started" though PRs #11–#27 merged and `main` is at #62. A board
that is wrong in the *safe* direction still costs a reader their scepticism.

---

## Already actioned this session (no decision needed)

- **91 unpushed commits** — the replumb existed only on this machine; `origin/design/resolution-redesign`
  was 91 behind at `e4a23f3`, so PR #63 showed 20 doc commits and none of the work. Pushed as a clean
  fast-forward (nothing on origin rewritten). PR #63 now represents the replumb truthfully.
- **Three stranded hand branches merged** into `design/resolution-redesign` — `s1/rk-test` (its A7
  discriminator suite), `s2/rk-data` and `s3/rk-data` (fixtures + the DATA handoff notes). All verified
  conflict-free; suite green at 1186 passed / 7 skipped / 2 xfailed. This matters because HANDOFF §5's
  reference map *cited these fixtures as available* while they were on no branch anyone would check out —
  including `S2-DATA-to-DATAC-site-type-vocabulary.md`, the spec for the `site_type` mapping that DATA owes
  and that §8 lists as an open item.
