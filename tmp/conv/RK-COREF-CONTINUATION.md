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

---

## Earlier snapshot — state at the context handoff, carried over from the design branch

The design branch kept a note under this same filename while the implementer kept the log above; the
merge preserves both. What follows is that earlier, mid-flight snapshot. It is a point-in-time record,
so where it disagrees with the log above, the log above is later and wins.


**S3 is mid-flight, not broken.** Everything below is committed on `design/resolution-redesign` (= PR #63).
Nothing is on `main`.

## Where it stands
- **Implementer** `s3/rk-impl`: all 11 scope items landed behind one flag — **`earned_identity.enabled`** in
  `config/resolution.yaml`, shipping `false`. Flag-off byte-identity held through every change (golden
  `bb6f16a5`, booted `160/73/18`, full `169/80/71/20`). **Currently working the last 8 failures.**
- **Test author** `s3/rk-test`: **108 tests, 74 failing against current code** (each proven to fail for its
  intended reason). M15's fixture collision fixed.
- **Data hand** `s3/rk-data`: 37 fixtures / 11 shapes, incl. the coref-baked sandbox (21 clusters, **only 7
  sound** — the rest deliberately over-bound, under-bound or mis-licensed).
- Last measured integration: **1293 passed / 34 failed** → implementer took it to **14**, of which **4 were
  M15's fixture** (now fixed) and **8 are its own remaining pass**.

## To resume
1. Merge `s3/rk-test` into `s3/rk-impl` (expect add/add on the G16/G19 gate files — **keep both**, test hand's
   at `_spec.py`; that has happened every stage).
2. `cd backend && python3 -m pytest` (not `-q`). Triage anything left by the three-way rule: impl defect ·
   spec gap · fixture artifact.
3. Verify **flag-off on both surfaces** and that **flag-on changes the graph** (an unchanged flag-on graph means
   the stage did nothing — §5a-bis). Flip the flag by editing the `enabled:` **key**, not the comment above it
   (that mistake cost a false "no change" reading in S2).
4. Then: freeze the A7 coref contract → **RK-BAKEOFF** → keyed re-record → **S4**.

## The 8 the implementer is finishing
C5's partial bind · `NAME_VARIANT` landing in `possible` instead of `candidates` (**doctrine, not mechanism**:
raise-only is only honest if the analyst actually gets it *with the quote*; `possible` is retained-but-never-
surfaced, i.e. a quiet drop) · the anaphor category/config agreement · the referent on emitted claims · the
contrast cap's control · **two decline mirrors** (trust these least — the decline is what makes an over-bind
reversible, so a mirror that cannot fail leaves D-13.18's whole promise unverified).

## Rulings issued this stage (all in `RK-COREF-RULINGS.md`)
**M1** mark-vs-word conjunct · **M2** licensing evidence is a span *set* · **M3** two missing config declaration
sites · **M4** all three S3 gates are fixture-only on this corpus · **M5** a presence merge is *permitted*, never
required (my wording would have forced density) · **M6** differing designation vetoes · **M7**
`coref_authoritative_min_grade` · **M8** rarity-graded name **deferred**, docs corrected, disclosed · **M9**
span-carrier shape reconciles at integration · **M10** `relational: false` types fragment honestly; curated
escape only · **M11** my fragmentation criterion was unsatisfiable → moves to RK-DATA · **M12** the mark test is
a *filter*, never a verdict (benign failure direction is why it is admissible) · **M13** M2 needs a **producer**
change; verbatim is per-span · **M14** re-record sits **after the bake-off**, between S3 and S4 · **M15** a
gate's control must use an evidence class **no other gate restrains** · **M16** bake-off is a real three-way
(Opus 5 / Gemini Flash 3.6 / GPT 5.6 Sol; all three SDKs import; only GPT needs a client class).

## Two standing method rules earned this stage
1. **A gate's control must be built from an evidence class no *other* gate restrains** — else two gates contend
   and the pressure lands on whichever cap is easier to loosen. (Second input-choice mis-routing after S2's
   unstated site classes.)
2. **When a stage adds a flag, add its discovery tokens in the same commit** — a behavioural test that cannot
   find the flag silently runs against the flag-off graph. (Cost 32 of 66 failures here.)

## Before the bake-off consumes it
Repair the sub-oracle's **twelve single-source `confirmed`** entries
(`tmp/conv/FOR-DATA-C-sub-oracle-single-source-confirm.md`) — otherwise all three candidates are measured
against a yardstick more confident than the system it grades.

---

## UPDATE — S3 integration now at **1324 passed / 4 failed** (2026-07-25, final this session)

The M15 fixture fix cleared **exactly the 4** the implementer predicted, which corroborates its diagnosis of the
rest. **All 4 remaining are test-side** (fixture or config-reading), none is an implementation defect:

1–2. **`test_a_non_conflicting_relationship_pair_still_binds`** (both params). The fixture's quote names both
   surface forms but carries **no equivalence marker**, so it fails D-13.17's third conjunct and **the bind never
   happens** — making both positive controls unreachable. Fix either way: add a marker, or relabel it
   `UNAMBIGUOUS_ANAPHOR`, which is what *"the 8th AD Battalion" → "the battalion"* actually is.
   **⚠ And the hazard beside them:** `test_a_grouping_whose_relationships_conflict_declines` passes **vacuously**
   next to these. The decline is the mechanism that makes an over-bind reversible, so a vacuous pass there leaves
   **D-13.18's whole promise unverified.** Fix the fixture *and* re-confirm that test can fail.
3. **`test_the_operator_slot_is_declared_critical`** reads raw config where a **stage override** lives; it should
   read through `ResolveConfig`. Measured cost of promoting it in the file instead: booted edges 73→76, full
   169/80/20→170/84/21 — i.e. **exactly the "SHATTERS legitimate merges" outcome the shipped comment predicted**,
   because unnormalised branch strings become drawn walls. The promotion *is* live with the flag on.
4. **`test_a_same_document_stated_contrast_caps_the_pair_at_probable`** — the contrast cap's control.

### The best find of the stage — circular corroboration through the scorer
`coref-same-as` claims are **real edges emitted as a star from one anchor**, so every pair of a cluster's members
"shared a neighbour" (the anchor) and `relational_score` read that as **independent corroboration of the identity
the same cluster had just proposed.** A three-member cluster whose third link the gate **refused** merged anyway.
That is *"one bad link licenses the rest"* arriving through the **scorer**, not the bind — a self-licensing loop no
gate could have caught. Both coref lanes now leave the neighbourhood, scoped to those two predicates so `same-as`
is untouched.

### Also fixed, and worth carrying as a pattern
The `NAME_VARIANT`-lands-in-`possible` doctrine failure was caused by an **enumeration**: the band demotion listed
three specific blockers, and a raise-only pair scoring into the auto band matched none of them, so it fell through
to the watch-list — retained, never surfaced. Replaced with a **derivation** (every pair reaching the collection
loop was already refused a merge, so an `auto` band there means something blocked it ⇒ review item unless a cap
explicitly withheld it). **An enumeration of blockers goes stale as blockers are added; a derivation does not.**
