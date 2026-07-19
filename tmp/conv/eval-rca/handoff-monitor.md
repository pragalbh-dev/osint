# EVAL RCA handoff — MONITOR (observables)

## Context

The pipeline was run end-to-end for the first time over real extracted bundles, and the resulting
knowledge-graph view diverges sharply from the oracle. This handoff is MONITOR's (the observables /
tripwire service's) share of the fix. Full evidence is in `tmp/conv/eval-rca/00-evidence-summary.md`
and `tmp/conv/eval-rca/view_full.json`; the generated claim bundles that fed the run are in
`corpus/scenarios/hq9p_primary/claims/`.

## TL;DR

1. **`compile_trigger`/`resolve_scope` silently drop the observable config's own keys** (`unit`,
   `from_site`, `to_site`, `window`, `match_on`) — the relocation tripwire cannot scope to the intended
   unit/sites and falls back to an unscoped watch. Fix once RESOLVE/entity-linking upstream is fixed.
2. **The relocation observable rewinds on the wrong time axis** — it uses an *availability*
   (transaction-time / ingest-time) rewind (`as_of='2021-12-31'`) to try to reconstruct a *valid-time*
   (event-time) fact ("where was the unit based in 2021 vs 2025"). These are not the same axis and an
   availability rewind cannot express a relocation when all docs are ingested together.
3. **The occupancy-crossing detector groups by `edge_instance`, not by edge source** — the default
   `edge_instance` embeds the target site (`edge:{subj}:{predicate}:{obj}`), so a before-edge to
   Rawalpindi and an after-edge to Rahwali get different instance keys and are never compared as a
   crossing, even once real basing edges exist.

All three are latent/config-level defects in MONITOR's own code and are independent of the "no basing
edges extracted yet" problem (that's INGEST's, not re-litigated here — see Reattributed-away below).

## Findings

### MON-1 — dead trigger-config keys (compile_trigger / resolve_scope ignore unit/from_site/to_site/window/match_on)

- **Symptom**: The relocation observable does not scope to `unit_hq9b` or filter
  `Rawalpindi -> Rahwali`. Scope resolution returns unscoped (`None`); once based-at edges exist, *any*
  unit's target change (e.g. BIRM's manufacturer-address edge moving) would fire as an occupancy change.
- **Evidence**:
  - `config/observables.yaml:14-17` — trigger declares `unit: unit_hq9b`, `from_site: site_rawalpindi`,
    `to_site: site_rahwali`, `window: '2025'`, `match_on: [resolved_unit, site_instance]`.
  - `backend/chanakya/observe/observable.py:50-81` (`compile_trigger`) reads only
    `on`/`edge_type`/`node_type`/`field`/`value`/`within_area` — the five keys above are never consumed.
  - `backend/chanakya/observe/observable.py:84-117` (`resolve_scope`) reads only `watch_instances` +
    lens anchors + `anchors_within_hops`.
  - Probe result: `obs.watch_instances == []`; `resolve_scope(...) -> None`; lens anchors
    (`unit_paad`, `site_karachi`) are absent from the current view entirely.
- **Root cause**: The trigger schema/compiler was never extended to consume the relocation-specific
  keys the config author declared; they are inert config, silently ignored rather than erroring.
- **Recommended fix**: Extend `compile_trigger`/`resolve_scope` to read `unit` into the watch scope and
  to honor `from_site`/`to_site`/`window`/`match_on` as crossing filters, so the tripwire scopes to the
  intended resolved instance and does not fire on unrelated units/sites.
- **Severity**: major.
- **Cross-service dependencies**: Depends on RESOLVE producing real entity ids for `unit_hq9b` /
  `site_rawalpindi` / `site_rahwali` in the view (Master A in the shared RCA — id-namespace split) and
  on INGEST emitting real based-at edges (Master B) before this fix is even observable end-to-end. Fix
  the config-consumption logic now (it's self-contained), but full verification waits on those two.

### MON-2 — relocation observable uses the wrong temporal axis (availability rewind instead of valid-time)

- **Symptom**: Even with real dates present, before/after occupancy cannot be separated: the harness
  reconstructs "before" via an availability (transaction-time) rewind, but a relocation is a valid-time
  (event-time) phenomenon.
- **Evidence**:
  - `backend/eval/harness.py:154-164` (`fire_relocation_observable`) calls
    `build_view(as_of='2021-12-31')` to get the "before" state.
  - `backend/chanakya/timeref.py:27-38` — availability is defined off `ingest_time`/`report_time`, not
    event/occurrence time.
  - `backend/chanakya/view/pipeline.py:338-339` — the `as_of` rewind filters purely by
    `is_available_by`, i.e. transaction time.
- **Root cause**: If all documents describing 2021 and 2025 occupancy are ingested in the same batch
  (as they are here), an availability rewind to `'2021-12-31'` doesn't select "facts true as of 2021" —
  it selects "facts ingested as of 2021," which for a batch ingest is either everything or nothing. The
  mechanism conflates transaction time with valid time.
- **Recommended fix**: Drive the relocation tripwire off the supersede-aware *active-edge delta* within
  a single current view — compare the superseded based-at edge (before) against the active based-at
  edge (after) — rather than simulating a valid-time relocation with an availability rewind. This needs
  a `before(superseded)` / `after(active)` comparison; `_active_edges` alone doesn't do this yet (see
  MON-3).
- **Severity**: major.
- **Cross-service dependencies**: Depends on `supersedes` edges actually being computed (owned by
  SCORE, per shared fix-order item 9 — "derived supersedes (relocation, with confidence floor vs the d20
  spoof)") and on INGEST's structural transforms producing the two based-at edges in the first place
  (shared fix-order item 4). Do not attempt MON-2 until those land, or you will be debugging against a
  graph with no `supersedes` edges to key off.

### MON-3 — occupancy-crossing detector keyed by `edge_instance`, not by edge source (unit)

- **Symptom**: Latent — even after based-at edges exist, the crossing detector will not recognize a
  Rawalpindi->Rahwali move, because the before and after edges do not share an `edge_instance`.
- **Evidence**:
  - `backend/chanakya/observe/evaluator.py:45-62` (`_active_edges`) groups by `e.edge_instance`.
  - `backend/chanakya/observe/evaluator.py:122-143` (`_crossing`) compares `target` *within the same*
    `edge_instance` key.
  - `backend/chanakya/view/pipeline.py:274` — the default `edge_instance` is
    `edge:{subj}:{predicate}:{obj}`, which embeds the object (site), so `unit->rawalpindi` and
    `unit->rahwali` get two *different* instance keys and are never compared.
  - Probe note: 99/101 view edges currently carry this default `edge_instance`; there are no real unit
    basing triples in the current run to exercise this against yet.
- **Root cause**: The crossing detector's grouping key is wrong for this use: the observable's own
  config already declares the intended key — `match_on: [resolved_unit, site_instance]`, i.e. group by
  the edge's *source* (the unit), not by the full instance string. (This was originally attributed to
  RESOLVE — "collapse the two basing edges to one instance" — but that would fight the oracle's design,
  which intentionally models two distinct based-at edges, one stale/one confirmed, linked by a
  site-level `supersedes`. The fix belongs in MONITOR's grouping logic, not in RESOLVE's edge-instance
  scheme.)
- **Recommended fix**: Key the occupancy-crossing detector by edge **source** (resolved unit) and track
  **target** as evolving state (supersede-aware), honoring `match_on` from the trigger config, instead
  of grouping by `edge_instance`.
- **Severity**: major.
- **Cross-service dependencies**: Depends on INGEST's structural transforms actually producing
  `based-at` edges for units (shared fix-order item 4 — ORBAT/basing transforms). Until then this is
  unverifiable by design (no real basing edges exist to test the grouping against).

## Reattributed away (not MONITOR's to fix — do not attempt)

- **No basing edges extracted** — INGEST (fix-order item ING-2): the `based-at` / `supersedes` edges
  the observable watches were never extracted from the corpus at all. MONITOR's fixes above are
  necessary but not sufficient without this.
- **Uniform seed ingest-time collapses the 2021 rewind to empty** — INGEST/DATA-C (ING-7): all docs
  currently carry a single frozen seed date rather than real per-doc `report_time`/`ingest_time`.
- **`based-at` edge type overloaded** (e.g. reused for a manufacturer's street address, "BIRM based at
  Yongding Road") — INGEST + DATA-C ontology issue: domain-constrain `based-at` to
  `unit/variant -> basing_site` at the ontology level; not a MONITOR-side fix.

## How to reproduce + verify your fix

```bash
export CHANAKYA_ROOT=/home/synaptic/data-science/research/rough/osint/wt-EVAL
/home/synaptic/data-science/research/rough/osint/wt-EVAL/backend/.venv/bin/python tmp/conv/eval-rca/rca_evidence.py
```

This regenerates the evidence bundle (`tmp/conv/eval-rca/00-evidence-summary.md`,
`tmp/conv/eval-rca/view_full.json`, `tmp/conv/eval-rca/view_lens.json`). After each fix, re-run it and
confirm:

- **MON-1**: `compile_trigger` on the `config/observables.yaml:14-17` relocation trigger produces a
  scope that resolves to the specific `unit_hq9b` instance (not `None`/unscoped), and firing the
  observable against an unrelated unit's edge change does **not** trigger it.
- **MON-2**: the relocation firing logic no longer calls `build_view(as_of=...)` to simulate the
  "before" state; instead confirm it reads the superseded vs. active based-at edge pair from a single
  current-view call, and that the fire/no-fire decision no longer depends on ingest-time batching.
- **MON-3**: with real based-at edges present (post INGEST/SCORE fixes), the crossing detector must
  report a crossing when a unit's active based-at target changes, grouping by the unit (edge source),
  not by the full `edge_instance` string — verify by checking `_active_edges`/`_crossing` group unit
  `unit_hq9b`'s two based-at edges (Rawalpindi, Rahwali) together and detect a target change.

Note: MON-2 and MON-3 cannot be *fully* end-to-end verified until INGEST's basing-edge transforms
(ING-2/ING-4) and SCORE's derived `supersedes` computation land — verify the config/grouping-logic fix
in isolation (unit test / synthetic edges) first, then re-verify against the real pipeline once upstream
lands.
