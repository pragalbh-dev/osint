# RESOLVE/HITL: accepting a Merge review card does not actually grow the alias table

**From:** README + EC2 shipping task (docs/readme-and-deploy), 2026-07-20, via a subagent
exploration of "does a review decision durably change graph state." Not fixed here — this
session was scoped to docs + deploy, explicitly no logic changes. Filing so RESOLVE/HITL
picks it up.

**What.** `build_merge_item()` (`backend/chanakya/hitl/controlpoints.py`) declares an
`accept` effect shaped `{"grow_alias": {"same_as": [a, b], ...}}`. The consumer that's
supposed to grow the alias table on accept, `resolve/aliases.py` (`_pair`/`_accepted`/
`_separated`, ~L105-131), only looks for a `pair`/`members`/`same_as` key directly under
`decision` or `context` — not one level deeper under `effects.grow_alias`, which is where
the real `/hitl/merge` API path actually puts it. Ran the real chain
(`build_merge_item → dispose → bind_writeback → aliases.build()`) end to end:
`equivalent()` returns `False` after a real accept.

**Effect.** Clicking **Merge** or **Keep separate** on a review card in LIVE mode (the one
path that calls the real backend — DEMO mode's cards are local-only and don't touch this
code at all) does **not** persist: the alias table isn't grown, `distinct_from` isn't
recorded, and the card's own promised consequence line ("Joins N claims, changes M node
statuses") does not occur. The same pair resurfaces as an ambiguous merge candidate on the
next rebuild — the review is not remembered.

**By contrast, Status-override (Promote/Demote/Reject) works correctly** —
`apply_decision_effects` in `backend/chanakya/view/pipeline.py` (~L527-558) handles
`set_status` and is consumed on every rebuild; there's a passing positive test
(`backend/tests/api/test_hitl.py::test_hitl_status_demote_propagates_with_no_restart`).
Only Merge is affected. Alert-disposition marks that specific fired alert dealt-with
(separate, working code path) but by design doesn't suppress future similar alerts.

**Why this matters more than a normal bug.** "HITL overrides propagate to graph state, not
just a log" is one of the project's four load-bearing architectural claims (`CLAUDE.md`).
Merge is the review-card type most likely to be exercised live on a call (the merge-queue
count is one of the QA sweep's headline numbers), and a reviewer who accepts a merge and
sees no lasting effect — or worse, sees the same "resolved" pair come back — will
reasonably read that as the system not listening to them.

**No test would have caught it.** `backend/tests/api/test_hitl.py` only has a 404 case for
`/hitl/merge`; there's no positive end-to-end test asserting the alias table actually grows
after a real accept, unlike the status path which has one.

**Not fixed here — out of scope for a README/deploy-only session with an explicit "no logic
changes" instruction.** The likely fix is small (point `aliases.py`'s pair-extraction at
`effects.grow_alias.same_as`, matching what `controlpoints.py` actually emits) but is
RESOLVE/HITL's call, with its own test to add.

**Everything reviewed here — working or not — is in-memory only** (`EvidenceLog`/
`DecisionLog` default to SQLite `:memory:`, no volume in `docker-compose.yml`) and resets
on container restart, same as ingested documents. That part is "by design," not a bug.
