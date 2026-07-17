# Session EVAL — Acceptance Harness (Spine Gate + 6 Demo Flexes)

**Wave 2 · the TOP acceptance gate · depends on all Wave-1 (RESOLVE, SCORE, MONITOR, ASK, HITL, INGEST) +
DATA-C (merged) · a Wave-2 merge requires this green.**
Read `../00-master-plan.md` §6 (testing standards — the **Acceptance (EVAL)** bullet: "runs the frozen
corpus end-to-end … asserts the spine-gate 5 criteria and the 6 demo flexes … the top-level gate; a Wave-2
merge requires it green"), §5 (the G1–G12 gates this re-exercises end-to-end, not per-unit), §3 (the DAG —
EVAL row + dependency notes), §4.2/§4.3/§4.8 (the view-JSON shapes it asserts against). This session writes
**no module logic** — it wires the merged spine to the frozen oracle and reports pass/fail.

## Goal

Prove the built system does what the brief is graded on, on the **one frozen scenario** an evaluator can pick
live. Run `corpus/scenarios/hq9p_primary` end-to-end (**ingest → rebuild → ask**) through the *real merged
Wave-1 code + real `config/*.yaml`*, then assert the computed view + answers against `answer_key.json`
(nodes, edges, per-node/edge status, places, and the per-doc `expect` oracle), the **5 spine-gate criteria**,
the **6 demo flexes**, and **C's rebuttal-to-beat**. Emit a short human-readable **report** (pass/fail per
criterion + per flex + a status-diff table) usable on the call. If EVAL is red, the demo is not shippable.

## Design docs to read first
`DECISIONS.md` §4 (the **Spine gate** 5 criteria, the **Layer gate**, and **C's rebuttal to beat** —
*"how do you know that node is real — confirmed or guessed?"*) · `C/02` (the one thread + the six demo
flexes, each mapped to a graded quality + planted scenario) · `product/04` (the frozen ground-truth entities
+ alias/merge traps + document index) · the eval oracle itself: `corpus/scenarios/hq9p_primary/answer_key.json`
(`ground_truth.{nodes,edges,places}`, `worked_query`, `observable`, `flexes.*`, `documents[].expect`) +
`SCENARIO_MANIFEST.json`. Skim `spine/04` (status vocabulary: confirmed/probable/possible/stale +
Known-Gap-off-scale) so status assertions match the machine, not prose.

## Scope (build these)

1. **Harness runner** (`eval/`) — a small orchestrator that, given a scenario dir, drives the *real merged
   pipeline*: seed the store from INGEST's pre-extracted claim bundles (keyless, recorded), load `config/*.yaml`
   through the config store, `rebuild()` the view, arm the seeded observable, and run the fixed hero query +
   the tested queries through ASK on **recorded traces**. Produces the report artifact. No scenario logic is
   hardcoded here — it reads `answer_key.json` as the expectation set.
2. **Corpus → view/answer assertions** (`tests/acceptance/`) — assert the rebuilt view against
   `ground_truth`: every node/edge in `answer_key` is present with the expected `status`
   (confirmed | probable | possible | stale | candidate; Known-Gap nodes off the confidence scale =
   insufficient), every `place` resolves to its canonical node at the right `precision_class`, and the
   `worked_query.expected_path` + `expected_answer` shape matches (chokepoint = HT-233 **candidate**, maker a
   **Known Gap**, substitutability UNKNOWN — never a fabricated sole-source). Then walk `documents[].expect`
   as a **per-doc oracle** (`contributes_to` / `resolves` / `location` / `note`): the aggregator collapse
   (d01→1 origin group), aligned-interest non-confirm (d02+d15), adversary-denial gate (d16), same-time
   contradiction→HITL (d08/d09), front-company relational resolve (d05), CPMIEC false-attribution refuted
   (d23 vs d22), and location normalization (d18 DMS ≡ d19 toponym+relative → `pl_rahwali`; port distinct-from).
3. **`answer_key.json` separation guard** — assert the oracle is **EVAL-ONLY**: a test that fails if any
   module under `chanakya/` (pipeline) or any `config/*.yaml` / ingest seed bundle references `answer_key.json`
   (import-boundary + path grep). The harness feeds the pipeline **only** corpus docs / pre-extracted bundles
   + `config/*.yaml`; `answer_key.json` is opened solely in `tests/acceptance/**` and `eval/**`.
4. **The 5 spine-gate criteria** (`DECISIONS.md` §4) — one assertion each:
   (1) the worked query runs end-to-end **reproducibly** (byte-stable answer/path across 2 runs on the
   recorded trace); (2) **insufficient-evidence trips** on the deliberately planted gap (d10 cloud-gap →
   `Known Gap` with `missing_slots` + `next_coverage_due`, not a guess); (3) **every claim/node one-click
   traceable** (each view node/edge → ≥1 claim_id → real `doc_ref` span; the G4 invariant asserted over the
   *real* corpus view); (4) a **HITL override propagates** to downstream state (append a decision to the log →
   `rebuild()` → the answer changes; the G12 invariant end-to-end); (5) **re-point by config, not core code**
   — a test that edits a config value (swap a `subjects.yaml` anchor / an `observables.yaml` tripwire / a
   `credibility.yaml` threshold) and re-runs, asserting the view/answer changes with **no** code edit.
5. **The 6 demo flexes** (`C/02`; anchors in `answer_key.flexes`) — one assertion each:
   1. **Confirmed vs probable** — `import_2021` reaches **confirmed** only with a genuinely cross-interest
      source (`corroborated`), while `sustain_spares` stays **probable** on a single source (`single_source`).
   2. **Insufficient-evidence on the cloud-gap** — `gap_insufficient_evidence` (d10 + d17b negative
      observation) → Known Gap with named missing slot + next coverage due.
   3. **M4 override** — `planted_tooclean` (d11 recycled parade image, first_seen 2019, + d12/d13 two
      reshares): the integrity/first-seen signal collapses the echo burst to **one** origin group and applies
      the too-clean penalty so the Rahwali-deployment claim does **NOT** become confirmed — the integrity
      gate **overrides** the corroboration count.
   4. **HITL merge + propagation** — `alias_merge_trap` (d03/d04): FD-2000 **same-as** HQ-9/P (auto-merge);
      HQ-9/P **distinct-from** HQ-9BE (flagship trap → HITL band → keep separate); FT-2000 **distinct-from**
      HQ-9/P (→ HITL → do NOT merge). Assert the analyst decision written back changes the downstream query
      answer (the propagating-HITL + learning-loop beat).
   5. **Freshness / stale** — `freshness_stale` (d14): confirmed-as-of-2016 → **probable (stale)**; and
      `site_rawalpindi` demotes to **stale** after the relocation.
   6. **Relocation observable, end-to-end** — `observable_relocation` + `supersede_spoof` (d17→d18→d19→d20):
      Rawalpindi **confirmed** (2021) → single 2025 pass → **probable** (decoy cap) → 2nd independent look →
      **confirmed** → **supersedes** retires the Rawalpindi position to **stale**; the d20 spoof is held as a
      candidate-supersede → HITL (the confidence floor resists it). Assert the `Alert` fires and the
      normalization (d18 DMS ≡ d19 relative-bearing → one `pl_rahwali`) is what unlocks the corroboration.
6. **C's rebuttal-to-beat** (the Layer gate) — assert that clicking **any** node/edge yields a truthful
   provenance/confidence/freshness answer: for every view node, the provenance drawer (`GET /evidence`
   shape) returns its claim clusters + status + freshness, and no node is "confirmed" without the G7 gate —
   the traceability + confirmed-vs-guessed test the interviewer runs live.
7. **Recorded-trace vs `@live`** — all graded/deterministic beats run on **recorded LLM traces** (INGEST's
   pre-extracted bundles + ASK's frozen hero/tested-query traces) so the harness is offline and reproducible;
   a separate opt-in **`@live`** suite (pytest marker, `master §6`) exercises the real Ask loop when
   `ANTHROPIC_API_KEY` is present — a bonus, never load-bearing on the gate.
8. **Report** (`eval/`) — a short markdown/JSON report: pass/fail per spine-gate criterion, per demo flex, and
   a node/edge **status-diff table** (expected vs computed). This is a demo deliverable — legible on the call.

## Contracts consumed (EVAL freezes nothing)
Master §4.2/§4.3 (record + stage signatures) and §4.8 + `product/03` A–H (view-JSON / provenance / ask /
observable / Known-Gap shapes) — EVAL asserts against these, it does not define them. It re-exercises the §5
gates (esp. **G4** traceability, **G7** confirmed-gate, **G8** insufficient-first-class, **G12**
HITL-propagation) at scenario scale. No F0-frozen surface is touched; if a real answer_key expectation
cannot be met because a contract is wrong, stop and raise an **F0-amendment PR** (master Rule 3) — do not
weaken the assertion to make it pass.

## Acceptance criteria
- [ ] The harness runs **green** over the frozen `hq9p_primary` corpus: ingest → rebuild → ask through the
      real merged Wave-1 code + real `config/*.yaml`, with no scenario logic hardcoded.
- [ ] Every `ground_truth` node/edge is present with its expected **status**; every `place` resolves to its
      canonical node at the right precision; the `worked_query` path + candidate-chokepoint/Known-Gap answer
      match; the per-doc `expect` oracle passes for all `documents`.
- [ ] All **5 spine-gate criteria** assert green (reproducible worked query · planted-gap insufficiency ·
      one-click traceability · HITL override propagation · config-only re-point).
- [ ] All **6 demo flexes** assert green (confirmed-vs-probable · cloud-gap insufficiency · M4 override ·
      HITL merge + propagation · freshness/stale · relocation observable + supersede-spoof floor).
- [ ] **C's rebuttal-to-beat** passes: any node click returns a truthful provenance/confidence/freshness
      answer and no node is confirmed without the G7 gate.
- [ ] `answer_key.json` is proven **EVAL-only**: no pipeline module or config references it; it is read solely
      under `tests/acceptance/**` + `eval/**`.
- [ ] The harness is **offline/deterministic** on recorded traces (byte-stable across 2 runs); the `@live`
      suite is opt-in and skipped without a key.
- [ ] The **report** is emitted (pass/fail per criterion + per flex + status-diff table), legible for the call.

## Owned paths (nothing else)
`tests/acceptance/**`, `eval/**` (the runner + report). **Depends on (merged):** all Wave-1 (RESOLVE, SCORE,
MONITOR, ASK, HITL, INGEST) + DATA-C. **LLM:** recorded traces (graded beats) + optional `@live` (real Ask).
Does not touch `chanakya/**`, `config/**`, `corpus/**`, `tests/{fixtures,gates,<module>}/**`, or deploy files.

## Out of scope
The module logic itself (Wave 1 fills the stages — EVAL only asserts the merged result); deployment / `make`
targets / image (SHIP); generating the corpus or `answer_key.json` (DATA-C owns the oracle — EVAL consumes it
read-only, never edits or regenerates it); the per-unit G1–G12 gate suite (F0 owns those; EVAL re-exercises
them end-to-end, it does not re-author them); the API app body (API).

## Worktree lifecycle
`git worktree add ../wt-EVAL -b feat/eval` → implement → PR `[EVAL]` → **you review & merge** → you update
`PROGRESS.md` → `git worktree remove ../wt-EVAL`. Runs in Wave 2 alongside API; both integrate merged Wave-1
code. Rebase onto `main` whenever a sibling merges (clean given disjoint ownership).
