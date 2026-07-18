# Handoff — Session <ID> <title>

**Fill this in as you go; paste the final into the PR body and into `PROGRESS.md` §Handoff notes (in your PR).**
This is what the next agent reads to trust and build on your work.

## Status at handoff
- Branch / worktree: `feat/<id>` / `../wt-<ID>`
- PR: `#<n>` — <in-review | merged @commit | blocked on …>
- Gates: G1–G12 <green | which failing & why> · ruff/mypy/pytest <green>
- Owned paths touched (and **nothing outside them**): <list>
- Frozen-file edits: **none** (or: F0-amendment PR #<n> for <what>)

## What shipped
- <module capability 1> — <one line + where the test is>
- …

## Contract points implemented
- Master §<…>: <how — the stage signature filled / endpoint added / config consumed>

## Decisions taken (record each; also append to `DECISIONS.md`)
- <choice> — principle <§1 #> invoked; rejected <alternative>; because <one line>.

## Deviations from the plan / design docs
- <none | what & why; flag any design-doc tail to enrich>

## Follow-ups & seams left for later sessions
- <what a dependent session should know: an attr it can read, a fixture it can reuse, a TODO>

## Verification evidence
- <command(s) run + result: `make test`, the acceptance snippet, a sample view-JSON / answer, etc.>
