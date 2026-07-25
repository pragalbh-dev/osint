# HANDOFF — the identity re-key / type-instance replumb (PR #63)

**Written 2026-07-25 at a context handoff. Read this first, then `01-replumb-implementation-plan.md`.**
Everything described here is committed on **`design/resolution-redesign` = PR #63**. **Nothing is on `main`**,
and #63 is an *accumulation branch*, not a landing target — the standing agreement is that everything entering
it gets reviewed, and it lands only when the whole chain is done.

> **Correction (2026-07-25, later the same day).** When this was written the sentence above was **not true of
> S3**: RK-COREF lived on `s3/rk-impl` in a separate worktree and had never been merged here, so a reader who
> trusted "everything described here is committed on `design/resolution-redesign`" would have looked for S3 on
> this branch and not found it. **S3 has since merged** (`s3/rk-impl` → this branch, along with
> `fix/anchor-resolution-honesty`), so the sentence is accurate again. Kept as a correction rather than a
> silent edit because the same drift is the thing to watch: this file describes work that may still be sitting
> on a stage branch, and "described here" has never automatically meant "merged here".

---

## 1. Where the work stands

| Stage | What it does | Status |
|---|---|---|
| **RK-SPIKE** (S0) | close the design opens; prototype characterize-and-cluster; build the claim-gold slice | **done** |
| **RK-ATOMS** (S1) | claim atom as the stable address; dormant referent field; atom-aware dedup; A7 discriminator schema | **done** (integrated) |
| **RK-LAYER** (S2) | layer typing; straddle split; presence/formation citizens; basing as a rebuild-derived edge | **done** (integrated, `0cfc069`) |
| **RK-COREF** (S3) | coref-cluster minting; per-layer policy; the caps; the relationship + namespace walls | **done, merged 2026-07-25** — `s3/rk-impl` is in this branch; suite green, flag ships off |
| **RK-BAKEOFF** | three-way extractor comparison | **not started** — next, see §4 |
| **RK-DATA** | keyed re-record + corpus/oracle regen | **not started** — after the bake-off |
| **RK-NAMECUT** (S4) | cut the name-key; re-anchor decisions to atoms | **not started** — after the re-record |
| **RK-MATERIALITY** | two-layer operator-scoped chokepoints | **not started** |

### The sequence, and why it is this order
> **S3 green → freeze the A7 coref contract → RK-BAKEOFF → keyed re-record with the winner → S4 → RK-MATERIALITY / rest of RK-DATA**

- **The bake-off precedes the re-record** because the chosen model *performs* the regen. Choosing afterwards
  means discarding the bundles or keeping ones from an unselected model — and re-extraction is **confirmed
  non-deterministic**, so a redo is a second full regen, not a cheap one.
- **The re-record precedes S4** because S4 re-anchors identity on **earned clusters**, and there are **zero
  coreference annotations in the 492 frozen claims** — S4 would otherwise land its most consequential change on
  data that cannot exercise it.

---

## 2. How the work is run (keep this — it is why the defects got found)

**Three hands per stage, structurally blind to each other**, each in its own worktree/branch:
- **implementer** (`s*/rk-impl`) — **corpus-blind**: never reads `corpus/**`, `answer_key.json`, or the data
  hand's fixtures. Thresholds chosen on general principle.
- **test author** (`s*/rk-test`) — **spec-only**: never reads the impl branch. Writes what correct *is*, and
  **must prove each test fails first** against unmodified code.
- **data hand** (`s*/rk-data`) — authors fixtures from the real corpus, and produces **abstracted** versions so
  the implementer gets the structural difficulty without the content.

The orchestrator is the **integration point**: merges test-into-impl, runs the suite, and **triages every
divergence** into *impl defect · spec gap · fixture artifact* — never accepting either hand's word. Verify the
load-bearing claims yourself; several reports were subtly wrong in ways that mattered.

**This is not ceremony.** Every stage's highest-value output came from a hand contradicting the spec:
S1 found four spec gaps; S2 found that a per-edge tag would silently kill the flagship and that a boolean cannot
carry three states; S3 found circular corroboration through the scorer. The data hand twice broke the design
before code was written.

### Practical gotchas
- `python3 -m pytest` **not** `-q` — `addopts` already carries `-q`, so the flag suppresses the summary line.
- Gate files collide **add/add** every single stage (both hands name them the same). **Keep both** — the
  implementer's at the canonical name, the test hand's at `…_spec.py`. Two independent takes on one gate are an
  asset; picking one discards half the coverage.
- Flip a flag by editing the `enabled:` **key**, never the comment above it — that mistake produced a false
  "flag-on changes nothing" reading in S2.

---

## 3. Finishing S3 — the 4 remaining, all test-side

Detail: `tmp/conv/RK-COREF-CONTINUATION.md`. Resume by merging `s3/rk-test` into `s3/rk-impl` and running.

1–2. **`test_a_non_conflicting_relationship_pair_still_binds`** (both params) — the fixture's quote names both
   surface forms but carries **no equivalence marker**, so it fails D-13.17's third conjunct and the bind never
   fires, making both positive controls unreachable. Fix: add a marker, **or** relabel to
   `UNAMBIGUOUS_ANAPHOR`, which is what *"the 8th AD Battalion" → "the battalion"* actually is.
   **⚠ HAZARD:** `test_a_grouping_whose_relationships_conflict_declines` passes **vacuously** beside them. The
   decline is what makes an over-bind reversible, so a vacuous pass leaves **D-13.18's whole promise
   unverified**. Fix the fixture *and* re-confirm that test can fail.
3. **`test_the_operator_slot_is_declared_critical`** — reads raw config where a **stage override** lives; should
   read through `ResolveConfig`. Measured cost of promoting it in the file instead: booted edges 73→76, full
   169/80/20 → 170/84/21 — **exactly the "SHATTERS legitimate merges" outcome the shipped comment predicted**,
   because unnormalised branch strings become drawn walls.
4. **`test_a_same_document_stated_contrast_caps_the_pair_at_probable`** — the contrast cap's control.

**Then:** verify flag-off on **both** surfaces and that **flag-on changes the graph** (an unchanged flag-on graph
means the stage did nothing).

---

## 4. Next: RK-BAKEOFF — a genuine three-way

**Candidates (user-fixed):** **Opus 5** · **Gemini Flash 3.6** · **GPT 5.6 Sol**. All three keys are in
`osint/.env`; **all three SDKs import cleanly** (`anthropic`, `google.genai`, `openai`) — so plan §8's
"`google-genai` is absent" note is **stale**, and its *"if only the incumbent can be exercised, the incumbent
stays"* fallback **no longer applies**. Report a real comparison, not a default.

- **Build work is small:** the `ExtractionClient` Protocol + `build_extraction_client` factory already exist,
  and two of three clients are built. **Only GPT needs a new client class.**
- **Gating preconditions are pass/fail, never weighted:** keep the **VLM imagery path** whole · be
  **live-runnable in the shipped image** *and* the producer that **freezes the seed bundles** (so KEYLESS≡LIVE
  holds by construction) · a **pinned** model id, never a floating `-latest`. No sampling params on any provider.
- **Measurement discipline matters more with three candidates, not less:** N repeated runs with **variance
  reported**, and a **minimum margin** before a difference is material. Re-extraction is confirmed
  non-deterministic on a small slice, so without this the scorecard manufactures a ranking out of jitter. A
  within-noise gap is **"no measured difference."**
- **⚠ PREREQUISITE — repair the ruler first.** The per-slice sub-oracle grades **twelve entries `confirmed` on a
  single source**, which violates the system's own rule (`min_independent_groups: 2`). Fix it
  (`tmp/conv/FOR-DATA-C-sub-oracle-single-source-confirm.md`) or all three candidates are measured against a
  yardstick more confident than the system it grades. Score against the **slice sub-oracle**, never the full
  answer key (else the result is dominated by which documents are in the slice).

---

## 5. Reference map — where the knowledge lives

| File | What it is |
|---|---|
| `artifacts/plan/01-replumb-implementation-plan.md` | **the runbook.** §5b = closure table C1–C11 · §5a = gate amendments · §5a-bis = the byte-identity rule · §7 = stage specs · §8 = bake-off · §10 = data regen |
| `artifacts/plan/sessions/RK-*.md` | per-stage thin specs (what a hand is handed) |
| `artifacts/plan/PROGRESS.md` | board + **five-beat handoffs for S1 and S2** (decisions, deviations, follow-ups, gate fixtures, how the three-hands separation was evidenced) |
| `artifacts/spine/13-*.md` | the design: D-13.1…**D-13.20** (§13 holds the spike's closures) |
| `tmp/conv/rk-spike-code-facts.md` | **the verified code baseline — overrides any design doc** |
| `tmp/conv/rk-spike-verified-defects.md` | **D1–D12**, each with target-correct requirements R* |
| `tmp/conv/rk-spike-DECISIONS.md` | D-13.17…20 + closures C1–C4, with mechanism tables |
| `tmp/conv/rk-spike-REVIEW-VERDICT.md` | the adversarial review: C5–C11, the corrected scoreboard, what the spike did *not* establish |
| `tmp/conv/RK-LAYER-RULINGS.md`, `RK-LAYER-INTEGRATION-TRIAGE.md` | S2's rulings (L1–L4) + its 3-round triage |
| `tmp/conv/RK-COREF-RULINGS.md` | **S3's rulings M1–M16** — the densest single file |
| `tmp/conv/RK-COREF-CONTINUATION.md` | S3 state + the 4 open items |
| `tmp/spike-rk/gold/` | claim-gold slice · per-slice sub-oracle · abstract shapes |
| `tmp/spike-rk/s2-fixtures/`, `s3-fixtures/` | abstracted fixtures (S3's includes the **coref sandbox**: 21 clusters, only **7 sound**) |
| `artifacts/md/16-design-note-disclosures.md` | the honest-limitations list for the design note |
| `DECISIONS.md` | ledger; the RK-SPIKE section is at the end |

**Measured baselines** (keep these; they are the flag-off targets): golden md5
`bb6f16a516c31eb0846494b62271a601` · **booted** view `160 nodes / 73 edges / 18 gaps / 450 claims`, hash
`22d668a3…dac3a9` · **full-scenario** `169 / 80 / 71 events / 20 gaps`. The booted surface **deliberately
withholds `d18_rahwali_pass1` + `d19_rahwali_confirm`** (ingested live for the demo) — and those are *exactly the
flagship relocation pair*, so **a flag-off assertion on the booted surface is blind to the supersede path.** Use
the full-scenario surface as the gate.

---

## 6. Findings that will bite you if you don't know them

**The severe one (D1).** An identity over-merge does not just miscount the order of battle — it **fabricates a
movement assessment and removes the human**. `based-at` is functional and unit-keyed, so fusing two co-located
batteries makes their two sites one unit's before/after; the supersede path then promotes it, **pops the pair out
of the analyst's queue** ("adjudicated by the machine"), **draws a relocation**, and **deletes the retired edge's
Known Gap** — turning an honest `insufficient` into `stale`. So the co-location cap is **anti-fabrication
machinery**, not hygiene. No planted lie required: two accurate reports of similar co-located units suffice.

**`stale` is not a free label.** It is defined as a freshness demotion **from confirmed**. So overwriting
`insufficient` with `stale` asserts the position *was* established and has merely aged — false in the system's own
vocabulary. **An assertion never established cannot age.** Retirement is carried by `superseded_by`, independent
of the status label.

**Circular corroboration through the scorer (S3's best find).** `coref-same-as` claims are real edges emitted as a
**star from one anchor**, so every pair in a cluster "shared a neighbour" (the anchor) and the relational scorer
read that as **independent corroboration of the identity the cluster had just proposed**. A cluster whose third
link the gate *refused* merged anyway. **Gate-hardening cannot catch this** — the gate worked and was bypassed
downstream.

**Name is still a verdict in Phase 1.** The caps live in the Phase-2 collection loop; the widest name-only fusion
path **bypasses the bands entirely** via the bootstrap disjunction, at *every* type. Also: alias
self-equivalence is reflexive where its docstring promises a real alias link, so the namespace-gated branch is
never reached — making cross-operator **and cross-type** fusion reachable in Phase 1.

**Anything the offline passes froze is evidence about an older graph.** A derived basing inherited the *later* of
its two premises' dates, so every basing of a unit shared one induction date and became unorderable — a 2021
sighting carried 2025.

**A schema that makes the sourced relation inexpressible and the unsourced one easy pressures extraction toward
fabrication.** The customs spine (event ↔ consignee ↔ shipper) was unrepresentable while an edge to a military
unit no such document mentions was easy.

**What is honestly inert** (§5a-bis: *inert because the data is sparse, mechanism at full strength* ≠ *hidden to
protect a fixture*): across all 52 documents there is essentially **one numbered formation and zero serials**,
**five `based-at` claims over three subjects** (corrected 2026-07-25 — this said "one stated basing", which was
wrong; the conclusion is unchanged, since the only multi-basing subject carries a dated succession rather than
the conflict G18 needs), and **zero coreference annotations**. So most of the discriminator ladder cannot fire, and
**G16 / G18 / G19 are all fixture-only**. That is why abstract fixtures were mandatory — and why fragmentation
metrics only become meaningful **after RK-DATA's re-record**, not at S3.

**Deferred and disclosed, not built:** rarity-graded name (no implementation, no observable contract; its contract
is recorded for later) · graded sub-confirmed relational weight (F9) · re-keying independence onto **evidential
lineage** (the *rule* — two independent sources ⇒ confirmed — stands; only detection is deferred, because
independence is keyed on publisher rather than lineage).

---

## 7. Five recurring failure patterns — the actual lessons

1. **A gate that cannot fail is a gate that lies.** Three of five gates would have passed while the harm they
   name happened. Every new gate needs a **non-vacuity control**, and a gate's **control must be built from an
   evidence class no *other* gate restrains** — else two gates contend and the pressure lands on whichever cap is
   easier to loosen.
2. **A green artifact carrying a false statement is worse than a red one**, because it switches off the next
   reader's scepticism. Four instances: a docstring claiming order-independence it only partly delivered; a
   passing test asserting a file was untouched after it was migrated; a comment promising a merge path the design
   forbids; a fixture comment claiming a baseline "does not reproduce" when it measured a different surface.
3. **An enumeration of blockers goes stale; a derivation does not.** Three separate defects were lists-of-cases
   that silently failed to cover a case.
4. **Config must be READ, never hand-copied, and flags must be DISCOVERED.** A hand-copied config block omitted a
   knob the implementation added, so a guard short-circuited and no fixture could enable it. A flag-discovery
   token list that predated a stage sent every behavioural test against the flag-off graph — 32 of 66 failures.
   **When a stage adds a flag, add its discovery tokens in the same commit.**
5. **Timidity is a failure mode, not a safe default.** An implementer fixing an over-permissive bug reaches for
   the broadest guard, because every test it can see rewards caution — S2 produced three successive
   over-corrections, each caught only by a **mirror** asserting what must still *work*. **Every prohibition needs
   its mirror beside it**, and when a mechanism has a three-way outcome the fixture must **state the
   discriminating input** rather than inherit a default.

---

## 8. Open items needing the user, not an agent

1. **The keyed re-record re-freezes the graded oracle** — the hardest-to-reverse action in the plan. Plan §10
   requires a **`DECISIONS.md` entry recording user approval**, EVAL coordination, and the **old oracle
   archived** so pre/post-re-key grading stays comparable. Two consequences to carry: **32 scripted-client tests
   need second queued responses** (with the flag on the coref producer fires and exhausts their queue), and
   re-extraction is non-deterministic so it is **frozen once and versioned**.
2. **DATA owes the `site_type` mapping.** Three alias entries were shown to restore the flagship relocation fully
   *and* de-conflict another unit's two basings into concurrently-valid ones — the proof that the held state is a
   refusal on specific grounds, not a disabled mechanism. Until it lands the flagship is honestly held with a
   named gap.
3. **`operated-by` has no producer.** Declared but non-extractor, so G18's `operated-by` arm is fixture-only
   unless the A7 extraction extension is owned. C11 scopes it to S3; if it slips, the gate must **declare the arm
   fixture-only** and it goes in the disclosures.
4. **The sub-oracle's twelve single-source confirms** — blocks the bake-off (§4).
