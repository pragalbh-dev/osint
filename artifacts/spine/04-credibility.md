# Spine — Credibility, Confidence, Freshness, Sufficiency, Integrity

The load-bearing doc. "Lead with credibility, not collection." Covers how a claim earns a confidence, how
freshness modulates it, how confirmed/probable/stale is decided, how insufficient-evidence is detected,
and how manipulated/miscaptioned media (Module 4) feeds the same score.

---

## Decisions

> **This is the "Confidence Resolver."** Its concrete, instantiated form — the factor rubric, the
> noisy-OR arithmetic, the exact gates, the three-axis independence rule, half-life defaults, and the
> supersedes/contradicts logic — is specified in `08-detailed-design.md` §3.4–3.8 and consumed by
> `../C/01-materiality-ontology.md`. This doc holds the *concepts and the why*; 08 holds the *numbers
> and formulas*.

### Credibility = a tunable function of user-defined factors (Module 1)
Module 1 is literally "credibility based on user-defined factors / criterion," so credibility is a
**configurable** function, not a hardcoded per-source number. Inputs:
- **Source reliability — *derived from an analyst-set factor rubric*, not a fiat per-class number.**
  The analyst configures *factors and weights* (authority, editorial/verification process, directness,
  track record); a source's reliability is the rubric's **output**. Per-class values (official > trade
  media > social) are illustrative rubric outputs, not typed-in constants — this is what makes "based
  on user-defined factors" literally true rather than a hardcoded tier table that only looks
  configurable. Grounded in the Admiralty/NATO STANAG A–F source-reliability axis. Full rubric: `08` §3.4.
- **Corroboration** — count of claims that are **independent on three axes** (origin / discipline /
  interest); see the upgraded rule below.
- **Integrity signals** — is the artifact authentic and correctly attributed (see M4 below).
- **"Too-clean" penalty** — a source that is suspiciously perfect / perfectly placed drops in credibility
  (deception resistance; see `06-adaptation.md`).

Output: a **confidence per claim** that propagates to node/edge confidence → **confirmed vs probable**.

### Corroboration alone is not enough — it's gameable, so independence is assessed on three axes
Corroboration counts *independent* sources. An adversary plants one fake plus two "independent" posts
referencing it; a corroboration-only system raises confidence on the fabrication. So corroboration is one
input, not the whole score. The C research sharpened *independence* into **three axes** — a pair must
clear all three or it is **false corroboration**:
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

Model: give each edge type a **half-life**; effective confidence =
`corroborated_confidence × decay(age, half_life_of_type)`.

**State machine:**
- **Confirmed** = multi-source corroboration **AND** freshness above threshold.
- freshness lapses → **Confirmed-as-of-DATE / coverage-lapsed** →
- → **Probable (stale)**.

A node **never silently stays "confirmed"** as it ages. This single rule operationalises both freshness
*and* the "sources close" half of adaptation (`06-adaptation.md`).

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
   (The recycled-2019-photo-with-new-caption case — corroboration can't catch it; first-seen/reverse-image
   can.)

**Cheap, defensible signals** (each applies a *credibility penalty*, not a binary fake/real verdict):
- **VLM caption-vs-image consistency** — caption says "launcher at Base X," VLM sees a civilian truck or
  95% cloud → flag.
- **Cross-source physical consistency** — satellite reports total cloud cover, but a "clear daylight photo"
  of the same base the same day exists → suspicious.
- **Provenance / recency** — first-seen date / reverse-image catches the recycled photo.
- **Coordinated inauthenticity** — N near-identical posts in a tight window → manufactured consensus,
  discount (this is the "too-clean"/independence signal; a network signal, not a content one).

### Image trust is source-tiered (satellite vs social)
- **Commercial satellite imagery — high-provenance confirmation.** Known provider/timestamp/geo. Job:
  confirm basing/disposition + geolocate → **promotes probable → confirmed**. Failure modes: staleness
  (old imagery as current) and occlusion (cloud → insufficient evidence).
- **Social-media images — low-provenance lead.** High volume; where misinformation concentrates. Job:
  tip-off only → can raise a node to *probable*, **never confirm it alone**; must run the full integrity
  stack.

The M4 demo flex: plant one **fabricated-but-corroborated** item and show an integrity signal overriding
the corroboration count — the single moment that proves you didn't fall into the corroboration-only trap.

### Credibility score-combination — LOCKED form (constants are calibration knobs)
Hybrid: per-indicator numeric score → origin-deduped **noisy-OR** → three-state label by explicit
precedence **gates** (numeric is a floor/backstop; the gates decide the label).
- **Per-indicator base** `s_i = w_R × w_C`. `w_R`(reliability A–F) = A 1.0 / B 0.8 / C 0.6 / D 0.4 / E 0.2 /
  F 0.0. `w_C`(credibility 1–6, as *intrinsic plausibility*; grade-1 "confirmed by others" must NOT
  self-certify corroboration) = 1:0.95 / 2:0.80 / 3:0.60 / 4:0.35 / 5:0.15 / 6:0.30.
- **Integrity/M4 multiplier** `m_i` = artifact_integrity{unaltered 1.0 / unverifiable 0.85 / edited 0.30 /
  synthetic 0.10} × first_seen{recycled 0.30 else 1.0} × caption{consistent 1.0 / uncheckable 0.9 /
  mismatched 0.30} × coordinated_inauthenticity{independent 1.0 / suspected 0.5 / too-clean 0.4}.
  **adversary_denial is a GATE, not a multiplier** (a flagged fake-second-source / denial claim is
  *discounted* — it neither corroborates nor downgrades).
- **Freshness** `f_i = 0.5^(age / half_life[edge])` on `valid_time`.
- `s''_i = s_i × m_i × f_i`; dedup indicators by `primary_origin_id` expanding `aggregator_of` (take **max
  within an origin group** so echoes never stack); combine independent groups by noisy-OR:
  `C_raw = 1 − ∏(1 − s''_g)`.
- **LABEL by gates:** **CONFIRMED** iff ≥2 independent origin groups, pairwise discipline-independent AND
  cross-interest, each `s_i≥0.50` and fresh (`f_i≥0.5`), no unresolved `contradicts` (same
  resolved-entity×edge-instance), clean integrity (all `m≥0.85`)+clean decoy, gated attrs
  (foreign_control/readiness) not UNKNOWN, and `C_raw≥0.80`. Else **PROBABLE** if any credible
  fresh-enough indicator or `C_raw≥0.40` (single high-reliability source, co-aligned pair, aggregator
  inheritance, analog-of propagation, or **any** integrity/too-clean/adversary-denial flag caps here). Else
  **INSUFFICIENT-EVIDENCE → Known Gap**. **STALE overlay:** if best `f<0.5`, demote one label step.
- Persist per-indicator scores, the origin-group dedup, `C_raw`, the gate pass/fail vector, and the final
  label — **fully replayable for audit** ("confidence is computed, not asserted").

### Freshness half-life defaults — LOCKED (`f=0.5` at one half-life; STALE = age > 1 half-life → demote one step)
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

### Confirmed / probable / stale thresholds — LOCKED
- **CONFIRMED** requires ALL: (1) **≥2 independent origin groups** after aggregator/`primary_origin_id`
  dedup (count *origins* not sources — two echoes = 1; SIPRI + the press it compiles = 1; ISPR + Chinese
  state media = fails cross-interest), discipline-independent AND cross-interest; (2) each corroborating
  indicator ≥ credibility floor (reliability A–C AND credibility 1–3, `s_i≥0.50`); (3) every corroborating
  indicator fresh (`age ≤ 1 half-life`); (4) no unresolved `contradicts` (same resolved-entity×edge-
  instance); (5) clean integrity/decoy (single-pass basing with decoy_risk **cannot** confirm); (6) gated
  attrs not UNKNOWN; + `C_raw≥0.80`.
- **DROPS TO PROBABLE:** only 1 independent origin; or ≥2 failing independence/discipline/cross-interest
  (aggregator inheritance, co-aligned pair); or any integrity/decoy/adversary-denial flag; or
  inferred-from-architecture w/o a naming indicator; or analog-propagated; or single-pass perishable with
  decoy_risk.
- **DROPS TO STALE** (then demote a step): freshest corroborating indicator older than 1 half-life.
- **DROPS TO INSUFFICIENT → Known Gap:** `C_raw<0.40`, or evidence is only never-observable /
  unsupported-range / unnamed-inferred.

---

## Open questions
- **⚠ Calibration constants (needs your sign-off).** The credibility weight tables (`w_R`/`w_C`), the
  `C_raw` 0.40/0.80 thresholds, and the `s_i≥0.50` floor are calibration knobs — the form is locked, the
  numbers get tuned on the frozen corpus.
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
