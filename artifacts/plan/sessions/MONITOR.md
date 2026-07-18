# Session MONITOR — Observable DSL Engine

**Wave 1 · depends on F0 only · no sibling code dependency · NO LLM.**
Read `../00-master-plan.md` §4.6 (the Observable DSL contract you implement), §4.2 (the **Alert object** +
the `alert_disposition` decision record), §4.3 (`rebuild()` emits the two views whose **delta** you consume),
§5 (gates G1/G6 you stay green on), and §8 (worktree/PR workflow). MONITOR is deliberately **thin**: it is one
declarative evaluator over view deltas, no new per-observable code — its whole point is that an analyst
composes a tripwire from fields that already exist. It builds against F0's frozen contracts + the golden
two-view fixture, never against sibling code.

## Goal

Ship the **observable evaluator**: a small declarative DSL over existing node/edge attributes + precomputed
materiality metrics that, given the before/after views of a `rebuild()`, fires **Alert objects** for any armed
observable whose condition crosses. The seeded C tripwire (the HQ-9B Rawalpindi→Rahwali `based-at` occupancy
state-change) must fire end-to-end on the fixture; the secondary tripwires ship **config-only**, proving
observables are declarative, not hardcoded. This is what makes the monitoring axis *real* — every ingest /
decision / config write → `rebuild()` → armed observables re-checked → crossings fire.

## Design docs to read first
`spine/07-monitoring-retrieval-viz` (the observable/tripwire decisions + the LOCKED C tripwire) · `spine/08`
**§3.8** (the declarative observable spec + the LOCKED Rawalpindi→Rahwali relocation) · `spine/09`
("Analyst-defined observables" + the hot-config **arm-on-save / fire-on-next-rebuild** model, DSL operator
set) · `C/02-demo-thread` (the Rawalpindi→Rahwali thread, flex 6 + the two secondary observables) ·
`product/03` **F** (the Alert/Observable shape the API/SPA bind to). Materiality attrs the DSL filters on are
in `C/01` (`occupancy_state`, `decoy_risk_flag`, `chokepoint_count`, `substitutability_state`).

## Scope (build these)

1. **The DSL** — a small condition grammar over **existing** view fields: node/edge raw attrs + precomputed
   materiality metrics, with the operator set `equality / threshold (<,≤,=) / crossing (state-change) / exists`
   over the demo node/edge types (`based-at`, `replenishes`, Component/Site/Unit/Contract attrs). It references
   only fields that already exist in the view JSON, so **adding an observable is a config edit, never code**
   (gate G6: no operators/thresholds/severities hardcoded in `observe/` core — all read from config).
2. **The declarative spec** (`spine/08` §3.8, master §4.6) — parse/validate an observable of the frozen shape:
   `{observable_id, subject|lens, trigger:{on (e.g. occupancy_state_change), edge_type (e.g. based-at),
   match_on:[resolved_unit, site_instance] — resolved instances, NEVER designator strings,
   anchors_within_hops}, severity, disposition:[real, noise, needs-more]}`. Load from `config/observables.yaml`
   (DATA-C content) through F0's config store, or from an API config write (hot-config) — never a baked file.
3. **Lifecycle** — **DEFINE** (config or API write) → **ARM immediately** (a read-only pass against the current
   view on save; optional **back-scan** of the event log for already-existing matches — no rebuild needed) →
   **FIRE** on the next `rebuild()` by consuming the **view delta** (prev_view → new_view; §4.3) → **DISPOSITION**
   (real/noise/needs-more) read back for tripwire tuning (`spine/06` adaptation).
4. **The evaluator** — a pure function `evaluate(prev_view, new_view, armed_observables, config) -> [Alert]`:
   for each armed observable, resolve its scope via the lens (`anchors_within_hops` from the subject anchors),
   match candidate node/edge instances **on resolved `entity_id`×`edge_instance`** (never a name/designator
   string, per §4.2 `resolved_ref`), and emit an **Alert** (§4.2 shape: `observable_id, subject, before, after,
   severity, fired_ts, disposition?`) for each crossing. `before`/`after` carry the changed state
   (e.g. `occupied@site-rawalpindi → occupied@site-rahwali`). No LLM, no network in this module.
5. **The seeded C observable** — `obs-basing-relocation`: the HQ-9B Rawalpindi→Rahwali `based-at` occupancy
   **state-change** for the one named fire-unit, matched on resolved unit×site instance. It fires on the
   before→after fixture; the credibility that resolves the new position to probable→confirmed and the
   supersede→stale of the old position are **SCORE/`rebuild()`'s job** — MONITOR only fires the state-change
   Alert off the delta.
6. **Secondary observables — config-only** — the follow-on interceptor order via `replenishes`, and the spares
   tender → probable-induction tripwire, ship as **config entries only** (in `config/observables.yaml`, DATA-C),
   not wired into the narrative: they must **load and arm without any code change**, proving the engine is
   declarative. MONITOR's tests assert they parse + arm; they need no bespoke handling.
7. **Disposition seam (fire-only)** — a fired Alert routes to disposition (real/noise/needs-more). **MONITOR
   just fires the alert**; the alert-disposition review card + the writeback are **HITL's** (§4.7). MONITOR
   owns the *consumption* side: it reads `alert_disposition` decision-log entries (§4.2) back on rebuild to
   feed tripwire tuning. Round-trip is proven in MONITOR's tests by appending an `alert_disposition`
   `DecisionRecord` to F0's decision log and asserting MONITOR reads it — the card/enqueue orchestration is
   out of scope (HITL).

## Contracts implemented
Master **§4.6** (Observable DSL — lifecycle, declarative spec, seeded + config-only observables), **§4.2**
(the Alert object + `alert_disposition` decision record), **§4.3** (consumes the prev→new view delta from
`rebuild()`). MONITOR implements against these; it **freezes nothing** and touches no F0-frozen file. If a
field on the Alert or observable spec must change, that is an **F0-amendment PR** (master §2 Rule 3), not an
edit in this PR.

## Acceptance criteria
- [ ] The seeded relocation observable **fires** on F0's before→after two-view fixture (a `based-at`
      occupancy state-change), emitting an Alert whose `before`/`after` carry `occupied@site-A →
      occupied@site-B`.
- [ ] The match is on the **resolved unit×site instance** (`entity_id`×`edge_instance`), **not** a designator
      string — a test with a spelling/designator variant that resolves to the same instance still fires; a
      different instance does not.
- [ ] A **config-only secondary observable** (`replenishes` follow-on order, or the spares tender) **loads and
      arms with no code change** — the DSL parses it, the evaluator scopes it, no bespoke branch exists for it.
- [ ] A **fired Alert records before→after** and matches the §4.2 / `product/03` F shape (`observable_id,
      subject, before, after, severity, fired_ts, disposition?`).
- [ ] **Disposition round-trips to the decision log**: an `alert_disposition` `DecisionRecord` appended to
      F0's decision log is read back by MONITOR for tuning (proving the HITL seam), without MONITOR owning the
      writeback.
- [ ] Gates green: **G1** (no `anthropic`/`httpx`/network import in `observe/`), **G6** (no operators /
      thresholds / severities hardcoded in `observe/` core — all from config), plus `ruff`/`mypy`/`pytest`.

## Owned paths (nothing else)
`chanakya/observe/**`, `tests/observe/**`. **Depends on:** F0 (merged). **LLM:** no. Reads config only through
F0's config store and views/logs only through F0's `view`/`store` surfaces — never edits them.

## Out of scope
The **alert-disposition review card + writeback** (HITL, §4.7) — MONITOR fires the alert and reads dispositions
back, but does not own the card or the enqueue/writeback. The **credibility that resolves probable/confirmed**
and the supersede→stale decay behind the relocation beat (SCORE / `rebuild()`). The **map animation** (pins
move + recolor) and any UI rendering of the alert (frontend). New DSL *code* for a metric that does not yet
exist as a view field (that is a redeploy, not an observable — `spine/09` honest boundary).

## Worktree lifecycle
`git worktree add ../wt-MONITOR -b feat/monitor` → implement inside owned paths only → PR `[MONITOR]` →
**you review & merge** → `git worktree remove ../wt-MONITOR`. Rebase onto `main`
whenever a sibling merges (always clean given disjoint ownership); does not block and is not blocked by any
other Wave-1 session.
