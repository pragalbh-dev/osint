# Handoff → RESOLVE + SCORE: make the grounded oracle *producible* (derivation logic)

**From:** grounding-audit session, 2026-07-19 (`fix/answer-key-grounding-apply`, off `origin/main`).
**Context:** the DATA-C/EVAL answer_key edits are **APPLIED** (see `handoff-answer-key-grounding.md`
STATUS block + `ANSWER-KEY-GROUNDING-AUDIT.md`). Softening the oracle is only half the loop — the pipeline
must now *derive* what the grounded oracle expects, or the graph still won't match. This handoff is the
RESOLVE + SCORE half. It **extends** the existing `handoff-resolve.md` (RES-1) and `handoff-score.md`
(SC-2/SC-4) with the specific requirements the grounding created; do not re-derive those, build on them.

**The one analyst principle that governs all of it:** *observed ≠ inferred, and the graph must show both.*
Imagery gives you equipment at a place (a strong, stated observation); attributing that equipment to a
named unit, or inferring that a component has a particular maker, is a **separate inferential hop that
carries its own, lower confidence.** The oracle now encodes that split explicitly (`basis: "derived"`,
`observed_layer` / `attribution_layer` on every `based-at` edge; the HT-233 maker as a Known Gap). Your job
is to make the derived layer *fall out of the pipeline* at the confidence the evidence supports — never to
mint a stated fact the corpus doesn't carry.

---

## RESOLVE — RES-G1: derive `unit --based-at--> site` as a two-layer edge  (extends RES-1)

**What the oracle now expects.** No document states "named unit X at named site Y." Each basing edge is a
derivation: **(a)** an equipment@site sighting (imagery observation — confirmed/probable by pass count and
decoy checks) **+ (b)** a hedged formation reference ("reportedly PAAD Command"; "consistent with a PAAD
deployment") that attributes the equipment to a unit. The oracle carries both layers
(`observed_layer` = the sighting, `attribution_layer` = the unit link) with the attribution graded
**probable**, and the overall edge status set by occupancy.

**What to build (on top of RES-1's endpoint-linking):**
- Resolve the equipment sighting's subject ("HQ-9B fire-unit", "HQ-9/P battery element") to the unit
  canonical id (`unit_hq9b` / `unit_paad`) via the entity registry (`config/entities.yaml`) + the hedged
  formation reference — **not** a bare string match. Where the formation reference is only a hedge, the
  attribution rides at **probable**, never confirmed.
- Emit the `based-at` edge with the two layers preserved: the occupancy confidence from the imagery
  (RESOLVE/SCORE), the attribution confidence from the formation hedge. Do **not** collapse them into one
  flat "confirmed stated" edge — that is the exact over-claim the grounding removed.
- **CASIC-via-program (D-G1 consequence):** there is no longer a direct `mfr_casic → comp_ht233` edge. When
  a query needs "who is behind the HT-233," RESOLVE must resolve CASIC through the variant
  (`comp_ht233 equips var_hq9p`, `mfr_casic manufactures var_hq9p`) and surface the HT-233 *maker* as the
  Known Gap (candidate `mfr_23rd_ri` via `supplies-component`, possible). Never resolve CASIC as the radar's
  maker.

**Verify:** the three `based-at` edges appear with `unit_*`/`site_*` canonical endpoints; each carries an
attribution status ≤ its occupancy status; the Karachi edge occupancy = confirmed, attribution = probable.

---

## SCORE — the derived statuses the grounding needs  (extends SC-2 / SC-4; NO credibility retune)

- **SC-G1 (basing stale, extends SC-2).** Rawalpindi must go **stale** — but honestly: staleness here is
  driven by perishable-`based-at` freshness decay **+** the redeployment inference (d19), **not** a negative
  observation at Rawalpindi (none exists). Add the bare `based-at` half-life so basing decays; the stale
  transition should read as "aged out / superseded by the Rahwali redeployment," not "observed empty."
- **SC-G2 (supersede with a floor, extends SC-4).** Synthesize `supersedes (site_rahwali → site_rawalpindi)`
  as a **derived** edge from the redeployment beat, held at a **confidence floor** so the d20 single-source
  reverse rumor ("moved back to Rawalpindi") cannot flip a confirmed basing. The oracle marks this edge
  `basis: derived` with the floor note — match that behavior. This is the counter-deception headline.
- **SC-G3 (the 2-independent-signal gate).** Rahwali must lift probable→confirmed **only** on a
  discipline-independent + cross-interest second signal (d19's repeat-EO **+** ELINT), never on a second
  look at the same pass. The single-pass d18 stays capped at probable under the decoy-risk flag.
- **SC-G4 (materiality — leave it honest).** The chokepoint stays **candidate**. Do **not** seed
  `foreign_control` / `SOLE_SOURCE` to force a CONFIRMED chokepoint (upholds D-C.1; verified no seed exists).
  If HT-233 should surface as *material* at all, rest it on the hedged techdata-authority (d21) +
  no-open-substitute-chassis (d24) axis at **probable**, hedges preserved. SC-1 (chokepoint nomination on
  supply-tier node types + correct direction) still applies — HT-233 is the target, not the variants/units.

**Verify:** `stale` node/edge count > 0 (Rawalpindi); `supersedes`/`sustained-by` edge counts > 0; Rahwali
confirmed only with two independent looks; `chokepoint_status(comp_ht233) == "candidate"` and it lands in
`query_graph`'s indeterminate partition for a `known-sole-source` filter (never a match).

---

## §ASK-coupling — a NEW dependency the grounding surfaced (ASK, not RESOLVE/SCORE — flagged so it isn't lost)

Fixing the false CASIC→HT-233 claim exposed that **ASK's deterministic hero path is coded to the same false
narrative.** `backend/chanakya/agent/loop.py::run_fixed_hero_path` (≈L167-174):
1. finds the chokepoint component (`comp_ht233`);
2. looks for its maker via a **`manufactures`** edge — which, after D-G1, no longer exists on a component;
3. **defaults** `mfr_id` to the literal `"mfr_casic"` when none is found — i.e. it will assert CASIC as the
   HT-233 maker, the exact disqualifying error.

The ASK unit tests use a self-contained fixture (`backend/tests/agent/fixtures.py`), **not** the oracle, so
the answer_key edit does not break them and this PR stays green — but the ASK hero path itself needs fixing
to stay honest against the real graph:
- find the chokepoint's maker via **`supplies-component`** (not `manufactures`), and when it resolves only
  to a `possible` candidate / a Known Gap, **surface the gap honestly** ("maker UNKNOWN; candidate 23rd RI,
  unconfirmed") instead of defaulting to CASIC;
- reach CASIC as the **program prime / design authority** (via `var_hq9p` + `sustain_techdata`), distinctly
  labelled, never as the radar maker;
- re-point the hero fixture edge `mfr_casic manufactures comp_ht233` → `mfr_casic manufactures var_hq9p`
  and update the coupled assertions (`test_tools.py::test_find_paths_hero_chain`, `api/test_ask.py`,
  `agent/test_fixture.py`) to the honest trace.

This overlaps the existing **`handoff-ask.md`** (Phase 4: crash-guard + honest refusal + hero-anchor
resolution). Owner: ASK. Not in scope for the RESOLVE/SCORE agent — listed here only so the coupling is
tracked. **Orchestrator note:** the user scoped this round to RESOLVE + SCORE; ASK is a third, separately
decidable handoff.
