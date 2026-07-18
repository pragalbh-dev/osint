# Spine — Credibility, Confidence, Freshness, Sufficiency, Integrity

The load-bearing doc. "Lead with credibility, not collection." Covers how a claim earns a confidence, how
freshness modulates it, how confirmed/probable/stale is decided, how insufficient-evidence is detected,
and how manipulated/miscaptioned media (Module 4) feeds the same score.

---

## Decisions

> **This is the "Confidence Resolver."** Its concrete, instantiated form — the factor rubric, the
> noisy-OR arithmetic, the exact gates, the three-axis independence rule, half-life defaults, and the
> supersedes/contradicts logic — is the **ratified canonical design in `08-spine-2.0-review.md` §C**
> (mirrored into `08-detailed-design.md` §3.4–3.8) and consumed by `../C/01-materiality-ontology.md`.
> This doc holds the *concepts and the why*; **the numbers, weights, and cutoffs live in §C / 08 — this
> doc does not lock its own conflicting numeric system.** Where a formula appears below it is a pointer
> to the §C canonical form, not an independent authority.

### Credibility = a tunable function of user-defined factors (Module 1)
Module 1 is literally "credibility based on user-defined factors / criterion," so credibility is a
**configurable** function, not a hardcoded per-source number. Inputs:
- **Source reliability — *derived from an analyst-set factor rubric*, not a fiat per-class number.**
  The analyst configures *factors and weights* (authority, editorial/verification process, directness,
  track record); a source's reliability is the rubric's **output**. Per-class values (official > trade
  media > social) are illustrative rubric outputs, not typed-in constants — this is what makes "based
  on user-defined factors" literally true rather than a hardcoded tier table that only looks
  configurable. Grounded in the Admiralty/NATO STANAG A–F source-reliability axis. Full rubric: `08` §3.4.
- **Intrinsic plausibility** — believability of the claim *on its face*, independent of source and
  corroboration (a world-knowledge prior); **folded into the source rubric as one factor**, and the one
  axis where an LLM *downward* sanity prior is legitimate.
- **Integrity signals** — is the artifact authentic and correctly attributed (see M4 below).
- **"Too-clean" penalty** — a source that is suspiciously perfect / perfectly placed drops in credibility
  (deception resistance; see `06-adaptation.md`).

**Corroboration is NOT an input to per-claim credibility.** It is a *separate, post-resolution* pooling
step (see "assertion-corroboration" below) — one source's claim earns its own `claim_credibility` in
isolation; independent claims are only combined afterwards into `assertion_confidence`.

Output: a **`claim_credibility` per resolved claim** that is pooled into node/edge `assertion_confidence`
→ **confirmed vs probable**. Lock the split: **credibility is per resolved-claim; confidence is per
resolved-assertion (pooled)** — two objects, never averaged.

### Assertion-corroboration alone is not enough — it's gameable, so independence is assessed on three axes
**Two distinct "corroborations", never conflated.** *Merge-corroboration* asks IDENTITY (are these the
same entity? — the `source_asserted` term inside resolution) and lives on the `same-as` edge as
`merge_confidence`. *Assertion-corroboration* — this section — asks TRUTH (is the resolved claim real?),
runs **after** resolution over claims sharing a `resolved_ref`, and produces `assertion_confidence`.
Claims are never merged; only entities merge, and co-reference via `resolved_ref` is what gets pooled here.

Assertion-corroboration pools *independent* sources. An adversary plants one fake plus two "independent"
posts referencing it; a corroboration-only system raises confidence on the fabrication. So corroboration
is a separate post-resolution pooling, not a term inside per-claim credibility. The C research sharpened
*independence* into **three axes** — a pair must clear all three or it is **false corroboration**:
- **origin-independent** — different publisher, neither citing the other; and an **aggregator inherits
  its upstream origins** (SIPRI + the press it compiles ≠ two origins);
- **discipline-independent** — different collection discipline (IMINT vs ELINT vs textual);
- **interest-independent** — different bias vector (ISPR + Chinese state media are aligned-interest, so
  **not** cross-interest corroboration however independent their bylines).

Also: an **adversary-denial** signal (an adversary asserting a fake second-source or denying a known
dependency) is *discounted*, never counted as corroboration. Full grouping rule + arithmetic: `08` §3.5.

### Confidence → status, with freshness as a per-edge-type modifier
**Freshness-sensitivity is a property of the edge type**, because facts perish at different rates:
- **Durable** (manufacturer→component, variant lineage) — effectively no decay.
- **Perishable** (basing, disposition, unit readiness) — decays fast.

Model: give each edge type a **half-life**; freshness enters `claim_credibility` directly (see §C form),
so a decayed claim pools into a lower `assertion_confidence`.

**STALE is a crisp two-step, never a silent hold:**
1. A **confirmed** assertion whose supporting claims age past the coverage cadence is annotated
   **"confirmed-as-of-DATE / coverage-lapsed"** — *still confirmed*, but flagged as coverage-overdue (a
   freshness **annotation**, the monitoring signal; the label has not changed).
2. Once age **> one half-life**, it is **demoted one step to "probable (stale)"** — an *actual label
   change*, not just an annotation.

A node **never silently stays "confirmed"** as it ages. This operationalises both freshness *and* the
"sources close" half of adaptation (`06-adaptation.md`).

**Supersedes vs. contradicts (a rebuild rule the C research added).** When two claims about the same
resolved entity×edge-instance disagree: if their real-world times *differ*, the newer **supersedes** the
older (a state change — e.g. a unit relocated), and the old assertion degrades to *stale*, not
contradicted; if the times are the *same*, it's a genuine **contradiction** → flagged → HITL. When
instance identity is uncertain (same mobile unit?), emit a *candidate-supersede* rather than silently
overwrite. This is what keeps the relocation observable honest (`../C/02-demo-thread.md`; `08` §1, §3.8).

### Insufficient-evidence via evidence-requirement templates
The non-negotiable ("return 'insufficient evidence', name what's missing, when next coverage is due")
is made demonstrable by a **configurable evidence-requirement template per assertion type**. Example:

> *confirm a basing* = (overhead imagery **OR** ≥2 independent textual sources) within the freshness window

Check which slots are filled. Empty slots → *"insufficient evidence; missing: overhead confirmation; next
coverage due DATE."* Because the template is explicit, the **gap statement is generated, not hand-written.**
This is the highest-leverage single pattern in the spine — it turns the non-negotiable into a checkable,
defensible mechanism. It's also configurable, satisfying "sufficiency should be a configurable decision."

**A failed template emits a first-class `Known Gap` node** (C/01's `Known Gap / Collection Requirement`
type), not just an inline string — so *"what do we NOT know?"* reads off nodes and doubles as
prioritized collection tasking. Its `observability_ceiling` (`confirmable | probable-max |
never-observable`) distinguishes a fixable coverage lapse from a *permanently* unobservable fact
(magazine depth, contract terms, C2 topology) — so the system never implies fresh imagery would close a
gap that is structurally unclosable. (`08` §3.7.)

### Module 4 (manipulated / AI-generated media / misinformation) — three orthogonal axes, one score
From `../md/04-claude-chat.md` Q4. Do **not** collapse M4 into "corroborate the claim." Three axes feed
the *same* unified confidence:
1. **Content veracity** — is the claim true? → corroboration + credibility.
2. **Artifact integrity** — is this image/video authentic and unmanipulated?
3. **Contextual provenance** — is a *real* artifact correctly attributed to the claimed time/place/event?
   (The recycled-2019-photo-with-new-caption case — corroboration can't catch it; the local first-seen
   hash-index can — reverse-image search is a roadmap enrichment.)

**Cheap, defensible signals** (each applies a *credibility penalty*, not a binary fake/real verdict):
- **VLM caption-vs-image consistency** — caption says "launcher at Base X," VLM sees a civilian truck or
  95% cloud → flag.
- **Cross-source physical consistency** — satellite reports total cloud cover, but a "clear daylight photo"
  of the same base the same day exists → suspicious.
- **Provenance / recency** — the **local first-seen hash-index** catches the recycled photo (reverse-image
  search = roadmap enrichment, `md/15` §1).
- **Coordinated inauthenticity** — N near-identical posts in a tight window → manufactured consensus,
  discount (this is the "too-clean"/independence signal; a network signal, not a content one).

**Detector discipline (per §D):** the structural signals — **two image hashes** (`sha256` exact-byte for
same-origin grouping + a **PDQ** perceptual near-dup hash for recycled/reshare detection — they do opposite
jobs, `md/15` §1), coordinated timestamps, aggregator/`primary_origin_id`, and the **local first-seen
hash-index** — are **deterministic detectors, never LLM-proposed**, and fail *closed* (a group counts as
independent only when metadata affirmatively establishes it). Hashes + EXIF are **computed by code and frozen
at ingest**; `first_seen` is then determined in `rebuild()` over the frozen hashes. **Reverse-image search
(TinEye) is a roadmap enrichment**, not this detector — if wired it runs at ingest as a frozen upstream
*proposer*, never inside `rebuild()`. Only the soft **"too-clean" narrative** may be LLM-proposed, and only
**downward**.

### Image trust is source-tiered (satellite vs social)
- **Commercial satellite imagery — high-provenance confirmation.** Known provider/timestamp/geo. Job:
  confirm basing/disposition + geolocate → **promotes probable → confirmed**. Failure modes: staleness
  (old imagery as current) and occlusion (cloud → insufficient evidence).
- **Social-media images — low-provenance lead.** High volume; where misinformation concentrates. Job:
  tip-off only → can raise a node to *probable*, **never confirm it alone**; must run the full integrity
  stack.

The M4 demo flex: plant one **fabricated-but-corroborated** item and show an integrity signal overriding
the corroboration count — the single moment that proves you didn't fall into the corroboration-only trap.

### Credibility score-combination — canonical form (numbers per §C / 08; constants are calibration knobs)
Hybrid: per-resolved-claim numeric credibility → origin-grouped **noisy-OR** → status label by explicit
precedence **gates** (numeric is a floor/backstop; the gates decide the label).

**Per resolved claim:** `claim_credibility (c) = R(source) × Π(integrity) × freshness`.
- `R(source) = Σ_f w_f · factor_f` over analyst-tunable factors: **authority, process, directness,
  track_record, + intrinsic_plausibility** (folded in as one rubric factor — this replaces the old
  standalone, non-monotonic `w_C` table). Illustrative R outputs (tunable, calibrate on the frozen
  corpus): SIPRI 0.85 · official 0.75 · think-tank 0.65 · customs/tender 0.60 · named-social 0.35 ·
  anon-social 0.25.
- **`model_conf = 1.0` for the demo** (everything is LLM-extracted); no extraction-confidence term is
  active now — the seam for real per-claim extraction confidence is design-noted, not built.
- `Π(integrity)` = artifact_integrity{unaltered 1.0 / unverifiable 0.85 / edited 0.30 / synthetic 0.10} ×
  first_seen{recycled 0.30 / else 1.0} × caption{consistent 1.0 / uncheckable 0.9 / mismatched 0.30} ×
  coordinated_inauthenticity{independent 1.0 / suspected 0.5 / too-clean 0.4}.
- `freshness = 2^(−age / half_life[edge])` on `event_time`; durable edges skip decay.
- **adversary_denial = GATE, NOT a multiplier** — a flagged fake-second-source / denial claim is
  **excluded from grouping** (it neither corroborates nor downgrades). Single-pass **`decoy_risk` = GATE**
  (caps the assertion at *probable*). Neither enters the arithmetic as a factor.

**Per resolved assertion:** group co-referring resolved claims into **independence groups** on the three
axes (origin / discipline / interest; aggregator inherits upstream origins; same-class-but-passing = 0.5
weight; adversary-denial excluded), then
`assertion_confidence = 1 − ∏_g (1 − c_g)`, where `c_g` = the **max `claim_credibility`** in group g
(echoes collapse → no fake corroboration). Noisy-OR = probabilistic OR under independence.

- **LABEL by gates:** **CONFIRMED** iff the sufficiency template is satisfied AND ≥2 independent origin
  groups (discipline-independent AND interest-independent), each fresh, no unresolved `contradicts` (same
  resolved-entity×edge-instance), clean integrity + clean decoy, gated attrs (foreign_control/readiness)
  not UNKNOWN, and `assertion_confidence ≥ 0.80`. Else **PROBABLE** if `0.50 ≤ assertion_confidence < 0.80`
  or the template is partially satisfied (single independent group) or **any** integrity/decoy/
  adversary-denial flag caps here. Else **POSSIBLE** if assessable but low-magnitude
  (`assertion_confidence < 0.50`) — a *lead*, never in the assessed picture. Else, if *assessability*
  fails, **INSUFFICIENT-EVIDENCE → Known Gap**. **STALE overlay:** past one half-life, demote one label
  step (see the two-step above).
- Persist per-claim credibilities, the origin-group grouping, `assertion_confidence`, the gate pass/fail
  vector, and the final label — **fully replayable for audit** ("confidence is computed, not asserted").

### Freshness half-life defaults (coarse defaults now, calibrate later — canonical table in 08; `f=0.5` at one half-life; STALE = age > 1 half-life → demote one step)
- **Durable:** manufactures 10y · design-authority-for 10y · variant-of 10y · exported-by 10y · analog-of
  lineage 10y · subordinate-to 3y · imported-by = event 10y / holdings 30mo · supplies-component = prime
  5y / tier-2-3 **18mo** · located-at = fixed 5y / fwd stockpile 18mo.
- **Force-revalidated** (5y clock, hard reset on a dissolution indicator): overhauled-at 5y (per-round
  recert 6mo) · trained-by 5y · software-controlled-by 5y.
- **Semi-durable:** inducted-into = possession 5y / named-unit 18mo · replenishes = event 10y / implication
  30mo.
- **Perishable (the live tripwires):** based-at = **field 30d** / garrison 18mo · operates/fields =
  instance 4mo / TOE 18mo · **operational-status 3mo** · reloaded-from = depth 4mo / relationship 18mo ·
  stocks-round = type 5y / depth 4mo · resupplied-by = rate 4mo / line-existence 5y.
- **N/A:** sustained-by (rollup), same-as, distinct-from, evidenced-by, corroborates, contradicts,
  supersedes, derived-from.
- Calibrate to real collection cadence: **based-at field (30d)** and **operational-status (3mo)**.

### Confirmed / probable / possible / stale status gates (cutoffs per §C: 0.50 / 0.80)
- **CONFIRMED** requires ALL: (1) **≥2 independent origin groups** after aggregator/`primary_origin_id`
  dedup (count *origins* not sources — two echoes = 1; SIPRI + the press it compiles = 1; ISPR + Chinese
  state media = fails cross-interest), discipline-independent AND cross-interest; (2) each corroborating
  claim clears the credibility floor; (3) every corroborating claim fresh (`age ≤ 1 half-life`); (4) no
  unresolved `contradicts` (same resolved-entity×edge-instance); (5) clean integrity/decoy (single-pass
  basing with decoy_risk **cannot** confirm); (6) gated attrs not UNKNOWN; + `assertion_confidence ≥ 0.80`.
- **DROPS TO PROBABLE:** `0.50 ≤ assertion_confidence < 0.80`; or only 1 independent origin; or ≥2 failing
  independence/discipline/cross-interest (aggregator inheritance, co-aligned pair); or any
  integrity/decoy/adversary-denial flag; or inferred-from-architecture w/o a naming indicator; or
  analog-propagated; or single-pass perishable with decoy_risk.
- **POSSIBLE:** assessable but low-magnitude (`assertion_confidence < 0.50`) — a *lead*, never in the
  assessed picture.
- **DROPS TO STALE** (then demote a step): freshest corroborating claim older than 1 half-life.
- **INSUFFICIENT → Known Gap:** *assessability* fails — a required evidence **kind** is missing per the
  sufficiency template (evidence is only never-observable / unsupported-range / unnamed-inferred). This is
  **off the confidence scale** (a refusal, not "confidence ≈ 0"). **POSSIBLE (low magnitude) and
  INSUFFICIENT (assessability failure) are orthogonal axes — insufficiency ≠ sparsity:** a strong claim
  with a few strong corroborations outranks a weak one with many, and a fully-corroborated assertion can
  still be INSUFFICIENT if a *required kind* of evidence is absent.

---

## Open questions
- **⚠ Calibration constants (needs your sign-off).** The source-rubric factor weights, the illustrative
  `R(source)` outputs, the `assertion_confidence` 0.50/0.80 cutoffs, and the per-edge half-lives are
  calibration knobs — the §C form is canonical, the numbers get tuned on the frozen corpus.
- **⚠ Cross-interest scope (needs your sign-off).** Recommended refinement: require **cross-interest**
  corroboration only for *interested/contested* claim classes (possession, performance, basing,
  sustainment-dependency, foreign_control); for *neutral durable* facts (design attribution, manufacture,
  radar-by-role, lineage) accept ≥2 origin- + discipline-independent refs even if they share a bias_vector
  (no interested party distorts *who designed a radar*). Confirm or make it universal.
- **"Independence" operationalization** — mostly resolved via `primary_origin_id` / `aggregator_of` /
  `bias_vector`; residual is the exact rule for *discipline*-independence (imagery vs ELINT vs text).

## Research directions
- Structured-analytic-technique grounding for confidence language (e.g. words-of-estimative-probability /
  ICD-203-style probability bands) so "confirmed/probable/possible" map to defensible ranges.
- Practical, cheap deepfake/manipulation signals that survive a demo (ELA, metadata, reverse-image APIs) —
  scope the "credible attempt," not a solved detector.
- Freshness / bi-temporal modelling patterns (cross-ref `01-graph-and-ontology.md`).
