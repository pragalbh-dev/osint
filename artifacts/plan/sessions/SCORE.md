# Session SCORE — Confidence Resolver + Sufficiency/Known-Gap + Materiality Precompute

**Wave 1 · depends F0 only · NO LLM · the densest session (the arithmetic + the non-negotiable).**
Read `../00-master-plan.md` §4.2 (records), §4.3 (the four stage signatures you fill + the fixed
`resolve → score_claims → (group by independence) → assign_status → check → precompute` call-order), §4.4
(config surface), and §5 (gates **G6/G7/G8** — the ones you must keep green and extend). SCORE implements the
**credibility, status, sufficiency, and materiality** stages of `rebuild()` — the part that decides every
number, every label, and every refusal. It is pure deterministic arithmetic over F0's frozen logs + config;
all constants come from `credibility.yaml`/`templates.yaml`, none from code (G6). *The soft "too-clean"
narrative is produced **upstream at ingest**, not here.*

## Goal

Turn resolved claims + the source registry + config into, per rebuild: a **`claim_credibility`** per claim,
independence **groups**, a pooled **`assertion_confidence`** per node/edge, a **gate pass/fail vector**, a
**status label**, a **sufficiency evaluation** (→ first-class `Known Gap` when a required evidence *kind* is
missing), and **precomputed materiality attrs** on nodes. Everything persisted on the derived assertion
state (§4.2) so the whole chain is **fully replayable for audit** — "confidence is computed, not asserted."
G7 (can't reach `confirmed` without the full gate) and G8 (a planted gap becomes a `Known Gap` with a
*templated* refusal) fall out of this session being correct.

## Design docs to read first
`spine/04-credibility.md` (**THE load-bearing doc** — read whole; concepts + why) · `spine/08` **§3.4**
(Confidence Resolver two-stage form + factor rubric + status machine), **§3.5** (three-axis independence),
**§3.6** (half-life defaults), **§3.7** (sufficiency templates + `next_coverage_due` + Known Gap) · `spine/09`
("Materiality is precomputed inside `rebuild()`" — the section, plus the honesty fork open question) ·
`C/01-materiality-ontology.md` (chokepoint criteria **#1/#4/#6/#7/#10**; gated attrs `foreign_control`/
`readiness`; the three-state `substitutable-by`) · `DECISIONS.md` "Spine 2.0 canonical design" rows
(canonical scoring form; INSUFFICIENT↔POSSIBLE orthogonality; two-scores-never-averaged; adversary_denial =
gate, not multiplier). **When a design doc and this plan disagree, the design doc wins.**

## Scope (build these)

Four pure stage functions (F0's frozen signatures, §4.3), living in the three owned packages. Grouping +
noisy-OR + the status machine all live in `chanakya/credibility/` (SCORE also fills the `assign_status`
stub F0 exports there); sufficiency in `chanakya/sufficiency/`; materiality in `chanakya/materiality/`.

1. **Per-claim credibility** — `score_claims(resolved_claims, sources, config) -> {claim_credibility}`:
   ```
   claim_credibility (c) = R(source) × Π(integrity_penalties) × freshness
   R(source)  = Σ_f w_f · factor_f      # factors {authority, process, directness, track_record,
                                         #   intrinsic_plausibility folded in}; weights normalised, from credibility.yaml
   model_conf = 1.0                      # extraction-confidence term INACTIVE (seam kept, do not delete)
   Π(integrity) = artifact_integrity{unaltered 1.0 / unverifiable 0.85 / edited 0.30 / synthetic 0.10}
                × first_seen{recycled 0.30 / else 1.0}
                × caption{consistent 1.0 / uncheckable 0.9 / mismatched 0.30}
                × coordinated_inauthenticity{independent 1.0 / suspected 0.5 / too-clean 0.4}
   freshness  = 2^(−age / half_life[edge_type])   on event_time (fallback report_time, FLAGGED);
                durable edge types skip decay (freshness = 1.0)
   ```
   Every literal above is a `credibility.yaml` default read through F0's config store, never a code constant.

2. **Three-axis independence grouping** (feeds `assign_status`) — cluster co-referring resolved claims on:
   - **origin** — different publisher, neither cites/quotes/embeds the other; **shared image hash → same
     group**; an **aggregator INHERITS its upstream origins** (via `primary_origin_id`/`aggregator_of` — SIPRI
     + the press it compiles = one origin).
   - **discipline** — IMINT / ELINT / textual-HUMINT (two reads of one satellite pass = one look).
   - **interest** — `bias_vector`; aligned parties (ISPR + Chinese state media) = **false corroboration**.
   A pair must clear **all three** or it is not independent. **Same-class-but-passing = 0.5 weight.**
   `adversary_denial`-flagged claims are **EXCLUDED from grouping entirely** (never enter a group).
   Fail-closed: a group is independent only when metadata affirmatively establishes it.

3. **Per-assertion noisy-OR** (inside `assign_status`):
   ```
   assertion_confidence = 1 − Π_g (1 − c_g)     c_g = MAX claim_credibility in group g
   ```
   Two independent 0.6 → `1 − 0.4·0.4 = 0.84`; N echoes of one origin collapse into one group → add nothing.

4. **Gates (not multipliers)** — applied in `assign_status`, never in the arithmetic:
   - `adversary_denial_flag` → claim excluded from grouping **AND** caps the assertion at *probable*.
   - single-pass `decoy_risk_flag` → caps the assertion at *probable* (single-pass basing cannot confirm).

5. **Status machine** — `assign_status(assertions, groups, config) -> {assertion_confidence, gate_vector,
   status}`. Report the **exact gate list**:
   - **confirmed** ⟺ ALL of: sufficiency template satisfied · **≥2 independent origin groups** (discipline-
     AND interest-independent, after aggregator/`primary_origin_id` dedup) · `assertion_confidence ≥ 0.80` ·
     every supporting claim fresh (`age ≤ 1 half-life`) · **no** unresolved `contradicts` (same
     resolved-entity×edge-instance) · clean integrity **and** clean decoy · gated attrs
     (`foreign_control`/`readiness`) **not UNKNOWN**.
   - **probable** ⟺ `0.50 ≤ assertion_confidence < 0.80` **OR** single independent group **OR** any
     integrity/decoy/adversary-denial gate caps here.
   - **possible** ⟺ `assertion_confidence < 0.50` — a *lead*, **never** in the assessed picture.
   - **insufficient → Known Gap** ⟺ *assessability* fails (a required evidence **KIND** is missing per the
     sufficiency template) — **OFF the confidence scale**, not "confidence ≈ 0".
   - **contradicted** ⟺ a credible opposing group on the same resolved-entity×edge-instance → flagged → HITL.
   - **STALE overlay** — a `confirmed` assertion past its coverage cadence → annotate
     **"confirmed-as-of-DATE / coverage-lapsed"** (label unchanged); once age **> 1 half-life** → **demote one
     step** to `probable (stale)` (actual label change). A node never silently stays confirmed.
   - **POSSIBLE (magnitude) and INSUFFICIENT (assessability) are orthogonal axes** — *insufficiency ≠
     sparsity*; a fully-corroborated assertion can still be INSUFFICIENT if a required *kind* is absent.
   - **Persist** per-claim credibilities, the grouping, `assertion_confidence`, the gate pass/fail vector, and
     the final label onto the derived assertion state (§4.2) — fully replayable.

6. **Supersedes-vs-contradicts (status effect only)** — F0 owns the rebuild-level resolution on
   `resolved_ref` (differ in `event_time` → supersede; same → contradict; uncertain instance →
   candidate-supersede). SCORE provides the **status consequence**: a superseded assertion degrades to
   **STALE** (not contradicted); a contradiction → `contradicted` → HITL. **D8 fix:** a superseding claim
   must itself clear **≥1 independent probable-grade look** before it may retire a *confirmed* assertion — so
   "vacant@A" cannot erase "occupied@B" on a single weak look.

7. **Sufficiency templates** — `check(assertion, claims, config) -> {satisfied, missing_slots,
   next_coverage_due, ceiling}` over `templates.yaml` (one template per assertion type). `next_coverage_due`
   is **generated** from the per-source `cadence` field (registry), never hand-written.
   `observability_ceiling ∈ {confirmable, probable-max, never-observable}`. A failed template emits a
   **first-class `Known Gap` node** (§4.2), and the refusal statement is a **DETERMINISTIC fill-in-the-blank
   template** — regenerated prose is CUT; only frozen, validated template output is displayed.

8. **Materiality precompute** — `precompute(view, config) -> node attrs`, pure config-driven graph
   computation inside `rebuild()` (no LLM), keeping **contributing claim/edge IDs** on each attr for
   citation. Implement chokepoint criteria **#1** (sole-source in-degree, three-state gated), **#4**
   (foreign-control severity), **#6** (deep-tier BOM via `component-of` + tier-2/3 `supplies-component`),
   **#7** (confidence ceiling on inferred — all-inferred/`analog-of`-propagated capped at *probable*), **#10**
   (confirmed-vs-candidate separation). Materialise node attrs `chokepoint_count`, `chokepoint_status`,
   `substitutability_state ∈ {known-sole-source, known-alternates, UNKNOWN}`. **UNKNOWN is NOT a chokepoint**
   — it renders as *candidate* + a `Known Gap`, and is **never printed as sole-source** (absence of evidence
   ≠ evidence of absence, the disqualifying line).

## HITL pickups (from session HITL — PR #12; wire + verify here)
HITL only *appends* decisions; the **recompute is yours**. Two beats were deliberately deferred to SCORE so
they land where they can actually be exercised (rationale in `DECISIONS.md` §6 "HITL"):

1. **Reject-claim → machine recompute.** HITL's status-override `reject` currently writes
   `effects.set_status→probable` (a *forced* demote, applied post-machine by F0 — indistinguishable from
   `demote` today). The richer beat is a `reject` that **excludes the supporting claim** so *your* status
   machine re-derives confirmed→probable from fewer independent groups. That needs a small **F0-amendment**
   (drop a decision-named claim upstream of scoring, like a retraction — HITL emits the effect, F0 applies
   it); once wired, SCORE needs no special handling, but **add a fixture asserting the confirmed→probable
   transition** when removing one look drops the group count below the confirmed gate (feeds spine-gate #4 /
   flex #4 at EVAL).
2. **Analyst integrity flag → per-claim + origin-wide penalty.** HITL appends `type: integrity_flag` with
   `effects.add_integrity_flag{element_id, flag}` (element-level, applied *today* by F0) **and**
   `effects.flag_origin{primary_origin_id, co_referring_claims}`. `score_claims` must also read the
   **decision-log** integrity flags (not only `sources.yaml coordinated_inauthenticity_flag`) and apply the
   penalty to **every claim sharing that `primary_origin_id` — including claims ingested *after* the flag**
   (the monitoring/adaptation beat). Verify the false-confidence collapse: flagged echoes → one penalised
   group → the resting assertion drops.

## Contracts implemented
Master **§4.2** (ClaimRecord, SourceRegistryEntry, DerivedAssertionState, KnownGap), **§4.3** (the four stage
signatures + fixed call-order — implemented *exactly*, not re-derived), **§4.4** (all knobs read from the
live config store: `credibility.yaml` factor rubric/weights/integrity-penalties/thresholds `0.50`/`0.80`/
half-lives; `templates.yaml` per-assertion templates). SCORE **freezes no contract**; if it needs a schema
or signature change it stops and files an **F0-amendment PR** (master Rule 3), never edits F0's files.
Enforces **G6** (no scoring/threshold/half-life literal in `credibility/`|`materiality/` core — all from
config), **G7** (`confirmed` unreachable without the full gate), **G8** (planted gap → `Known Gap`, templated
refusal); extends those three gates' fixtures without weakening them.

## Acceptance criteria
- [ ] **Noisy-OR:** two origin-/discipline-/interest-independent `0.6` claims → `assertion_confidence = 0.84`.
- [ ] **Echo collapse:** two reshares of one origin → **one** group → **no** confidence boost (stays 0.6).
- [ ] **adversary_denial:** a flagged claim is **excluded from grouping** AND **caps** the assertion at
      *probable* — never counted as corroboration, never silently multiplied.
- [ ] **single-pass decoy_risk:** caps the assertion at *probable* (a single-pass basing signature cannot
      confirm).
- [ ] **Confirmed gate (property test over fixtures):** `confirmed` requires ≥2 independent groups AND
      `≥0.80` AND template-satisfied AND clean integrity/decoy AND gated attrs not UNKNOWN — no path reaches
      confirmed missing any one (G7).
- [ ] **Planted missing-kind → INSUFFICIENT:** a fixture missing a required evidence *kind* yields a
      `Known Gap` with `missing_slots` + `next_coverage_due` + `observability_ceiling`, **off the confidence
      scale**, refusal prose is the deterministic template (G8).
- [ ] **Stale demotion:** a confirmed assertion whose freshest look ages **> 1 half-life** demotes one step to
      `probable (stale)` (and annotates `coverage-lapsed` before that).
- [ ] **UNKNOWN substitutability:** renders as *candidate* + `Known Gap`, **not** confirmed sole-source.
- [ ] **HT-233-style candidate chokepoint:** an inferred/UNKNOWN deep-tier chokepoint renders as
      **CANDIDATE**, not confirmed.
- [ ] **Replayability:** per-claim credibilities, groups, `assertion_confidence`, gate vector, and label are
      all persisted on the derived assertion state and reproduce byte-identically on re-run (feeds G2).
- [ ] `ruff` + `mypy` + `pytest` (incl. G6/G7/G8) green; **G1 purity** holds (no LLM/network/clock/RNG in any
      SCORE path).

## Owned paths (nothing else)
`chanakya/credibility/**` (score_claims + independence grouping + noisy-OR + status machine),
`chanakya/sufficiency/**` (templates + Known Gap), `chanakya/materiality/**` (chokepoint precompute), and
their `tests/` dirs (`tests/credibility/**`, `tests/sufficiency/**`, `tests/materiality/**`). **Depends on:**
F0 (merged). **LLM:** no — the soft "too-clean" narrative is produced upstream at ingest, not here.

## Out of scope
Entity resolution + `resolved_ref`/supersede-match production (**RESOLVE** + F0); the ReAct agent that *reads*
the precomputed materiality attrs and `check_sufficiency` at query time (**ASK**); the HITL override/queue UI
and decision-log writeback (**HITL**); the observable evaluator (**MONITOR**); extraction and the too-clean
narrative (**INGEST**); config *content* (**DATA-C** authors the YAML; SCORE only consumes it through F0's
store). SCORE never edits a frozen/shared file (master Rule 3).

## Worktree lifecycle
`git worktree add ../wt-SCORE -b feat/score` → implement e2e inside owned paths → PR `[SCORE]` (template in
master §8) → **you review & merge** → append outcomes to the handoff note →
`git worktree remove ../wt-SCORE` and delete the branch. Rebase onto `main` on each sibling merge (always
clean given disjoint ownership). Does not block any other Wave-1 session.
