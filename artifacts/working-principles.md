# Working principles — how to run an agent build on this project

These were set during the resolution-redesign build (2026-07-23). They are **method**, not domain — carry
them forward to any agent doing substantial work here. Most are strong defaults; the non-negotiable is
marked. (They extend, and in places sharpen, the working agreements in `CLAUDE.md`.)

## 1. Target-first — the data bends to the design, never the reverse
Build the **general/target system** at full strength. The corpus and `answer_key.json` are **synthetic,
regenerable demo fixtures** — never curb, gate-off, or default-away a target-correct capability to keep the
current data or a golden fixture green. Build the target's capability even when it's *ahead* of the current
data; let the data catch up. "Extendable" means the target is extendable — not that the current demo is
preserved.

## 2. Three surfaces, three separate hands — nobody validates their own work
The three surfaces of a change — **code** (implementation), **test** (validation), **data** (corpus /
sandbox / fixtures) — must each be authored by a *different* hand. A test may *reference* code (import/call
it — the one inherent touch) but its **author** must differ from the code's author and must write it from
the **spec** (asserting what correct behaviour *is*). Data is authored independently of both. The
orchestrator is the integration point: it defines the contract up front, then runs the independently-
authored tests against the independently-authored code on independently-authored data.
- **The implementer stays corpus-blind**: it never boots/measures the primary corpus, and its
  gates/thresholds are chosen on *general principle* — because seeing the specific data biases it to tune to
  that data. The orchestrator measures corpus impact separately, after the code is frozen.
- This separation repeatedly caught real bugs the implementer (and the orchestrator's own contract) missed.

## 3. The agent regenerates nothing — it documents; the user regenerates
When a target-correct change invalidates a fixture (even a derived one like a golden snapshot) or an
answer-key expectation, the agent does **not** regenerate it. It keeps the target behaviour, marks the
stale test `xfail(strict, reason=…)` (annotation, not a fixture edit), and records precisely what needs
regenerating in a **calibration/data-refresh ledger**. The user runs the data/regeneration pass.

## 4. Data-staleness must NEVER mask a logic bug
- **Primary defence**: cover every mechanism with GREEN, *corpus-independent* unit tests, so logic
  correctness never depends on a stale-corpus test.
- **Predict-then-verify**: before running, document each expected failure with its exact signature (test id
  + the precise diff + why it's target-correct). A failure counts as "expected" only if the observed diff
  matches and nothing else in that test moved.
- Any **new**, **unmatched**, or **compound** failure is a REGRESSION until proven otherwise — never waved
  off as "probably staleness." Keep the expected-red set minimal.

## 5. Surface the target's outputs — don't hide them to protect a fixture
Additive changes that keep the frozen partition stable are good. But keeping a target *output* off the wire
(`exclude=True`, in-memory-only) *specifically to keep a golden snapshot byte-identical* is the same
curb-for-the-demo anti-pattern as gating a mechanism. Surface the outputs; let the golden change; log the
regeneration (per #3). Distinguish "byte-inert on the corpus" (a legitimate *consequence* of sparse data,
mechanism at full strength) from "hidden to protect the fixture" (not allowed).

## 6. Explore the code, not the docs
Design docs/MDs drift. Verify every load-bearing claim against the **current code**. When a doc and the
running code disagree, the code is the fact.

## 7. Demand proof of work, then verify it yourself
Every delegated finding must be backed by real `file:line` snippets and, for anything quantitative, actual
run output — never a paraphrase. The orchestrator independently verifies the load-bearing claims (spot-read
the cited code, re-run the tests) before building on them.

## 8. Delegate to keep context lean; right-size the model
Push heavy reading, searching, and multi-file investigation into subagents; read back their *conclusions*,
not raw files. Size each subagent to the task — a cheaper model for mechanical extraction/rendering, the
stronger model for genuine judgement/design. Make the choice deliberately per task.

## 9. Smallest verifiable increment; each stage verified + committed
Prefer the targeted change over the principled refactor. Decompose a big stage into verifiable sub-stages;
verify each (independent tests + integration) and commit it before the next, so history is bisectable and a
regression is isolatable. Sequence by dependency.

## 10. Confidence + the north star; escalate only genuine forks
Drive toward the target's real capability with confidence; decide freely and report; reserve check-ins for
load-bearing forks (something expensive to undo, or that could fabricate/unground an assessment) — not
permission for the obvious next step. The verification rigor above is what *earns* the confidence; it is
forward momentum, not timidity.

## 11. Worktree hygiene
Do the work in a dedicated `wt-*` worktree branched off `origin/main`; keep the primary checkout pristine.

## 12. Commits & PRs — author as the human, no AI attribution
Commit each verified stage with a clear conventional message. **Never** add a `Co-Authored-By: …AI…` or
"Generated with…" trailer to a commit or PR body — author as the human committer only.

## 13. Talk to the human in concepts, keep the code in the files
Explain the *why*, the tradeoff, and the *so-what* in plain language and analogies — never dump code,
schema, or `file:line` at the user in chat. Depth lives in the files, the design docs, and the handoff
notes for other agents; translate it out of the conversation.

## The one non-negotiable (runtime, orthogonal to all the above)
The **running system** must never fabricate an assessment: where evidence is absent/ambiguous/contradictory
it returns an explicit "insufficient evidence," names what is missing, and escalates to the analyst.
Fabricated/hallucinated assessments are disqualifying. This is about the system's honesty at query time —
distinct from (and unaffected by) the malleability of test data in #1/#3.
