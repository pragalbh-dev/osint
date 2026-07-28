# RESUME HERE — session state at 2026-07-26

**Written mid-flight, so a session that ends abruptly loses nothing.** Read this, then
`HANDOFF-REPLUMB.md`. Everything below was verified by command, not recalled.

---

## 1. Work IN FLIGHT when this was written

Two background workflows were running. Both use `resumeFromRunId`, so **completed agents replay from
cache and only the unfinished ones re-run** — resuming is cheap, restarting is not.

| Workflow | Run ID | Script | Worktrees it owns |
|---|---|---|---|
| `rkdata-anchor` | `wf_5d520985-e73` | `…/workflows/scripts/rkdata-anchor-wf_5d520985-e73.js` | `wt-RK-DATA` |
| `instrument-repair` | `wf_1aa726c3-353` | `…/workflows/scripts/instrument-repair-wf_1aa726c3-353.js` | `wt-INGEST-FIX`, `wt-RK-BAKEOFF-impl`, `wt-GOLD-REPAIR` |

Scripts live under
`~/.claude/projects/-home-synaptic-data-science-research-rough-osint-osint/<session>/workflows/scripts/`.
Resume with `Workflow({scriptPath, resumeFromRunId})`. **Check each worktree's `git log` first** — both had
already committed real work, so the branch may be further along than the workflow's last report.

**What each is doing:**
- **rkdata-anchor** — third attempt at making the order-of-battle undercount trap load-bearing. The bar is an
  *experiment*, not an argument: relax the co-location ceiling ⇒ the two batteries must fuse; ship it ⇒ they
  must not. Two earlier versions were vacuous (a different rail intercepted the pair each time). **If it
  fails again, ship it as a stated limitation — do not attempt a fourth.**
- **instrument-repair** — three hands fixing what §3 describes, then re-scoring the *already-paid* bake-off
  receipts offline. **Zero new API calls**: every bundle and call record is on disk under
  `wt-RK-BAKEOFF-impl/tmp/rk-bakeoff/run/`.

---

## 2. Branch state (verified)

`design/resolution-redesign` @ `9641f02`, **1 commit ahead of origin — push it.**

| Branch | Merged? | Carries |
|---|---|---|
| `defaulton/rk-impl` | **MERGED** | identity unconditional; HITL overrides mutate the graph |
| `bakeoff/rk-impl` | UNMERGED | the whole bake-off harness, the live result, the diagnosis |
| `bakeoff/rk-data` | UNMERGED | gold adapter + identifier match policy (contained in `rk-impl`) |
| `bakeoff/gold-repair` | UNMERGED | the repaired labeled slice |
| `rkdata/author` | UNMERGED | six new corpus documents + the site_type map |
| `fix/ingest-payload-validation` | UNMERGED | **a live production fix — see §3** |

**Merge order that avoids pain:** `bakeoff/rk-data` → `bakeoff/gold-repair` → `bakeoff/rk-impl` → design;
then `rkdata/author`; then `fix/ingest-payload-validation`. `DECISIONS.md` conflicts every single time because
every branch appends to its tail — **keep both blocks**, never pick one.

---

## 3. The findings that must not be lost

**A live production defect (highest priority).** The extraction client accepted a truncated tool payload with
no validation and recorded `error: None`. The consumer iterated the string, got characters, emitted nothing —
silently. It destroyed the single best coreference answer either model produced (the gold's own note: *"the
ONLY identifier-backed equivalence in the slice"*), twice. Those two runs are exactly the two that scored
lowest, inflating the measured noise floor **threefold** — the number the whole "no measured difference"
verdict rested on. **This is on the shipped ingest path, not the eval harness.** Fix on
`fix/ingest-payload-validation`.

**The bake-off measured our instrument, not the models.** Established by rebuilding the scorer offline and
reproducing its arithmetic to 4 dp. Three specifics:
1. **The top-weighted metric pays for the harm the project exists to prevent.** The only two gold clusters
   with 2+ entity-form claims are both *anti*-coreference traps, and they sat in the **positive** set. Falling
   for both scores **+0.27** on a metric weighted 5.0 — **29× the composite gap that decided the verdict.**
2. **The tie was manufactured.** 0.0095 was not similarity: four lines separated cleanly in *opposite*
   directions and averaged into silence. Two of the cleanest carry **weight 0**.
3. **27% of the weight is one string test run twice** — strip the locality window from `citation_faithfulness`
   and it *is* `extract_only_stated` to 3 dp. Both declared vetoes, so one measurement vetoed twice.

**We scored a metric we never asked for.** The extraction prompt contains **zero** occurrences of
"discriminator"; `discriminator_capture` is weighted 4.5. That explains the enormous run-to-run variance on
one model — it was guessing at an unstated target.

**A correction to an earlier claim of mine:** `trap_avoidance` does **not** survive. All 25 apparent hits are
span-overlap artefacts, zero are fabricated assertions, and on a containment basis the ordering **reverses**.
Anything citing it as the robust separator is wrong.

---

## 4. The rule that governs the repair

Two changes must never be blurred:
- **The instrument is WRONG** (rewards the harm, double-counts a weight, scores what no model could produce) ⇒
  fix it; that is what makes the measurement valid.
- **The instrument is HARSH and could be tuned to score better against these 125 rows** ⇒ that is tuning to
  the benchmark. It inflates scores without improving extraction.

The test: *would this help a real analyst reading real documents, or only help us score against this gold?*
**A verdict manufactured by adjusting the instrument until a winner appears would be worse than the original
artefact, because it would carry a repair's credibility.** An honest tie from a repaired instrument is a good
outcome.

---

## 5. What remains after this

1. **RK-DATA re-record** — keyed re-extraction, pre-authorised by the user (do not re-ask). Scope is
   `hq9p_primary` **only**; `hq9p_sandbox` is untracked/gitignored and should be declared dead, not
   regenerated. Detail in `tmp/conv/S4-anchors-and-rerecord-scope.md`.
2. **RK-NAMECUT (S4)** — cut name-derived node ids. Blast radius is 156 of 183 nodes; the entity registry is
   already the one thing pinning ids and should be **exempted, not re-keyed**. Same note.
3. **RK-MATERIALITY** — smallest of the four; its value depends on (1) having produced individuated instances.
4. **Re-run the bake-off** only after the instrument is repaired *and* the harder corpus lands. A repaired
   instrument on today's thin slice may still tie honestly — that is a legitimate result, not a reason to
   re-run.

**Open for the user, not an agent:** the frontend is unverified by any compiler (`node_modules` absent — run
`npm ci && npm run typecheck`); the design note still describes the pre-replumb system; and GPT-5.6 Sol was
never measured, blocked by two account rate-limit tiers rather than anything about the model.
