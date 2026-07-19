# EVAL RCA handoff — INGEST (extraction)

## Context

The pipeline was run end-to-end for the first time over real extracted bundles, and the resulting graph
diverges sharply from the oracle (`answer_key.json`). A root-cause investigation was done across all
services; this handoff is INGEST's share of the fix. Evidence: `tmp/conv/eval-rca/00-evidence-summary.md`
and `tmp/conv/eval-rca/view_full.json`, probed against the generated claim bundles at
`corpus/scenarios/hq9p_primary/claims/*.json`.

**Reattributed away from INGEST (don't fix these here):** component surface-form fragmentation
(comp_ht233→9 nodes, comp_tel_chassis→8) is RESOLVE under-merge, not INGEST over-generation — emitting one
node per stated surface form is correct extract-raw behaviour; `type='unknown'` default is minted in
`view/pipeline.py:286`, not by extraction, and is a symptom of RESOLVE's id-namespace split; empty
`resolved_place_ref` is by design at INGEST (freezes raw coords) — RESOLVE never writes the resolved id back.

## TL;DR

1. **Hard-constrain relation extraction to the ontology edge enum** and stop letting the denial/negation
   lane mint free-text knowledge edges + junk "unknown" endpoint nodes (ING-1).
2. **Add deterministic structural transforms** for supply-chain and ORBAT/basing edges — right now almost
   none of `supplies-component` / `exported-by` / `sustained-by` / `imported-by` / `based-at` /
   `supersedes` are ever emitted (ING-2). This is a **blocks-demo** severity finding.
3. **Stop emitting `same-as`/`distinct-from` as knowledge triples** — route them to the merge-proposal
   channel RESOLVE actually consumes (ING-6). This single bug fabricated 42 phantom edges and made an
   earlier evidence pass falsely report dozens of "fired" merge decisions.

Also blocks-demo: **ING-7**, uniform frozen-seed dates collapse every `as_of` rewind to an empty graph.

## Findings

### ING-2 — No structural transform for relationship edges/nodes (severity: blocks-demo)

**Symptom:** Canonical supply-chain edges `supplies-component`, `exported-by`, `sustained-by` are emitted
**zero** times; `contract_import_event` appears only once (from the tender doc, not the customs import);
`interceptor_stockpile` and `techdata_authority` are declared node types that are never instantiated.
ORBAT/basing edges are hit-or-miss: `based-at`=1 (and wrong — see below), `inducted-into`=1,
`imported-by`=2, `supersedes`=0. Oracle nodes/edges `import_2021`, `sustain_spares`, `sustain_techdata`,
unit basing, and the relocation supersede-edge are all missing from the built graph as a result.

**Evidence:**
- `backend/chanakya/ingest/extract.py:757,778,909,972` — grep of `em.entity`/`em.triple` calls shows
  `same-as` is the only relation ever hardcoded; nothing structurally emits the others.
- `NodeTypeName` declares `interceptor_stockpile`/`techdata_authority` (extract.py:75-78) but no transform
  ever calls `em.entity()` for them.
- `extract.py:879-932` — customs transform mints manufacturer entities + a `TransferEvent`, never a
  `contract_import_event` node nor `exported-by`/`imported-by` edges.
- `extract.py:935-999` — tender transform mints `contract_import_event` + line-items but no
  `sustained-by`/stockpile/authority.
- `extract.py:1060-1071` — imagery transform mints a `SightingEvent`, never a `unit->site based-at` edge.
- `extract.py:821-844` — `_emit_event` produces `InductionEvent`/`TransferEvent`, never the corresponding
  `inducted-into`/`imported-by` edge.
- Probe on `d05_customs_manifest.json`: 3 events / 6 entities / 2 triples, all events typed `TransferEvent`
  — no supply edge at all.
- The one `based-at` triple in the whole corpus is `d22`: "BIRM -> Yongding Road" (a manufacturer's street
  address, not a unit basing fact). The actual relocation is phrased as `d20` "it --leaving--> Rahwali
  airbase" and `d12` "--turned into--> fertilizer plant fire" — both fall off-ontology into free text
  instead of a structural edge.
- `config/ontology.yaml:58-65` (intended endpoints), `:64` (`sustained-by` documented as "rollup only"),
  `:74` (`supersedes` documented as structural/derived).
- `00-evidence-summary.md` lines 19-49, 162-177 (edge histogram).

**Root cause:** Every relationship edge except `same-as` is representation-dependent on the LLM
voluntarily filling the free `RelationMention.relation` enum field correctly — there is no deterministic
transform path from a customs/tender/imagery/occupancy document to the specific edge the oracle grades.
Facts instead get structurally captured as **events** (`TransferEvent`/`InductionEvent`/`SightingEvent`,
79 total) rather than projected onward into the edges. This is an event-vs-node/edge representation gap,
compounded by relocation/supply language landing in the negation/free-text lane instead of a positive
typed relation.

**Recommended fix:** Add explicit structural transforms:
- customs → mint a `contract_import_event` node + `exported-by` (shipper/OEM) and `imported-by`
  (consignee) edges;
- tender/sustainment → mint `interceptor_stockpile`/`techdata_authority` nodes + `sustained-by` edges;
- stated Mfr→Component statements → `supplies-component`;
- occupancy/imagery → `unit->site based-at` edge (+ feed `supersedes` inputs);
- ensure supersede/supply statements extract as positive typed relations, not swallowed by the
  negation/free-text lane.
Note: linking `import_2021` to `unit_paad` (the end-user) is RESOLVE's job, not INGEST's — INGEST should
only emit `imported-by -> shell-consignee`.

**Cross-service dependencies:** Needs the DATA-C edge-vocabulary redesign first (edge names currently
collide with natural language, e.g. hero Component→Variant should land on `equips` not `component-of`;
Mfr→Component should land on `supplies-component` not `manufactures`) so facts land on the *right* edge
name once the transform exists. This finding is fix-order item 3 and is a listed FOUNDATION-dependency
input that RESOLVE's endpoint-linking (fix-order item 6) and SCORE's materiality/status work need.

---

### ING-1 — Denial lane + unconstrained predicates mint junk edges/nodes (severity: major)

**Symptom:** ~22 ad-hoc, free-text edge predicates appear in the view (`'issued a formal press release
confirming'`, `'has not acknowledged'`, `'was unable to locate'`, `'cannot be established from open
sources'`, `'makes it (confused for manufacturer)'`), plus ~34 pure-junk `'unknown'`-typed endpoint nodes
(`'This desk'`, `'it'`, `'Chinese state media'`, `'October induction date'`, `'Sargodha strike'`).

**Evidence:**
- `backend/chanakya/ingest/extract.py:206-212` — `DenialMention.predicate` is typed as free `str|None`,
  unlike `RelationMention.relation:189-195` which is typed `EdgeTypeName|None` (the ontology enum).
- `extract.py:812-816` (`transform_prose_claim` emits denials via `em.triple()`), `:1031-1035`
  (`transform_social_post` negations, same path) — both flow denial predicates straight into the knowledge
  graph as if they were ordinary relations.
- `extract.py:685-692` — `_offontology` only **flags** off-vocabulary edge types in tier-3 attrs; it never
  rejects or remaps them.
- `backend/chanakya/view/pipeline.py:286` — any undeclared endpoint string is minted as a `type='unknown'`
  node; no downstream RESOLVE fix can rescue these because they're not real entity mentions.
- Probe: **all 22** ad-hoc-predicate triples are `polarity=negative`; **0** positive triples carry an
  ad-hoc predicate. 34-40 distinct junk endpoint strings appear **only** on negative triples.
- `00-evidence-summary.md` lines 27-49 (ad-hoc edge histogram), 155-177 (1:1 map to denial examples).

**Root cause:** The negation lanes (`DenialMention.predicate` in prose docs, `PostMention.negations` in
social posts) carry unconstrained free-text predicates, and the transforms emit each straight through
`em.triple()` as a real relationship edge. The LLM's natural-language verb phrases (and their arbitrary
free-text subjects/objects) flow unfiltered into the view, where `pipeline.py:286` mints "unknown" nodes
for the endpoints.

**Recommended fix:** Hard-constrain relationship extraction to the ontology edge enum via function-calling
enum (not soft/flagging guidance) + post-hoc canonicalization. Model a denial as a typed negative
sufficiency observation feeding SCORE's insufficient-evidence machinery (or a small fixed
`contradicts`/`absence` vocabulary) — never as a free-standing subject→object edge. Never mint nodes from
denial endpoints.

**Cross-service dependencies:** Needs the DATA-C edge-type vocabulary redesign (fix-order item 1) to supply
the enum + domain/range to constrain against. This is one of the two upstream master defects
(Master B: extraction contract gaps) that everything downstream — RESOLVE fragmentation, SCORE
status, ASK traversal — inherits.

---

### ING-6 — Identity assertions (same-as/distinct-from) emitted as knowledge triples (severity: major)

**Symptom:** 52 `same-as` + 2 `distinct-from` identity assertions are rendered as 42 phantom "same-as"
**knowledge edges** in the view, whose raw-string endpoints each mint an `'unknown'` node. INGEST's
strongest alias signal is simultaneously polluting the graph (as fake edges) and being discarded as
merge evidence (RESOLVE doesn't consume triples). This was the single most misleading artifact in the RCA
— it made an earlier evidence pass report dozens of "fired" merge decisions when the resolver actually
fired only 5.

**Evidence:**
- `corpus/scenarios/hq9p_primary/claims/*.json`: `same-as`=52, `distinct-from`=2 (raw extraction output).
- `backend/chanakya/resolve/__init__.py:86-102` — RESOLVE ingests merge proposals only from
  `merge_proposal` decision records, never from triples.
- `backend/chanakya/view/pipeline.py:278-279` — `build_instance_edges` renders **every** predicate
  including `same-as` as an ordinary knowledge edge.
- `view_full.json` probe: 42 `same-as` edges, all triple-derived (`claim_ids` set, `merge_confidence` is
  null — i.e. never actually a resolver decision).
- `00-evidence-summary.md` lines 179-226 (the mislabeled "decisions that FIRED" list, which was generated
  from view `same-as`/`distinct-from` edges, not from real resolver decisions).

**Root cause:** INGEST extracts resolution relations as ordinary knowledge triples
(`predicate='same-as'`/`'distinct-from'`) that flow through `_assemble` as graph edges, instead of routing
them to the merge-proposal decision channel RESOLVE consumes.

**Recommended fix:** Route identity assertions to `merge_proposal` DecisionRecords (RESOLVE's raise-only
proposer channel); never emit them as view edges.

**Cross-service dependencies:** Pairs directly with RESOLVE's consumption side (fix-order item 7 — "consume
the extracted same-as/distinct-from as raise-only merge/veto candidates and promote source-asserted
identity into Phase-1 bootstrap"). No DATA-C/ontology dependency; independent of ING-1/ING-2's
vocabulary-redesign dependency and can be fixed immediately.

---

### ING-7 — Uniform frozen-seed dates break temporal rewind (severity: blocks-demo)

**Symptom:** `based-at@2021` rewind returns `[]`, and the **entire view** rewinds to 0 nodes / 0 edges at
`as_of=2021-12-31` — the relocation observable has no "before" state to diff against.

**Evidence:**
- Probe: distinct claim availability ISO dates = `Counter({'2026-07-19': 452})` (all 452 claims); claims
  available by `2021-12-31` = 0; `VIEW@2021` nodes=0, edges=0; claims with `report_time` set = 0.
- `corpus/scenarios/hq9p_primary/claims/d22_deep_tier_supplier.json` — `ingest_time.iso='2026-07-19'`,
  `raw='frozen-seed-baseline'`, `report_time=None` (representative of all 452 claims).
- `backend/chanakya/timeref.py:34-38` — `claim_available_iso` prefers `ingest_time` **before**
  `report_time`.
- `backend/chanakya/view/pipeline.py:338-339` — `as_of` rewind filters via `is_available_by`, which uses
  the above precedence.
- `00-evidence-summary.md` lines 250-252.

**Root cause:** All 452 claims carry the identical frozen-seed `ingest_time` (`2026-07-19`,
`raw='frozen-seed-baseline'`) with `report_time` null. Because `claim_available_iso` consults `ingest_time`
first, every claim is hidden for any past `as_of` regardless of when the underlying document was actually
reported. **Note:** stamping only `report_time` will not fix this on its own, since `ingest_time` (still
`2026-07-19`) is consulted first — either the seed dates themselves need to carry real per-doc values, or
the precedence in `claim_available_iso` needs to change.

**Recommended fix:** Stamp each claim's real per-doc `report_time` **and** `ingest_time` (and `event_time`
for sightings) so a past `as_of` can rewind meaningfully.

**Cross-service dependencies:** Needs DATA-C to supply real per-doc corpus dates (fix-order item 5). Even
after this is fixed, MONITOR's relocation tripwire has a separate, independent defect (MON-2): it currently
does a transaction-time rewind of what is fundamentally a valid-time relocation — that axis mismatch must
still be fixed in MONITOR regardless of date-stamping.

---

### ING-8 — Imagery VLM lane never ran (severity: major)

**Symptom:** The subject-blind VLM shape-observation lane and the cited attribution inference "D" never
appear anywhere in the extracted claims; no claim anywhere has `extraction.method='vlm'`; a downstream
"attribute --record" step proposed 0 links, all logged as "no-vlm-shape-observation".

**Evidence:**
- Probe: every claim's `doc_ref.file` is `.txt` (only `d25` is `.pdf`); `docs/` on disk contains 9 `.png`
  files (`d07, d08, d10, d11, d12, d13, d17, d17b, d18`); every claim's `extraction.method='llm'`,
  `version='gemini-flash-latest'` — zero claims with `method='vlm'`.
- `backend/chanakya/ingest/seed.py:113-141` — `_extract_source` dispatches on a **single** citation's file
  extension (`.png` → VLM lane, else → text lane) and never co-loads a sibling image alongside a `.txt`
  citation, so `read_image_document` never runs for the GEOINT docs that have a paired `.png`.
- `backend/chanakya/ingest/lane.py:73-75,184-185` — the **live** (keyed) lane already supports co-located
  images via `DocInput.images`; the VLM machinery itself is present and correct, it's just never exercised
  because the seed path doesn't populate `images`.
- `config/sources.yaml:21-35` — imagery docs are cited with `citation_url=*.txt` only, no image-artifact
  pointer.
- `answer_key.json:556-583` — attribution inference D requires the `d18` `.png` as premise A.

**Root cause:** The frozen seed bundles were recorded from `.txt` citations only. The 9 `.png` frames sit
on disk uncited, and `seed._extract_source` has no mechanism to discover and co-load a sibling image next
to a GEOINT `.txt` citation.

**Recommended fix:** Two independent angles, either unblocks this:
- **DATA-C side:** cite the `.png` in `sources.yaml` / add an explicit image-artifact pointer so the `.png`
  lane is discoverable at all.
- **INGEST side:** have `seed._extract_source` co-load the sibling `.png` beside a GEOINT `.txt` into
  `DocInput.images`, mirroring what the live lane already does (the design principle here is
  KEYLESS==LIVE — the seeded path should exercise the same code paths as the real one).
Once either lands, `attribute --record` will actually have VLM shape observations to link against.

**Cross-service dependencies:** Needs DATA-C to add the image-artifact pointer (or INGEST can work around
it via co-load, per above) — listed as shared with DATA-C in fix-order context, not a blocking dependency
either direction.

---

### ING-3 — Shell trading companies typed as `manufacturer` (severity: minor)

**Symptom:** 17 `manufacturer` nodes include several shell trading/freight companies (`ORIENT ELECTRO
TRADING`, `SINO-GALAXY IMP/EXP`) that are not manufacturers — padding and mis-classifying the manufacturer
set, and giving the shell consignee/shipper the same node type as the real OEM (CASIC).

**Evidence:**
- `backend/chanakya/ingest/extract.py:898-909` — both the customs `consignee` and `shipper` are typed via
  `em.entity('manufacturer', ...)`, merely stamping `role=consignee`/`shipper` in attrs.
- Probe on `d05_customs_manifest.json`: 5 `manufacturer`-typed entities, all with `role=consignee|shipper`
  (`ORIENT ELECTRO TRADING`, `SINO-GALAXY` variants).
- `00-evidence-summary.md:211,218` — shell orgs appear in `same-as` fires typed as manufacturers.

**Root cause:** `transform_customs_gd_bol` has no generic org/trading-company node type to reach for, so it
types every customs party as `manufacturer`, depriving the resolver's shell→end-user reasoning of a clean
starting type.

**Recommended fix:** Introduce a trading-org/intermediary node type and type customs consignee/shipper
accordingly, reserving `manufacturer` for actual OEMs.

**Cross-service dependencies:** Needs DATA-C to add the org/trading-company type to the ontology first.

---

### ING-4 — `known_gap` entities minted per full sentence (severity: minor)

**Symptom:** 14 `known_gap` ENTITY nodes are minted from imagery caveats, each keyed by the full verbose
sentence (`'Cloud cover ~15%'`, `'No SAR pass...'`, `'Collection over the primary AOI on 10 May was
severely degraded...'`) so they never merge with each other or with anything; the oracle expects only two:
`gap_ht233_maker` and `gap_launcher_count`.

**Evidence:**
- `backend/chanakya/ingest/extract.py:1087-1096` — `em.entity('known_gap', desc)` uses the whole
  `GapMention.description` string as the node name/key.
- Probe: 14 claims carry `payload.entity_type=known_gap` (INGEST-extracted) — distinct from SCORE's own
  `gap:*` ids in `view.known_gaps` (`view/pipeline.py:428-438`; `materiality/precompute.py:150-164`).
- `00-evidence-summary.md` lines 51-65 (the 14 verbose nodes); `answer_key.json` oracle has only the two
  gaps above.

**Root cause:** Collection gaps are fundamentally a sufficiency/coverage signal, not an order-of-battle
entity. Keying by the raw sentence guarantees no two mentions of "the same" gap ever normalize to one node,
and SCORE's sufficiency machinery (which produces the correctly-shaped `gap:*` ids) is left unfed by these.

**Recommended fix:** Emit gaps as sufficiency/coverage observations feeding SCORE's insufficient-evidence
templates, attached to the site/slot they concern (e.g. a launcher-count caveat should feed a
based-at/observation assertion's `check()` so it yields `gap_launcher_count`). If a `known_gap` node is
kept at all, key it by the normalized missing-slot name, not the raw sentence.

**Cross-service dependencies:** None — independently fixable.

---

### ING-5 — Tender line-items minted as first-class component nodes (severity: minor)

**Symptom:** Descriptive spare-part line-items become standalone component nodes (e.g. `'Ground support
vehicle spares for erector-launcher chassis'`, `'Battery/charging modules for engagement radar cabin'`,
`'Calibration/test jigs for missile round check-out'`), inflating the 45-component set with one-off
descriptive strings.

**Evidence:**
- `backend/chanakya/ingest/extract.py:981-989` — the tender transform emits one component entity per line
  item, keyed by its raw descriptive string.
- `d06_spares_tender.json` probe (line-item node list); `00-evidence-summary.md` lines 77-108.

**Root cause:** Same mechanism as ING-4 (raw-string keying), scoped to tender line items. Note: the
larger `comp_ht233→9` / `comp_tel_chassis→8` fragmentation seen in the view is **RESOLVE under-merge**
(not this bug) — this finding is only the narrow sub-part where INGEST itself creates descriptive,
non-canonical line-item nodes that shouldn't be standalone components at all.

**Recommended fix:** Treat descriptive spare-part line items as tier-2 attributes on the parent system
rather than standalone nodes, and/or emit a `component_class`/canonical-name hint so RESOLVE can cluster
surface forms more easily.

**Cross-service dependencies:** None blocking, but pairs conceptually with RESOLVE's under-merge fix
(fix-order item 7) for the broader component-fragmentation picture.

## How to reproduce + verify your fix

```bash
export CHANAKYA_ROOT=/home/synaptic/data-science/research/rough/osint/wt-EVAL
cd /home/synaptic/data-science/research/rough/osint/wt-EVAL

# Re-run extraction / regenerate claim bundles as needed for your change, then:
/home/synaptic/data-science/research/rough/osint/wt-EVAL/backend/.venv/bin/python tmp/conv/eval-rca/rca_evidence.py
```

`tmp/conv/eval-rca/rca_evidence.py` regenerates the evidence bundle (`tmp/conv/eval-rca/00-evidence-summary.md`,
`view_full.json`, `view_lens.json`) from the current corpus + code. After each fix, re-run it and confirm
the specific symptom is gone, e.g.:

- **ING-1:** ad-hoc-predicate edge count in the histogram (00-evidence-summary.md lines 27-49) should drop
  to 0, and the ~34 junk `'unknown'`-typed endpoint nodes sourced from denial/negation text should
  disappear from `view_full.json`.
- **ING-2:** `supplies-component`/`exported-by`/`sustained-by` counts in the edge histogram should become
  nonzero; a `contract_import_event` node should appear with `exported-by`/`imported-by` edges sourced from
  the customs doc (not just the tender); a `unit->site based-at` edge should appear from the occupancy doc.
- **ING-6:** the `same-as`/`distinct-from` edge count in `view_full.json` should drop to 0 (they should
  instead appear only as `merge_proposal` decision records, which RESOLVE — not this bundle — consumes).
- **ING-7:** re-run the availability probe; distinct claim availability ISO dates should no longer collapse
  to a single `2026-07-19` value, and `VIEW@2021-12-31` should have nonzero nodes/edges for facts genuinely
  known by then.
- **ING-8:** claims extracted from the imagery docs with a paired `.png` should show
  `extraction.method='vlm'` instead of `'llm'`.
- **ING-3 / ING-4 / ING-5:** re-check node-type histograms for `manufacturer` (should drop the
  shell-trader entries), `known_gap` (should collapse to ≤2 canonical gap ids), and component counts from
  tender line items.
