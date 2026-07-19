# EVAL RCA handoff — DATA-C (config + corpus + oracle)

## Context

The pipeline was run end-to-end for the first time over real extracted bundles, and the resulting
graph diverges heavily from the oracle (`answer_key.json`). This handoff is DATA-C's share of the
fix — the config/corpus/oracle-side root causes, separated from what belongs to RESOLVE, INGEST,
SCORE, ARCH, MONITOR, and ASK. Full evidence is in `tmp/conv/eval-rca/00-evidence-summary.md` and
`tmp/conv/eval-rca/view_full.json`; the generated per-doc claim bundles you'll be editing behavior
around live at `corpus/scenarios/hq9p_primary/claims/`.

## TL;DR

1. **Redesign the edge-type vocabulary** (`config/ontology.yaml`) — `equips`/`component-of` and
   `manufactures`/`supplies-component` collide with how the LLM extractor naturally reads text, so
   correctly-extracted facts land on the wrong edge name and every downstream consumer keyed to the
   right name sees nothing. This is joint with INGEST (who owns enforcement) but the vocabulary
   design itself is yours.
2. **Build a real entity canonical-id registry** — promote `config/resolution.yaml`'s `alias_table`
   (name→aliases, no id column) into a `{canonical_id, type, canonical_name, aliases[]}` registry
   mirroring `config/places.yaml`'s `place_id` pattern, and expand coverage far beyond the HQ-9
   variant family (HT-233 family, TEL/8x8 chassis, Taian, Pakistani formations).
3. **Seed materiality + lens inputs** — `foreign_control` node attrs, `substitutable-by` edges, and
   subject-lens anchors that are graph-resolvable (not literal oracle ids) — otherwise chokepoint
   confirmation and the subject lens stay permanently empty even after (1) and (2) land.

Note: do NOT retune credibility weights/thresholds — the "everywhere probable" status skew is a
RESOLVE fragmentation symptom, not a DATA-C credibility-config problem (see Findings below).

## Findings

### DC-1 — Edge vocabulary collides with natural language (blocks-demo)

**Symptom:** The hero relation `comp_ht233 --equips--> var_hq9p` never forms. `equips` fires 11x but
*always* as Variant→Unit or Unit→Variant (the oracle's `inducted-into` relation), the
Component→Variant hero instead lands on `component-of` (12x), and `supplies-component` fires **0**
times — the extractor consistently chose `manufactures` for Mfr→Component edges, including the
deep-tier Taian→chassis link.

**Evidence:**
- `config/ontology.yaml:59-63` — declares BOTH `equips` (Component→Variant) AND `component-of`
  (Component→Component), AND both `manufactures` AND `supplies-component`, with no disambiguating
  domain/range hints.
- `corpus/scenarios/hq9p_primary/claims/d21_techdata_authority.json` — "HT-233 phased-array
  engagement radar" `--component-of-->` "HQ-9/P" (should be `equips`).
- `corpus/scenarios/hq9p_primary/claims/d01_sipri_transfer.json` — "HQ-9/P" `--equips-->` "Pakistan
  Air Force"; `d06` — "the System" `--equips-->` squadrons (both should be `inducted-into`).
- `corpus/scenarios/hq9p_primary/claims/d24_tel_chassis_attribution.json` — "Taian..."
  `--manufactures-->` "heavy 8x8 special wheeled chassis"; chassis `--component-of-->` HQ-9 (should
  be `supplies-component`).
- Verified counts in the generated view: `equips` emitted 11x, all Variant↔Unit; `component-of`
  emitted 12x for Component→Variant; `supplies-component` = 0.
- `answer_key.json:179-218` — oracle convention: `equips` = Component→Variant, `supplies-component`
  = Mfr→Component.

**Root cause:** The vocabulary is self-overlapping and reads backwards from ordinary English. "The
system equips the force" reads naturally as Variant→Unit to an LLM, but DATA-C defined `equips` as
Component→Variant. `manufactures` and `supplies-component` are near-synonyms with no domain/range
constraint to force the deeper-tier choice.

**Recommended fix:** Jointly owned with INGEST (who must enforce via function-calling enum +
domain/range), but the vocabulary redesign itself is DATA-C's call. Two options to choose between
and record in DECISIONS.md:
- (a) Collapse `manufactures`/`supplies-component` into one edge with a tier attribute, and rename
  the Component→Variant edge to `component-of` (retire `equips`), using `inducted-into` for
  Variant→Unit. This matches how the LLM already reads the text.
- (b) Keep the current names but add a predicate-synonym normalization map applied at write time:
  `manufactures@Mfr→Component ⇒ supplies-component`, `component-of@Component→Variant ⇒ equips`,
  `equips@Variant→Unit ⇒ inducted-into`.

Verify whichever you pick against all six graded scenarios, not just the hero thread.

**Severity:** blocks-demo.

**Cross-service dependencies:** Must land before/with INGEST's extraction-constraint work (INGEST
step in fix order). Nothing in DATA-C depends on another service to start this — it's the most
foundational item.

---

### DC-2 — Entity registry / alias coverage missing canonical ids (blocks-demo)

**Symptom:** The pipeline mints name-derived `ent:<type>:<name>` ids that never equal the oracle's
canonical ids. Many real surface forms — the HT-233 radar family, TEL/8x8 chassis, Taian
(Wanshan), Pakistani formations (PAAD / Army Air Defence Command / PAF) — have zero or wrong alias
coverage, so RESOLVE can't even propose them as merge candidates, and there is no stable anchor for
lenses/observables to target.

**Evidence:**
- `config/resolution.yaml:20-49` — `alias_table` covers only the HQ-9 variant family, two design
  authorities, and S-400; it has no id column at all (canonical NAME → [alias names], not
  canonical_id → aliases); the manufacturer canonical is written as "CASIC Second Academy" while
  the oracle uses "CASIC" (`mfr_casic`).
- `config/places.yaml` — the intended pattern: every place already has a `place_id` (e.g.
  `pl_nurkhan`) plus aliases. Entities have no equivalent.
- `answer_key.json:2-56,113-125` — oracle canonical ids: `mfr_casic`, `comp_ht233`,
  `comp_tel_chassis`, `mfr_taian`, `unit_paad`, `unit_hq9b`.
- `tmp/conv/eval-rca/00-evidence-summary.md` lines 77-108 (HT-233 shows up as 9 different name
  variants with no shared id), lines 98-100 (Taian 2-way split), lines 125-133 (`unit_paad`
  8-way split, incorrectly co-listing PAF entries that should be a separate unit).

**Root cause:** No name→canonical-id registry exists for entities (unlike places), so RESOLVE has
no stable merge target and invents a fresh id per surface string it sees.

**Recommended fix:** Promote `alias_table` into a canonical-entity registry:
`{canonical_id (== oracle id), type, canonical_name, aliases[]}`, mirroring `places.yaml`. Expand
coverage to:
- HT-233 family (all radar-name variants)
- TEL / 8x8 chassis (normalize "8x8" spelling variants)
- Taian (Wanshan)
- Pakistani formations — PAAD / Pakistan Army Air Defence Command / Army Air Defence Command as
  one canonical unit (`unit_paad`), kept **separate** from PAF / "Pakistan Air Force"
  (`unit_hq9b` — do not co-merge these two, they are the oracle's intended distinct-from trap
  alongside FT-2000 / HQ-9BE / 4th-Academy / 23rd-RI(BIRM), which must also stay distinct).

Note: alias-equivalence triggers a Phase-1 bootstrap merge that bypasses RESOLVE's confidence bands,
so this registry pays off even before RESOLVE's band recalibration lands — but the full effect
(all merges, not just alias-exact ones) needs RESOLVE's RES-1/RES-2 fixes too. Also record in
DECISIONS.md whether canonical-id-exact-match or attribute-similarity-match is the graded contract
for the eval — this determines how strict the registry needs to be.

**Severity:** blocks-demo.

**Cross-service dependencies:** Needs ARCH to ratify the registry as a contract-level decision
(fix-order step 1). Unblocks RESOLVE's endpoint-linking pass (RES-1) and Phase-1 bootstrap
promotion (RES-2), which is the "master fix" for the id-namespace split described below.

---

### DC-3 — Materiality confirmation inputs not seeded (major)

**Symptom:** No node is ever CONFIRMED as a chokepoint (`chokepoint_count = 0` across all 294
nodes). The real single point of failure, `comp_ht233`, is never surfaced as confirmed even though
it should be.

**Evidence:**
- Probe of the generated view: `substitutable-by` edges = 0 (so `substitutability` = UNKNOWN on
  every node), `supplies-component` = 0, `exported-by` = 0; nodes carrying a `foreign_control`
  attr = 0; `chokepoint_count` histogram = `{0: 294}`; `substitutability_state` histogram =
  `{UNKNOWN: 294}`.
- `backend/chanakya/materiality/precompute.py:52-74` (`_substitutability`: no `substitutable-by`
  edge → UNKNOWN), `:46-49` (`_foreign_control_backed` reads `node.attrs['foreign_control']` — an
  absent attr is a silent no-op, not a bug in SCORE's code), `:113-121` (CONFIRMED chokepoint status
  requires `SOLE_SOURCE` or evidence-backed `foreign_control`).

**Root cause:** SCORE's materiality precompute logic is correct and already computes
`chokepoint_status` on every node (HT-233 fragment lands as `candidate`) — but all three of its
confirming inputs are absent from the corpus/config layer: no `substitutable-by` edges are seeded,
no node carries a `foreign_control` attribute, and (separately, INGEST-owned) no
`supplies-component`/`exported-by` edges are extracted.

**Recommended fix:** DATA-C-owned parts: populate `foreign_control` attrs on the relevant
component/manufacturer nodes from the corpus narrative, and seed `substitutable-by` edges where the
corpus supports a substitution claim (e.g. alternate suppliers). Do not touch SCORE's precompute
code — it already does the right thing once these inputs exist.

**Severity:** major.

**Cross-service dependencies:** Depends on INGEST's structural-transform work (ING-2, emitting
`supplies-component`/`exported-by`) landing in parallel/first for full effect. Unblocks SCORE's
existing materiality code to confirm `comp_ht233` with no SCORE code changes needed.

---

### DC-4 — Subject-lens anchors unmintable (blocks-demo)

**Symptom:** The subject lens `lens-hq9p-pk` returns 0 nodes / 0 edges. Its anchors, `unit_paad`
and `site_karachi`, don't exist anywhere in the generated view.

**Evidence:**
- `config/subjects.yaml:7-10` — anchors specified as literal oracle ids `unit_paad`, `site_karachi`.
- `tmp/conv/eval-rca/00-evidence-summary.md:5` — lens returns 0 nodes; `view_lens.json` is empty.
- `view_full.json` — every entity is minted as `ent:<type>:<name>`; no node anywhere has id
  `unit_paad` or `site_karachi`.

**Root cause:** `subjects.yaml` anchors were hand-written using the oracle's canonical ids, but the
live pipeline only ever mints name-derived `ent:<type>:<name>` ids (see DC-2) — so the anchor lookup
seeds against ids that will never exist unless the registry (DC-2) is adopted and RESOLVE elects
those ids, or the lens itself resolves anchors by alias instead of literal id (ARCH's AR-2, not
yours to fix, but you must coordinate the anchor spec format with them).

**Recommended fix:** Either (a) specify anchors in `subjects.yaml` as graph-resolvable descriptors
(type + alias/name) that ARCH's lens code resolves through the alias index rather than literal id
match, or (b) rely on the DC-2 registry so the graph mints `unit_paad`/`site_karachi` directly. (a)
and (b) are not mutually exclusive — the registry helps regardless, but the lens spec format is a
joint decision with ARCH (AR-2).

**Severity:** blocks-demo.

**Cross-service dependencies:** Depends on DC-2 (registry) and ARCH's AR-2 (lens resolves anchors
via alias instead of literal id match). Do not attempt to fix by hardcoding a different literal id
in `subjects.yaml` — that just moves the fragility, it doesn't resolve it.

---

## Reattributed away (not DATA-C's root cause, noted so you don't duplicate work)

- **Merges fire but don't collapse nodes** → RESOLVE (RES-2). The union-find/collapse mechanism
  already works; the real blocker is unreachable merge confidence bands plus the id-namespace split
  (see Cross-Service Master A below), not a missing collapse step.
- **"Everywhere probable" status skew** → RESOLVE (RES-2), not `config/credibility.yaml`. Do
  **not** retune credibility weights/thresholds to fix this — it is a fragmentation symptom (many
  tiny unmerged claim clusters, each too small to corroborate itself past PROBABLE). Retuning
  credibility would mask the real defect and likely miscalibrate the confirmed/probable boundary
  for the demo. The `gated_attrs` suppression worry (that an absent `foreign_control`/`readiness`
  attr silently suppresses a status flag) was investigated and is a non-issue — an absent attr adds
  no flag, it's a no-op, not a corruption.
- **`supersedes`/`sustained-by` are computed, not extracted** → SCORE/MONITOR (SC-4/MON-2). These
  are derived-by-design roll-up edges the derived layer must synthesize from `based-at` inputs (an
  INGEST responsibility to emit first); DATA-C does not need to seed them directly in the corpus.

## Cross-service context (why this looks worse than any single finding)

Two upstream master defects explain most of the divergence; DATA-C's findings above are necessary
but not sufficient conditions for the fix:

- **Master A (RESOLVE id-namespace split):** triple endpoints are kept as bare LLM surface strings
  while entity nodes are keyed `ent:<type>:<name>`, and `entity_canonical` is populated only for
  already-merged clusters — so the edge graph and entity graph are two disjoint id sets (0/109 edge
  endpoints match an entity id; 0/190 entities carry an incident edge). DC-2's registry is the input
  RESOLVE needs to close this gap, but RESOLVE's own endpoint-linking pass (RES-1) is the master fix.
- **Master B (extraction contract gaps):** INGEST emits denials/identity claims as free-text
  knowledge triples and has no deterministic transform for supply-chain/ORBAT edges — and DATA-C's
  colliding edge vocabulary (DC-1) means even correctly-extracted facts land on the wrong valid edge
  name. DC-1 is DATA-C's share of Master B.

Practically: DC-1 and DC-2 should land early (they're inputs everyone downstream needs), DC-3 can
land in parallel with INGEST's structural-transform work, and DC-4 needs both DC-2 and ARCH's AR-2
before it can be verified end-to-end.

## How to reproduce + verify your fix

```bash
export CHANAKYA_ROOT=/home/synaptic/data-science/research/rough/osint/wt-EVAL
/home/synaptic/data-science/research/rough/osint/wt-EVAL/backend/.venv/bin/python tmp/conv/eval-rca/rca_evidence.py
```

This regenerates `tmp/conv/eval-rca/view_full.json`, `view_lens.json`, and
`00-evidence-summary.md`. After each fix, re-run and confirm the specific symptom is gone, e.g.:

- **DC-1:** `supplies-component` edge count > 0 and includes Mfr→Component pairs (incl.
  Taian→chassis); the Component→Variant hero edge (`comp_ht233`→`var_hq9p`) exists on whichever
  edge name you settled on; `equips` (or its replacement) is never Variant→Unit.
- **DC-2:** grep the regenerated `view_full.json` for `unit_paad`, `comp_ht233`, `comp_tel_chassis`,
  `mfr_taian` as literal node ids (not `ent:*` strings) — after RESOLVE's endpoint-linking also
  lands, these should appear as canonical ids with incident edges.
- **DC-3:** re-check `chokepoint_count` histogram — `comp_ht233` should show as `candidate` moving
  toward `CONFIRMED` once `foreign_control` attrs and `substitutable-by` edges are present, and
  `substitutability_state` histogram should no longer be 100% UNKNOWN.
- **DC-4:** `view_lens.json` for `lens-hq9p-pk` should be non-empty (after DC-2 + ARCH's AR-2 also
  land — a DATA-C-only fix will not fully clear this one; verify anchors resolve at least via the
  alias index).
