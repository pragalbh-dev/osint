# Pre-Implementation Audit — gaps to close before writing code

**What this is.** A pre-flight audit of the whole design corpus + the partially-built code, produced by a
multi-agent workflow (7 independent audit lenses → 59 raw findings → adversarial verification → 58
survived → synthesized to 19). Each finding is a concrete gap that would hurt the build, the live demo,
or the interview if not closed first. Verified against the actual files; the highest-severity items were
double-checked by hand (see the "verified" notes). *As of 2026-07-16. Deadline 20 Jul 2026, 12:00.*

**How to use it.** Work the **§ Close before writing code** list at the bottom in order — it's the
minimum to lock before implementation. The numbered findings give the full reasoning. Stack decisions
live in `07-stack.md`.

> **Two items already fixed this session:** (1) a `.gitignore` was added at repo root — `.env` (with
> `CLAUDE_API_KEY`) was previously only untracked, so `git add -A` would have committed the key. (2) The
> "temperature-0 agent" in `spine/08` is confirmed wrong: **Opus 4.8 rejects `temperature`/`top_p`/`top_k`
> with HTTP 400** (verified against the claude-api reference) — determinism must come from frozen
> extraction + a recorded hero trace + `effort: low`, not a sampling parameter. See H-BUILD-1 below.

---

## Running this cold (fresh-session hand-off)

**If you are an agent picking this up in a new session:** this doc is the driver, but it is an *index into
the repo*, not a standalone spec. Do these four things, in order.

**1. Boot reading — before touching anything.** `CLAUDE.md` (auto-loaded) → this doc → `DECISIONS.md`
(§2 locked ledger, §3 open items) → then, per finding, the files it cites: `spine/08` (proposed detailed
design **and its §7 veto list**), `spine/04` (credibility), `C/01` (ontology + edge grammar), `C/02` (demo
thread), `corpus/scenarios/hq9p_primary/answer_key.json` + `SCENARIO_MANIFEST.json`, `tools/generate/`.
Stack decisions live in `07-stack.md`.

**2. Re-verify before acting — this is a dated snapshot (2026-07-16).** Every finding was true against the
files at that moment; the corpus and docs may have moved since, and *fixing one finding can stale another*.
Before executing any item, re-check it against the live files. If a finding no longer reproduces, note that
and skip it — never act on the snapshot blind.

**3. Know which decisions are yours vs Pragalbh's.** This is a judgement-graded take-home — Pragalbh must
own the load-bearing calls (they *are* what's being graded), so **do not unilaterally lock them.** The
§-checklist items are tagged:
- `[needs Pragalbh]` — surface the decision with a clear recommendation and **wait**; do not guess.
- `[agent]` — execute directly; it follows mechanically from the brief, the `C/01` edge grammar, or a
  recommendation already stated in this doc. Some `[agent]` items are **gated** on a `[needs Pragalbh]`
  decision above them (noted inline) — don't run them until that decision is made.

**4. Done-condition.** The decision session is complete when: every §-item is either resolved (its fix
landed *and* recorded in `DECISIONS.md` §2, with the source-doc tail updated) or explicitly parked with a
reason; the doc↔data drift (items 4–6) is reconciled and the corpus re-frozen; and `spine/08` is flipped
from "proposed" to "ratified." Only then does the build start, at `07-stack.md` Stage 0.

---

## The six cross-cutting themes

1. **Docs and data have drifted apart.** The design corpus (spine/C/DECISIONS) evolved past the frozen
   `answer_key.json`/generator. The locked relocation observable, the flagship entity-resolution case, the
   worked-query edges, the node types, and even the confidence resolver disagree between the doc layer and
   the data layer. **A single doc↔data reconciliation pass is the highest-leverage pre-flight activity** —
   it's the source of most of the high-severity findings.
2. **"Locked/decided" is overstated; ownership is thin.** `spine/08` is unratified, the stack is nominally
   open, and several "LOCKED" items are contradicted by their own bodies (the resolver) or by the fixtures.
   On a judgement-graded call the candidate must own decisions he currently only received — so ratifying,
   promoting to the ledger, and reconciling names is as much about defensibility as correctness.
3. **Sophistication is asserted faster than it is computed, verified, or grounded.** Deception resistance,
   coordinated-inauthenticity, the corruption operators, the credibility thresholds, the citation
   guarantee, and the VLM subsystem are described as capabilities but are actually hand-labelled,
   prompt-steered, curve-fit, or substrate-less. The senior move: **compute ONE real signal end-to-end**
   (a coordination/near-duplicate detector, or a genuine VLM call) and honestly bound the rest as
   decision-support or roadmap. Pretending otherwise is the disqualifying honesty failure.
4. **The graded epistemic-honesty property lives in artifacts that don't exist yet.** The
   confirmed/probable/stale/insufficient status encoding, the insufficient-evidence boundary handling, the
   citation validator's real teeth, and the imagery-honesty posture all decide whether the non-negotiable
   is *visible and enforced* — and each is currently a default, a placeholder, or an assertion.
5. **Breadth is competing with depth under a ~3.5-day clock.** A self-imposed hosted full-stack SPA with
   two viz surfaces and eight UX surfaces threatens to leave the graded moments not actually firing on
   screen. A written build/drop ladder, a guaranteed recorded fallback, and cutting animation before
   cutting graded flexes are the insurance.
6. **The most legible judgement artifacts are unwritten.** Reviewers who won't read the repo grade the
   2–3 page design note. Drafting it (plus the M1–M5 coverage map and the sensitivity/eval tables) as a
   budgeted outline now is cheap, delegable, and off the critical build path — and prevents last-day
   compression from dropping the crown jewels.

---

## HIGH severity

### H-CONSIST-1 — The worked-query ground truth is internally broken *(verified)*
**Where:** `corpus/scenarios/hq9p_primary/answer_key.json` `worked_query.expected_path` vs
`ground_truth.edges`; same in `tools/generate/scenarios/hq9p_primary.yaml`; vs `C/01` edge grammar.
**Problem:** `expected_path = [site_karachi, unit_paad, import_2021, mfr_casic, comp_ht233]`, but **no edge
connects `import_2021→mfr_casic`** (there is no `exported-by` edge anywhere) and **none connects
`mfr_casic→comp_ht233`** (CASIC only `manufactures→var_hq9p`; HT-233 only `supplies-component→var_hq9p`).
Two of four hops don't exist — the graph is hub-and-spoke around `var_hq9p`. Separately, the edge
semantics contradict `C/01`: `manufactures` runs Mfr→Variant (should be `design-authority-for`),
`supplies-component` runs Component→Variant (should be `variant-of`). *(Hand-verified against the
answer_key edge list — the two missing hops are real.)*
**Why it hurts:** The multi-hop trace-to-chokepoint is THE thread the brief demands shown end-to-end. A
deterministic path check can never pass, the agent has no correct path to reproduce, and an agent built to
`C/01`'s grammar but scored against these edge strings fails spuriously — worst case it fabricates a
traversal to satisfy the narrated hop, which is the disqualifying non-negotiable.
**How to close:** Rewire `answer_key.json` + the generator to `C/01`'s grammar: `manufactures`
mfr_casic→comp_ht233/comp_missile; `variant-of` comp_ht233/comp_missile→var_hq9p; `exported-by`
import_2021→mfr_casic; keep `imported-by` import_2021→unit_paad and `based-at` unit_paad→site_karachi. Then
`expected_path` is fully connected. Add an acceptance check asserting every consecutive pair in
`expected_path` is edge-connected against the built graph. Do this in the same pass as H-CONSIST-4.

### H-CONSIST-2 — The locked marquee observable (Rawalpindi→Rahwali relocation) has zero seed data *(verified)*
**Where:** `DECISIONS.md` (LOCKED), `C/02` flex 6, `spine/08` §3.8, `product/00-ux-brief.md` §7 beat 7 —
vs `tools/generate/scenarios/hq9p_primary.yaml` (`observable.primary: basing_crossing`; orphan
`site_second`) and the corpus (no `Rahwali`, no relocation, no supersede pair).
**Problem:** Every design doc locks the demo climax as the HQ-9B Rawalpindi→Rahwali relocation (2021
occupied@Rawalpindi → single 2025 pass capped *probable* by decoy → 2nd independent source → *confirmed*
→ `supersedes` retires the stale position), explicitly rejecting the "bare status flip." The frozen corpus
implements exactly that rejected flip (`site_karachi` probable→confirmed via `d07`). No different-valid-time
state-change pair exists, so `supersedes` can never fire; `site_second` ("second/relocated site") is an
orphan with no seed doc. `product` §7 even falsely claims the scenario is "already built into the demo data."
*(Hand-verified: `SCENARIO_MANIFEST.json` shows `observable.primary: basing_crossing`; no Rahwali in corpus.)*
**Why it hurts:** The docs call this "the richest single moment in the demo." On the call there is nothing
to run it against. The hero beat silently degrades to the weaker flip the note brags about surpassing (an
interviewer who read the note notices), or you improvise corpus edits under deadline and break the
frozen/reproducible guarantee. **Timeline-gated** — resolve before extraction is frozen.
**How to close (preferred):** Regenerate the corpus with the relocation thread — add `site_rawalpindi`
(occupied@2021, perishable), retarget `site_second→site_rahwali`; seed three docs (2021 imagery
occupied@Rawalpindi; single 2025 pass occupied@Rahwali carrying `decoy_risk_flag`→probable; a discipline-
*and*-interest-independent 2025 confirmer with a clean decoy check→confirmed); add a `supersedes` edge
matched on resolved unit×site instance; set `observable.primary=basing_relocation` (keep `basing_crossing`
as a config-only secondary); update `SCENARIO_MANIFEST` + `answer_key`; re-freeze. Fix `product` §7's false
claim regardless. **Fallback:** formally de-lock back to the Karachi flip and strip all Rahwali/supersede
demo language — only if the ~half-day of corpus work is truly unaffordable.

### H-CONSIST-3 — The flagship HITL merge beat has no instantiated entities *(verified)*
**Where:** `C/01` (flagship = HQ-9/P vs HQ-9BE via `distinct-from`; FD-2000/FT-2000 = "easy secondary") vs
`spine/08` §3.9–3.10 + `C/02` flex 4 ("FD-2000≠FT-2000" = marquee) vs `answer_key.json` `alias_merge_trap`
+ `ground_truth.edges`.
**Problem:** Docs disagree on which pair is the flagship, and the corpus instantiates neither mechanism:
**FT-2000 appears in zero of the 14 docs and is not a node; there are zero `same-as` or `distinct-from`
edges anywhere;** the `alias_merge_trap` flex cites d03+d04, which contain no FT-2000. The material that
*does* exist (d04 HQ-9/P vs HQ-9BE range fork; d03 FD-2000 alias) is never wired as a merge decision.
*(Hand-verified: no same-as/distinct-from edges in answer_key.)*
**Why it hurts:** HITL merge adjudication is one of the three ★ deep-build flexes and the named "marquee";
analyst-in-the-loop is among the most-graded qualities. As built, the narrated trap has no trigger — the
demo shows an empty queue or the candidate improvises a nonexistent entity, and the docs contradict each
other live.
**How to close:** Lock **HQ-9/P vs HQ-9BE** as the flagship in `DECISIONS.md` (d04 seeds it; both variant
nodes exist). Reconcile `spine/08` §3.9/§3.10 and `C/02` to that pair. In `answer_key` add a
`distinct-from` edge var_hq9p↔var_hq9be (the HITL keep-separate) and a `same-as`/alias link FD-2000→HQ-9/P
(the auto-merge), so both mechanisms have real write-back targets. Rewrite the `alias_merge_trap` expect
string to match its cited docs. Either drop FT-2000 (C/01 calls it easy) or, only if you want it on screen,
add an FT-2000 node + one doc mentioning it.

### H-DEVIATION-1 — Imagery/VLM has no substrate *(verified)*
**Where:** `corpus/` (zero raster/video; `manifest.jsonl` imagery rows `path:""`; `SCENARIO_MANIFEST`
`template_gaps` "missing"); d07/d10/d11 are `.txt` prose; vs `spine/04` (VLM caption-vs-image, EXIF/ELA,
reverse-image), `spine/08` §3.4/§4/§5 (`method: parser|llm|vlm`), `C/02` flex 3, `md/05` §5.
**Problem:** There is not a single image/video file. d07/d10 are prose "satellite products" and d11 is
social text whose body literally states the verdict ("same frame floating around in 2019", "seen this jpg
hash before"). Yet the design repeatedly commits to a live VLM extractor, a VLM-confidence credibility
multiplier, and computed image-integrity signals — none of which can run on text. The M4 "catch the
recycled image" beat (the candidate's self-nominated most-memorable flex) is produced by an LLM reading
narration that hands it the answer. *(Hand-verified: `SCENARIO_MANIFEST.template_gaps` marks both imagery
templates "missing".)*
**Why it hurts:** M4 (VLM on imagery, flag manipulated media) is an explicit graded module and the honesty
axis is the disqualifying one. "You said VLM — show me the image pipeline" has no honest answer on this
corpus; presenting text-parsing as image analysis is exactly the "LLM wrapper" failure the brief warns
against, and leaving VLM in the build path wastes days on a dead stub. (The text+≥1-non-text minimum is
met by *social text*, which is fine — but must be owned, not implied.)
**How to close:** Lock the honest posture in `DECISIONS.md` and reconcile every doc: imagery enters as
analyst-report TEXT (product headers/annotations); the M4 override is coordinated-inauthenticity +
provenance/first-seen computed from text + timestamps; live VLM / EXIF / reverse-image is roadmap. Demote
`vlm` from the `08` §4/§5 build path so no time is spent on it; reframe §3.4's "0.85 × VLM conf" as
narrated-classifier confidence parsed from the report. **Strip the give-away lines from d11** so the signal
is *earned* from the near-duplicate/burst-timing cluster (d11/d12/d13), not read off the narration.
*Only if you insist on a real VLM:* gather 3–4 real assets (one Karachi site chip, one cloud frame, one
parade still, one 2019 reused JPG) into `corpus/raw/imagery/`, wire exactly one genuine VLM call, re-gen.

### H-DEFENSIBILITY-1 — Deception resistance is asserted in config, not computed
**Where:** `spine/04` (too-clean/coordination), `spine/08` §3.5 (provenance groups keyed on hand-set
`primary_origin_id`/`aggregator_of`/`bias_vector`/`coordinated_inauthenticity_flag`), §1/§3.8 (supersedes
keyed on `event_time` ordering); `C/01` Source-node attrs.
**Problem:** Every input to the three-axis independence rule and the too-clean penalty —
`primary_origin_id`, `aggregator_of`, `coordinated_inauthenticity_flag`, `first_seen=2019`,
`decoy_risk_flag` — is **hand-populated by the candidate**; nothing computes co-origin, alignment, or
coordinated timing from raw content. Separately, `supersedes` keys on `event_time` with no confidence
floor, so an adversary planting a fresh-dated relocation report **routes around the contradiction flag**
and silently demotes the true confirmed position to stale.
**Why it hurts:** The brief's hardest graded axis is "resist planted/withheld signals; recognise
deception." The kill-shot: *"In a live feed nobody hands you `coordinated_inauthenticity_flag` — what
derives it?"* If the answer is "the analyst configures it," the resistance is an oracle. And *"what stops
me moving your confirmed battery with a newer-dated sighting?"* currently has no alarm — the meta-rule
"degrade visibly, never silently" is violated by the system's own supersede path.
**How to close:** Promote **one** coordination/independence signal to genuinely computed: near-duplicate-
text + burst-timing detection over the reshare cluster (d11/d12/d13 already carry ~1-hr-window
near-verbatim posts) that auto-derives coordinated inauthenticity, plus shared-image-hash / citation-
following origin grouping (already parenthetical in `08` §3.5). Add a **confidence-floor clause to
`supersedes`** (a superseding claim must clear ≥1 independent probable-grade look before it *retires* a
confirmed assertion; below that it coexists as a candidate) and route confirmed→stale displacement through
the alert-disposition HITL. In the design note, state the machine-derived vs analyst-provided boundary
explicitly and **defend** `bias_vector`/reliability weights as legitimate analyst tradecraft rather than
apologising.

### H-BUILD-1 — The top-graded algorithm (confidence resolver) is doubly-defined with incompatible math *(verified)*
**Where:** `spine/04` §"Credibility score-combination — LOCKED" + §thresholds-LOCKED vs `spine/08` §3.4;
`DECISIONS.md` (locks the rubric mechanism but cites `04`, whose LOCKED body contradicts it).
**Problem:** `04`'s locked form is `s_i = w_R(Admiralty A–F fiat table) × w_C(1–6 item-credibility table)`
with a six-condition CONFIRMED gate and C_raw 0.40/0.80 thresholds; `08` §3.4 is
`c = R(source)=Σ w_f·factor_f × integrity × model_conf` with a three-gate machine and a 0.50 probable
cutoff. Different base decompositions (item-credibility exists only in `04`; `model_conf` multiplies only
in `08`), different confirmed gates, different probable cutoffs (0.40 vs 0.50), different state-sets (3 vs
5). `reliability_grade` is simultaneously an input (`04`'s `w_R`) and an output (`08`'s rubric). *(Hand-
verified: `04` lines 118–179 contain a full standalone LOCKED resolver that contradicts `08`. This is
partly self-inflicted — the top of `04` was reframed to point at `08`'s rubric this session, but the
locked math at the bottom of `04` was never updated.)*
**Why it hurts:** Credibility/confidence is the single most-graded spine capability and the input to every
status, drawer breakdown, and demo flex. Build the wrong one and the live numbers won't reproduce the
design note; "walk me through how R is computed" yields two different answers from your own repo.
**How to close:** Pick `08`'s **factor-rubric** form as canonical (it's the Module-1-defensible one and
already the DECISIONS mechanism). Rewrite `04`'s two LOCKED sections to delete the `w_R×w_C` base and
redirect to `08`, keeping only concepts + the freshness half-life table + the 6-condition gate re-expressed
on `08`'s `eff`. Decide whether item-credibility (`w_C`) survives as a rubric factor; confirm `model_conf`
multiplies per-claim; pick one probable cutoff and one state-set; make `reliability_grade` a derived
display label. Paste the single per-claim formula + constants into `DECISIONS.md` §2. Shared skeleton →
hours, not a rebuild.

---

## MEDIUM severity

### M-OPENQ-1 — Ratify `spine/08` and lock the stack + open decisions in one sitting
`08` is stamped unratified with 8 flagged veto calls; the stack is nominally open; several leanings
(scripted-query run, cross-interest scope, deep-tier depth) are tagged "needs your call" though their
substance is decided. A coding agent will build straight to `08`'s verdicts on foundations never signed
off. **Close:** run a focused ratify/veto pass — spend real attention on **#6 events-first-class** (the one
genuine retrofit hazard) and **#1 store**; the rest are config-side/drop-in. Freeze the stack to `07-stack.md`.
Promote every verdict + the leanings into `DECISIONS.md` §2, clear the matching §3 rows, flip `08` to
"ratified." ~30–60 min; converts a proposed spec into an owned one.

### M-UNDERSPEC-1 — Lock the status visual language before frontend work
The confirmed/probable/stale/insufficient encoding (+ freshness overlay, source-tier icon, superseded and
Known-Gap treatments) is the product's core and the only place epistemic honesty becomes visible. It's not
a ledgered decision, and the frontend has zero days of slack. **Close:** before any frontend work, produce
and lock ONE artifact — the legend/style tile the UX brief already asks for (5 statuses × freshness × tier
icons + superseded + Known-Gap, shown on node/edge/pin/citation-chip) — and record it as a `DECISIONS.md`
§2 row. Promote the brief's layout instinct (left rail + switching stage + right provenance drawer) to a
one-liner. Leave the ~18 other "OPEN" UX items as deferrable build-time taste.

### M-BUILD-2 — Pin the two load-bearing algorithms that gate graded moments
The **0.40 relational/shared-neighbourhood** merge term (the dominant signal of C's marquee ER feature)
has no defined computation; and `supersede`/`contradict` match on "resolved entity×edge-instance" while
**edge-instance identity is never defined** — key on `(subj,edge,obj)` and relocations never fire; key on
`(subj,edge)` and normal multi-site basing wrongly collapses. **Close:** add ~5 lines to `08` §3.9 —
relational = confidence-weighted Jaccard of resolved-neighbour sets over a named edge-type whitelist, with
a zero-and-renormalise fallback when a node has <k neighbours; single-pass at demo scale; worked numbers
for FD-2000↔HQ-9 (auto) and HQ-9/P↔HQ-9BE (mid-band). For supersede: compare claims sharing
`(resolved_subject_entity, edge_type)` — object NOT in the key; different valid_time + changed value →
supersede; equal valid_time + conflict → contradict→HITL; uncertain subject → candidate-supersede. Add one
config line declaring which edges are single-valued-per-subject (`based-at` single-valued per
unit×site_type) so garrison+field basing doesn't collapse.

### M-BUILD-3 — Harden reproducibility and the no-fabrication guardrail
The evidence log is produced by LLM/VLM extraction (nondeterministic) but is never declared a **one-time
frozen offline pass** whose committed log is loaded verbatim — if extraction re-runs at boot, every
status/path/flex can drift. The citation validator's "supports its hop" has no algorithm and no structured
hop→claim binding to consume, and there's no extraction P/R scored against `answer_key`. **Close:** declare
extraction a one-time OFFLINE build step (commit the claims, load verbatim, rebuild/replay from the static
log; a regenerate command exists only as a build tool); cache the hero query's decomposition + answer +
path so it replays identically; define the agent answer as a structured object (statements tagged
observed|inferred, each with `claim_ids` + `hop_ref`) built FROM traversed edges, and extend the validator
to reject any statement whose citations' `resolved_ref` don't match its hop or whose backing isn't
sufficiency-satisfied — forcing insufficient-evidence rather than a silent pass. Score entity/edge P/R
against `answer_key` for the design note.

### M-INCONSIST-1 — The demo overclaims HT-233 as a CONFIRMED chokepoint, contradicting C/01's own honesty rule
`answer_key` hard-labels HT-233 a confirmed sole-source chokepoint on "single-source in-degree." But
`C/01`'s own rule says sole-source is CONFIRMED only with a *named* sole-source indicator (sanctions
listing, evidence-gated foreign_control=OEM, follow-on order); absent that it's a **CANDIDATE**. The corpus
has no naming indicator, so in-degree-1 is a coverage artifact of a 14-doc hand-built graph, not a
confirmed fact. **Why it hurts:** this is the payload of the marquee worked query and it contradicts the
candidate's most sophisticated defensive move (chokepoints as prioritized collection tasking; candidate ≠
ignorance). "Your ontology says CANDIDATE, your demo asserts confirmed — which is your real system?"
**Close:** set `comp_ht233` to `chokepoint:'candidate'` + `substitutability:'UNKNOWN'` with an attached
Known Gap; keep the `supplies-component` edge confirmed/sourced but move the chokepoint onto a separate
candidate overlay; reword `expected_answer` to "structural chokepoint CANDIDATE — single-source in-degree,
substitutability UNKNOWN, surfaced as collection tasking (criterion #1/#7)." Same edit pass as H-CONSIST-1.

### M-TIMELINE-1 — Full-stack scope has no ordered cut/drop ladder
Nothing is built except data tooling; the specified build is a complete event-sourced backend + a real SPA
(map, graph explorer, provenance drawer, review queue, Ask view, alerts, credibility panel) + hosting +
rehearsal, for one person in <4 days. A spine-gate floor and a depth-in-batches posture exist, but there's
no single ordered build+drop ladder. **Close:** add a short ordered ladder to `DECISIONS.md` §5 (or a
`BUILD_PLAN.md`): (1) spine gate first — backend end-to-end, reproducible, one-click trace,
insufficient-evidence trips, one HITL override propagates; (2) Ask view → cited answer → provenance drawer
→ graph explorer as primary viz; (3) merge HITL wired deep with visible rebuild; (4) the relocation
observable + alert-disposition; (5) map as confidence-coded pins with the single scripted state change, no
animation unless the gate cleared early. **Explicit DROP-ORDER if behind:** animation → linked map
selection → status-override-as-deep-third-HITL → M4-render depth — holding merge + relocation as the last
two to cut (each a distinct graded flex). Keep the B pre-wirings that are brief-mandated/exercised (events,
bi-temporal, inference-as-claim-kind); only absence-as-evidence is truly B-only (a free defaulted enum).

### M-DATA-1 — Corruption operators are prompt labels, not verified transforms
The named messy operators (`hs_code_8526_bland`, `front_company_consignee`, `first_seen_2019`,
`near_duplicate…`) are free-text hints handed to the LLM in `generate.py`, not deterministic transforms,
and nothing records which actually landed in each frozen doc — so the locked claim ("every operator is
programmatic/reportable", `DECISIONS.md`) is unsupported. The model also improvised past the operators: d05
resolves the civil-telecom cover story in-line against the invoice, making the most load-bearing supply-
chain doc too easy. **Close (do NOT build a generic engine for 14 docs):** (1) reword `DECISIONS.md` + the
yaml header from "applied programmatically/deterministic" to "named operators, prompt-steered from real
specimens and manually audited post-freeze"; (2) hand-audit the 14 frozen docs once and record per-doc
which operators actually landed (a short manifest/design-note table) — an hour that turns the weakest probe
into a strength; (3) lightly edit d05 — delete the in-line resolution + bracketed analyst flags so the
declared-civil vs invoice contradiction is surfaced by the pipeline, not pre-resolved.

---

## LOW severity

- **L-CONSIST-1 — Reconcile the corpus's front-run naming with the docs + clean stale open-lists.** The
  frozen corpus silently answered still-"OPEN" questions (radar type, sustainment node) with off-ontology,
  misspelled type strings (`radar_command_node`, `sustenance_node`, `contract_import`); the ledger still
  lists items the corpus settled (Karachi site, node count); a third temporal field name (`evidence_date`)
  escaped the naming reconciliation; three docs give different "six-flex" lists while the corpus ships 8;
  `official_routine_framing.txt` has no `manifest.jsonl` row. **Close:** one sweep after ratification —
  align eval-fixture type strings to `C/01` (note they're display/eval labels, not the pipeline ontology);
  lock the leaning ontology decisions; mark Karachi-site/node-count resolved-by-corpus (keep the tier-2/3
  depth residual open); annotate `evidence_date` as eval-only; write one canonical "8 seeded moments staged
  as 6 flexes" statement; add the missing manifest row + a pre-freeze completeness check.
- **L-LOOSE-1 — Draft the 2–3 page design note as a budgeted outline now.** Six mandated sections + a hard
  page limit; substance exists at high quality but there's no draft/outline/word budget, so last-day
  compression risks over-length or dropping the strongest ideas. **Close:** ~30 min on a six-heading
  skeleton with a hard budget (~1,300–1,600 words), each heading pointing at the single deepest idea +
  source doc; delegate the draft to a subagent to keep it off the critical build path.
- **L-FIDELITY-1 — State the M1–M5 module-coverage map + the M3/M5/monitoring framing in the design note.**
  Only M1 and M4 appear by name; M2 (typed extraction), M3 (social tier + coordinated-inauthenticity), M5
  (Ask-view cited answer + map), and monitoring (freshness + observable + learning loop) are covered
  functionally but unframed. **Close:** add a 5-row coverage matrix to the design note only (pure framing,
  zero build); state that the Ask-view answer IS the M5 assessment; give monitoring its own named beat.
- **L-BUILD-4 — Consolidate the decided-but-unwritten build specs so the coding agent serializes rather
  than invents.** The provenance-drawer confidence-breakdown record is described in two different field-sets
  and never as a concrete struct; never-observable Known Gaps have no instantiation mechanism; the ingest
  set isn't pinned in `08` §5 (the raw dir holds 100+ page reference PDFs); the LLM claim-emission tool
  schema is principle-level. **Close (~1 hr each):** one YAML struct for the breakdown record; an
  `observability_ceiling` field in `templates.yaml` + a subject-level `expected_facts` list so
  never-observable gaps mint proactively; pin the ingest set to `corpus/scenarios/<name>/docs/*.txt`
  (reference PDFs = generator templates, never ingested); write the LLM tool schema with the enumerated
  C/01 predicates/node-types + `event_time`/`report_time`/`polarity` fill rules.
- **L-DEMO-1 — Guarantee the demo against hosting failure modes.** A hosted live demo adds failure classes
  (free-tier cold start = 30–50s blank screen at the worst moment) and no recorded run is committed. **Close:**
  commit a recorded end-to-end screencast of the scripted worked query on the deployed URL as the true
  fallback (brief-sanctioned); keep the instance warm (min-instance=1); relabel hosting in `DECISIONS.md`
  as a stretch on top of a guaranteed one-command local run + recorded fallback. (See `07-stack.md`.)
- **L-DEFENSIBILITY-2 — Prepare the design-note defensibility artifacts for interview kill-shots
  (write-up, no build).** Add a ±20% sensitivity table on the credibility constants (n=14, self-labelled,
  owned as "by design", with one deliberate label-flip proving the mechanism discriminates); an extraction
  P/R + escalation-confusion table over the 14 docs; frame adaptation precisely (freshness-decay + closed
  alias-loop automated; dynamic per-source rating next; adversary-method-change human-gated roadmap); a
  one-line cadence rationale per half-life and reconcile the two conflicting half-life tables (`04` vs `08`);
  name the over-fire/under-fire boundary pair (d07 slot-filled vs d10 slot-empty; d06 as over-fire guard)
  and route empty agent traversals through the sufficiency/Known-Gap path (never a confident "no such
  dependency").

---

## § Close before writing code (ordered)

1. `[needs Pragalbh]` **Ratify `spine/08` as-is in one sitting** — spend real attention on #6 (events-first-class) and #1
   (store); the rest are config-side. Freeze the stack to `07-stack.md`. Promote every verdict + the
   still-leaning calls into `DECISIONS.md` §2; flip `08` to "ratified." *(M-OPENQ-1)*
2. `[needs Pragalbh — confirm direction, then agent executes]` **Choose the single canonical confidence resolver** (recommend `08`'s factor-rubric × integrity ×
   freshness, gated); delete/redirect `04`'s competing `w_R×w_C` tables; reconcile `reliability_grade`, the
   confirmed gate, the probable cutoff, the state-set; paste the one formula into `DECISIONS.md` §2.
   *(H-BUILD-1)*
3. `[needs Pragalbh]` **Lock the imagery/VLM posture** — "imagery enters as analyst-report text; coordinated-inauthenticity +
   provenance is the M4 signal; live VLM/EXIF/reverse-image is roadmap" (or explicitly commit to gathering
   real images); reconcile every doc naming a live VLM; pull VLM out of the build path; strip d11's
   give-away lines. *(H-DEVIATION-1)*
4. `[needs Pragalbh]` **Decide the relocation observable and reconcile the data layer to the doc layer BEFORE freezing
   extraction** — regenerate the corpus with the Rawalpindi→Rahwali + supersede thread (rebuild the orphan
   `site_second`), or formally de-lock the docs to the Karachi flip. *Timeline-gated.* *(H-CONSIST-2)*
5. `[agent — gated on #4]` **Repair the worked-query ground truth** in `answer_key` + generator — rewire edges to the C/01 grammar
   so `expected_path` is fully traversable (add an acceptance check); in the same pass relabel HT-233 as a
   CANDIDATE chokepoint (substitutability UNKNOWN + Known Gap), separating the sourced `supplies-component`
   edge from the inferred sole-source conclusion. *(H-CONSIST-1 + M-INCONSIST-1)*
6. `[agent — confirm flagship = HQ-9/P vs HQ-9BE]` **Fix the merge/resolution beat data** — lock HQ-9/P vs HQ-9BE as the flagship (d04 seeds it), add the
   `same-as` + `distinct-from` edges so both mechanisms have real write-back targets, correct the
   `alias_merge_trap` expect strings, demote FT-2000 to a design-note example. *(H-CONSIST-3)*
7. `[needs Pragalbh — confirm, then agent implements]` **Promote one deception signal to genuinely computed** (near-duplicate + burst-timing over d11/d12/d13)
   and add a confidence-floor to `supersedes` routed through alert-disposition HITL; state the
   machine-derived vs analyst-provided boundary in the design note. *(H-DEFENSIBILITY-1)*
8. `[needs Pragalbh + design collaborator]` **Lock the status visual language before any frontend work** — deliver and ledger the legend/style tile;
   adopt the brief's layout instinct as a ratified `DECISIONS.md` §2 one-liner. *(M-UNDERSPEC-1)*
9. `[agent]` **Pin the load-bearing algorithms as concrete functions with worked numbers** — the 0.40 relational
   merge term, the supersede/contradict match key (edge-instance identity + which edges are single-valued),
   the citation-validator "supports its hop" + sufficiency rule — and declare extraction a one-time frozen
   offline pass with the hero query cached. *(M-BUILD-2 + M-BUILD-3)*
10. `[agent — draft for review]` **Produce the planning artifacts that steer the build** — the six-section design-note outline with a
    hard word budget + the M1–M5 coverage matrix, an ordered build/drop ladder (spine gate first;
    drop-order animation → linked selection → deep third HITL, holding merge + relocation last), and a
    committed recorded end-to-end run as the demo fallback. *(M-TIMELINE-1 + L-LOOSE-1 + L-FIDELITY-1 + L-DEMO-1)*
