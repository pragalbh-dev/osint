# PHASE-2 INGEST extraction rework — result

**Branch:** `fix/phase2-ingest-extraction` (stacks on Phase-1 edge-vocab/entity-registry + C edge_direction).
**Scope:** the seven tasks in the ratified handoff, with the two corrections (denials → drop, identity →
leave as-is) applied exactly.

## What changed (files)

- **`backend/chanakya/ingest/extract.py`** — the bulk of the work:
  - **Enum narrowing (task 1).** `RelationMention.relation` is now a plain `str`; the allowed values are
    injected into the tool schema at build time from `EdgeLaneIndex.extractor_edges()` via the new
    `_constrain_relation_enum()` (called in `extract_document`). The hardcoded 19-value `EdgeTypeName`
    literal + its dead `_EDGE_TYPE_SET` are removed. Identity/evidence/derived edges are no longer
    assertable through the `relations` slot.
  - **Write-time re-lane + endpoint recovery (task 2) + provenance rule (task 3).** New `_Emitter.relation()`
    method. The emitter now tracks a per-document `name -> entity_type` map (populated by `entity()`), so a
    relation's endpoints are typed from the entities the same document emitted; structural transforms pass
    types directly. Both-typed → `relane()` (name + orientation); one-typed → `edge_direction.reversed_for_types()`
    (orientation only, as-stated predicate kept); neither-typed → keep as-stated + tier-3 `_endpoint_typing`
    flag. Rejected endpoints → a tier-3 `_rejected_relation` note on the subject node, never an edge.
    Re-laned claims carry `_as_stated_predicate` + verbatim `source_quote` + `_relane_reason`.
  - **Denials dropped (task 4).** The prose `denials` loop and the social `negations` loop no longer emit
    triples. Zero denial-derived edges / `unknown` nodes.
  - **Identity untouched (task 5).** `same-as`/`distinct-from` from `aka`/`designators`/`aliases`/`distinctions`
    still emit verbatim via `triple()` (the raw path — never re-laned).
  - **Imagery gaps (task 6).** `transform_imagery_geoint` mints a `known_gap` node **only** when a
    `missing_slot` is stated, keyed by the slot (never the verbose sentence). No slot ⇒ no node.
  - **Structural transforms (task 7).** Customs types consignee/shipper as `trading_org` (not
    `manufacturer`), and mints a `contract_import_event` node + `exported-by`→shipper / `imported-by`→consignee
    edges (deterministic role projection, emitted verbatim). Tender mints `interceptor_stockpile` /
    `techdata_authority` nodes from two new optional schema fields — **nodes only, no `sustained-by`**.
- **`backend/chanakya/edge_direction.py`** — added the public `reversed_for_types(predicate, subj_type,
  obj_type, rules)` (the partial-typing orientation helper), refactored to share `_orientation_score`.
- **`config/ontology.yaml`** — added the `trading_org` node type (ING-3). No edge references it → no
  domain/range collision.
- **Tests** — `backend/tests/ingest/test_extract.py` updated (customs → `trading_org` + import node/edges;
  social negation → no edge). New `backend/tests/ingest/test_phase2_relane.py` (12 tests) covering enum
  narrowing, re-lane + provenance, backwards/rejected/untypable relations, denials, identity, imagery gaps,
  and the tender sustainment nodes.

## Decisions that leaned on a guiding principle

1. **Denials are dropped, not retained as negative-polarity claims.** *Principle:* the graph must not be
   polluted with junk (RCA ING-1); "record it, drawn nowhere" is preferred but only if possible.
   *Rejected alternative:* keep the negation as a negative Triple. *Why rejected:* `view/pipeline.py` draws
   **every** triple as an edge (no polarity filter) and mints `unknown` nodes from edge endpoints, so a
   retained negation would still create junk. The task's sanctioned fallback ("drop entirely if retaining
   would create a junk node") applies. No consumer reads denials, so nothing is lost downstream.
2. **Customs role-edges (`exported-by`/`imported-by`) are emitted verbatim, NOT re-laned.** *Principle:*
   re-lane normalizes unreliable *LLM verbs*; a deterministic structural projection is not an LLM assertion.
   *Rejected alternative:* route them through `relane()` with `trading_org` endpoints. *Why rejected:* the
   ontology ranges these edges at contract→manufacturer / contract→unit, so `relane(contract, trading_org)`
   would **reject** them; and broadening both edges' `to` to include `trading_org` would create a
   `(contract, trading_org)` **collision** in `EdgeLaneIndex` (breaks `test_no_endpoint_collisions`). The
   role *is* the edge; the generic `trading_org` endpoint is intentional (shell→end-user linking is RESOLVE's).
3. **A rejected relation is recorded as a tier-3 note on the subject node.** *Principle:* provenance is not
   optional — "do not drop the provenance." *Rejected alternative:* emit the rejected triple flagged (mirror
   the old `_offontology` flag-but-emit). *Why rejected:* that still draws an ad-hoc-predicate edge, which the
   task forbids. Known limitation: the note rides in the tier-3 bag, which `dedup` excludes from its
   signature, so through the full lane it can merge into an un-noted restatement of the same subject. The
   primary guarantee (no ad-hoc edge, no `unknown` node) holds regardless; rejected relations are rare.
4. **`trading_org` added as a config node type, not hardcoded.** *Principle:* config-driven & extensible.
   Reserves `manufacturer` for real OEMs; gives RESOLVE a clean shell-org starting type (ING-3).
5. **Tender sustainment captured via two new all-optional schema fields.** *Principle:* schema-flexible,
   extract-what-is-stated, transform-by-fixed-table (never keyword-inference over raw strings). Maps cleanly
   to the declared `interceptor_stockpile` / `techdata_authority` node types.

## Deliberately deferred (out of this task's lane)

- **Identity rendering / consumption → Phase 3.** View-side "don't draw `same-as` as a knowledge edge" and
  RESOLVE-side "consume aliases as source-weighted merge/veto" are Phase-3. INGEST keeps emitting the
  sourced identity claims (verified they still emit).
- **`sustained-by` and `based-at` → derived, not INGEST.** `sustained-by` is SCORE's Phase-4 rollup (nodes
  only here). No `based-at` transform added: no corpus doc states a unit stationed at a site, so a
  deterministic `based-at` would require inventing the unit (that edge is RESOLVE-derived, Phase 3).
- **Re-recording the frozen `claims/*.json`** — needs API keys + is non-deterministic; a separate follow-up.
  All validation here is via unit tests over synthetic filled-dicts (the transforms are pure functions).

## Test results

- `backend/tests/ingest` + `backend/tests/test_ontology.py`: **247 passed, 4 skipped**.
- Full backend suite: **568 passed, 6 skipped** (1 pre-existing httpx deprecation warning, unrelated).
- `ruff check` clean on the changed files; `mypy` shows only pre-existing errors (third-party stub gaps +
  the pre-existing `_emit` `str`→`Literal` args, untouched by this change).

---

## Follow-up: ING-8 (imagery co-load) + ING-7 (real per-doc dates) — DONE

Same branch (`fix/phase2-ingest-extraction`), separate pass over the two items the section above listed as
deferred. No corpus/`claims/*.json` re-record — that keyed step is still separate and still needs API keys.

### What changed (files)

- **`backend/chanakya/schemas/claim.py`** (`SourceRegistryEntry`) — two new optional fields:
  - `images: list[str] = []` — repo-relative sibling frame(s) for a citation whose primary payload is
    prose (a GEOINT `.txt` beside its `.png`). A list, not a single pointer, for generality.
  - `report_date: str | None = None` — ISO `YYYY-MM-DD`, the date the document *itself* states. Populated
    only from a verbatim, unambiguous statement; left unset otherwise (see audit table below).
- **`config/sources.yaml`** — `images` added for the 9 sources with a sibling `.png` on disk (verified via
  `ls corpus/scenarios/hq9p_primary/docs/*.png`); `report_date` added for 24 of the 53 sources (see table).
  A doc-comment block explains both fields and points here for the audit trail.
- **`backend/chanakya/ingest/seed.py`** (`_extract_source`):
  - New `_report_time_for(entry)` — builds an `ExactDate(iso_date=entry.report_date, boundary_source=
    "explicit")` when `report_date` is set, else `None`. Threaded as `report_time` into every
    `extract_document` / `read_image_document` call the source makes (previously only `ingest_time` was
    passed — `report_time` was silently dropped even though both downstream functions already accepted it).
  - New `_merge_chunks(chunks)` — namespaces + flattens the claims from **multiple** extraction calls for
    one source (text lane + N co-loaded images) before `dedup_within_doc`/`assign_claim_ids`. This is the
    same chunk-prefix-then-remap logic `lane._extract_doc_claims` already runs for the live path (needed
    because provisional claim ids are only unique *within* one extraction call — concatenating two calls'
    output unprefixed risks a premises/targets remap collision). Verified functionally identical to the
    live lane's own logic; not extracted into a shared module to keep this change scoped to `seed.py` only.
  - `_extract_source` now: resolves `report_time` once; for a `.png` citation, runs the VLM lane alone (as
    before, now also carrying `report_time`); for a text citation, runs the text lane **and then** loops
    `entry.images`, running `imagery.read_image_document` on each sibling frame — mirroring exactly how the
    live (keyed) lane feeds co-located frames via `DocInput.images` in `lane.py`. A GEOINT doc's prose
    write-up is never dropped in favour of its image, or vice versa — both extraction calls' claims survive
    into the bundle.
  - `extract_corpus`'s per-source dispatch, scenario filter, and stale-bundle pruning are unchanged.
- **`backend/tests/ingest/test_seed.py`** — 3 new tests (all offline/scripted, no API key):
  1. `test_coloaded_image_runs_both_text_and_vlm_lane` — a source with a `.txt` citation + `images`
     pointer yields claims with `extraction.method` in `{"llm", "vlm"}` (both lanes ran), the VLM claim is
     a subject-blind `observation` carrying `image_fingerprint`, and claim ids stay collision-free.
  2. `test_report_date_flows_to_report_time_on_every_claim` — a `report_date="2022-03-14"` source yields
     `report_time.iso_date == "2022-03-14"` on every claim (text lane **and** co-loaded image lane).
  3. `test_unset_report_date_yields_no_report_time` — no `report_date` ⇒ `report_time is None` on every
     claim (the anti-fabrication check).

### Decisions that leaned on a guiding principle

1. **`report_date` is `str | None` (plain ISO string), not a `DateValue`.** *Principle:* config-driven,
   no magic — the registry is hand-authored YAML; a bare `"YYYY-MM-DD"` string is what a human types and
   audits, and `_report_time_for` is the single, obvious place that promotes it to the typed `ExactDate`
   INGEST already uses everywhere else. *Rejected alternative:* store a `DateValue` directly in the
   registry. *Why rejected:* would require YAML authors to spell a discriminated-union shape (`kind:
   exact`, `boundary_source: explicit`, …) by hand for a field whose only legitimate value is "the day this
   document states, or nothing" — more surface for a typo to silently become a fabricated date.
2. **Month/year-only mastheads are left `report_date`-unset, never rounded to a day.** *Principle:* the
   non-negotiable — "never invent, infer, or approximate" a date; a fabricated date is disqualifying. Many
   corpus docs carry only an issue masthead ("October 2021", "Issue dated: May 2021") with no day. Rounding
   to the 1st (or any day) would be a fabrication dressed as data. *Rejected alternative:* accept a
   `YYYY-MM` partial and let `report_time` carry a `LabelDate`. *Why rejected:* the task spec fixed the
   registry field's format at ISO `YYYY-MM-DD`; broadening it is an ontology/schema change beyond this
   task's scope and was not asked for — flagged here rather than done silently.
3. **A header-stated year combined with a body-stated day-month (no year on that sentence) is left unset.**
   E.g. `d16_adversary_denial`'s thread header says "May 2025 update" and body text says "forwarded to me
   yesterday (13 May)" — a plausible 2025-05-13 requires reading two separate sentences together and one
   inferential step ("yesterday" vs. "today"). *Principle:* the same non-negotiable — a value assembled by
   inference is not "the document literally states." *Rejected alternative:* combine the two literal
   fragments into one date. *Why rejected:* too easily reads as the system quietly manufacturing precision
   the source doesn't unambiguously offer; left null and flagged in the table instead (7 sources hit this:
   d16, cd06, cd07, cd08, cd09, cd13, cd17 — see table for the specific reasoning per source).
4. **A multi-post/multi-entry document (a compiled social thread, a NOTAM bulletin, a multi-line-item
   customs manifest) uses the *first explicit date stated, read top-to-bottom*, when the document has no
   single self-declared "report date."** *Principle:* determinism/reproducibility — a mechanical,
   content-order rule that any future re-audit reproduces identically, rather than a per-doc judgment call
   about "the most representative" date. Applied to d08, d12, d13, d20, ce02, ce03, cd05 (first
   `OPKC`-relevant NOTAM). *Rejected alternative:* use the chronologically-earliest or -latest date
   mentioned anywhere in the doc. *Why rejected:* both require scanning and ranking every date in the doc
   (more surface for error) and "latest" in particular risks picking up a later reply/correction rather
   than the artifact's own dateline.
5. **A compiled/generated-extract document (a customs manifest, a re-indexed IGM compilation) uses its own
   stated `Generated:` timestamp over any individual line item's `Filing Date:`.** Applied to
   `d05_customs_manifest` (`Generated: 25-NOV-2020`) and `cs03_stale_customs` (`Generated: 04-03-2017`).
   *Principle:* `report_date` means "when **this document** reported," not "when the earliest/latest fact
   inside it happened" (that's `event_time`'s job, already handled per-transform, untouched here).
   *Note:* `cs03`'s `Generated:` date (04-03-2017) precedes some of its own listed `Filing Date:` entries
   (11–27 March 2017) — chronologically odd, but it is what the document literally states, and the doc is
   explicitly a "stale"/re-indexed compilation by design; not corrected or second-guessed.
6. **`cd04_civ_electronics`'s `Manifest Filed: 07/11/2021` is left unset — genuinely ambiguous format.**
   The rest of the same doc uses unambiguous `DD-MON-YYYY` (`19-JUL-2021`) and a `DD/MM/YYYY` table
   (`20/04/2021`), but neither convention resolves whether `07/11` means 7-Nov or 11-Jul, and the two
   readings disagree with each other on plausibility (11-Jul precedes the doc's stated arrival date; 7-Nov
   doesn't). *Principle:* the non-negotiable again — guessing the higher-plausibility reading is still a
   guess. Left null and flagged rather than picked.
7. **`cd17_academic_radar`'s explicit `received`/`revised`/`accepted` manuscript dates were not used as
   `report_date`**, even though `accepted March 19, 2018` is a fully-qualified date. *Principle:* avoid a
   judgment call passing as a stated fact — the doc's own masthead date is month/year-only ("May 2018"),
   and picking one of three explicit-but-different candidate dates to stand in for "report date" is an
   editorial choice, not a transcription. Left null (this is chaff; costs nothing functionally).

### ING-8 — sources with a co-located image pointer (9)

Verified on disk via `ls corpus/scenarios/hq9p_primary/docs/*.png` — matches the handoff's expected list
exactly:

`d07_sat_confirm_karachi`, `d08_social_sighting`, `d10_sat_cloud_gap`, `d11_recycled_image`,
`d12_reshare_a`, `d13_reshare_b`, `d17_rawalpindi_2021`, `d17b_withheld_gap`, `d18_rahwali_pass1`.

**Note (surfaced, not acted on):** `hq9p_chaff/docs/` also has 3 sibling `.png` files (`ce01_reshare_c`,
`ce02_reshare_d`, `ce03_reshare_e` — the same "recycled parade photo" reshare family as d11–d13). The
handoff and this task scoped ING-8 to the 9 `hq9p_primary` docs specifically; the chaff siblings were left
un-co-loaded rather than silently included. Flagging for the orchestrator/DATA-C to decide whether the
chaff reshares should also get `images` pointers in a follow-up (they're deliberately "same recycled photo,
different repost" chaff, so co-loading them would add VLM `observation` claims but presumably no new
corroboration signal — a call for whoever owns chaff-scenario design intent, not INGEST alone).

### ING-7 — full date audit (one row per source, all 53)

`report_date stamped` / verbatim source line the date came from, or "NO DATE STATED" / the reason left
null. All primary-scenario dates below directly enable the `based-at@2021` / `as_of=2021-12-31` rewind the
RCA flagged as returning an empty graph (d01, d02, d17 are now available by end-2021).

| source_id | report_date | verbatim source line / reason |
|---|---|---|
| d01_sipri_transfer | 2021-10-11 | `Issue No. 41/2021 \| 11 October 2021 \| Subscription intelligence digest` |
| d02_ispr_induction | 2021-10-14 | `Dated: 14 October 2021` |
| d03_quwa_analysis | NO DATE STATED | masthead is month/year only: `Vol. 41, No. 10 — October 2021` |
| d04_armyrec_ranges | NO DATE STATED | byline is month/year only: `Army Recognition — October 2021` |
| d05_customs_manifest | 2020-11-25 | `Generated:       25-NOV-2020 14:07 (PKT) -- Batch Ref: WB/KHI/2020-11/0447` (doc's own generation date; per-line `Filing Date:` entries are event-level, not used) |
| d06_spares_tender | 2023-02-06 | `Date of Issue: 06 February 2023` |
| d07_sat_confirm_karachi | 2022-03-14 | `DATE OF REPORT: 2022-03-14` |
| d08_social_sighting | 2025-05-09 | `Date: 09 May 2025, 0620 hrs PKT` (POST 1, first dated entry; all 5 posts converge on 09 May 2025) |
| d09_official_routine | 2025-05-09 | `Rawalpindi — 9 May 2025` |
| d10_sat_cloud_gap | 2025-05-10 | `REPORT DATE: 2025-05-10` |
| d11_recycled_image | NO DATE STATED | Reddit thread carries only relative timestamps ("14h", "13h" ago); no absolute date anywhere |
| d12_reshare_a | 2025-05-08 | `—@Raj_DefenceEye · May 8, 2025` (first dated entry; all reposts converge on May 8, 2025) |
| d13_reshare_b | 2025-05-11 | `Date: 2025-05-11 (~14:22 PKT)` (POST 1, first dated entry; thread also contains May 8-dated posts being discussed) |
| d14_stale_holding | NO DATE STATED | masthead is `Weekly Open-Source Update — Issue 34/2016` (issue number/year, no calendar date); doc explicitly notes an internal cable "is undated" |
| d15_globaltimes_aligned | NO DATE STATED | masthead is month/year only: `November 2021 Issue — Procurement & Force Posture Roundup` |
| d16_adversary_denial | NO DATE STATED | thread header is month/year only ("May 2025 update"); body's "(13 May)" is a quote-forwarding reference, not clearly the post's own dateline — see decision 3 above |
| d17_rawalpindi_2021 | 2021-10-14 | `DATE OF REPORT: 14 OCT 2021` |
| d17b_withheld_gap | 2025-06-11 | `Imagery date: 2025-06-11 (single pass, ~1030 local)` |
| d18_rahwali_pass1 | NO DATE STATED | doc explicitly withholds it: `Imagery basis: single commercial EO pass, 2025 (date/time group withheld per source handling)` |
| d19_rahwali_confirm | 2025-04-04 | `Issue dated: 04 April 2025 (reporting period 24–31 March 2025)` |
| d20_supersede_spoof | 2025-06-11 | `Date: 2025-06-11` (POST 1, first dated entry) |
| d21_techdata_authority | NO DATE STATED | masthead is month/year only: `Issue dated June 2022 \| Weekly briefing supplement` |
| d22_deep_tier_supplier | NO DATE STATED | masthead is month/year only: `March 2025` (IISS background paper) |
| d23_cpmiec_false_attribution | NO DATE STATED | masthead is month/year only: `November 2019 Issue` |
| d24_tel_chassis_attribution | NO DATE STATED | masthead is month/year only: `Reference brief, September 2024` |
| d25_hq9_site_fingerprint | NO DATE STATED | reference/recognition PDF; no date stated anywhere in the document |
| ce01_reshare_c | NO DATE STATED | no absolute date/timestamp anywhere in the thread |
| ce02_reshare_d | 2025-05-11 | `@DefenceDekhoo` / `2:47 AM · May 11, 2025` (first dated entry) |
| ce03_reshare_e | 2023-05-07 | `@Defence_Watch_1 · 07 May 2023` (first dated entry; a later reply is dated 12 May 2025 — not used, see decision 4) |
| cd01_s400_china | NO DATE STATED | masthead is month/year only: `Issue dated: May 2021` |
| cd02_india_s400 | 2021-12-28 | `Dated: 28 December 2021` |
| cd03_pak_hq16 | NO DATE STATED | masthead is month/year only: `March 2022 Issue` |
| cd04_civ_electronics | NO DATE STATED | `Manifest Filed:     07/11/2021` — ambiguous DD/MM vs MM/DD, conflicting internal signals — see decision 6 |
| cd05_civ_notam | 2025-04-15 | `CREATED: 15 APR 2025 06:31:00` (first `OPKC`-relevant NOTAM's creation timestamp; doc opens with an apparently unrelated `KHNL`/Honolulu NOTAM line with no year given, not used) |
| cd06_entity_collision_factory | NO DATE STATED | bulletin header is month/year only: `No. 2019-06 (June Issue)`; internal item dates are event dates, not the bulletin's own dateline |
| cd07_unit_collision | NO DATE STATED | month/year only: `Current Organisation (as of September 2020)` / `current to September 2020` |
| cd08_turkey_sam | NO DATE STATED | masthead is month/year only: `Ankara — January 2023 Edition` |
| cd09_generic_iads | NO DATE STATED | masthead is month/year only: `RUSI Occasional Paper, January 2020` |
| cd10_rumor_test | NO DATE STATED | no absolute date stated; only relative references and a caption's "07 Feb 2023" on an unrelated recycled photo |
| cd11_drone_deal | NO DATE STATED | masthead is month/year only: `Volume 14, Issue 33 — August 2024` |
| cd12_turkey_s400 | 2019-07-26 | `Issue dated: 26 July 2019` |
| cd13_saudi_patriot | NO DATE STATED | masthead is month/year only: `September 2021 Edition`; body's "on 3 September" has no year in that sentence — see decision 3 |
| cd14_china_hq22 | NO DATE STATED | masthead is month/year only: `November 2022 issue` |
| cd15_civ_container | 2022-02-07 | `Date/Place of Issue: KARACHI, 07-FEB-2022` (B/L's own issue date; preferred over the separate `SHIPPED ON BOARD DATE: 06-FEB-2022`) |
| cd16_pak_civ_notam | NO DATE STATED | only NOTAM validity windows (`B)`/`C)` effective dates) given; no explicit `CREATED`/issued line |
| cd17_academic_radar | NO DATE STATED | masthead is month/year only (`Vol. 54, No. 3, May 2018`); explicit received/revised/accepted dates exist but none is unambiguously "the report date" — see decision 7 |
| cd18_forwarder_collision | 2021-04-04 | `PLACE AND DATE OF ISSUE:  SHENZHEN, 04 APR 2021` |
| cd19_rumor_missile | NO DATE STATED | no absolute date stated; only relative references and an unrelated repost-tracking date ("07 Jan 2025") |
| cd20_defense_budget | NO DATE STATED | dateline is month/year only: `ISLAMABAD, June 2024` |
| cs01_stale_orbat | 2013-03-11 | `[Note: original page last modified per server header — 11 March 2013 09:47 GMT]` (preferred over the separate `Retrieved via cache: 04 June 2015` line — this doc is deliberately "stale," so the last-modified date is the meaningful one) |
| cs02_stale_deployment | NO DATE STATED | dateline is month/year only: `Islamabad / May 2025`; body's `27 August 2018` commissioning date is an event date, not this article's own report date |
| cs03_stale_customs | 2017-03-04 | `Generated: 04-03-2017 for internal cross-check with FBR WeBOC database` (see decision 5 for the chronological-oddity note) |
| cx01_spoof_karachi | 2025-06-19 | `Posted: 2025-06-19, 11:47 PKT` |

**Totals:** 24 of 53 sources stamped (14 of 26 primary, 10 of 27 chaff); 29 left `report_date`-unset, each
with a stated reason above. Zero dates invented, inferred, or rounded.

### Validation

- `backend/.venv/bin/python -m pytest backend/tests/ingest backend/tests/test_ontology.py -q` →
  **250 passed, 4 skipped** (3 new tests added to the 247 above).
- `backend/.venv/bin/python -m pytest backend/tests -q` → **571 passed, 6 skipped**, 0 failed (no wider
  regression from the two field additions or the `_extract_source` rewiring).
- `ruff check` + `mypy` clean on `chanakya/schemas/claim.py`, `chanakya/ingest/seed.py`.
- Config load sanity: `SourcesConfig.model_validate(yaml.safe_load(open("config/sources.yaml")))` parses
  all 53 entries; 9 carry `images`, 24 carry `report_date` — counts match the tables above exactly.

### Explicitly NOT done here (per task scope)

- `corpus/scenarios/hq9p_primary/claims/*.json` is **not** re-recorded — that keyed re-record (needs
  `GEMINI_API_KEY`/`ANTHROPIC_API_KEY`) is the next, separate step.
- `ingest_time` stays pinned at `FROZEN_INGEST_TIME` (2026-07-19); `claim_available_iso`'s
  ingest-before-report precedence is untouched. The relocation observable's valid-time rewind
  (MONITOR/MON-2, per the handoff) is out of scope here.
- No extraction transforms, the edge re-lane, or anything from 80a8702 was touched.
