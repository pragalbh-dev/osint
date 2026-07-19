# EVAL RCA handoff — SCORE (credibility/status/sufficiency/materiality)

## Context

The pipeline was run end-to-end for the first time over real extracted bundles, and the resulting graph
diverges sharply from the oracle answer key. This handoff is SCORE's share of the fix — the credibility,
confirmed/probable/stale status, sufficiency, and materiality (chokepoint) machinery. Evidence base:
`tmp/conv/eval-rca/00-evidence-summary.md` and `tmp/conv/eval-rca/view_full.json`, generated from the real
bundles at `corpus/scenarios/hq9p_primary/claims/`.

**Read this first:** the graph's overall divergence from the oracle is dominated by two upstream master
defects that are NOT yours — RESOLVE's id-namespace split (edge endpoints are bare LLM surface strings,
entity nodes are keyed `ent:<type>:<name>`, so 0/109 edge endpoints match an entity id) and INGEST's
extraction contract gaps (denials/identity minted as knowledge triples, missing structural transforms for
supply-chain/ORBAT edges, edge-vocabulary collisions). **Do not retune credibility to compensate** — a
counterfactual probe confirmed that once RESOLVE correctly merges entities, SCORE's existing
confirmed/probable gate promotes `unit_paad`, `site_karachi`, `comp_tel_chassis` to confirmed on its own.
Your real, SCORE-owned defects are narrower: a chokepoint materiality-logic bug, an unreachable stale
path for basing, an overly coarse discipline taxonomy, and missing derived-edge computation.

## TL;DR

1. **Fix chokepoint nomination** (SC-1, major) — it nominates variants and units (consumers) as supply
   chokepoints instead of components/manufacturers (suppliers); verified to survive correct entity merging,
   so it is a real logic bug, not just a fragmentation artifact.
2. **Fix the unreachable basing stale-path** (SC-2, major) — no bare `based-at` half-life fallback exists,
   so basing edges are treated as durable and can never go stale, breaking the relocation story.
3. **Compute the missing derived edges** (SC-4, major) — `supersedes` and `sustained-by` are never
   synthesized, so relocation and sustainment rollups never appear; the contradiction gate is sound but
   unfed.
4. (minor) **Broaden the discipline taxonomy** (SC-3) — two distinct textual source classes both count as
   "textual" and get same-class-halved, capping entities like `mfr_taian` at probable when they should
   confirm.

## Findings

### SC-1 — Chokepoint nomination has no node-type or supply-direction filter

- **Symptom:** 12 candidate chokepoints are nominated on the WRONG node types — variants (`HQ-9/P`,
  `HQ-9B`, `HQ-9BE`) and units (PAF air defence squadrons, Pakistan Army Air Defence Command) are nominated
  as *supply* chokepoints, spawning 12 `gap:chokepoint:*` known-gaps. The real chokepoint, `comp_ht233`,
  is not distinguished from this noise.
- **Evidence:**
  - `backend/chanakya/materiality/precompute.py:100-118` — `sole_edges` computed as per-edge-TYPE
    in-degree == 1, with no node-type or direction filter.
  - `backend/chanakya/materiality/precompute.py:29-32` — `_SUSTAINMENT` set includes
    `manufactures`/`equips`/`component-of`/`design-authority-for`, all of which point AT the consumer, not
    the supplier.
  - Probe `/tmp/probe_score4.py`: simulating a fully-merged HQ-9/P entity still yields `equips=1` +
    `design-authority-for=1` distinct suppliers → **still nominated**. This proves the bug survives correct
    RESOLVE merging — it is not merely a fragmentation artifact.
  - Probe `/tmp/probe_score3.py`: all 12 current candidates are units/variants/unknown, each with per-type
    in-degree exactly 1.
  - `view_full.json` known_gaps: `gap:chokepoint:HQ-9/P`, `HQ-9B`, `HQ-9BE`, `PAF air defence squadrons`,
    `Pakistan Army Air Defence Command` (12 total).
- **Root cause:** Criterion #1 for chokepoint nomination fires on ANY node with a sole in-edge of a given
  type, regardless of node type or which end of the edge represents "the supplier." Sole-source risk
  semantically belongs to the *supplier* side (the component/manufacturer with only one downstream
  consumer would be a different, valid signal — but nominating the *consumer* because it has only one
  supplier of a given type is backwards for a "supply chokepoint").
- **Recommended fix:** Restrict chokepoint nomination to supply-tier node types (`component`,
  `manufacturer`) and nominate the correct end — the supplier, not the variant/unit it supplies. This is
  the real fix, not optional hardening; tune/verify against the oracle's real chokepoint (`comp_ht233`).
- **Severity:** major.
- **Cross-service dependencies:** None — independent of the two masters, fixable now. Unblocks: cleaner
  materiality output for ARCH's lens and MONITOR's tripwires once they read known_gaps/chokepoints.

### SC-2 — Basing can never go stale (unreachable half-life path)

- **Symptom:** No node/edge ever reaches `stale` status. The oracle wants `site_rawalpindi` = stale, and
  the basing decay that should drive the relocation story never happens.
- **Evidence:**
  - `config/credibility.yaml:70-84` — `half_lives_days` keys basing ONLY under variant sub-keys
    `based-at.field:30` and `based-at.garrison:540`; there is **no bare `based-at` key**.
  - `backend/chanakya/credibility/scoring.py:153-164` — `_half_life_days` looks up
    `<edge>.<variant>` then falls back to bare `<edge>`; if neither key exists, returns `None` → treated as
    durable.
  - `backend/chanakya/credibility/scoring.py:195-237` — `assertion_freshness` with `half_life=None` never
    sets the STALE flag.
  - `backend/chanakya/credibility/status.py:117-120` — STALE status requires `strong` + the `_STALE` flag.
  - Probe: `freshness_variant` is `None` on ALL 452 claims (the field is never populated by extraction) →
    `stale` node count = 0.
- **Root cause:** The half-life config only has variant-specific keys for `based-at`, and no producer
  currently tags `freshness_variant` (`field` vs `garrison`) on claims, so the lookup falls through to
  `None` for every basing claim, structurally disabling staleness for basing under the current
  config+producer contract.
- **Recommended fix:** Add a bare `based-at` half-life fallback (e.g. 540 days) in `credibility.yaml` so
  basing decays even when `freshness_variant` is untagged. Optionally also have INGEST start tagging
  `freshness_variant=field|garrison` for finer-grained decay later.
- **Severity:** major.
- **Cross-service dependencies:** Necessary but not sufficient — the observable symptom (0 relocation
  alerts) is INGEST-dominated too: currently only one garbage `based-at` edge exists in the graph at all.
  Depends on INGEST producing real `based-at` edges (see fix-order item 4, ING-2) for the full relocation
  story to appear; this SCORE config fix alone will not produce visible stale nodes until that lands, but
  should still be made now since it's a one-line, clearly-correct config gap.

### SC-3 — Discipline taxonomy too coarse: two textual source classes both get halved

- **Symptom:** An entity corroborated by exactly two independent textual source *classes* (e.g.
  think-tank + curated-register) cannot reach `confirmed`. `mfr_taian` (oracle wants confirmed) stays
  `probable` even when correctly merged.
- **Evidence:**
  - `config/credibility.yaml:63` — `min_independent_groups: 2`.
  - `config/credibility.yaml:64` — `same_class_weight: 0.5`.
  - `config/credibility.yaml:67` — `disciplines: {satellite: IMINT}` — only satellite is distinguished;
    everything else defaults to a single "textual" discipline.
  - `backend/chanakya/credibility/independence.py:170-178` — the 2nd+ same-discipline group is weighted
    by `same_class_weight` (0.5).
  - `backend/chanakya/credibility/status.py:69-74,101-108` — `_effective_looks` sums weighted looks;
    `strong` requires effective looks ≥ 2.
  - Probe: `mfr_taian` pooled claims (think-tank 0.69 + curated-register 0.848) → `eff_looks = 1.5` →
    **PROBABLE**, despite `conf = 0.821` clearing the 0.80 magnitude cut.
- **Root cause:** The discipline map treats all non-satellite sources as one undifferentiated "textual"
  discipline, so genuinely independent textual source classes (think-tank analysis vs a curated
  registry/database) get same-class-halved instead of counted as two real independent looks.
- **Recommended fix:** Broaden the discipline map so distinct textual source classes count as distinct
  disciplines (or exempt cross-source-class textual pairs from the same-class halving), or adjust
  `min_independent_groups` / `same_class_weight`. These are DATA-C-tuned config knobs; the mechanism itself
  (independence weighting) is SCORE's and is sound — tune the knobs against oracle-want=confirmed entities
  like `mfr_taian`.
- **Severity:** minor (narrow impact: entities with exactly two textual-class looks).
- **Cross-service dependencies:** None — independent of the two masters, fixable now.

### SC-4 — Derived edges never computed: `supersedes`, `sustained-by`, contradiction unfed

- **Symptom:** `supersedes` and `sustained-by` emit **zero** edges; `contradicted` status never fires. The
  relocation supersede (`site_rahwali supersedes site_rawalpindi`) and the sustainment rollup never appear.
- **Evidence:**
  - Probe: `supersedes = 0`, `sustained-by = 0`, `contradicts = 0`, `corroborates = 0`; `contradicted` node
    count = 0.
  - `config/ontology.yaml:64` — `sustained-by` documented as "rollup only".
  - `config/ontology.yaml:74` — `supersedes` documented as structural/derived.
  - `backend/chanakya/credibility/status.py:94,110-115` — the contradiction gate correctly reads the
    `_CONTRADICTION` flag, but nothing sets it.
  - `backend/chanakya/view/pipeline.py:375,390-391` — the flag is meant to come from
    `el.attrs['contradiction']` / `opposing_claims`, which are never populated upstream.
  - `00-evidence-summary.md:176` — `supersedes`: 0 view edges.
- **Root cause:** `supersedes` and `sustained-by` are derived-by-design (not expected from single-doc
  extraction), but no service currently *synthesizes* them from the underlying claims — the relocation
  state-change beat that should mint a `supersedes` edge and demote the prior `based-at` to stale never
  runs, and no sustainment rollup is produced. Separately, the contradiction gate logic is sound but
  structurally unfed because `opposing_claims`/`contradiction` attrs are never populated by RESOLVE.
- **Recommended fix:** SCORE (with MONITOR, since relocation detection is a tripwire concern) should
  synthesize the derived edges: implement supersede-on-relocation (with a confidence floor to resist a
  spoofed single-claim relocation — the "d20 spoof" risk) and the `sustained-by` rollup. RESOLVE needs to
  populate `opposing_claims`/`contradiction` for the contradiction gate to ever fire.
- **Severity:** major.
- **Cross-service dependencies:** Depends on INGEST producing real structural relationship edges (fix-order
  item 4, ING-2 — no structural transforms today), RESOLVE fixing the edge/entity namespace split (fix-order
  item 6, RES-1) so the two Rahwali/Rawalpindi basing mentions unify into one entity pair first, and
  MONITOR's temporal-axis fix (fix-order item 11, MON-2) for the relocation tripwire itself. This SCORE
  work is the synthesis step that sits downstream of all three — don't start it until those land, or you'll
  be building the rollup logic against edges that don't exist yet.

## Reattributed away (not SCORE's fault — confirmed during investigation)

- **Status-skew-is-mostly-probable** → RESOLVE (RES-2, edge-namespace split / fragmentation). The
  confirmed/probable gate and credibility math are correct as-is; pooling merged claims through the
  UNCHANGED gate promotes `unit_paad`/`site_karachi`/`comp_tel_chassis` to confirmed once RESOLVE merges
  correctly. **Do not retune credibility** to compensate for fragmentation.
- **Known-gap nodes for missing entities** → INGEST (ING-4).
- **Materiality-starved inputs** (`substitutable-by`/`foreign_control`/`supplies-component` missing) →
  INGEST (ING-2) + DATA-C (DC-3). SCORE's materiality logic has nothing to compute over here.
- **Contradiction-gate-unfed** → INGEST (canonical `contradicts` edges, ING-2) + RESOLVE (`opposing_claims`
  population). The SCORE gate itself is sound (see SC-4).

## How to reproduce + verify your fix

```bash
export CHANAKYA_ROOT=/home/synaptic/data-science/research/rough/osint/wt-EVAL
/home/synaptic/data-science/research/rough/osint/wt-EVAL/backend/.venv/bin/python tmp/conv/eval-rca/rca_evidence.py
```

This regenerates the evidence bundle (`view_full.json`, `view_lens.json`, `00-evidence-summary.md`) under
`tmp/conv/eval-rca/`. After each fix, re-run and confirm the specific symptom is gone:

- **SC-1:** check `known_gaps` in `view_full.json` no longer contains `gap:chokepoint:*` entries keyed to
  variant/unit node types (`HQ-9/P`, `HQ-9B`, `HQ-9BE`, PAF squadrons, Army Air Defence Command); confirm
  `comp_ht233` (or its merged equivalent) is nominated instead.
- **SC-2:** check that at least one `based-at` claim/edge now carries a non-null half-life and that stale
  node count > 0 once INGEST's real `based-at` edges are present (full symptom needs ING-2 too — verify the
  config fix in isolation via a probe script computing `_half_life_days` for a bare `based-at` claim).
- **SC-3:** check `mfr_taian` (or oracle-equivalent) reaches `confirmed` status with two distinct textual
  source classes pooled, without inflating unrelated single-look entities to confirmed.
- **SC-4:** check `supersedes` and `sustained-by` edge counts in the view are no longer zero, and that a
  relocation scenario correctly demotes the prior `based-at` edge/site to stale (subject to a confidence
  floor, not fired by a single low-confidence claim).

Use `/tmp/probe_score3.py` and `/tmp/probe_score4.py` (chokepoint), and equivalent ad hoc probes for SC-2/3
(freshness_variant / effective_looks) as templates — they contain the exact repro logic used to confirm
these findings.
