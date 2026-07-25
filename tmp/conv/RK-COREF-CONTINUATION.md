# RK-COREF (S3) — state at context handoff (2026-07-25)

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
