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
