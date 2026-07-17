# Handoff — Session F0 · Foundation, store, `rebuild()` skeleton, fixtures, gates, CI

**This is what the next agent reads to trust and build on F0.** Onboarding chain still applies:
`CLAUDE.md` → `PROGRESS.md` → `sessions/<ID>.md` → the design docs it names → master §4.

## Status at handoff
- Branch / worktree: `feat/f0-foundation` / `../wt-F0`
- PR: `#<n>` — <in-review | merged @commit>
- Gates: **G1–G12 green** · ruff/mypy/pytest **green** (`make check` → 63 passed, 0 lint, 0 type errors)
- Owned paths touched (and **nothing outside them**, except the two reconciliations below): `backend/**`
  (`pyproject.toml`, `chanakya/{schemas,config,store,view}`, all stub packages, `tests/{fixtures,gates,
  view,store,config,schemas}`), `Makefile`, `.github/workflows/ci.yml`, `artifacts/plan/sessions/HANDOFF-F0.md`,
  `DECISIONS.md` (append only — see below).
- Frozen-file edits: **none**.

## What shipped
- **Schemas (`chanakya/schemas/`)** — every frozen record + value object + view/config/API model (master
  §4.2, §4.8). Discriminated-union claim payload (`triple`/`entity`/`event`) cross-checked against
  `asserts`; **no network/parse in any validator** (keeps rebuild reload G1-safe). Value objects
  `Date`(Exact/Label/Period)/`Location`/`Quantity` are shapes + canonical slots only; pure
  `canonical_iso_bounds()` gives SCORE an offline freshness read. `Location` carries `geocode_candidates`
  + `proposed_alias` (closes the PROGRESS "F0 location descriptor" reconciliation) + `resolved_place_ref`.
- **Config store (`chanakya/config/`)** — live, versioned, writable; `seed_from(config/*.yaml)`,
  `snapshot()` (deep copy — determinism-safe), `set_section`/`update_credibility` (hot writes bump
  `version`). Wave-1 reads config **through this**, never files.
- **Store (`chanakya/store/`)** — append-only SQLite evidence + decision logs. **No update/delete on the
  API**; `BEFORE UPDATE/DELETE` triggers `RAISE(ABORT)` so even raw SQL can't mutate (G3). `seed_from`
  (JSON array or JSONL) + `replay` are insertion-ordered → deterministic (G2).
- **View (`chanakya/view/`)** — `rebuild()` pure orchestrator (fixed stage order); **real** F0 pieces:
  retraction handling, supersede-vs-contradict on `resolved_ref` (`supersede.py`), `apply_lens`
  (N-hop-from-anchors + materiality filter, NetworkX), deterministic JSON export (`export.py`), and HITL
  decision-effect application (G12).
- **Stage stubs** — `resolve/credibility/sufficiency/materiality/observe/agent/ingest/hitl/api` each export
  their frozen stage function as a trivial, pure, magic-number-free stub so the skeleton runs today.
- **Fixtures + gates + CI** — golden synthetic scenario (decoupled from the C corpus) exercising supersede,
  retraction, and a G12 override in one view; per-stage seeds for RESOLVE/SCORE/MONITOR; **G1–G12**
  implemented; GitHub Actions runs ruff+mypy+pytest on every push/PR.

## Contract points implemented
- Master §4.1 (layout/deps), §4.2 (records + value objects), §4.3 (stage signatures + rebuild order +
  supersede + lens + export), §4.4 (config store), §4.8 (API/view-JSON models), §5 (G1–G12).

## Frozen stage signatures (Wave-1 fills the body, keeps the signature)
```
resolve(claims, config, prev_view=None) -> Partition
score_claims(resolved_claims, sources: dict[str,SourceRegistryEntry], config) -> {claim_id: float}
group_by_independence(claim_ids, claims: dict[str,ClaimRecord], sources, config) -> [IndependenceGroup]
assign_status(assertions: [AssertionInput], config) -> {element_id: AssertionAssessment}
check(assertion: AssertionInput, claims: dict[str,ClaimRecord], config) -> SufficiencyEval
precompute(view, config) -> GraphView            # fills node.materiality
evaluate(prev_view, view, config) -> [Alert]     # post-rebuild (MONITOR)
```

## Decisions taken (also in DECISIONS.md → "F0 build decisions"; surfaced in the PR body)
See DECISIONS.md. Highlights: renamed the rebuild *module* to `view/pipeline.py` (function stays
`rebuild`) to kill a module/function name shadow; edge id = `e:{src}:{type}:{tgt}`, supersede groups on
`resolved_ref.edge_instance`; G4 exempts resolution edges; records `extra="forbid"` / config
`extra="allow"`.

## Deviations / reconciliations vs `sessions/F0.md`
- **`make test`/`lint` are real, not `echo TODO`** — acceptance requires `make test` green; only the app
  targets (extract/build/ingest/ask/run) are stubbed. (Master §7 wins over F0.md scope #1's literal list.)
- **`PROGRESS.md` not edited in this PR** — master §2 Rule 4 (never in a PR; user maintains at merge)
  overrides F0.md scope #10's "seed"; the board already exists. Paste the F0 handoff row at merge.
- **F0 own-module tests live in `tests/{view,store,config,schemas}`** — master §4.1 ("`tests/<module>/`
  owned by that module's session"; F0 owns those four modules). F0.md's owned-path list named only
  `tests/{fixtures,gates}`; these dirs are conflict-free (no other session touches them).

## Follow-ups & seams for later sessions
- **RESOLVE:** `resolve()` stub is identity; the fixture convention is that a relationship claim's
  `payload.subject/object` are already node ids. RESOLVE should add surface-string→entity-id endpoint
  resolution (and set `resolved_ref.edge_instance` so co-referring state claims share an instance → drives
  supersede). Extend `per_stage/resolution_partition.json` with `expected_merged` and emit `same_as`
  (+ `merge_confidence` on the same-as edge — never into `assertion_confidence`, G5).
- **SCORE:** fill `score_claims`/`group_by_independence`/`assign_status`/`check`/`precompute`. The confirmed
  gate invariant + fixtures live in `gates/test_g7_*` + `per_stage/status_cases.json`; the Known-Gap
  emission path in `pipeline.py` already fires when `check` returns `satisfied=False` (see
  `gates/test_g8_*`). Wire `superseded_by` → `stale` in `assign_status` (F0 sets the structure, not the
  status — G5). All numbers from `config.credibility` (G6).
- **MONITOR:** `observe.evaluate` stub fires nothing; seed + expected shape in `per_stage/alert_delta.json`.
- **INGEST:** owns the `Date`/`Location`/`Quantity` normalization *adapters* (run at extraction,
  pre-append — never as validators). `ingest.ingest_bundle` is a minimal keyless-append helper to extend.
- **API:** `create_app()` is a stub; all shapes are in `schemas/api_models.py`.

## Verification evidence
- `make check` → `ruff: All checks passed` · `mypy: Success, 30 files` · `pytest: 63 passed`.
- Golden view (`tests/fixtures/golden/expected_view.json`) frozen and byte-matched by G2; G1 rebuilds with
  socket/anthropic/time/random patched to raise; G2 also compares two subprocess runs under differing
  `PYTHONHASHSEED`.
