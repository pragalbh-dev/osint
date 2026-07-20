# QA sweep — integration of the eight `qa/*` branches onto `qa/live-fixes`

**Base:** `origin/main` @ `8932793`. All eight task branches merged, in dependency order:
`t1-coref-gate → t7-phase4-residuals → t2-karachi-coords → t3b-fragmentation → t5-map-coverage →
t6-drawer-semantics → t3a-review-queue → t4-graph-legibility`.

## Did we preserve every agent's logic? — the deterministic evidence

**1. Test-count arithmetic is exact.** Each branch's new tests survive the merge with none dropped:

| | tests | delta |
|---|---|---|
| `origin/main` baseline | 788 | — |
| + T7 (residuals) | 794 | +6 |
| + T2 (geo veto) | 804 | +10 |
| + T3b (fragmentation) | 824 | +20 |
| + T5 (map coverage) | 841 | +17 |
| + T6 (drawer/API) | 843 | +2 |
| + T3a, T4 (frontend only) | 843 | +0 |
| **integrated** | **843 passed, 6 skipped, 1 xfailed** | |

`788 + 6 + 10 + 20 + 17 + 2 = 843`. `ruff` and `mypy` clean (96 source files). Frontend: `tsc --noEmit`
clean, **155** vitest tests (T5 + T6 + T3a + T4 suites all present and passing).

> **Correction (2026-07-20).** This line originally said 134 vitest tests. That was wrong — 134 was the
> count after the T3a merge, before T4's suite landed. Both T10 and T11 independently re-measured the
> branch at **155** (T10 verified by stashing its own changes and re-running). Recorded here rather than
> silently edited, because two agents were briefed against the wrong baseline and correctly pushed back.

## Second wave — T9, T11, T10 (merged 2026-07-20)

| | tests (backend) | delta | frontend |
|---|---|---|---|
| first-wave integration | 843 | — | 155 |
| + T9 (hero query) | 845 | +2 | 155 |
| + T11 (config read + watching) | 854 | +9 | 162 |
| + T10 (merge-card evidence) | **861** | +7 | **170** |

`843 + 2 + 9 + 7 = 861` ✓ and `155 + 7 + 8 = 170` ✓. `ruff`, `mypy`, `tsc --noEmit` all clean. Graph
unchanged at **166 / 84 / 19 / 457**. `make beat` still fires `obs-basing-relocation` with
`before_ref = e:unit_hq9b:based-at:site_rawalpindi` → `after_ref = e:unit_hq9b:based-at:site_rahwali`.

Only one conflict in the second wave: `DECISIONS.md` (T9 and T11 both appended a section) — unioned.
T10 and T11 stayed off each other's files by design; T10 made **zero** changes to `api/routes/` and T11
made **zero** changes to `adapters.ts`.

**2. Every agent's own acceptance suite passes by name** — run individually, not just in aggregate:
`test_geo_conflict` (7) · `test_map_position_integrity` (3) · `test_t3b_fragmentation` (12) ·
`test_t3b_fragmentation_corpus` (8) · `test_worked_query` (4) · `test_plotted_point_provenance` (3) ·
`test_location_precision` (7) · `test_places` (24) · `test_node_evidence` (7) · `test_supersede` (12+xfail)
· `test_loop` (6).

**3. Every agent's headline behavioural claim holds *jointly*** — measured on the integrated build, which
is the thing no single branch could prove:

| claim | `origin/main` | branch claimed | **integrated** |
|---|---|---|---|
| merge queue (`same-as` candidates) | 40 | 8 (T3b) | **8** ✓ |
| nameless nodes | 11 | 0 (T3b) | **0** ✓ |
| `unknown`-typed nodes | 11 | 6 (T3b) | **6** ✓ |
| plotted nodes (real coords) | 2 | 12 (T5) | **12** ✓ |
| nodes / edges | 171 / 105 | 166 / 79 (T3b alone) | **166 / 84** ✓ |

Edges land at 84 rather than T3b's solo 79 because T5's six area-non-identity `distinct_from` vetoes are
*drawn* (made visible rather than silent) — an addition, not a regression.

**4. The flagship beat still fires** — `make beat` emits `obs-basing-relocation`,
`before_ref = e:unit_hq9b:based-at:site_rawalpindi`, `after_ref = e:unit_hq9b:based-at:site_rahwali`.

## Conflicts resolved, and how

* **`backend/tests/resolve/_helpers.py`** (T2/T3b/T5) — additive keyword params, unioned.
* **`config/resolution.yaml`** (T2/T5) — orthogonal blocks (`entity_geo_conflict_max_km` vs
  `place_identity_precision_classes`), both kept; YAML re-validated.
* **`DECISIONS.md`**, **`tmp/conv/API-to-FRONTEND-contract-log.md`** — appended sections unioned. The
  contract log was an add/add: T6 carried the file header, T5 only its own entry; T6's document kept and
  T5's entry appended.
* **`frontend/src/api/adapters.ts`** (T5/T6/T3a/T4) — the heavy one.
  * `StagePinExtras`: T5's precision fields ∪ T6's supersession fields.
  * T5's `supersededSites` is *superseded by* T6's richer `supersessions`/`SupersessionFact`; T6 kept a
    thin compatibility shim over it, so T5's callers and tests still work.
  * Pin construction now carries **both** T6's supersede fields and T5's precision fields.
  * Two collisions git merged *silently and wrongly*, caught only by typecheck:
    `humanizeToken` declared twice (byte-identical; duplicate dropped), and T3a calling `.trim()` on
    `Location.raw` which T5 had correctly widened to `string | string[]`. Fixed by adding one shared
    `locationRawText()` normaliser and routing both readers through it.
* **`frontend/src/api/adapters.test.ts`** — two appended suites unioned around a shared closer.

## One adjudication, recorded

`test_every_plotted_node_sits_on_a_coordinate_one_of_its_claims_states` (T2) **went red under T5** and was
**amended, not reverted**. As written it required every drawn point to equal a coordinate one of the
node's own claims states — which forbids *any* gazetteer derivation however well cited, outlawing the
whole `md/13` design. Amended clause: a plotted point must be **(a)** stated by one of the node's own
claims, **or (b)** exactly the `canonical_dd` of the curated anchor named in `location.resolved_place_ref`,
and only when the node stamps `location_source == 'gazetteer-anchor'`.

Verified **load-bearing, not vacuous**: 2 nodes take branch (a), 10 take branch (b); and a mutation check
confirmed it still fails both on a teleport (Karachi given Rahwali's coordinates) and on a *forged*
`gazetteer-anchor` stamp. T5's `test_plotted_point_provenance.py` is kept alongside — the two ask
different questions.

## Still open after integration — one real defect

**A Karachi ↔ central-Punjab merge card survives** (`Army Air Defence Centre, Karachi` ↔ `fenced compound
near a PAF airbase in central Punjab`, `merge_confidence` 0.519). This is the user's original complaint
class, and it is the gap T5 identified in T2's veto: **`scoring.geo_conflict_km` reads the coordinate a
claim *states*, but after toponym geocoding these entities have no stated coordinate** — their position
comes from the curated anchor they resolved to, derived at rebuild. So the rail never fires on them. T5
closed six such pairs with config `distinct_from` rows; this one is not among them.

**Attempted at integration and deliberately reverted.** A `places.place_geo_conflict_pairs()` sibling to
`place_distinct_pairs()` (veto when two *resolved anchors* are further apart than the same
`entity_geo_conflict_max_km` tolerance) computes the right 73 pairs — but folding it into the `veto` set
did **not** suppress the candidate: it only drew 22 more `distinct-from` edges, leaving the graph
asserting both "these are distinct" and "these might be the same" about the same pair. The candidate-
emission path evidently does not consult `veto` the way the merge path does. That is a subsystem fix
needing its own diagnosis and tests, not an integration fix, so it was reverted to keep the merge honest.

The other 7 surviving candidates are **genuinely good questions** and should stay: CPMIEC ↔ its full
expansion, the two SINO-GALAXY spellings, HQ-16 ↔ LY-80, `comp_ht233` ↔ Type 120 / Type 305B,
FD-2000/HQ-9P interceptor ↔ HQ-9P fire-control radar, Sargodha ↔ "fenced compound in central Punjab"
(Sargodha *is* in central Punjab — arguably legitimate).
