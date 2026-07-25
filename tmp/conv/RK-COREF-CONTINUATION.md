# RK-COREF (S3) — continuation log

Running record for the S3 stage after the implementer/test hands finished. Numbers only, with the surface
and flag state named on every one. A number without its surface is not a number here.

---

## 2026-07-25 — S3 stage verification

Verified on `s3/rk-impl` @ `bee9e40`, worktree `wt-RK-COREF-impl`, clean tree.
Run as `cd backend && python3 -m pytest`; measurements via `eval.harness.build_view` (full scenario) and
`chanakya.api.state.build_default_state().boot()` (booted app).

**Verdict: PASS.** The flag-on graph changes, deterministically, on both surfaces. It is not
INERT_BECAUSE_SPARSE *as a stage* — but six of the twelve S3 mechanisms are individually inert on this
corpus, for a measurable reason, and that split is recorded per mechanism below.

### 1. Flag OFF — the baselines hold

| surface | measured | target | verdict |
|---|---|---|---|
| golden fixture md5 | `bb6f16a516c31eb0846494b62271a601` | same (`PRE_S1_EXPECTED_VIEW_MD5`) | HOLDS |
| golden rebuild md5 | `bb6f16a516c31eb0846494b62271a601` (rebuild reproduces the fixture byte-for-byte) | same | HOLDS |
| booted app | 160 nodes / 73 edges / 66 events / 18 gaps / 450 claims | 160 / 73 / 18 / 450 | HOLDS |
| booted app view md5 | `e692319d16d71de88bad4886a7d792a8` | (not previously pinned) | recorded |
| full scenario | 169 nodes / 80 edges / 71 events / 20 gaps / 492 claims | 169 / 80 / 71 / 20 | HOLDS |
| full scenario view md5 | `74bab69eca59847687f4373036b5a974` | (not previously pinned) | recorded |

Gate tests, flag off, verbatim:

* `tests/gates/test_s1_zero_behavioural_change.py` + `tests/gates/test_s2_flag_off_equivalence.py` →
  **`7 passed in 4.63s`**
* those two plus G1 / G2 / G16 / G18 / G19 → **`36 passed in 7.08s`**
* whole suite, flag off → **`1329 passed, 7 skipped, 2 xfailed in 75.37s`**

**There is no S3 flag-off equivalence gate.** `test_s2_flag_off_equivalence.py` is the only real-corpus
flag-off pin and it reads *ambient* config rather than explicitly forcing the flag off, so under
`--earned-identity=on` it measures a flag-ON graph while asserting the flag-OFF baseline. That is a
harness gap, not an implementation defect — but it means the flag-off baseline is currently unpinned
against an S3-flag-on deployment. Same shape:
`tests/config/test_resolution_attribute_roles.py::test_unit_service_branch_is_promoted_to_critical_by_earned_identity`,
whose `_cfg()` also reads ambient config.

### 2. Flag ON — the graph moves, and the move is deterministic

Flipped `resolution.earned_identity.enabled: false → true` (the `enabled:` key, not the comment).
`ontology.layer_routing.enabled` (S2) stayed **false** throughout — the delta below is S3 alone.

| surface | flag OFF | flag ON | delta |
|---|---|---|---|
| full scenario | 169 / 80 / 71 / 20 | **183 / 102 / 71 / 22** | **+14 nodes, +22 edges, 0 events, +2 gaps** |
| booted app | 160 / 73 / 66 / 18 | **173 / 94 / 66 / 20** | **+13 nodes, +21 edges, 0 events, +2 gaps** |
| full scenario view md5 | `74bab69e…` | `cff72c693dd049b3f3f0dd96cf1d230a` | changed |
| booted app view md5 | `e692319d…` | `df5495b45d63c593d4c01c0eacb2b7a1` | changed |

**Determinism, flag on:** identical md5s on both surfaces across two consecutive rebuilds in separate
processes and across `PYTHONHASHSEED` 0 / 1 / 7 / 99 — 8 measurements, one value per surface.

Partition, full scenario (flag off → flag on):

* `same-as` candidate edges **6 → 17**; every one carries `merge_band: "candidate"`, both endpoints remain
  as separate nodes, and none is an accepted fusion
* `distinct-from` edges **20 → 30**
* nodes by type: `area_of_operations` 5→10, `basing_site` 25→26, `component` 29→31, `source` 56→58,
  `trading_org` 2→3, `unit` 6→8, `variant` 19→20 (all others unchanged)
* node status: possible 45→49, probable 110→119, confirmed **13→14**, insufficient 1→1

The two new Known Gaps, and the one that matters:

* `gap:chokepoint:comp_tel_chassis` — missing `named_supplier`, `substitutability`
* `gap:e:var_hq9p:inducted-into:unit_paad` — missing `official_announcement`. Flag-off the system asserted
  `var_hq9p --inducted-into--> unit_paad` at **probable** on the back of an over-merged unit node; flag-on
  that edge drops to **insufficient** and raises a gap naming what is missing. That is the anti-fabrication
  direction, measured, on the real corpus.

Drift worth flagging: `tmp/conv/RK-COREF-IMPL-NOTES.md` §2 records flag-on full scenario as
**183 / 100 / 71 / 22**, view sha `6b5400afbff6`. Current HEAD measures **183 / 102 / 71 / 22**, md5
`cff72c69…`. Edge count moved +2 after those notes were written (most likely `f118ae8`'s six mechanism
fixes). Treat 102, not 100, as current.

### 3. Per-mechanism: which fire, which are inert, and why

The frozen bundles carry **0 `coref-same-as` claims, 0 `coref-distinct-from` claims, 0 `referent_id`s and 0
`_coref_*` tier-3 attributes across all 492 claims** in `corpus/scenarios/hq9p_primary` (independently
re-verified here, two ways: raw JSON scan and a replay of the seeded evidence log). The coref *producer* is
a second extraction call at ingest; a rebuild from frozen bundles cannot see its output at all. So every
mechanism whose input is a coref annotation is structurally unexercised.

| # | mechanism | verdict | evidence |
|---|---|---|---|
| 1 | coref promoted to a required tier, referent minted | **INERT_BECAUSE_SPARSE** | 0 coref claims / 0 referent ids in 492 claims |
| 2 | D-13.17 auto-bind policy + gates + grade floor | **INERT_BECAUSE_SPARSE** | no coref input to bind; `coref_authoritative_evidence = {EXPLICIT_EQUIVALENCE, UNAMBIGUOUS_ANAPHOR}` is populated and reachable, but has nothing to admit |
| 3 | D-13.18 decline | **INERT_BECAUSE_SPARSE** | no coref groupings to decline |
| 4 | Tier-1 same-doc + contrast lane | **INERT_BECAUSE_SPARSE** | 0 contrast claims |
| 5 | name / discriminator score split | **NO-OP BY CONSTRUCTION** | the split is a `max` of a decomposition; it moves no score by itself |
| 6 | discriminator ladder + composite AND-key | **INERT_BECAUSE_SPARSE** | corpus states no `designator`+`service_branch` pair and no serials — 0 key matches |
| 7 | co-location cap (G16) | **FIRES** | `unit_paad` un-fuses: flag-off one `confirmed` node named "Army Air Defence"; flag-on `unit_paad` = "Pakistan Army Air Defence (PAAD)" plus two separate unit nodes. `unit` nodes 6→8 |
| 8 | relationship-conflict wall (G18) | **INERT_BECAUSE_SPARSE** | one stated basing, no `operated-by` data — 0 walls drawn |
| 9 | G19 cross-namespace / cross-type non-fusion | **FIRES** | two cross-type fusions closed: `known_gap`↔`component` (`comp_tel_chassis`) and `variant`↔`component` (`ent:variant:HT-233` splits from `comp_ht233`) |
| 10 | the three ceilings bound to the Phase-1 bootstrap | **FIRES** | 11 new candidate `same-as` edges, most at exactly `0.45` = the `possible` band cap. `ent:variant:HQ-9 ↔ HQ-9A` scores `name: 0.94` raw and lands at `merge_conf 0.45, merge_band candidate` — capped, not merged, and now visible to the analyst |
| 11 | `places.augment` ordering fix | **FIRES** | 5 new `area_of_operations` nodes keyed in the `basing_site` namespace (Punjab, Sindh, Karachi coastal belt, …) + 8 new `distinct-from` edges between basing sites; place resolution now precedes entity resolve |
| 12 | residual fragmentation reported as a coverage gap | **FIRES** | +2 Known Gap records, incl. the `inducted-into` demotion above |

So: **6 inert, 1 no-op by construction, 5 firing.** No mechanism is gated, defaulted away, or curbed to keep
a fixture green — the four flag-on test failures below are all *unresolved disagreements left standing*, not
suppressed behaviour.

### 4. Flag-on test failures — reported, not fixed

Whole suite with the tree flag flipped: **`7 failed, 1322 passed, 7 skipped, 2 xfailed in 77.68s`**.
Whole suite via the sanctioned shadow-config route (`python3 -m pytest --earned-identity=on`):
**`6 failed, 1323 passed, 7 skipped, 2 xfailed in 77.47s`** — the seventh
(`tests/ingest/test_coref.py::test_the_shipped_config_ships_the_stage_flag_off`) passes there by design,
because the shadow route never touches the working tree.

Of the 6:

* **3 × `tests/gates/test_s2_flag_off_equivalence.py::test_flag_off_leaves_the_real_corpus_graph_unchanged[node_count|edge_count|known_gap_count]`**
  — ambient-config leakage, described in §1. The test wants a flag-off baseline and does not pin one.
* **`tests/config/test_resolution_attribute_roles.py::test_unit_service_branch_is_promoted_to_critical_by_earned_identity`**
  — same class: its `off = _cfg()` reads ambient config, so under the shadow route the "flag-off" half sees
  `service_branch` already promoted to critical. The assertion is right; the fixture cannot express it.
* **`tests/acceptance/test_t3b_fragmentation_corpus.py::test_the_identical_string_ht233_fragment_is_gone`**
  — **a genuine, substantive disagreement between two stages.** T3b's beat says the ontology settles the
  type and `HT-233` must be one node; S3's G19 says a designator declared `component` by one document and
  `variant` by another was being fused in Phase 1 at confidence 1.0 through the reflexive alias branch, past
  every band, and refuses. Flag-on there are two nodes with the exact name `HT-233`
  (`comp_ht233`, `ent:variant:HT-233`). **A human has to rule on which is right. Do not weaken either side.**
* **`tests/acceptance/test_per_type_automerge_corpus.py::test_the_floor_did_not_leak_into_identity_sensitive_types`**
  — the failure message says "a variant-family pair became a merge: `ent:variant:HQ-9`/`ent:variant:HQ-9A`".
  **That statement is factually wrong about what happened.** Both nodes remain separate flag-on; the edge is
  `merge_band: candidate` at `merge_conf 0.45`, i.e. the name ceiling capping a raw `0.94` name score to
  `possible` and routing the pair to the analyst instead of fusing it. Flag-off the pair reached the analyst
  **not at all**. The test forbids candidate edges as well as merges, so it fails on the correct behaviour.
  Also needs a human ruling.

### 5. The one weakness this verification found on its own

G19's cross-type refusal removes the fabricated fusion but **does not route the un-fused pair anywhere**.
Flag-on, `ent:variant:HT-233` and `ent:known_gap:transporter-erector-launchers (TELs)` each have **zero
edges** — no candidate `same-as`, no `distinct-from`, no gap record. So for cross-type pairs the
anti-fabrication half fires and the "escalate to the analyst, don't guess" half does not: the system stops
asserting a wrong identity and then says nothing at all about the question. Contrast mechanism 10, where
every capped pair *does* reach the queue with a reason. Reported here, not fixed — it is a design call.

### 6. Flag restored

`git diff` clean; `config/resolution.yaml` back to the shipped `earned_identity.enabled: false`, comments
untouched. Re-measured after restore: full scenario 169 / 80 / 71 / 20, booted 160 / 73 / 66 / 18, golden
md5 `bb6f16a516c31eb0846494b62271a601`.

### 7. The sentence for the design-note disclosures

The stage as a whole is **not** an inert-mechanism disclosure — it changes the graph. The coreference half of
it is, and that is what belongs in the disclosures:

> The in-document coreference layer — the pass that binds "the battery", "the same unit" and "it" back to a
> named referent, and the auto-bind, decline and contrast-lane policies that govern when such a bind may
> merge entities rather than merely raise them for an analyst — is built, tested on fixtures, and
> **unexercised on the corpus we ship**: the frozen claim bundles were extracted before the pass existed and
> contain zero coreference annotations and zero referent ids across all 492 claims, so the mechanism has no
> input to act on and its effect on the demonstrated graph is exactly nil. It needs an evidence class we do
> not yet have — documents re-extracted with the second, coreference-resolving extraction pass enabled, so
> that pronouns and definite descriptions arrive carrying the referent they point at. The same applies to
> the discriminator ladder's composite key (this corpus states no unit designator + service-branch pair and
> no serial numbers) and to the relationship-conflict wall (no `operated-by` data). What *is* exercised on
> the real corpus is the identity-ceiling machinery that shares the same flag: with it on, the graph gains
> 14 nodes and 2 Known Gaps, two cross-type fusions and two co-located-unit fusions are refused, and eleven
> pairs that previously either merged silently or were never surfaced now reach the analyst as capped
> candidates with a stated reason.
