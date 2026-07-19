# EVAL RCA handoff — RESOLVE (entity + place resolution)

## Context

The full pipeline (INGEST -> RESOLVE -> SCORE -> VIEW) was run end-to-end for the first time over real
extracted bundles, and the resulting graph diverges heavily from the oracle. This handoff is RESOLVE's
share of the fix. Evidence lives in `tmp/conv/eval-rca/00-evidence-summary.md` and the rebuilt view dump
`tmp/conv/eval-rca/view_full.json`; the generated claim bundles RESOLVE consumes are under
`corpus/scenarios/hq9p_primary/claims/`.

## TL;DR — fix in this order

1. **RES-1 (blocks-demo): edge/entity id-namespace split.** Entity nodes are keyed `ent:<type>:<name>`
   but edge subject/object stay as raw LLM strings — the two id spaces never touch. This is the single
   biggest defect in the whole pipeline: it mints 109 `unknown` twin nodes, zeroes `relational_score` /
   `source_asserted_score` for every candidate pair, starves the Phase-2 fixpoint, and disconnects the
   graph for lens/hop traversal. Fix this first — everything else in RESOLVE is unblocked or made
   meaningful by it.
2. **RES-2 (blocks-demo): band/weight geometry is unreachable.** Even strong attribute matches
   (name_sim 0.85-0.95) cap around 0.40-0.45, below `hitl_low` 0.55 — so the HITL merge queue is
   structurally empty (0 candidates across 26 docs) and near-duplicate entities never merge or even
   surface for review.
3. **RES-3 (major): `resolved_place_ref` is computed but never written back** — RESOLVE finds 3 valid
   place matches but they never reach the view, so the map/relocation/based-at machinery has nothing to
   bind to.

RES-4 and RES-5 are real but lower severity/secondary — see below.

## Findings (ordered by severity)

### RES-1 — Edge/entity id-namespace split (severity: blocks-demo)

**Symptom.** The rebuilt view has 294 nodes, of which 109 are `type='unknown'` — one per bare edge
endpoint that never resolved to a real entity. Real typed entity nodes carry ~0 incident edges (e.g.
`ent:variant:HQ-9/P` has 0 incident edges while the bare string `'HQ-9/P'` has 15). Fragmented surface
forms never collapse; the relational fixpoint fires 0 merges; lens/multi-hop traversal returns nothing
because the graph is disconnected.

**Evidence.**
- `backend/chanakya/resolve/entities.py:101-111` — `Edge` is built with `subject=p.subject` /
  `object=p.object`, i.e. the raw triple designator string, never an entity id.
- `backend/chanakya/resolve/entities.py:41-44,91` — entities are keyed `base_ref='ent:<type>:<name>'`.
- `backend/chanakya/schemas/stage_io.py:48` — `entity_canonical` is documented as "merged refs only";
  its keys are always `ent:type:name`, never bare surface names.
- `backend/chanakya/resolve/cluster.py:37` — a mention-only triple endpoint becomes its own union-find
  root and is never linked to an entity profile.
- `backend/chanakya/view/pipeline.py:245` (entity node id = `ent:{type}:{name}`) vs `:271,:274`
  (edge endpoint keyed via `to_canonical(bare subject)`) vs `:283-286` (fallback that mints an
  `unknown` node when `to_canonical` fails to find a match).
- Probe (`/tmp/probe_edges.py`): distinct edge endpoints = 109; endpoints that equal an existing entity
  id = 0; entities with >=1 incident edge = 0/190.
- `view_full.json`: 109 `unknown` nodes = exactly the 109 bare endpoints; edge-endpoint namespace split
  is `{(ent,ent): 2, (unk,unk): 99}`.
- Probe: `relational_score = 0` and `source_asserted_score = 0` for **all** candidate pairs;
  `entity_canonical` size = 5 (only `ent:->ent:` merge mappings, never bare-name->eid).
- `00-evidence-summary.md` lines 9-17 (`unknown:109` is the largest node class), lines 155-177
  (`equips`/`manufactures` edges never touch `ent:` nodes).

**Root cause.** RESOLVE never runs a mention-linking pass. It builds a clean entity graph (`ent:type:name`)
and a separate raw-edge graph (LLM subject/object strings) and has no step that maps the latter into the
former's id-space, except for the narrow case of already-merged cluster members.

**Recommended fix.** Add a mention -> canonical-node linking pass: for every triple subject/object,
resolve it to the entity whose normalized name/alias matches (reuse the existing `normalize()` +
`AliasIndex` / `_matching_eids` helper you already have), and populate `partition.entity_canonical` with
**bare-name -> canonical-id**, not just merged-cluster-member -> id. Then `view/pipeline.py`'s
`to_canonical` hook will attach edges to the real typed node instead of falling through to the
`unknown`-node fallback at `pipeline.py:283-286`.

**Severity.** blocks-demo — this is Master Defect A in the cross-service RCA; nothing downstream
(SCORE status correctness, lens/ASK traversal, MONITOR tripwires) works until this lands.

**Cross-service dependencies.**
- Depends on: INGEST's extraction-constraint fix (fewer/cleaner junk endpoints to link) and DATA-C's
  entity registry (canonical ids to link mentions against) landing first — see shared FIX ORDER items
  1-4.
- Unblocks: RES-2 (relational_score revives once edges connect, so band totals stop being
  attribute-only), RES-4, and everything downstream in ARCH (lens anchors), MONITOR (occupancy/relocation
  tripwires), and ASK (hero query traversal).

---

### RES-2 — Band/weight geometry makes attribute-only merges unreachable (severity: blocks-demo)

**Symptom.** Even near-identical surface forms never merge or even reach HITL. E.g. `'Pakistan Army Air
Defence (PAAD)'` vs `'Army Air Defence Command'` (attribute score 0.85-0.91) totals ~0.40-0.43; `HT-233`
vs `'HT-233 engagement radar'` totals ~0.33-0.355 — both below `hitl_low` 0.55. The HITL merge review
queue is **structurally empty**: 0 candidates surfaced across 26 documents. This is the direct cause of
the fragmentation and the "everything sits at probable, nothing merges to confirmed" symptom seen
elsewhere.

**Evidence.**
- `config/resolution.yaml:6-9` — weights: attribute 0.30, relational 0.40, temporal 0.15,
  source_asserted 0.15.
- `config/resolution.yaml:11-13` — bands: `auto_merge` >= 0.85, `hitl_low` >= 0.55.
- `backend/chanakya/resolve/scoring.py:150` — `total = sum(w * signal)`.
- `backend/chanakya/resolve/scoring.py:120-122` — `temporal_score(False) = 1.0` (a constant, not a real
  discriminator).
- `backend/chanakya/resolve/cluster.py:60-70` — `_band`: auto >= 0.85, hitl >= 0.55.
- Probe (`/tmp/probe_resolve.py`): TEL variants name_sim 0.946 -> total 0.434; PAAD-Command name_sim
  0.945 -> total 0.434 with `rel = 0.00`; live run: HT-233 pair total = 0.332/0.355; CASIC vs "China
  Aerospace..." total = 0.320; candidates surfaced = 0.
- Counterfactual (SCORE probe, confirms the fix would actually work): `unit_paad` pooled confidence
  0.965/0.991, eff_looks 3.5 -> CONFIRMED once merged; `site_karachi` conf 0.984 -> CONFIRMED;
  `comp_tel_chassis` conf 0.999 -> CONFIRMED through the UNCHANGED gate.
- `00-evidence-summary.md` lines 77-133 (`comp_ht233` FRAGMENTED-9, `unit_paad` FRAGMENTED-8,
  `comp_tel_chassis` FRAGMENTED-8, `site_karachi` FRAGMENTED-9).

**Note (correcting an earlier hypothesis):** the union-find/collapse mechanism itself **works** — 5
merges did collapse cleanly (FD-2000/HQ-9P/Hongqi-9/Triumph/ORIENT). The claim that "same-as is recorded
but never collapses" is false; the real problem is that scores simply never reach the collapse threshold.

**Root cause.** With relational dead (RES-1) and temporal a fixed 1.0 weighted at only 0.15, the
maximum score a strong attribute match alone can reach is `0.30*attribute + 0.15 = 0.45 < 0.55`. There is
also no containment/head-token/acronym-expansion bootstrap, so `'HT-233'` being a substring of `'HT-233
engagement radar'` is not treated as a high-precision identity signal.

**Recommended fix.** Rebalance the geometry so a strong attribute signal alone can reach HITL — raise
the attribute weight, lower `hitl_low`, and/or make temporal a genuine discriminator instead of a
constant. Additionally add a high-precision containment/head-token/acronym-expansion bootstrap within the
same type+namespace. `resolution.yaml` is DATA-C-tuned config, so coordinate the exact numbers with
DATA-C, and re-verify against the FT-2000/HQ-9BE and 4th-Academy/23rd-RI(BIRM) distinct-from traps so the
new geometry doesn't over-merge.

**Severity.** blocks-demo.

**Cross-service dependencies.**
- Depends on: RES-1 landing first — relational_score revives and will carry most legitimate merges once
  edges connect, changing what "just needs a geometry fix" vs "needs relational support" looks like.
- Unblocks: node-status correctness downstream in SCORE (pooling merged claims through the UNCHANGED
  gate is what promotes `unit_paad`/`site_karachi`/`comp_tel_chassis` to CONFIRMED).

---

### RES-3 — `resolved_place_ref` computed but never written back (severity: major)

**Symptom.** `resolved_place_ref` is empty on **all 294** view nodes, even though RESOLVE's own place
matcher computes 3 valid matches: Malir -> `pl_karachi_ad` (auto, 0m), Rahwali -> `pl_rahwali` (auto,
toponym match), Army AD Centre -> `pl_karachi_port` (HITL, proximity). The map view, the based-at
temporal rewind, and the relocation observable have nothing to bind to as a result.

**Evidence.**
- `backend/chanakya/resolve/places.py:113-126` — `_place_of` computes a `PlaceMatch.place_id`.
- `backend/chanakya/resolve/places.py:147-183` — `augment()` uses that `place_id` **only** to decide
  place-vs-place same-as/candidate merges; it is never persisted anywhere else.
- `backend/chanakya/resolve/__init__.py:107-118` — `_to_partition` returns no place field.
- `backend/chanakya/schemas/stage_io.py:39-48` — `Partition` has no place-ref channel at all.
- `backend/chanakya/schemas/values.py:158` — `Location.resolved_place_ref` is declared as "filled by
  RESOLVE," but a grep across `{resolve,view,materiality,credibility}` shows it is never assigned.
- Probe (`/tmp/probe_resolve.py`): `_place_of` resolves 3 sites, yet the view shows 0 nodes with
  `resolved_place_ref` set. Downstream, `backend/chanakya/observe/dsl.py:32` already reads
  `location.resolved_place_ref` — the reader exists and is waiting for a writer.
- `00-evidence-summary.md` lines 254-262 (`resolved_place_refs seen in view: {}`).

**Root cause.** There is no writer of `resolved_place_ref` anywhere in `resolve/` or `view/`. The
frozen coordinates themselves are readable fine (top-level `wgs84_lat`/`wgs84_lon` 24.9012/67.2034 parse
correctly at `places.py:47-54`) — the defect is purely the missing write-back of the computed match, not
a coordinate-shape problem.

**Recommended fix.** Persist each place-type entity's matched `place_id`: either add a place-ref map to
the `Partition`, or stamp `Location.resolved_place_ref` during `_apply_partition` so `rebuild()` attaches
it to the `NodeView`. `config/places.yaml` needs no change — this is purely a wiring fix inside RESOLVE.

**Severity.** major.

**Cross-service dependencies.** None upstream. Unblocks the map/relocation/based-at visualization and
observable logic (MONITOR, product/UX) once landed.

---

### RES-4 — Extracted identity assertions (same-as/distinct-from) are not consumed by RESOLVE (severity: major)

**Symptom.** 52 extracted `same-as` and 2 `distinct-from` identity assertions neither auto-merge nor
reach HITL. RESOLVE fired only 5 real merges total. The strongest explicit identity signal a document can
give ("X is also known as Y") is architecturally under-weighted relative to weaker statistical signals.

**Evidence.**
- `backend/chanakya/resolve/__init__.py:86-102` — `_llm_pairs` reads only `merge_proposal` decision
  records, never identity triples directly.
- `backend/chanakya/resolve/scoring.py:125-130` — `source_asserted_score` is binary 1.0/0.0.
- `backend/chanakya/resolve/scoring.py:148,150` — weighted at `w_s = 0.15`.
- `backend/chanakya/resolve/cluster.py:166-176` — Phase-1 bootstrap triggers are: shared_unique_id,
  alias_equivalent, or exact-name+namespace — there is no source-asserted-identity path.
- Corpus predicate histogram: `same-as` = 52, `distinct-from` = 2 — the two largest predicate classes in
  the corpus, effectively wasted.
- Probe on `view_full.json`: 42 `same-as` edges present, all 42 carry `claim_ids` (i.e. they are
  triple-derived, sitting as knowledge edges), 0 carry `merge_confidence`/`merge_band`
  (i.e. none of them ever reached RESOLVE's scoring machinery).

**Root cause.** Even with RES-1 fixed, `source_asserted (1.0) * 0.15 + attribute (<=0.30) <= 0.45 <
hitl_low 0.55` — so a source-asserted identity alone still cannot clear the bar under the current
geometry.

**Recommended fix.** Consume `same-as`/`distinct-from` assertions as raise-only merge/veto candidates
(gated on type/namespace compatibility, with `distinct-from` acting as a hard veto), and promote a
source-asserted identity into the Phase-1 bootstrap trigger set alongside alias-equivalence. This is
paired with an INGEST-side fix: identity assertions need to be routed out of the knowledge-edge lane and
into the merge-proposal decision channel that RESOLVE already reads (see shared FIX ORDER item 3,
"ING-6-identity-as-knowledge-triples").

**Severity.** major.

**Cross-service dependencies.**
- Depends on: INGEST routing identity out of the knowledge-edge lane (so RESOLVE has a clean channel to
  consume instead of scraping knowledge triples), and RES-1 (namespace fix) landing first.

---

### RES-5 — Place matching keys off raw display name with no place-type/precision gate (severity: minor)

**Symptom.** Only 3 basing-site entities match the gazetteer at all, and one is wrong: `'Army Air
Defence Centre'` snaps to `pl_karachi_port` — a port terminal — at 4478m via a proximity match (routed to
HITL, not auto-asserted, hence lower severity). Most sites match nothing.

**Evidence.**
- `backend/chanakya/resolve/places.py:57-62` — `_toponym_matches` uses the raw entity display name.
- `backend/chanakya/resolve/places.py:103-110` — `_location_of` uses `ent.name` directly as the
  toponym.
- `backend/chanakya/resolve/places.py:89-99` — the proximity path has no place-type/precision-class
  compatibility gate.
- Probe (`/tmp/probe_resolve.py`): `Army Air Defence Centre` -> `pl_karachi_port` (hitl, 4478m); a
  separate case — `'fenced compound near a PAF airbase'` — geocodes via Nominatim of `'central Punjab'`
  to lat 29.377/lon 71.699, which is a Bahawalpur mosque (an upstream INGEST geocoding-confidence issue,
  not RESOLVE's to fix, but it compounds this symptom).

**Root cause.** Two compounding issues: (1) RESOLVE has no clean toponym slot and instead matches on
the entity's full descriptive display name, and its proximity path has no place-type/precision-class
compatibility gate, so a military AD site can be pulled toward an unrelated port terminal; (2) upstream,
INGEST sometimes freezes a low-confidence geocode for a vague descriptive phrase, feeding garbage
coordinates into RESOLVE's proximity matcher.

**Recommended fix (RESOLVE side).** Match on a frozen toponym/candidate field rather than the raw
display name, and gate proximity matches on place-type/precision-class compatibility (don't let a
"basing site" match to a "port terminal" class place). The companion INGEST-side fix (flagging/fixing
low-confidence Nominatim geocodes) is out of RESOLVE's scope — flag it to INGEST if not already covered.

**Severity.** minor.

**Cross-service dependencies.** Depends on RES-3 (place-ref write-back) so that a corrected match
actually surfaces anywhere downstream.

---

## Reattributed away from RESOLVE (not this service's fix)

- **Lens anchor id mismatch:** even after the RES-1 namespace fix lands, node ids stay
  `ent:<type>:<name>`. The actionable fix for lens-anchor resolution lives in `view/lens.py` (resolve
  anchors via alias/registry), not in RESOLVE — RESOLVE only needs to expose a `_matching_eids`-style
  helper for ARCH to call. See shared FIX ORDER item 10 (ARCH).
- **"Eval matches by literal oracle id"** (a claim made by ARCH in the shared RCA) is **not** a real
  defect and is **not** RESOLVE's to carry as a scoring bug. `report.py` already matches by name/type
  overlap; the divergence it reports **is** this service's real fragmentation (RES-1/RES-2), not a
  reporting artifact.

## How to reproduce + verify your fix

```bash
export CHANAKYA_ROOT=/home/synaptic/data-science/research/rough/osint/wt-EVAL
/home/synaptic/data-science/research/rough/osint/wt-EVAL/backend/.venv/bin/python tmp/conv/eval-rca/rca_evidence.py
```

This regenerates the evidence bundle (`tmp/conv/eval-rca/00-evidence-summary.md`,
`tmp/conv/eval-rca/view_full.json`, `view_lens.json`) from the current code + the frozen bundles at
`corpus/scenarios/hq9p_primary/claims/`. Run it once before your change to confirm the baseline symptom,
then again after your fix, and check:

- **RES-1 fix verified when:** `unknown`-typed node count in `view_full.json` drops from 109 toward 0
  (or close to it, modulo genuinely un-linkable mentions), and probing `relational_score`/
  `source_asserted_score` for known pairs (e.g. `unit_paad` variants) shows non-zero values instead of
  the current uniform 0.
- **RES-2 fix verified when:** the HITL merge queue is non-empty (currently 0 candidates across 26 docs)
  and the specific pairs cited above (PAAD/Army Air Defence Command; HT-233/'HT-233 engagement radar')
  score above `hitl_low` (0.55) rather than 0.40-0.45.
- **RES-3 fix verified when:** `view_full.json` nodes of place-adjacent types carry a non-empty
  `resolved_place_ref` for the 3 known matches (Malir, Rahwali, Army AD Centre).
- **RES-4 fix verified when:** at least some of the 52 `same-as` edges carry `merge_confidence`/
  `merge_band` (i.e. they went through RESOLVE's scoring, not just survived as knowledge edges).
- **RES-5 fix verified when:** `Army Air Defence Centre` no longer proximity-matches `pl_karachi_port`
  (either matches nothing, or matches a compatible place-type/precision-class candidate).

Also re-check `00-evidence-summary.md`'s per-entity fragmentation counts (lines 77-133) for
`comp_ht233`, `unit_paad`, `comp_tel_chassis`, `site_karachi` — these FRAGMENTED-N counts should shrink
toward 1 as merges succeed.
