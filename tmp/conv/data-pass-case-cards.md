# Data-pass case cards — contracts for the three hands

Working note (not committed). Drives the corpus/answer-key curation that makes the resolution-redesign
machinery (PR #63) live and demonstrable on the demo corpus. Consumes `artifacts/spine/12-data-refresh-calibrations.md`
(§A + §B) and obeys `artifacts/working-principles.md`.

**Governing constraints (read once):**
- **Three separate hands.** *Config/code hand* stays **corpus-blind** — declares roles/thresholds on general
  principle, never having booted our specific corpus. *Data hand* authors documents + answer-key oracle.
  *Test hand* writes validation from the spec (the card), not from the code. The orchestrator integrates,
  measures corpus impact, and commits.
- **Sandbox-first.** All corpus curation happens on `corpus/scenarios/hq9p_sandbox` (a gitignored faithful
  twin — boots to 160 nodes / 73 edges, identical to primary). Prove the whole recipe (full `pytest` + the
  relocation beat) on the sandbox before a single byte of `hq9p_primary` moves.
- **Real extraction, never hand-faked claims.** New cases enter as realistic documents (from real-world
  templates) run through the actual keyed extraction pipeline; the resulting claim bundles are frozen. This
  keeps "keyless ≡ live" honest. Deterministic passes (georef) are preferred over re-recording existing docs
  (LLM re-extraction drifts curated structure — the d17 lesson from the attribution runbook).
- **Re-freeze the enrichment after any resolution-affecting change.** `based-at` / attribution edges are
  derived offline over the *resolved* view (`python -m chanakya.ingest basing|attribute|georef --scenario … --record`)
  and frozen as `*__basing.json` / `*__attr.json`. Any data change that moves resolution requires re-running
  the relevant enrichment and re-freezing, or the keyless boot won't reflect it.
- **The relocation beat is a PROTECTED INVARIANT of every step.** After each card: `python -m eval beat`
  must still fire exactly one alert on the correct relocating unit, `before_site != after_site`, no collateral
  alerts. Any card that changes the partition must be re-checked against it before commit.
- **Per-card commit.** Each card is a bisectable commit on `design/resolution-redesign`; human author, no AI trailer.

**Card template:** *Watch happen* (reviewer-visible intent) · *Config contract* (corpus-blind) · *Data contract*
(+ **must-not-disturb**) · *Expected resolved outcome* (answer-key) · *Test contract* · *Verify + freeze*.

Sequencing: §A (done separately) → B1 → B2 → B4 → B5 → Relocation → B3 (highest hero-beat coupling, last).

---

## Card B1 — declarative critical-attribute wall goes live (D5)

**Watch happen.** Two variants that share the "HQ-9" name signal but state *different operator branches*
(China/PLA vs the Pakistan export line) are kept apart by a **hard veto computed from the data, before any
scoring** — a wall no name/BM25 similarity can cross, enforced transitively. Today `variant.operator_branch`
is the one wired `critical` attribute but **no variant states it**, so the wall fires on zero pairs.

**Config contract (corpus-blind).** No new declaration needed — `attribute_roles.variant.operator_branch:
{role: critical}` already exists. Do **not** promote `service_branch` / `origin_country` to critical in this
card: the corpus states them unnormalised (`PAF` vs `Pakistan Air Force`; `CHINA` vs `China`) and a critical
veto would false-shatter legitimate merges — that needs a value-normalization step first, logged as a
separate code follow-on, **not built here**.

**Proven-firing basis (from `tests/resolve/test_attribute_roles.py::test_critical_conflict_never_merges_even_at_alias_score_1`).**
The wall fires when two entities the **alias table would fuse at confidence 1.0** state **different values on a
critical attribute** → merge vetoed, pair left as a *drawn* `distinct_from` (visible, not a silent gap; not a
`candidate`). The test deliberately used a *non-namespace* critical attr to isolate the role-veto. Because
`operator_branch` IS a namespace field, we must fire the wall via the **namespace-blind alias-equivalence path**
(the only path that still collides two differently-namespaced mentions), not the namespace-scoped token block.
Corpus facts that matter: alias class `"HQ-9"` = {Hongqi-9, 红旗-9} auto-merges any bare "HQ-9"/"Hongqi-9"
mention into the existing **China family node `ent:variant:HQ-9`** (confirmed, CASIC-linked); the Pakistan
`var_hq9p`/`var_hq9be` are in *separate* alias classes and must not be touched.

**Data contract — TWO new sandbox documents, bare "HQ-9" designator on both (never "HQ-9/P"/"HQ-9BE"):**
- **Doc A — China/PLA (grade B–C).** A register/reference entry on China's HQ-9 (Hongqi-9) as the **PLA's**
  system → must extract to a `variant` mention named "HQ-9"/"Hongqi-9" with `operator_branch ≈ "PLA"`. Merges
  into `ent:variant:HQ-9`, stamping `operator_branch=PLA` on it.
- **Doc B — Pakistan/Army (grade ≥ C; this is the vetoing claim).** A regional entry calling Pakistan's system
  loosely "HQ-9" (the real terminological looseness), **operated by the Pakistan Army / Army Air Defence** →
  must extract to a `variant` mention named "HQ-9" with `operator_branch ≈ "Pakistan Army"`. The alias scan
  pulls it toward `ent:variant:HQ-9` (now PLA); the `operator_branch` conflict **walls it**.
- **No explicit "distinct-from"/"not the same as" sentence** in either doc — the wall must fire from the
  *attribute* conflict alone (that is the D5 mechanism; an explicit distinct-from would trigger the *old*
  claim-sourced veto instead and prove nothing new).
- **Must-not-disturb:** neither doc may use "HQ-9/P"/"HQ-9BE" designators, name the relocation
  sites/units (Rawalpindi/Rahwali, unit_hq9b/unit_paad), or state anything about `var_hq9p`/`var_hq9be` — keep
  the collision strictly in the bare-"HQ-9" alias class.

**Expected resolved outcome.** A **drawn `distinct_from`** between `ent:variant:HQ-9` (PLA) and the new
Pakistan-Army "HQ-9" node, arising from the `operator_branch` conflict — the wall beating a would-be 1.0 alias
merge. The pair is NOT in `same_as` and NOT in `candidates`. `var_hq9p`/`var_hq9be`/unit partition unchanged;
the CASIC→`ent:variant:HQ-9` edge gains Doc A's corroborating claim, mints no new manufacturer node.

**Test contract.** (i) Existing corpus-independent critical→veto unit test stays green. (ii) New corpus
assertion: the China vs Pakistan HQ-9 pair is vetoed / never merged, and BM25 name score alone would have
otherwise pulled them together (show the veto beats the score). (iii) Relocation beat unaffected.

**Verify + freeze.** Boot sandbox; confirm the two HQ-9 variants are separate nodes; partition-diff vs the
baseline shows only the added China node + the new wall (no collateral merges/splits); `eval beat` green.

**⚠ FINDING (2026-07-24) — B1-as-specced is structurally INERT on this corpus; do NOT force it.**
Empirically verified after authoring/extracting d26 (China "HQ-9"=PLA) + d27 (Pakistan "HQ-9"=Army):
- Both bare-"HQ-9" mentions **collapse onto the one registry node `ent:variant:HQ-9`** (exact-name attach).
  The operator conflict lands *inside* the node — `attr_history[operator_branch]` now holds BOTH
  "People's Liberation Army" (d26) and "Pakistan Army" (d27), PLA winning the scalar. The wall only vetoes
  *pairwise* merges of distinct entities; it cannot split an already-conflated node (monotone, Support-5).
- Using distinct designators (HQ-9 vs HQ-9/P) instead: the corpus's alias-class + `containment_min_descriptor_len`
  guards ALREADY separate them — **no `same-as`/candidate pressure exists** between `ent:variant:HQ-9` and
  `var_hq9p`/`var_hq9be` (only distinct-from/equips/manufactures/inducted-into edges). A wall there vetoes a
  merge never proposed → inert.
- So there is **no natural VARIANT pair** on this single-subject corpus that "would merge on name but must be
  split by operator." The mechanism is proven by `test_attribute_roles.py`; the corpus just doesn't collide.

**Two consequences (see conversation / DECISIONS):**
1. *Roadmap gap (code, out of scope):* a critical-attribute conflict formed INSIDE a node via same-name
   collapse is neither walled nor surfaced (my China node silently shows PLA over a retained Pakistan-Army
   claim). Log for the design note; do not fix in the data pass.
2. *Where the wall IS non-inert here:* the two UNITS — the (Air Force) HQ-9 fire unit vs the (Army) Air
   Defence command — genuinely compete (the Rahwali attribution tie). A critical wall there is meaningful and
   is the same work as the relocation card. **Plan: document the variant wall as unit-test-proven /
   corpus-inert (working-principle #5), and demonstrate D5 for real via the units in the relocation card.**
   d26/d27 to be removed from the sandbox (d26's China=PLA + CASIC corroboration optionally retained). B2
   (credibility floor) rides on whichever wall we demonstrate → follows the same move.

---

## Card B2 — credibility floor on the critical wall (D5 take-care a)

**Watch happen.** The *same* critical conflict behaves differently by source quality: asserted by a credible
source (≥ `critical_veto_min_grade`, currently **C**) it **walls**; asserted only by a flaky low-grade source
(D/E) it **raises to HITL, does not wall** — one flaky source cannot shatter a well-supported merge.

**Config contract (corpus-blind).** `critical_veto_min_grade: C` already set — confirm, no change.

**Data contract.** Two conflict instances:
- (a) an operator_branch critical conflict asserted by a **grade-C-or-better** source → must WALL;
- (b) a *different* pair whose operator_branch critical conflict is asserted **only by a grade-D/E** source →
  must **not** wall; surfaces as a HITL candidate carrying the conflict flag.
- **Must-not-disturb:** relocation entities.

**Expected resolved outcome.** (a) walled cannot-link; (b) a `probable`/HITL candidate with the critical-conflict
reason, *not* vetoed.

**Test contract.** (i) Unit test for the floor stays green. (ii) Corpus assertions for both (a) walls and (b)
raises-not-walls. (iii) Beat unaffected.

**Verify + freeze.** Boot sandbox; confirm (a) in veto set, (b) in HITL/candidate set with the flag; `eval beat` green.

---

## Card B4 — time-aware conflict: an update is not a contradiction (D8)

**Watch happen.** The same **perishable** attribute asserted with different values at *different times* reads
as an **update** (ordered succession → retained as a time-series, no conflict, no penalty, no wall); the same
attribute with different values at the *same time* reads as a genuine **contradiction** (a conflict). Today no
attribute is declared `perishable: true`, so the update-vs-contradiction waiver never fires.

**Config contract (corpus-blind).** Taxonomy decision — declare a concrete perishable attribute, e.g.
`attribute_roles.unit.alert_posture: {role: supporting, perishable: true}` (a unit's transient posture /
readiness / deployment status). Chosen on principle: posture is expected to change over time; designation /
maker / serial are not.

**Data contract.** A claim series on that perishable attribute:
- (a) value V1 dated T1 and value V2 dated T2 (T1 < T2), from sources whose event/report dates carry the
  distinct times → **ordered succession** (must NOT count as a conflict);
- (b) values V1 and V2 both under the *same* dateline T → **contradiction** (must count as a conflict).
- **Must-not-disturb:** relocation entities. (Note: this overlaps the relocation card's succession machinery —
  keep the exercised attribute distinct from `based-at` so the two cards stay independent.)

**Expected resolved outcome.** (a) `attr_history` shows the two values as an ordered series; identity score is
**not** penalized; no wall. (b) surfaces as a flagged contradiction.

**Test contract.** (i) Time-aware-conflict unit test stays green. (ii) Corpus assertions: (a) succession
retained + no penalty; (b) contradiction flagged. (iii) Beat unaffected.

**Verify + freeze.** Boot sandbox; inspect the node's `attr_history`; confirm (a) no conflict, (b) conflict;
`eval beat` green.

---

## Card B5 — trajectory support + perishable-only confirmation cap (3B-iii-A)

**Watch happen.** Attribute **agreement** raises an identity score (trajectory-aware support); but a
would-be-*confirm* resting **solely** on a perishable-attribute agreement is **capped at `probable`** — it
never auto-confirms, because "two distinct entities that passed through the same transient states at different
times" is a real false-merge mode. A pair agreeing on a **durable** attribute can still confirm.

**Config contract (corpus-blind).** The full trigger recipe (from ledger §B5):
- (a) a perishable supporting attr, e.g. `unit.readiness_state: {role: supporting, perishable: true}`;
- (b) a durable counterpart, e.g. `unit.oob_designation` (durable / hard-id) so confirm-vs-cap is exercisable;
- (c) lower `auto_merge_by_type.unit` to ~0.35 so a perishable-agreement pair can reach the auto band at all;
- (d) make the perishable attr **also a blocking key** (a `hard_id_fields.categorical` entry, or ensure the
  two mentions share a name token) — a perishable-only pair is only *compared* (hence only *cappable*) if
  blocking generates it as a candidate.

> ⚠ **Riskiest config change in the pass.** Lowering the per-type `unit` auto-merge floor to 0.35 can cause
> *collateral* unit merges. Sandbox partition-diff is mandatory; if any unintended unit pair merges (esp.
> anything on the relocation path), raise the floor / narrow the blocking key until only the intended pair is
> affected. This is the one place the ledger recipe risks "tuning to the corpus" — hold the line: the cap must
> be demonstrable *without* over-merging. If it can't be, log it and demote this card to a unit-test-only
> demonstration (the mechanism is already proven by its corpus-independent test).

**Data contract.** A unit pair sharing only a transient perishable state (same `readiness_state`) at
compatible times, blocked together → would-be-confirm on perishable-only → **must cap at `probable`**; plus a
pair agreeing on the **durable** `oob_designation` → **can confirm**.
- **Must-not-disturb:** relocation units (`unit_hq9b`, the decoy, and their partition).

**Expected resolved outcome.** perishable-only pair = `probable` (capped); durable-agreement pair = `confirmed`;
no other unit merges move.

**Test contract.** (i) Unit tests (trajectory support + cap) stay green. (ii) Corpus assertions: cap holds;
durable confirm holds; partition-diff shows no unintended merges. (iii) Beat unaffected.

**Verify + freeze.** Boot sandbox; partition-diff; confirm the two pairs' statuses; `eval beat` green.

---

## Card R — Relocation: earned attribution, tie-break killed (the hero-beat integrity card)

**Watch happen.** The relocation beat trips because ONE unit is genuinely, defensibly resolved as the operator
of the relocating battery — attribution won by a real **corroboration margin under today's methods**, not by
the current **2-claims-vs-2-claims alphabetical tie-break** between `unit_hq9b` (demo's story) and the seeded
decoy `unit_paad` (whose aliases — "Pakistan Army Air Defence Command" / "Army Air Defence Command" — the
Rahwali docs currently use). The decoy remains a genuine *distinct* unit and a plausible-but-losing candidate:
the system visibly picks the better-corroborated unit over a plausible distractor.

**Discovered risk this card exists to fix.** Rahwali's `based-at` subject is derived offline by attributing the
HQ-9BE equipment to a unit via `inducted-into` edges; both candidate edges currently have 2 claims each, and
the "correct" one wins only because `"unit_hq9b" < "unit_paad"` sorts first. A partition change from any other
card can silently flip this onto the unwatched decoy → the beat stops firing with no test catching it (the
current beat test loads pre-frozen bundles and never re-runs the tie-break).

**Open narrative fork (bring to user; grounding in flight).** The Rahwali designators actually alias the
*decoy* Army-AD unit, while the "correct" attribution rides on PAF-alias claims — so which unit truly operates
the battery is contestable **in the data as authored**. A web-grounding pass on the real HQ-9/P operating
service (PAF vs Pakistan Army Air Defence) is running; its result + the demo thread decide which single unit we
corroborate. **We do not preserve the coin-flip; we make the data tell one coherent, corroborated story.**

**Config contract (corpus-blind).** Prefer **none** — this is a genuine-*data* fix, not a config-tuning fix.
(If basing posture is modelled as perishable, reuse B4's declaration; do not invent relocation-specific dials.)

**Data contract.** Curate the Rawalpindi(2021)/Rahwali(2023) documents so they **consistently and truthfully
designate the same operating unit**, corroborated by ≥2 independent sources carrying real identity evidence, so
the attribution clears the evidence bar with a margin. Keep the decoy unit as a real `distinct_from` unit but
no longer accidentally winning. The `based-at` succession (Rawalpindi → Rahwali) must be a clean **ordered**
supersession on that one unit.
- **Must-preserve:** the beat fires (one alert, correct unit, `before != after`, no collateral); the
  supersede-spoof decoy (d20) still fires nothing.

**Expected resolved outcome.** Rahwali HQ-9BE attributes to the correct unit by corroboration margin (not
tie-break); relocation reads as one unit's `based-at` update; decoy stays separate and loses on evidence.

**Test contract (the missing regression guard).** A NEW test that exercises the **live basing derivation with
the competing decoy candidate present** — asserts the correct unit wins by *evidence margin*, and would fail if
the margin collapsed back to a tie (unlike today's test, which hardcodes the winner). Plus the existing beat
test, plus a partition assertion that the two units stay `distinct_from`.

**Verify + freeze.** On sandbox: re-run `ingest basing --scenario hq9p_sandbox --record` after the data change,
re-boot, confirm the beat fires on the correct unit with a non-tie margin; full `pytest` + `eval beat` green.

---

## Operational recipe — adding a NEW document to the sandbox (verified against code)

Membership is by **`citation_url` path segment**, not a scenario field: a source belongs to `hq9p_sandbox`
iff `hq9p_sandbox` is a path component of its `citation_url`. So a new sandbox doc needs a `config/sources.yaml`
entry whose `citation_url` is `corpus/scenarios/hq9p_sandbox/docs/<id>.txt`.

1. **Author** the raw prose at `corpus/scenarios/hq9p_sandbox/docs/<id>.txt` (one citable line = one Region;
   `.txt` → line-level provenance).
2. **Register** one entry in `config/sources.yaml` (working-tree only during sandbox iteration — do NOT commit
   sandbox-scoped entries; they're replaced with `hq9p_primary` paths at promotion). Minimal fields:
   `source_id`, `source_type` (must be a `credibility.yaml` `source_class_factors` key), `citation_url`;
   set `reliability_grade` + `report_date` for the case. Unregistered docs are **invisible** to extraction.
3. **Export the key** (extraction is keyed; code reads it from the env, does not auto-load the sibling `.env`):
   `export GEMINI_API_KEY=$(grep -E '^GEMINI_API_KEY=' ../osint/.env | cut -d= -f2-)` (or ANTHROPIC). Never echo it.
4. **Extract SCOPED** — `--only <id>` is **mandatory** on the sandbox: a bare `extract --scenario hq9p_sandbox`
   would prune (delete) all 25 copied bundles, because none of the existing sources are registered under a
   `hq9p_sandbox` citation_url. Command: `cd backend && CHANAKYA_ROOT=<worktree> .venv/bin/python -m chanakya.ingest
   extract --scenario hq9p_sandbox --only <id>` → writes `…/hq9p_sandbox/claims/<id>.json`.
5. **Re-run enrichment if the doc completes a basing/attribution triangle** (does NOT auto-fire):
   `… ingest basing --scenario hq9p_sandbox --record` (keyless) and/or `… attribute --scenario hq9p_sandbox --record` (keyed).
6. **Boot** picks up the new bundle automatically (glob over `claims/*.json`); no manifest edit needed.
   `answer_key.json documents[]` is eval-only — update it for the oracle at promotion, not for boot/extraction.

> Git hygiene: sandbox docs/bundles are gitignored; the `config/sources.yaml` sandbox entries are NOT — keep
> them out of every commit (stage explicit paths only) until promotion swaps them for `hq9p_primary` paths.

## Promotion (after all cards proven on sandbox)

Apply the same recipes to `hq9p_primary`; regenerate `answer_key.json` (data hand); re-freeze all enrichment
bundles; full `pytest` (no xfails) + `eval beat` green on primary; delete the sandbox + its `.gitignore` line;
update `DECISIONS.md` + design-note disclosures (esp. the B5 floor decision and the relocation narrative call).
